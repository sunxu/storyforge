"""CPU-only S0 audit: reuse frozen Sample100 + Pilot20, no model or DB calls.

Default emits only aggregate SAFE. Optional create-only Owner-private case ledger
contains position, model decision, six scores, severe flags and reason categories,
never the original reasons or history/target text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_calibration_sample_cpu as sample
import r60_real1000_pilot20_local_review as review
import r60_real1000_pilot20_packets_cpu as pilot
import r60_real_private_batch as private

SAFE_SCHEMA = "storyforge_r60_real1000_s0_audit_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_real1000_s0_position_ledger_private_v1"
PRIVATE_NAME = "R60_REAL1000_S0_POSITION_LEDGER_PRIVATE.json"
MAX_SAMPLE = 65536


class Hold(ValueError):
    pass


def audit(sample_dir: Path, output_dir: Path) -> tuple[dict, dict]:
    """Validate complete Pilot20 receipts and deterministic Sample100 binding."""
    config, packets, progress = review.get_state(output_dir)
    if progress["processed"] != 20 or progress["remaining"] != 0:
        raise Hold("PILOT20_NOT_COMPLETE_HOLD")
    private.private_dir(sample_dir, create=False)
    frozen = json.loads(private.read_private(sample_dir / sample.FILENAME, MAX_SAMPLE))
    if (
        not isinstance(frozen, dict)
        or set(frozen) != {"schema", "status", "pool_sha256", "method",
                             "cases", "quality_review_performed", "train_admitted"}
        or frozen["schema"] != sample.SCHEMA
        or frozen["status"] != "CALIBRATION_SAMPLE100_PRIVATE__NOT_REVIEWED"
        or frozen["method"] != "stable_sha256_rank_unique_story_per_bin_v1"
        or frozen["quality_review_performed"] is not False
        or frozen["train_admitted"] != 0
        or not isinstance(frozen["pool_sha256"], str)
        or len(frozen["pool_sha256"]) != 64
        or not isinstance(frozen["cases"], list)
        or len(frozen["cases"]) != 100
    ):
        raise Hold("SAMPLE100_SCHEMA_HOLD")
    bins = Counter()
    seen = set()
    last = 0
    for entry in frozen["cases"]:
        if (not isinstance(entry, dict)
                or set(entry) != {"position", "target_char_bin"}
                or type(entry["position"]) is not int
                or not 1 <= entry["position"] <= 1000
                or entry["position"] <= last
                or entry["position"] in seen
                or entry["target_char_bin"] not in sample.QUOTAS):
            raise Hold("SAMPLE100_ENTRY_HOLD")
        last = entry["position"]
        seen.add(last)
        bins[entry["target_char_bin"]] += 1
    if bins != Counter(sample.QUOTAS):
        raise Hold("SAMPLE100_QUOTA_HOLD")

    chosen = []
    for entry in frozen["cases"]:
        position = entry["position"]
        category = entry["target_char_bin"]
        rank = hashlib.sha256(
            b"r60-pilot20-v1\x00" + frozen["pool_sha256"].encode("ascii")
            + b"\x00" + str(position).encode("ascii")
        ).hexdigest()
        chosen.append((rank, position, category))
    selected = []
    for category, needed in pilot.SAMPLE_QUOTAS.items():
        subset = sorted(x for x in chosen if x[2] == category)
        if len(subset) < needed:
            raise Hold("PILOT20_QUOTA_HOLD")
        selected.extend(subset[:needed])
    selected.sort(key=lambda x: x[1])
    expected = [(position, category) for _, position, category in selected]
    observed = [
        (p["sample100_position"], p["target_char_bin"])
        for p in packets["packets"]
    ]
    if expected != observed:
        raise Hold("PILOT20_SAMPLE100_BINDING_HOLD")

    rows = []
    decisions = Counter()
    flags = Counter()
    for position, packet in enumerate(packets["packets"], 1):
        receipt_path = output_dir / review.receipt_name(position)
        conflict_path = output_dir / review.conflict_name(position)
        if receipt_path.is_file() and not receipt_path.is_symlink():
            record = json.loads(private.read_private(receipt_path, review.MAX_RECEIPT_BYTES))
            kind = "VALID_ADVISORY"
            decision = record["decision"]
        elif conflict_path.is_file() and not conflict_path.is_symlink():
            record = json.loads(private.read_private(conflict_path, review.MAX_RECEIPT_BYTES))
            kind = "PASS_BELOW_FLOOR_CONFLICT"
            decision = record["original_decision"]
        else:
            raise Hold("POSITION_MISSING_HOLD")
        if record["position"] != position:
            raise Hold("POSITION_BINDING_HOLD")
        scores = record["scores"]
        severe = record["severe_flags"]
        below = [name for name, floor in private.FLOORS.items() if scores[name] < floor]
        rows.append({
            "pilot_position": position,
            "sample100_position": packet["sample100_position"],
            "target_char_bin": packet["target_char_bin"],
            "review_kind": kind,
            "original_model_decision": decision,
            "scores": scores,
            "severe_flags": severe,
            "below_floor_dimensions": below,
            "independent_reference_status": "NOT_ADJUDICATED",
        })
        if kind == "VALID_ADVISORY":
            decisions[decision] += 1
            flags.update({name: 1 for name, on in severe.items() if on})

    if len(rows) != 20 or dict(decisions) != {k: v for k, v in
            progress["model_decisions_advisory"].items() if v}:
        raise Hold("DECISION_COUNT_HOLD")
    if any(flags[name] != progress["model_severe_flag_counts_advisory"][name]
           for name in private.SEVERE):
        raise Hold("FLAG_COUNT_HOLD")
    if sum(row["review_kind"] == "PASS_BELOW_FLOOR_CONFLICT" for row in rows) != progress["conflict_pending"]:
        raise Hold("CONFLICT_COUNT_HOLD")

    ledger = {
        "schema": PRIVATE_SCHEMA,
        "status": "S0_POSITION_LEDGER__ADVISORY_ONLY",
        "pilot_packets_sha256": config["packets_sha256"],
        "sample100_manifest_sha256": review.sha(
            private.read_private(sample_dir / sample.FILENAME, MAX_SAMPLE)),
        "rows": rows,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "S0_PILOT20_SAMPLE100_AUDIT_PASS__ADJUDICATION_PENDING",
        "pilot20_processed": 20,
        "pilot20_receipts_valid": progress["model_reviewed"],
        "pilot20_conflicts": progress["conflict_pending"],
        "sample100_frozen_cases": 100,
        "sample100_target_char_bins": {name: bins[name] for name in sample.QUOTAS},
        "pilot20_target_char_bins": {name: sum(
            x["target_char_bin"] == name for x in rows) for name in pilot.SAMPLE_QUOTAS},
        "sample100_pilot20_exact_binding": True,
        "model_decisions_advisory": {k: decisions[k] for k in ("PASS", "HOLD", "REJECT")},
        "model_severe_flag_counts_advisory": {k: flags[k] for k in private.SEVERE},
        "independent_reference_reviews": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "model_inference_calls": 0,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }
    return safe, ledger


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--private-report-dir", type=Path)
    args = p.parse_args()
    try:
        safe, ledger = audit(args.sample_dir, args.output_dir)
        if args.private_report_dir is not None:
            if args.private_report_dir.exists() or args.private_report_dir.is_symlink():
                raise Hold("REPORT_EXISTS_HOLD")
            private.private_dir(args.private_report_dir, create=True)
            private.write_new(args.private_report_dir / PRIVATE_NAME, review.canonical(ledger))
            safe["private_ledger_written"] = True
        else:
            safe["private_ledger_written"] = False
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never expose private error text
        code = str(exc) if isinstance(exc, Hold) else "S0_INPUT_OR_BINDING_HOLD"
        if not code.isascii() or len(code) > 80:
            code = "S0_INPUT_OR_BINDING_HOLD"
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "S0_AUDIT_HOLD",
            "reason_code": code,
            "database_accessed": False, "model_inference_calls": 0,
            "gpu_job_started": False, "private_values_emitted": False,
            "quality_v1_admitted": 0, "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only V1/V2/V3 verified crosswalk and create-only private candidate audit.

Never calls models, touches DB/GPU, or promotes Gold/Train. Re-verifies
every frozen V1 record, V2 record and V3 record via the existing validators.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_v2_priority_replay as v2
import r60_real1000_v3_consistent_replay as v3
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_real1000_crosswalk_private_v1"
SAFE = "storyforge_r60_real1000_crosswalk_safe_v1"
FILENAME = "R60_REAL1000_V123_CROSSWALK_PRIVATE.json"
MAX_REPORT = 900_000


class Hold(ValueError):
    pass


def _valid_decision(review: dict) -> str:
    if review["decision"] not in ("PASS", "HOLD", "REJECT"):
        raise Hold("DECISION_UNSUPPORTED_HOLD")
    ai.parse_model_response({
        k: review[k]
        for k in ("decision", "scores", "severe_flags", "reason_cn")
    })
    return review["decision"]


def _apply(cases: list[dict], v1: list[dict], v2_rows: list[dict],
           v3_rows: list[dict], v2_selected: list[dict],
           v3_queue: list[dict]) -> dict:
    if len(cases) != 1000 or len(v1) != 1000 or len(v2_selected) != 237:
        raise Hold("CROSSWALK_SCOPE_HOLD")
    merged = {}
    for i, (case, record) in enumerate(zip(cases, v1), 1):
        if (record["position"] != i or
                record["case_key"] != case["case_key"] or
                record["history_messages_sha256"] !=
                case["history_messages_sha256"] or
                record["assistant_target_sha256"] !=
                case["assistant_target_sha256"]):
            raise Hold("V1_IDENTITY_HOLD")
        sides = {}
        for review in record["reviews"]:
            side = review["reviewer_key"].removeprefix("ai-model-")
            if side not in ("a", "b") or side in sides:
                raise Hold("V1_SIDE_DUPLICATE_HOLD")
            sides[side] = {
                "source": "V1", "decision": _valid_decision(review),
                "source_receipt_sha256": record["receipt_sha256"],
            }
        merged[i] = {
            "position": i, "case_key": case["case_key"],
            "history_messages_sha256": case["history_messages_sha256"],
            "assistant_target_sha256": case["assistant_target_sha256"],
            "v1_receipt_sha256": record["receipt_sha256"],
            "sides": sides,
        }
    for index, record in enumerate(v2_rows):
        item = v2_selected[index]
        position = item["position"]
        side = item["missing_slots"][0]["side"]
        if record["position"] != position or record["side"] != side:
            raise Hold("V2_CROSSWALK_POSITION_HOLD")
        if side in merged[position]["sides"]:
            raise Hold("V2_OVERWRITES_V1_HOLD")
        if record["status"] == "TECHNICAL_HOLD":
            continue
        merged[position]["sides"][side] = {
            "source": "V2", "decision": _valid_decision(record["result"]),
            "source_receipt_sha256": record["receipt_sha256"],
        }
    for index, record in enumerate(v3_rows):
        item = v3_queue[index]
        position = item["position"]
        side = item["side"]
        if (record["position"] != position or record["side"] != side
                or record["v1_receipt_sha256"] !=
                merged[position]["v1_receipt_sha256"]):
            raise Hold("V3_CROSSWALK_POSITION_HOLD")
        if side in merged[position]["sides"]:
            raise Hold("V3_OVERWRITES_EARLIER_VALID_REVIEW_HOLD")
        if record["status"] == "TECHNICAL_HOLD":
            continue
        merged[position]["sides"][side] = {
            "source": "V3", "decision": _valid_decision(record["result"]),
            "source_receipt_sha256": record["receipt_sha256"],
        }
    counts = Counter()
    provenance = Counter()
    candidates = []
    noncandidate_counts = Counter()
    for position, row in merged.items():
        sides = row["sides"]
        if (len(sides) == 2 and
                all(entry["decision"] == "PASS" for entry in sides.values())):
            counts["dual_pass_candidate"] += 1
            provenance["+".join(sides[s]["source"] for s in ("a", "b"))] += 1
            candidates.append({
                k: row[k] for k in (
                    "position", "case_key", "history_messages_sha256",
                    "assistant_target_sha256", "v1_receipt_sha256"
                )
            } | {"side_evidence": sides})
        elif len(sides) == 2:
            counts["two_valid_not_dual_pass"] += 1
            noncandidate_counts["+".join(
                sides[s]["decision"] for s in ("a", "b"))] += 1
        elif len(sides) == 1:
            counts["one_valid"] += 1
        elif not sides:
            counts["neither_valid"] += 1
        else:
            raise Hold("CROSSWALK_SIDE_OVERFLOW_HOLD")
    if sum(counts.values()) != 1000:
        raise Hold("CROSSWALK_TOTAL_HOLD")
    return {
        "schema": SCHEMA,
        "candidate_count": len(candidates),
        "outcome_counts": dict(sorted(counts.items())),
        "dual_pass_provenance": dict(sorted(provenance.items())),
        "noncandidate_decisions": dict(sorted(noncandidate_counts.items())),
        "entries": candidates,
        "independence_verified": False,
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "world_isolation_verified": False,
        "gold_promoted": False,
        "train_admitted": 0,
    }


def inspect(old_dir: Path, plan_dir: Path, v2_dir: Path,
            v3_dir: Path, output_dir: Path, *, write: bool) -> dict:
    if (output_dir.parent != private.BASE
            or not output_dir.name.startswith("r60-real1000-v123-crosswalk-")
            or output_dir.is_symlink() or output_dir in (
                old_dir, plan_dir, v2_dir, v3_dir)
            or (write and output_dir.exists())):
        raise Hold("CROSSWALK_OUTPUT_PATH_HOLD")
    with batch.expand.locked(v3_dir):
        old, cases, v3_queue, progress = v3._inspect(
            v3_dir, old_dir, plan_dir, v2_dir)
        if (progress["reviewed_slots"] != progress["planned_slots"]
                or progress["remaining_slots"] != 0):
            raise Hold("V3_NOT_COMPLETE_HOLD")
        old2, cases2, selected, v2_progress = v2._inspect(
            v2_dir, old_dir, plan_dir)
        if old2 != old or cases2 != cases:
            raise Hold("CROSSWALK_SOURCE_DRIFT_HOLD")
        v1_rows = [
            json.loads(private.read_private(
                old_dir / batch.receipt_name(i), batch.MAX_CASE_BYTES))
            for i in range(1, 1001)
        ]
        v2_rows = [
            json.loads(private.read_private(
                v2_dir / v2.receipt_name(i), v2.MAX_RECEIPT))
            for i in range(1, v2_progress["reviewed_slots"] + 1)
        ]
        v3_rows = [
            json.loads(private.read_private(
                v3_dir / v3.receipt_name(i), v3.MAX_RECEIPT))
            for i in range(1, progress["reviewed_slots"] + 1)
        ]
        report = _apply(
            cases, v1_rows, v2_rows, v3_rows, selected, v3_queue)
    safe = {
        "schema": SAFE,
        "status": ("CROSSWALK_PRIVATE_REPORT_SAVED__NO_ADMISSION"
                   if write else "CROSSWALK_PREFLIGHT_PASS__NO_FILES"),
        "cases_total": 1000,
        "v2_verified_receipts": len(v2_rows),
        "v3_verified_receipts": len(v3_rows),
        "candidate_dual_pass": report["candidate_count"],
        "outcome_counts": report["outcome_counts"],
        "dual_pass_provenance": report["dual_pass_provenance"],
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "world_isolation_verified": False,
        "reviewer_independence_verified": False,
        "gold_promoted": False, "train_admitted": 0,
        "private_values_emitted": False,
        "model_requests": 0, "gpu_started": False,
        "database_modified": False,
    }
    if write:
        private.private_dir(output_dir, create=True)
        blob = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n").encode()
        if len(blob) > MAX_REPORT:
            raise Hold("CROSSWALK_REPORT_OVERSIZE_HOLD")
        private.write_new(output_dir / FILENAME, blob)
    return safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--old-dir", type=Path, required=True)
    p.add_argument("--plan-dir", type=Path, required=True)
    p.add_argument("--v2-dir", type=Path, required=True)
    p.add_argument("--v3-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--write-private-report", action="store_true")
    args = p.parse_args()
    try:
        result = inspect(
            args.old_dir, args.plan_dir, args.v2_dir,
            args.v3_dir, args.output_dir, write=args.write_private_report)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        code = str(exc)
        if (type(exc) not in {
            Hold, v2.Hold, v3.Hold, ai.Hold, batch.Hold, private.Hold
        } or not re.fullmatch(r"[A-Z][A-Z0-9_]{3,79}", code)):
            code = "CROSSWALK_LOCAL_RUNTIME_HOLD"
        print(json.dumps({
            "schema": SAFE, "status": "CROSSWALK_HOLD",
            "reason_code": code, "model_requests": 0,
            "private_values_emitted": False,
            "gpu_started": False, "train_admitted": 0,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

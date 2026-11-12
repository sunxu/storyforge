"""Prepare S1 independent blind packets from frozen Pilot20 on Owner Mac.

CPU-only, no network, no inference. Never place Claude decisions/scores/reasons
in the independent reviewer packet. Store the case-position crosswalk separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot_review
import r60_real1000_s0_audit_cpu as s0
import r60_real_private_batch as private

BLIND_SCHEMA = "storyforge_r60_real1000_s1_blind20_private_v1"
CROSSWALK_SCHEMA = "storyforge_r60_real1000_s1_blind20_crosswalk_private_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_s1_blind20_prepare_safe_v1"
BLIND_FILENAME = "R60_S1_BLIND20_INPUT_PRIVATE.json"
CROSSWALK_FILENAME = "R60_S1_BLIND20_OWNER_CROSSWALK_PRIVATE.json"


class Hold(ValueError):
    pass


def prepare(sample_dir: Path, review_dir: Path) -> tuple[dict, dict, dict]:
    """Verify S0 and emit separate blind source and Owner-only index map."""
    safe, _ledger = s0.audit(sample_dir, review_dir)
    config, packets, progress = pilot_review.get_state(review_dir)
    if (
        safe["status"] != "S0_PILOT20_SAMPLE100_AUDIT_PASS__ADJUDICATION_PENDING"
        or progress["processed"] != 20
        or progress["independent_reference_reviews"] != 0
    ):
        raise Hold("S0_GATE_HOLD")
    digest = config["packets_sha256"]
    ranked = []
    for entry in packets["packets"]:
        position = entry["pilot_position"]
        rank = hashlib.sha256(
            b"r60-s1-blind20-v1\x00" + digest.encode("ascii")
            + b"\x00" + str(position).encode("ascii")
        ).hexdigest()
        ranked.append((rank, position, entry))
    ranked.sort(key=lambda x: (x[0], x[1]))
    blind_cases = []
    crosswalk = []
    for blind_index, (_, original, entry) in enumerate(ranked, 1):
        blind_id = f"B{blind_index:03d}"
        payload = {
            "history_messages": entry["history_messages"],
            "assistant_target": entry["assistant_target"],
        }
        source_sha = pilot_review.sha(pilot_review.canonical(payload))
        blind_cases.append({
            "blind_id": blind_id,
            "history_messages": entry["history_messages"],
            "assistant_target": entry["assistant_target"],
            "reference_status": "NOT_ADJUDICATED",
        })
        crosswalk.append({
            "blind_id": blind_id,
            "pilot_position": original,
            "sample100_position": entry["sample100_position"],
            "case_payload_sha256": source_sha,
        })
    blind = {
        "schema": BLIND_SCHEMA,
        "status": "S1_BLIND20_INPUT_READY__NO_REFERENCE_REVIEWS",
        "review_instructions": {
            "history_scope": "THREE_PRIOR_MESSAGES_ONLY",
            "judge": "INDEPENDENT_OF_CLAUDE_MODEL_ADVISORY",
            "dimensions": list(private.FLOORS),
            "severe_flags": list(private.SEVERE),
            "decision_values": ["PASS", "HOLD", "REJECT"],
            "requirements": [
                "Judge only visible three-message history and assistant target",
                "Do not infer missing original System or world configuration",
                "HOLD if there is insufficient evidence for a serious allegation",
                "Support serious flags with precise available text evidence",
                "Do not automatically admit PASS into training",
            ],
        },
        "cases": blind_cases,
    }
    mapping = {
        "schema": CROSSWALK_SCHEMA,
        "status": "S1_OWNER_CROSSWALK_PRIVATE__SEALED",
        "pilot_packets_sha256": digest,
        "blind_input_sha256": pilot_review.sha(pilot_review.canonical(blind)),
        "entries": crosswalk,
        "model_advisory_excluded_from_blind": True,
    }
    report = {
        "schema": SAFE_SCHEMA,
        "status": "S1_BLIND20_PACKETS_READY__INDEPENDENT_REVIEW_PENDING",
        "cases_prepared": len(blind_cases),
        "unique_blind_ids": len({x["blind_id"] for x in blind_cases}),
        "crosswalk_entries": len(crosswalk),
        "model_advisory_excluded": True,
        "independent_reference_reviews": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }
    return report, blind, mapping


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--blind-dir", type=Path, required=True)
    p.add_argument("--crosswalk-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        if (args.blind_dir == args.crosswalk_dir
                or args.blind_dir.exists() or args.blind_dir.is_symlink()
                or args.crosswalk_dir.exists() or args.crosswalk_dir.is_symlink()):
            raise Hold("OUTPUT_EXISTS_OR_OVERLAP_HOLD")
        report, blind, mapping = prepare(args.sample_dir, args.review_dir)
        private.private_dir(args.blind_dir, create=True)
        private.write_new(args.blind_dir / BLIND_FILENAME,
                          pilot_review.canonical(blind))
        private.private_dir(args.crosswalk_dir, create=True)
        private.write_new(args.crosswalk_dir / CROSSWALK_FILENAME,
                          pilot_review.canonical(mapping))
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never echo private data or paths
        code = str(exc) if isinstance(exc, Hold) else "S1_INPUT_OR_BINDING_HOLD"
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "S1_BLIND20_PREPARE_HOLD",
            "reason_code": code,
            "model_inference_calls": 0, "database_accessed": False,
            "gpu_job_started": False, "private_values_emitted": False,
            "quality_v1_admitted": 0, "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

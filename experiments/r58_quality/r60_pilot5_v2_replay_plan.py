"""Create-only offline Pilot5 v2 failed-side replay plan; NO model calls.

The plan never includes private story content, reviewer reasons, endpoint
credentials, or model output. It binds to frozen v1 receipts and cannot alter
them. Executing the plan requires a separate future reviewed workflow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import r60_real_quality_batch as quality
import r60_real_private_batch as private

PLAN_NAME = "R60_PILOT5_V2_REPLAY_PLAN_PRIVATE.json"
SCHEMA = "storyforge_r60_pilot5_v2_replay_plan_private_v1"
SAFE = "storyforge_r60_pilot5_v2_replay_plan_safe_v1"
PILOT5 = 5
ALLOWED_FAILURES = frozenset({
    "MODEL_JSON_INVALID", "QUALITY_FLOOR_DECISION_INCONSISTENT",
})


class Hold(ValueError):
    pass


def prepare(quality_dir: Path, output_dir: Path) -> dict:
    summary = {
        "schema": SAFE, "status": "PILOT5_V2_REPLAY_PLAN_HOLD",
        "failed_slots": 0, "planned_positions": 0,
        "model_requests": 0, "gpu_started": False,
        "database_modified": False, "train_admitted": 0,
        "private_values_emitted": False,
    }
    try:
        if output_dir.exists() or output_dir.is_symlink():
            raise Hold("OUTPUT_ALREADY_EXISTS")
        # Full production-level frozen pool integrity and immutable v1 receipts.
        original = quality.inspect(quality_dir)
        if original["cases_reviewed"] != PILOT5:
            raise Hold("PILOT5_REVIEW_COUNT_HOLD")
        config = quality.validate_config(quality_dir)
        cases, pool_hash = quality.frozen_pool(Path(config["source"]))
        if pool_hash != config["pool_sha256"]:
            raise Hold("SOURCE_POOL_MISMATCH_HOLD")
        planned = []
        for index in range(1, PILOT5 + 1):
            case = cases[index - 1]
            receipt = json.loads(private.read_private(
                quality_dir / quality.receipt_name(index),
                quality.MAX_CASE_BYTES,
            ))
            signed = {k: v for k, v in receipt.items()
                      if k != "receipt_sha256"}
            if (receipt.get("receipt_sha256") != private.digest(signed)
                    or receipt.get("case_key") != case["case_key"]):
                raise Hold("RECEIPT_MISMATCH_HOLD")
            # A failed slot is a missing review, never a HOLD/REJECT verdict.
            present = {v.get("reviewer_key", "").removeprefix("ai-model-")
                       for v in receipt["reviews"]}
            missing = [side for side in ("a", "b") if side not in present]
            failures = receipt["attempt_holds"]
            if len(missing) != len(failures):
                raise Hold("FAILED_SLOT_COUNT_HOLD")
            if any(f not in ALLOWED_FAILURES for f in failures):
                raise Hold("UNEXPECTED_FAILED_SLOT_HOLD")
            # v1 persisted attempt_holds without reviewer-side association.
            # For two failed sides, identical codes need no correspondence.
            # For one failed side, its sole code is unambiguous.
            if len(missing) == 2 and len(set(failures)) != 1:
                raise Hold("AMBIGUOUS_FAILED_SIDE_HOLD")
            for side, failure in zip(missing, failures):
                planned.append({
                    "position": index,
                    "side": side,
                    "original_failure": failure,
                    "model_id": config["model_" + side],
                    "protocol": config.get("protocol_" + side, "openai-chat"),
                    "original_receipt_sha256": receipt["receipt_sha256"],
                    "history_messages_sha256": case["history_messages_sha256"],
                    "assistant_target_sha256": case["assistant_target_sha256"],
                    "status": "REPLAY_NOT_AUTHORIZED",
                })
        if len(planned) != 3:
            raise Hold("EXPECTED_THREE_FAILED_SLOTS_HOLD")
        manifest = {
            "schema": SCHEMA, "pool_sha256": pool_hash,
            "quality_batch_config_digest": private.digest(config),
            "original_receipt_count": PILOT5,
            "original_v1_preserved": True,
            "source_rechecked": True,
            "reviewer_independence_not_proven": True,
            "training_authorized": False,
            "model_requests_performed": 0,
            "slots": planned,
        }
        private.private_dir(output_dir, create=True)
        # Create-only 0600 write; v1 files are never written.
        private.write_new(output_dir / PLAN_NAME,
                          json.dumps(manifest, ensure_ascii=False,
                                     sort_keys=True).encode("utf-8") + b"\n")
        summary["status"] = "PILOT5_V2_REPLAY_PLAN_PREPARED__NO_REQUEST"
        summary["failed_slots"] = len(planned)
        summary["planned_positions"] = len({v["position"] for v in planned})
    except (ValueError, OSError, KeyError, IndexError, TypeError):
        # Fail closed: private data and arbitrary exception strings are NEVER logged.
        summary["status"] = "PILOT5_V2_REPLAY_PLAN_HOLD"
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    status = prepare(args.quality_dir, args.output_dir)
    print(json.dumps(status, sort_keys=True))
    return 0 if status["status"] == "PILOT5_V2_REPLAY_PLAN_PREPARED__NO_REQUEST" else 42


if __name__ == "__main__":
    raise SystemExit(main())

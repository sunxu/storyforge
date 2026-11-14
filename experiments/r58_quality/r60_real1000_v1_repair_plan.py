"""Offline, immutable REAL1000 V1 priority-and-repair plan.

No provider calls, no database or GPU. Validates all V1 receipts before
writing a create-only Owner-private plan. Prints aggregate SAFE counts only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_real1000_v1_repair_plan_private_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_v1_repair_plan_safe_v1"
NAME = "R60_REAL1000_V1_REPAIR_PLAN_PRIVATE.json"
MAX_PLAN_BYTES = 1_000_000
EXPECTED = 1000
SIDES = ("a", "b")


class Hold(ValueError):
    pass


def _decide(record: dict, case: dict) -> tuple[str, list[dict]]:
    """Return priority class and failed-side assignments with source binding."""
    by_side = {
        review["reviewer_key"].removeprefix("ai-model-"): review
        for review in record["reviews"]
    }
    if set(by_side) - set(SIDES) or len(by_side) != len(record["reviews"]):
        raise Hold("REVIEW_SIDE_INTEGRITY_HOLD")
    missing = [side for side in SIDES if side not in by_side]
    # Reason codes are not side-labelled in V1 if both reviews failed.
    if len(missing) != len(record["attempt_holds"]):
        raise Hold("MISSING_SLOT_INTEGRITY_HOLD")

    if not missing:
        if record["quality_reason_code"] == "INDEPENDENCE_NOT_ATTESTED":
            priority = "READY_DUAL_PASS_NEEDS_ATTESTATION"
        elif record["quality_decision"] == "REJECT":
            priority = "EXISTING_REJECT_REVIEW"
        else:
            priority = "DUAL_VALID_OTHER_REVIEW"
    elif len(missing) == 2:
        priority = "BOTH_MISSING_LOW_PRIORITY"
    else:
        counterpart = next(iter(by_side.values()))
        if (counterpart["decision"] == "PASS"
                and not any(counterpart["severe_flags"].values())
                and all(counterpart["scores"][dimension] >= floor
                        for dimension, floor in private.FLOORS.items())):
            priority = "SINGLE_PASS_REPAIR_FIRST"
        elif (counterpart["decision"] == "REJECT"
              or any(counterpart["severe_flags"].values())):
            priority = "SINGLE_REJECT_DEFER"
        else:
            priority = "SINGLE_OTHER_DEFER"

    assignments = []
    for side in missing:
        assignments.append({
            "side": side,
            "reason_code": (record["attempt_holds"][0]
                            if len(missing) == 1 else
                            "UNASSIGNED_TWO_FAILURES"),
            "case_key": case["case_key"],
            "history_messages_sha256": case["history_messages_sha256"],
            "assistant_target_sha256": case["assistant_target_sha256"],
        })
    return priority, assignments


def build(cases: list[dict], records: list[dict], pool_sha: str) -> dict:
    if len(cases) != EXPECTED or len(records) != EXPECTED:
        raise Hold("FROZEN_1000_REQUIRED")
    priorities = Counter()
    slots = Counter()
    plans = []
    for position, (case, record) in enumerate(zip(cases, records), 1):
        if record.get("position") != position:
            raise Hold("POSITION_INTEGRITY_HOLD")
        if record.get("pool_sha256") != pool_sha:
            raise Hold("POOL_IDENTITY_HOLD")
        if (record.get("case_key") != case["case_key"]
                or record.get("history_messages_sha256") !=
                case["history_messages_sha256"]
                or record.get("assistant_target_sha256") !=
                case["assistant_target_sha256"]):
            raise Hold("CASE_IDENTITY_HOLD")
        priority, assignments = _decide(record, case)
        priorities[priority] += 1
        for assignment in assignments:
            slots[assignment["side"]] += 1
        plans.append({
            "position": position,
            "case_key": case["case_key"],
            "assistant_target_sha256": case["assistant_target_sha256"],
            "history_messages_sha256": case["history_messages_sha256"],
            "priority": priority,
            "original_quality_decision": record["quality_decision"],
            "original_quality_reason_code": record["quality_reason_code"],
            "original_receipt_sha256": record["receipt_sha256"],
            "missing_slots": assignments,
        })

    # Explicit separate queues: no attempt to retry all slots blindly.
    priority_order = {
        "READY_DUAL_PASS_NEEDS_ATTESTATION": 0,
        "SINGLE_PASS_REPAIR_FIRST": 1,
        "DUAL_VALID_OTHER_REVIEW": 2,
        "SINGLE_OTHER_DEFER": 3,
        "SINGLE_REJECT_DEFER": 4,
        "EXISTING_REJECT_REVIEW": 5,
        "BOTH_MISSING_LOW_PRIORITY": 6,
    }
    plans.sort(key=lambda row: (priority_order[row["priority"]],
                                row["position"]))
    return {
        "schema": SCHEMA,
        "pool_sha256": pool_sha,
        "cases_total": EXPECTED,
        "source_kind": "IMMUTABLE_DUAL_REVIEW_V1",
        "train_admitted": 0,
        "promoted_to_gold": False,
        "priorities": dict(sorted(priorities.items())),
        "missing_slots_by_side": dict(sorted(slots.items())),
        "entries": plans,
    }


def _safe(plan: dict, *, status: str) -> dict:
    return {
        "schema": SAFE_SCHEMA,
        "status": status,
        "cases_total": plan["cases_total"],
        "priority_counts": plan["priorities"],
        "missing_slots_by_side": plan["missing_slots_by_side"],
        "missing_slots_total": sum(plan["missing_slots_by_side"].values()),
        "model_requests": 0,
        "private_values_emitted": False,
        "database_modified": False,
        "gpu_started": False,
        "train_admitted": 0,
        "gold_promoted": False,
    }


def execute(old_dir: Path, output_dir: Path, *, write: bool) -> dict:
    private.private_dir(old_dir, create=False)
    if (output_dir.parent != private.BASE
            or not output_dir.name.startswith("r60-real1000-v1-repair-plan-")
            or output_dir.is_symlink()
            or old_dir == output_dir
            or (write and output_dir.exists())):
        raise Hold("PRIVATE_PLAN_OUTPUT_PATH_HOLD")
    with batch.expand.locked(old_dir):
        config = batch.validate_config(old_dir)
        cases, pool_sha = batch.frozen_pool(Path(config["source"]))
        if pool_sha != config["pool_sha256"]:
            raise Hold("SOURCE_DRIFT_HOLD")
        summary = batch.inspected_records(old_dir, config, cases, pool_sha)
        if summary["cases_reviewed"] != EXPECTED:
            raise Hold("V1_REVIEW_INCOMPLETE_HOLD")
        records = [
            json.loads(private.read_private(
                old_dir / batch.receipt_name(i), batch.MAX_CASE_BYTES))
            for i in range(1, EXPECTED + 1)
        ]
        plan = build(cases, records, pool_sha)
    if not write:
        return _safe(plan, status="REPAIR_PLAN_PREFLIGHT_PASS__NO_FILES")
    private.private_dir(output_dir, create=True)
    blob = (json.dumps(plan, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")
    if len(blob) > MAX_PLAN_BYTES:
        raise Hold("PLAN_SIZE_LIMIT_HOLD")
    # One create-only private file; do not echo its contents to stdout.
    target = output_dir / NAME
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(blob)
        handle.flush()
        os.fsync(handle.fileno())
    return _safe(plan, status="REPAIR_PLAN_SAVED__NO_MODEL_REQUEST")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--write-private-plan", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args.old_dir, args.output_dir,
                                 write=args.write_private_plan),
                         sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "REPAIR_PLAN_HOLD",
            "model_requests": 0, "private_values_emitted": False,
            "train_admitted": 0, "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

"""R58 Gold192 scoped exclusion: validate private queue and write SAFE receipt only."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from legacy_gold_target_reuse import (
    SCHEMA,
    canonical,
    private_file,
    safe_reason,
)

ALLOWED = {
    "CONTEXT_EQUIVALENCE_UNVERIFIED",
    "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND",
    "WORLD_OR_TARGET_IDENTITY_HOLD",
}
EXCLUDED = "WORLD_OR_TARGET_IDENTITY_HOLD"


def inspect_scope(tasks_path, queue_path):
    tasks = {}
    with open(tasks_path, encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            case_id = row.get("case_id")
            if (row.get("schema") != SCHEMA or not isinstance(case_id, str)
                    or not case_id or case_id in tasks
                    or row.get("quality_v1_admitted") is not False
                    or row.get("training_authorized") is not False
                    or not isinstance(row.get("story_uuid"), str)
                    or not isinstance(row.get("target_text"), str)
                    or not isinstance(row.get("messages"), list)
                    or hashlib.sha256(row["target_text"].encode("utf-8")).hexdigest()
                    != row.get("target_sha256")
                    or hashlib.sha256(canonical(row["messages"])).hexdigest()
                    != row.get("input_messages_sha256")):
                raise ValueError("SCOPE_TASK_INVALID")
            tasks[case_id] = row
            if len(tasks) > 100000:
                raise ValueError("SCOPE_COUNT_INVALID")
    states = {}
    with open(queue_path, encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            case_id, reason = row.get("case_id"), row.get("reason_code")
            if (not isinstance(case_id, str) or not case_id or case_id in states
                    or reason not in ALLOWED or set(row) != {"case_id", "reason_code"}):
                raise ValueError("SCOPE_QUEUE_INVALID")
            states[case_id] = reason
            if len(states) > 100000:
                raise ValueError("SCOPE_COUNT_INVALID")
    if set(tasks) != set(states):
        raise ValueError("SCOPE_SET_MISMATCH")
    counts = Counter(states.values())
    if (len(tasks) != 195 or counts[EXCLUDED] != 3
            or counts["CONTEXT_EQUIVALENCE_UNVERIFIED"] != 105
            or counts["HISTORICAL_EVIDENCE_NOT_FULLY_BOUND"] != 87):
        raise ValueError("SCOPE_EXPECTED_COUNTS_MISMATCH")
    return {
        "schema": "r58_gold192_scoped_exclusion_safe_v1",
        "status": "GOLD192_SCOPE_VALIDATED__QUALITY_HOLD",
        "frozen_original_gold_count": 195,
        "scoped_candidate_count": 192,
        "excluded_world_identity_unresolved": 3,
        "gold108_basic_evidence_bound": 105,
        "gold87_evidence_pending": 87,
        "excluded_case_status": "EXCLUDED_WORLD_ID_UNRESOLVED",
        "source_frozen_gold_modified": False,
        "private_candidate_artifact_written": False,
        "scope_receipt_only": True,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-tasks", type=Path, required=True)
    parser.add_argument("--private-queue", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        tasks = private_file(args.private_tasks, root)
        queue = private_file(args.private_queue, root)
        if tasks.resolve() == queue.resolve():
            raise ValueError("SCOPE_INPUTS_NOT_DISTINCT")
        result = inspect_scope(tasks, queue)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error) in {
            "SCOPE_TASK_INVALID", "SCOPE_QUEUE_INVALID", "SCOPE_COUNT_INVALID",
            "SCOPE_SET_MISMATCH", "SCOPE_EXPECTED_COUNTS_MISMATCH",
            "SCOPE_INPUTS_NOT_DISTINCT",
        } else safe_reason(error)
        print(json.dumps({
            "schema": "r58_gold192_scoped_exclusion_safe_v1",
            "status": "GOLD192_SCOPE_INVALID__HOLD",
            "reason_code": code,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

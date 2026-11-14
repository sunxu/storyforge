"""Read-only REAL1000 339-candidate identity and duplication preflight.

Never uses R50 datasets or claims cross-world isolation. Does not write files,
call providers, touch DB/GPU, or promote Gold/Train.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import r60_real1000_v3_consistent_replay as v3
import r60_real1000_v123_crosswalk as crosswalk
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_real1000_candidate_identity_safe_v1"


class Hold(ValueError):
    pass


def audit(cases: list[dict], report: dict) -> dict:
    if len(cases) != 1000 or report.get("candidate_count") != 339:
        raise Hold("CANDIDATE_COUNT_OR_SOURCE_HOLD")
    entries = report.get("entries")
    if not isinstance(entries, list) or len(entries) != 339:
        raise Hold("CANDIDATE_ENTRIES_HOLD")
    positions, case_keys, message_ids = set(), set(), set()
    targets = defaultdict(list)
    history_targets = defaultdict(list)
    stories = defaultdict(list)
    sessions = defaultdict(list)
    for entry in entries:
        pos = entry.get("position")
        if type(pos) is not int or not 1 <= pos <= 1000 or pos in positions:
            raise Hold("DUPLICATE_OR_INVALID_POSITION_HOLD")
        positions.add(pos)
        case = cases[pos - 1]
        if (entry.get("case_key") != case.get("case_key")
                or entry.get("assistant_target_sha256") !=
                case.get("assistant_target_sha256")
                or entry.get("history_messages_sha256") !=
                case.get("history_messages_sha256")):
            raise Hold("CANDIDATE_SOURCE_IDENTITY_HOLD")
        key = case["case_key"]
        source = case.get("source")
        if (not isinstance(source, dict)
                or not isinstance(source.get("story_id"), str)
                or not isinstance(source.get("session_id"), str)
                or not isinstance(source.get("assistant_message_id"), str)):
            raise Hold("CANDIDATE_SOURCE_FIELDS_HOLD")
        aid = source["assistant_message_id"]
        if key in case_keys or aid in message_ids:
            raise Hold("DUPLICATE_CASE_OR_MESSAGE_HOLD")
        case_keys.add(key)
        message_ids.add(aid)
        targets[case["assistant_target_sha256"]].append(pos)
        history_targets[(
            case["history_messages_sha256"],
            case["assistant_target_sha256"]
        )].append(pos)
        stories[source["story_id"]].append(pos)
        sessions[(source["story_id"], source["session_id"])].append(pos)
    duplicate_target_groups = [p for p in targets.values() if len(p) > 1]
    duplicate_pair_groups = [
        p for p in history_targets.values() if len(p) > 1
    ]
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_IDENTITY_PREFLIGHT_PASS__NO_ADMISSION",
        "candidate_count": len(entries),
        "unique_case_keys": len(case_keys),
        "unique_assistant_message_ids": len(message_ids),
        "unique_story_count": len(stories),
        "unique_story_session_count": len(sessions),
        "stories_with_multiple_candidates": sum(
            len(p) > 1 for p in stories.values()),
        "max_candidates_per_story": max(map(len, stories.values())),
        "same_target_hash_groups": len(duplicate_target_groups),
        "same_target_hash_extra_cases": sum(
            len(p) - 1 for p in duplicate_target_groups),
        "same_history_and_target_hash_groups": len(duplicate_pair_groups),
        "same_history_and_target_hash_extra_cases": sum(
            len(p) - 1 for p in duplicate_pair_groups),
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "world_isolation_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "gold_promoted": False,
        "model_requests": 0,
        "private_values_emitted": False,
        "database_modified": False,
        "gpu_started": False,
    }


def execute(old_dir: Path, plan_dir: Path, v2_dir: Path,
            v3_dir: Path, audit_dir: Path) -> dict:
    private.private_dir(audit_dir, create=False)
    with batch.expand.locked(v3_dir):
        old, cases, _queue, progress = v3._inspect(
            v3_dir, old_dir, plan_dir, v2_dir)
        if progress["remaining_slots"] != 0:
            raise Hold("V3_NOT_COMPLETE_HOLD")
        report_path = audit_dir / crosswalk.FILENAME
        report = json.loads(private.read_private(
            report_path, crosswalk.MAX_REPORT))
        # Reconstruct the entire crosswalk from frozen V1/V2/V3 evidence;
        # distrust report count or digest claims until exact equality.
        cfg, cases2, selected, v2status = crosswalk.v2._inspect(
            v2_dir, old_dir, plan_dir)
        if cfg != old or cases2 != cases:
            raise Hold("SOURCE_DRIFT_HOLD")
        v1_rows = [
            json.loads(private.read_private(
                old_dir / batch.receipt_name(i), batch.MAX_CASE_BYTES))
            for i in range(1, 1001)
        ]
        v2_rows = [
            json.loads(private.read_private(
                v2_dir / crosswalk.v2.receipt_name(i),
                crosswalk.v2.MAX_RECEIPT))
            for i in range(1, v2status["reviewed_slots"] + 1)
        ]
        v3_rows = [
            json.loads(private.read_private(
                v3_dir / v3.receipt_name(i), v3.MAX_RECEIPT))
            for i in range(1, progress["reviewed_slots"] + 1)
        ]
        expected = crosswalk._apply(
            cases, v1_rows, v2_rows, v3_rows, selected, _queue)
        if report != expected:
            raise Hold("PRIVATE_CANDIDATE_REPORT_DRIFT_HOLD")
        return audit(cases, report)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--old-dir", type=Path, required=True)
    p.add_argument("--plan-dir", type=Path, required=True)
    p.add_argument("--v2-dir", type=Path, required=True)
    p.add_argument("--v3-dir", type=Path, required=True)
    p.add_argument("--audit-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        result = execute(
            args.old_dir, args.plan_dir, args.v2_dir,
            args.v3_dir, args.audit_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        reason = str(exc)
        if (type(exc) not in {Hold, private.Hold, batch.Hold,
                             v3.Hold, crosswalk.Hold}
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{3,79}", reason)):
            reason = "CANDIDATE_IDENTITY_LOCAL_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "CANDIDATE_IDENTITY_HOLD",
            "reason_code": reason, "model_requests": 0,
            "private_values_emitted": False, "train_admitted": 0,
            "gpu_started": False, "database_modified": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

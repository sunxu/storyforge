"""Read-only R50 original50 vs Common2 exact story/session/message ID isolation.

No source IDs, story text, hashes, private paths, or exception contents are emitted.
Exact-ID disjointness is not semantic world/alias isolation, final heldout seal,
nor authorization to train.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.r60_r50_original50_complement_cpu import jsonl
    from scripts.r60_r50_freeze_status_projection_cpu import read_private_json
except ModuleNotFoundError:
    from r60_r50_original50_complement_cpu import jsonl
    from r60_r50_freeze_status_projection_cpu import read_private_json

SCHEMA = "storyforge_r60_r50_common2_exact_source_isolation_safe_v1"
RECOVERY_SCHEMA = "storyforge_r60_qd20_common2_supabase_recovery_private_v1"
RECOVERY_STATUS = "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT"


def source_id(value):
    if type(value) is not str or not value or len(value) > 256:
        raise ValueError("SOURCE_ID_SCHEMA_HOLD")
    return value


def r50_sources(rows):
    stories, sessions, messages = set(), set(), set()
    for row in rows:
        stories.add(source_id(row.get("source_story_id")))
        sessions.add(source_id(row.get("source_session_id")))
        ids = row.get("history_message_ids")
        if type(ids) is not list or not ids:
            raise ValueError("R50_HISTORY_SCHEMA_HOLD")
        for value in ids:
            messages.add(source_id(value))
        messages.add(source_id(row.get("cutoff_message_id")))
    return stories, sessions, messages


def common2_sources(manifest):
    if (manifest.get("schema") != RECOVERY_SCHEMA
            or manifest.get("status") != RECOVERY_STATUS
            or manifest.get("train_admitted") != 0
            or type(manifest.get("cases")) is not list
            or len(manifest["cases"]) != 2):
        raise ValueError("COMMON2_RECOVERY_CONTRACT_HOLD")
    stories, sessions, messages, targets = set(), set(), set(), set()
    for item in manifest["cases"]:
        if type(item) is not dict or item.get("last_three_exact_source_match") is not True:
            raise ValueError("COMMON2_SOURCE_ATTESTATION_HOLD")
        stories.add(source_id(item.get("story_id")))
        sessions.add(source_id(item.get("session_id")))
        target = source_id(item.get("assistant_message_id"))
        if target in targets:
            raise ValueError("DUPLICATE_TARGET_HOLD")
        targets.add(target)
        hist = item.get("history_messages")
        if type(hist) is not list or not hist:
            raise ValueError("COMMON2_HISTORY_SCHEMA_HOLD")
        if item.get("message_count_before_target") != len(hist):
            raise ValueError("COMMON2_HISTORY_COUNT_HOLD")
        case_ids = []
        for msg in hist:
            if type(msg) is not dict:
                raise ValueError("COMMON2_HISTORY_SCHEMA_HOLD")
            case_ids.append(source_id(msg.get("id")))
        if len(set(case_ids)) != len(case_ids) or target in case_ids:
            raise ValueError("COMMON2_HISTORY_IDS_HOLD")
        messages.update(case_ids)
        messages.add(target)
    if len(stories) != 2 or len(sessions) != 2:
        # No assumption that two candidates must have distinct stories/sessions.
        # Each target must, however, be separately identified.
        pass
    return stories, sessions, messages


def audit(r50: Path, common2: Path) -> dict:
    result = {
        "schema": SCHEMA,
        "status": "R50_COMMON2_EXACT_ISOLATION_HOLD",
        "reason_code": "UNVERIFIED",
        "r50_original_sha_verified": False,
        "r50_cases_checked": 0,
        "common2_cases_checked": 0,
        "exact_story_overlap_count": None,
        "exact_session_overlap_count": None,
        "exact_message_overlap_count": None,
        "exact_source_id_disjoint_verified": False,
        "semantic_world_alias_isolation_verified": False,
        "r45_full_source_isolation_verified": False,
        "final_heldout_seal_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        if r50.resolve(strict=False) == common2.resolve(strict=False):
            raise ValueError("SAME_INPUT_HOLD")
        r50_rows = jsonl(r50, 50, "provenance")
        result["r50_original_sha_verified"] = True
        result["r50_cases_checked"] = 50
        cm = read_private_json(common2)
        a_story, a_session, a_msg = r50_sources(r50_rows)
        b_story, b_session, b_msg = common2_sources(cm)
        result["common2_cases_checked"] = 2
        result["exact_story_overlap_count"] = len(a_story & b_story)
        result["exact_session_overlap_count"] = len(a_session & b_session)
        result["exact_message_overlap_count"] = len(a_msg & b_msg)
        disjoint = not any((result["exact_story_overlap_count"],
                            result["exact_session_overlap_count"],
                            result["exact_message_overlap_count"]))
        result["exact_source_id_disjoint_verified"] = disjoint
        result["status"] = (
            "R50_COMMON2_EXACT_KEYS_DISJOINT__SEMANTIC_R45_SEAL_HOLD"
            if disjoint else "R50_COMMON2_EXACT_SOURCE_OVERLAP__TRAIN_HOLD")
        result["reason_code"] = (
            "EXACT_THREE_LEVEL_DISJOINT" if disjoint else "EXACT_OVERLAP_FOUND")
    except Exception as exc:
        known = {
            "SAME_INPUT_HOLD", "SOURCE_ID_SCHEMA_HOLD", "R50_HISTORY_SCHEMA_HOLD",
            "COMMON2_RECOVERY_CONTRACT_HOLD", "COMMON2_SOURCE_ATTESTATION_HOLD",
            "DUPLICATE_TARGET_HOLD", "COMMON2_HISTORY_SCHEMA_HOLD",
            "COMMON2_HISTORY_COUNT_HOLD", "COMMON2_HISTORY_IDS_HOLD",
            "SYMLINK_HOLD", "FILE_MODE_OR_SIZE_HOLD", "FILE_CHANGED_HOLD",
            "ORIGINAL_SHA_HOLD", "ROW_COUNT_HOLD", "ROW_SCHEMA_HOLD",
        }
        result["reason_code"] = (str(exc) if type(exc) is ValueError and
                                 str(exc) in known else "INPUT_FORMAT_OR_RUNTIME_HOLD")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r50-original-provenance", type=Path, required=True)
    parser.add_argument("--common2-recovery", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.r50_original_provenance, args.common2_recovery)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["exact_source_id_disjoint_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())

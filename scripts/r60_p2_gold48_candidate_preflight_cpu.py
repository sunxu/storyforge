"""Offline-only Gold48 candidate artifact preflight. Never confers Owner Freeze.

Reads only create-only Owner-private files from the existing capture adapter.
No database, model calls, training, Git writes, or file creation.
Prints count-only SAFE results. Never prints Story, Session, prompt, reply,
identity, input paths, case IDs, or their hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
from collections import Counter
from itertools import pairwise
from pathlib import Path

SHARED_STATUS = "NEW_RECONSTRUCTED_48_CANDIDATES__NOT_OWNER_FROZEN"
ORIGIN = "PRIOR_20261120_PROVISIONAL_TARGET_IDS_NOT_PRESERVED__NEW_SELECTION"
CONTRACT = "RECONSTRUCTED_EVALUATION_INPUT"
SCHEMAS = {
    "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json":
        "storyforge_r60_gold48_recovered_locators_private_v1",
    "GOLD48_CANDIDATE_PREFIXES_PRIVATE.json":
        "storyforge_r60_gold48_recovered_prefixes_private_v1",
    "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json":
        "storyforge_r60_gold48_recovered_references_private_v1",
}
SAFE = "storyforge_r60_p2_gold48_candidate_preflight_safe_v1"
HEX = set("0123456789abcdef")


class Hold(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Hold(reason)


def sha_utf8(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def is_sha(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def read_0600(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and stat.S_IMODE(info.st_mode) == 0o600
            and 0 < info.st_size <= 80 * 1024 * 1024,
            "OWNER_PRIVATE_FILE_PERMISSION_OR_SIZE_HOLD")
    data = json.loads(path.read_bytes())
    require(isinstance(data, dict), "PRIVATE_DOCUMENT_FORMAT_HOLD")
    return data


def cases_by_id(data, expected_schema):
    require(data.get("schema") == expected_schema
            and data.get("status") == SHARED_STATUS
            and data.get("origin_identity") == ORIGIN
            and data.get("eval_input_contract") == CONTRACT,
            "PACKAGE_CONTRACT_HOLD")
    rows = data.get("cases_PRIVATE")
    require(isinstance(rows, list) and len(rows) == 48,
            "CASE_COUNT_HOLD")
    ids = [r.get("candidate_case_id_PRIVATE") if isinstance(r, dict) else None
           for r in rows]
    require(ids == [f"G48-C{i:02d}" for i in range(1, 49)],
            "CASE_SEQUENCE_HOLD")
    return dict(zip(ids, rows, strict=True))


def evaluate(root):
    require(root.is_dir() and not root.is_symlink()
            and stat.S_IMODE(root.stat().st_mode) == 0o700,
            "OWNER_PRIVATE_DIRECTORY_HOLD")
    bundle = {filename: cases_by_id(read_0600(root / filename), schema)
              for filename, schema in SCHEMAS.items()}
    locators = bundle["GOLD48_CANDIDATE_LOCATORS_PRIVATE.json"]
    prefixes = bundle["GOLD48_CANDIDATE_PREFIXES_PRIVATE.json"]
    references = bundle["GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json"]
    captured = read_0600(root / "GOLD48_CAPTURE_SAFE.json")
    require(captured.get("schema") ==
            "storyforge_r60_p2_gold48_private_recovery_capture_safe_v1"
            and captured.get("status") ==
            "NEW_GOLD48_PRIVATE_CANDIDATES_CAPTURED__NOT_FROZEN"
            and captured.get("case_count") == 48
            and captured.get("original_reference_count") == 48
            and captured.get("request_metadata_unique_count") == 48
            and captured.get("owner_final_gold48_freeze") is False,
            "CAPTURE_SAFE_RECEIPT_HOLD")
    source_counts = Counter()
    source_to_story = {}
    story_to_key = {}
    flagged = Counter()
    seen_prompt, seen_reply, seen_target, seen_request = set(), set(), set(), set()
    sessions = set()
    for case_id in locators:
        loc, pre, ref = locators[case_id], prefixes[case_id], references[case_id]
        messages = pre.get("prefix_messages_PRIVATE")
        reply = ref.get("original_reply_PRIVATE")
        require(isinstance(messages, list) and 3 <= len(messages) <= 40
                and messages[-1].get("role") == "user"
                and isinstance(reply, str) and bool(reply.strip()),
                "HISTORY_PREFIX_OR_REPLY_SHAPE_HOLD")
        require(all(
            isinstance(m, dict) and set(m) == {"role", "content"}
            and m["role"] in ("user", "assistant")
            and isinstance(m["content"], str) and bool(m["content"].strip())
            for m in messages
        ), "PREFIX_MESSAGES_INVALID_HOLD")
        require(all(a["role"] != b["role"]
                    for a, b in pairwise(messages)),
                "PREFIX_ROLE_SEQUENCE_HOLD")
        prefix_hash = sha_utf8(canonical(messages))
        reply_hash = sha_utf8(reply)
        require(pre.get("prefix_sha256_PRIVATE") == prefix_hash
                and loc.get("prefix_sha256_PRIVATE") == prefix_hash
                and ref.get("original_reply_sha256_PRIVATE") == reply_hash
                and loc.get("original_reply_sha256_PRIVATE") == reply_hash,
                "PROMPT_OR_ORIGINAL_SHA_BINDING_HOLD")
        history = pre.get("history_recovery_PRIVATE")
        require(isinstance(history, dict)
                and history.get("history_message_count") == len(messages)
                and history.get("target_sha256") == reply_hash
                and history.get("history_materialized_in_leaf_session") is True
                and isinstance(history.get("history"), list)
                and [{"role":m.get("role"), "content":m.get("content")}
                     for m in history["history"]] == messages,
                "LEDGER_RECOVERY_SOURCE_BINDING_HOLD")
        story = loc.get("story_id_PRIVATE")
        key = loc.get("source_key_PRIVATE")
        session = loc.get("session_id_PRIVATE")
        target = loc.get("assistant_message_id_PRIVATE")
        request = loc.get("request_id_PRIVATE")
        require(all(isinstance(v, str) and bool(v)
                    for v in (story, key, session, target, request))
                and history.get("story_id") == story
                and history.get("session_id") == session
                and history.get("target", {}).get("message_id") == target
                and is_sha(loc.get("source_snapshot_sha256_PRIVATE"))
                and type(loc.get("source_public_revision_PRIVATE")) is int,
                "CASE_SOURCE_IDENTITY_HOLD")
        require((key not in source_to_story or source_to_story[key] == story)
                and (story not in story_to_key or story_to_key[story] == key),
                "SOURCE_KEY_STORY_BIJECTION_HOLD")
        source_to_story[key] = story
        story_to_key[story] = key
        source_counts[key] += 1
        sessions.add((story, session))
        require(prefix_hash not in seen_prompt and reply_hash not in seen_reply
                and target not in seen_target and request not in seen_request,
                "CROSS_CASE_DUPLICATE_HOLD")
        seen_prompt.add(prefix_hash)
        seen_reply.add(reply_hash)
        seen_target.add(target)
        seen_request.add(request)
        if loc.get("exclude_from_42_sensitivity") is True:
            flagged[story] += 1
        else:
            require(loc.get("exclude_from_42_sensitivity") is False,
                    "SENSITIVITY_FLAG_SHAPE_HOLD")
    require(len(source_counts) == 8 and set(source_counts.values()) == {6}
            and len(flagged) == 1 and list(flagged.values()) == [6]
            and len(sessions) == captured.get("session_count")
            and captured.get("flagged_story_case_count") == 6
            and captured.get("primary_count") == 48
            and captured.get("sensitivity_count") == 42,
            "EIGHT_BY_SIX_OR_SENSITIVITY_SCOPE_HOLD")
    return {
        "schema": SAFE,
        "status": "GOLD48_PRIVATE_CANDIDATE_PREFLIGHT_PASS__NOT_FROZEN",
        "case_count": 48,
        "source_count": 8,
        "source_cases_each": 6,
        "session_count": len(sessions),
        "full_prefix_count": 48,
        "original_reference_count": 48,
        "unique_success_request_count": 48,
        "primary_count": 48,
        "sensitivity_count": 42,
        "prior_provisional_48_identity_verified": False,
        "full_reconstructed_system_world_rules_memory_verified": False,
        "owner_gold48_freeze": False,
        "private_values_emitted": False,
        "database_accessed": False,
        "files_modified": False,
        "gpu_started": False,
        "model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.candidate_dir)
    except (Hold, ValueError, TypeError, KeyError, OSError, IndexError):
        result = {
            "schema": SAFE, "status": "HOLD",
            "reason_code": "GOLD48_PRIVATE_CANDIDATE_PREFLIGHT_HOLD",
            "private_values_emitted": False,
            "database_accessed": False,
            "files_modified": False,
            "gpu_started": False,
            "model_calls": 0,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

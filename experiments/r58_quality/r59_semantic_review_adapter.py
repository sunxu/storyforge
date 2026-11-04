"""R59 Pilot8 review input adapter (CPU-only; never performs inference/admission).

Creates an immutable, explicit full-history review materialization for later HF CPU
prompt/token measurement. It does not cut a review history to fit a context
window: a too-long review is HOLD until a separately approved coverage policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

SCHEMA = "storyforge-r59-semantic-review-input-private-v1"
SAFE_SCHEMA = "storyforge-r59-semantic-review-input-safe-v1"
PILOT_SCHEMA = "r59_semantic_pilot8_private_v1"
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
REVIEW_POLICY = "R59_FULL_VISIBLE_HISTORY_SEMANTIC_REVIEW_V1"
MAX_INPUT_BYTES = 160 * 1024 * 1024
REQUIRED_PRIORITIES = {"HIGH_CONTEXT_RISK": 5, "TRUNCATED_CONTEXT_REVIEW": 1, "FULL_HISTORY_REVIEW": 2}


class Hold(ValueError):
    pass


def canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_private(path: Path, max_size: int = MAX_INPUT_BYTES) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise Hold("INPUT_NOT_REGULAR")
    before = path.stat()
    if (not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1 or not 0 < before.st_size <= max_size):
        raise Hold("INPUT_PERMISSIONS_OR_SIZE")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        after = os.fstat(stream.fileno())
        if (after.st_ino, after.st_dev) != (before.st_ino, before.st_dev):
            raise Hold("INPUT_CHANGED")
        raw = stream.read(max_size + 1)
    if len(raw) > max_size:
        raise Hold("INPUT_SIZE")
    return raw


def jsonl(raw: bytes) -> list[dict]:
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeError, ValueError):
        raise Hold("INPUT_JSONL_INVALID") from None
    if not rows or any(not isinstance(r, dict) for r in rows):
        raise Hold("INPUT_JSONL_INVALID")
    return rows


def validate_messages(messages: object) -> bool:
    if not isinstance(messages, list) or len(messages) < 2:
        return False
    if not isinstance(messages[0], dict) or not isinstance(messages[-1], dict):
        return False
    if messages[0].get("role") != "system" or messages[-1].get("role") != "user":
        return False
    if not all(isinstance(x, dict) and set(x) == {"role", "content"}
               and x["role"] in {"system", "user", "assistant"}
               and isinstance(x["content"], str) and x["content"].strip()
               for x in messages):
        return False
    if any(x["role"] == "system" for x in messages[1:]):
        return False
    return all(a["role"] != b["role"] for a, b in zip(messages[1:], messages[2:]))


def make_rows(stage_rows: list[dict], pilot: dict, stage_sha: str, pilot_sha: str):
    if not isinstance(pilot, dict) or pilot.get("schema") != PILOT_SCHEMA:
        raise Hold("PILOT_SCHEMA_INVALID")
    if not isinstance(pilot.get("cases"), list) or len(pilot["cases"]) != 8:
        raise Hold("PILOT_COUNT_INVALID")
    if len(stage_rows) != 72:
        raise Hold("STAGE_COUNT_INVALID")
    index = {}
    for s in stage_rows:
        if (s.get("schema") != STAGE_SCHEMA or s.get("status") != STAGE_STATUS
                or not isinstance(s.get("case_id"), str) or not s["case_id"]
                or s["case_id"] in index):
            raise Hold("STAGE_IDENTITY_OR_STATUS_INVALID")
        index[s["case_id"]] = s
    selected, seen, priorities, stories = [], set(), Counter(), set()
    for i, case in enumerate(pilot["cases"]):
        if not isinstance(case, dict) or case.get("pilot_index") != i:
            raise Hold("PILOT_INDEX_INVALID")
        cid = case.get("case_id")
        if cid in seen or cid not in index or case.get("pilot_status") != "SELECTED_NOT_REVIEWED":
            raise Hold("PILOT_IDENTITY_INVALID")
        seen.add(cid)
        s = index[cid]
        if (case.get("target_sha256") != s.get("target_sha256")
                or case.get("story_id") != s.get("story_id")
                or sha(s["target_text"].encode("utf-8")) != s["target_sha256"]
                or not validate_messages(s.get("messages"))
                or sha(canon(s["messages"])) != s.get("input_messages_sha256")):
            raise Hold("PILOT_STAGE_CONTENT_MISMATCH")
        prio = case.get("review_priority")
        if prio not in REQUIRED_PRIORITIES:
            raise Hold("PILOT_PRIORITY_INVALID")
        history = s["messages"][1:]
        if (len(history) != case.get("retained_history_messages")
                or case.get("assistant_first") is not (history[0]["role"] == "assistant")
                or type(case.get("removed_prefix_messages")) is not int
                or case["removed_prefix_messages"] < 0):
            raise Hold("PILOT_HISTORY_METADATA_MISMATCH")
        priorities[prio] += 1
        stories.add(s["story_id"])
        selected.append({
            "schema": SCHEMA,
            "pilot_index": i,
            "case_id": cid,
            "story_id": s["story_id"],
            "target_sha256": s["target_sha256"],
            "stage_file_sha256": stage_sha,
            "pilot_file_sha256": pilot_sha,
            "source_input_messages_sha256": s["input_messages_sha256"],
            "generic_system_prompt": s["messages"][0]["content"],
            "visible_history": history,
            "target_text": s["target_text"],
            "history_coverage": {
                "scope": "FULL_STAGED_SUFFIX_ONLY",
                "retained_history_messages": len(history),
                "removed_upstream_prefix_messages": case["removed_prefix_messages"],
                "history_origin_verified_from_database": False,
                "historical_world_card_approved": False,
                "context_semantically_verified": False,
            },
            "review_priority": prio,
            "review_policy_version": REVIEW_POLICY,
            "review_decision": None,
            "owner_evidence_created": False,
            "quality_v1_admitted": False,
            "training_authorized": False,
        })
    if dict(priorities) != REQUIRED_PRIORITIES or len(stories) != 6:
        raise Hold("PILOT_COVERAGE_INVALID")
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "R59_PILOT8_FULL_HISTORY_INPUT_BUILT__TOKEN_PREFLIGHT_PENDING",
        "pilot_cases": 8,
        "stories": 6,
        "priority_counts": dict(sorted(priorities.items())),
        "full_staged_suffix_materialized": 8,
        "review_history_truncated_by_adapter": 0,
        "tokenizer_checked": False,
        "semantic_reviews_completed": 0,
        "owner_evidence_created": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return selected, safe


def create_only(path: Path, blob: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def is_inside_git_checkout(path: Path) -> bool:
    """Reject output beneath any checkout, independent of the current cwd."""
    resolved = path.resolve()
    return any((parent / ".git").exists() for parent in (resolved, *resolved.parents))


def run(stage_path: Path, stage_safe_path: Path, pilot_path: Path, output_dir: Path) -> dict:
    raw = read_private(stage_path)
    stage_sha = sha(raw)
    safe_receipt = json.loads(read_private(stage_safe_path, 1024 * 1024))
    if safe_receipt.get("staged_file_sha256") != stage_sha or safe_receipt.get("context_staged") != 72:
        raise Hold("STAGE_RECEIPT_MISMATCH")
    pilot_raw = read_private(pilot_path)
    pilot = json.loads(pilot_raw)
    rows, safe = make_rows(jsonl(raw), pilot, stage_sha, sha(pilot_raw))
    if output_dir.exists() or output_dir.is_symlink() or is_inside_git_checkout(output_dir):
        raise Hold("OUTPUT_INVALID_OR_EXISTS")
    parent = output_dir.parent
    if (parent.is_symlink() or not parent.is_dir()
            or stat.S_IMODE(parent.stat().st_mode) != 0o700):
        raise Hold("OUTPUT_PARENT_PERMISSION_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        payload = b"".join(canon(row) + b"\n" for row in rows)
        safe["private_input_file_sha256"] = sha(payload)
        create_only(output_dir / "R59_SEMANTIC_PILOT8_REVIEW_INPUT_PRIVATE.jsonl", payload)
        create_only(output_dir / "R59_SEMANTIC_PILOT8_REVIEW_INPUT_SAFE.json", canon(safe) + b"\n")
    except BaseException:
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()
        raise
    return safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--staged-jsonl", type=Path, required=True)
    p.add_argument("--staging-safe", type=Path, required=True)
    p.add_argument("--pilot-json", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(run(args.staged_jsonl, args.staging_safe, args.pilot_json, args.output_dir), sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "R59_PILOT8_REVIEW_INPUT_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
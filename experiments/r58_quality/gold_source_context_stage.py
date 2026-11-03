"""Stage verified Supabase Gold contexts for Quality-v1 review, without admission.

Consumes existing Owner-local R59 source-context JSONL and a pinned Owner
system prompt. No database/ledger/network/HF/R50 access. Never manufactures
review decisions, evidence flags, or semantic world identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter
from pathlib import Path

from quality_v1 import canonical, sha

SCHEMA = "storyforge-gold-quality-supabase-source-stage-safe-v1"
MAX_INPUT_BYTES = 160 * 1024 * 1024
MAX_CASES = 192
HEX = re.compile(r"^[0-9a-f]{64}$")
ROLES = {"user", "assistant"}


class StageHold(ValueError):
    pass


def _private_file(path: Path, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise StageHold("SOURCE_NOT_REGULAR")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1 or not 0 < info.st_size <= max_bytes):
        raise StageHold("SOURCE_PERMISSIONS_OR_SIZE")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        after = os.fstat(stream.fileno())
        if (after.st_ino, after.st_dev) != (info.st_ino, info.st_dev):
            raise StageHold("SOURCE_CHANGED")
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise StageHold("SOURCE_TOO_LARGE")
    return raw


def _read_rows(data: bytes):
    try:
        rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise StageHold("SOURCE_JSONL_INVALID") from None
    if not 1 <= len(rows) <= MAX_CASES:
        raise StageHold("SOURCE_COUNT_INVALID")
    return rows


def _history(messages):
    if not isinstance(messages, list) or not messages:
        raise StageHold("HISTORY_EMPTY")
    output = []
    prev = None
    for msg in messages:
        if not isinstance(msg, dict):
            raise StageHold("HISTORY_STRUCTURE_INVALID")
        role = msg.get("role")
        content = msg.get("content")
        if (role not in ROLES or role == prev
                or not isinstance(content, str) or not content.strip()
                or msg.get("status") != "completed"):
            raise StageHold("HISTORY_STRUCTURE_INVALID")
        prev = role
        output.append({"role": role, "content": content})
    if output[-1]["role"] != "user":
        raise StageHold("CURRENT_USER_MISSING")
    return output


def stage_source(rows, system_text: str):
    if not isinstance(system_text, str) or not system_text.strip():
        raise StageHold("SYSTEM_PROMPT_MISSING")
    seen_cases = set()
    seen_targets = set()
    staged = []
    counts = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise StageHold("SOURCE_ROW_INVALID")
        cid = row.get("case_id")
        target = row.get("target_assistant_text")
        digest = row.get("target_sha256")
        if (not isinstance(cid, str) or not cid or cid in seen_cases
                or not isinstance(target, str) or not target.strip()
                or not isinstance(digest, str) or HEX.fullmatch(digest) is None
                or digest in seen_targets or sha(target.encode("utf-8")) != digest):
            raise StageHold("SOURCE_TARGET_IDENTITY_INVALID")
        if (not isinstance(row.get("story_id"), str)
                or not row["story_id"]
                or not isinstance(row.get("session_id"), str)
                or not row["session_id"]):
            raise StageHold("SOURCE_SESSION_IDENTITY_INVALID")
        seen_cases.add(cid)
        seen_targets.add(digest)
        try:
            history = _history(row.get("history"))
        except StageHold as exc:
            # Keep per-case reasons private, never silently discard text.
            counts[str(exc)] += 1
            staged.append({
                "case_id": cid, "status": "SOURCE_STRUCTURE_HOLD",
                "private_reason_code": str(exc),
                "target_sha256": digest,
            })
            continue
        msgs = [{"role": "system", "content": system_text}, *history]
        staged.append({
            "schema": "storyforge-quality-v1-source-staging-private-v1",
            "case_id": cid,
            "story_id": row["story_id"],
            "session_id": row["session_id"],
            "target_sha256": digest,
            "target_text": target,
            "messages": msgs,
            "input_messages_sha256": sha(canonical(msgs)),
            "status": "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
            "world_component_id": None,
            "split": None,
            "reviews": None,
            "evidence": None,
            "source_version_sha256": None,
            "historical_system_prompt_verified": False,
            "historical_exact_replay_required": False,
            "source_context_temporal_verification": "NOT_PROVEN",
            "quality_v1_admitted": False,
        })
        counts["STAGED"] += 1
    staged.sort(key=lambda x: x["case_id"])
    return staged, {
        "schema": SCHEMA,
        "status": "GOLD_SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
        "source_rows": len(rows),
        "context_staged": counts["STAGED"],
        "context_structure_hold": len(rows) - counts["STAGED"],
        "structure_hold_reasons": dict(sorted((k, v) for k, v in counts.items()
                                               if k != "STAGED")),
        "world_component_isolation_verified": False,
        "reviewer_scores_imported": False,
        "historical_exact_replay_required": False,
        "quality_v1_admitted": 0,
        "tokenizer_collator_checked": False,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def _create_only(path: Path, payload: bytes):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload).hexdigest()


def run(context_path: Path, system_path: Path, system_sha256: str,
        output_dir: Path):
    raw = _private_file(context_path, MAX_INPUT_BYTES)
    system_raw = _private_file(system_path, 64 * 1024)
    if hashlib.sha256(system_raw).hexdigest() != system_sha256:
        raise StageHold("SYSTEM_PROMPT_PIN_MISMATCH")
    try:
        system = system_raw.decode("utf-8")
    except UnicodeError:
        raise StageHold("SYSTEM_PROMPT_UTF8_INVALID") from None
    rows, safe = stage_source(_read_rows(raw), system)
    if output_dir.exists() or output_dir.is_symlink():
        raise StageHold("OUTPUT_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise StageHold("OUTPUT_IN_REPO")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise StageHold("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        output = b"".join(canonical(row) + b"\n" for row in rows)
        private_hash = _create_only(
            output_dir / "GOLD_SOURCE_STAGING_PRIVATE.jsonl", output
        )
        safe.update({
            "source_context_file_sha256": hashlib.sha256(raw).hexdigest(),
            "system_prompt_sha256": system_sha256,
            "staged_file_sha256": private_hash,
        })
        _create_only(
            output_dir / "GOLD_SOURCE_STAGING_SAFE.json",
            json.dumps(safe, ensure_ascii=False, sort_keys=True,
                       indent=2).encode("utf-8") + b"\n",
        )
    except BaseException:
        for path in output_dir.iterdir():
            path.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-context-jsonl", required=True, type=Path)
    parser.add_argument("--system-prompt-file", required=True, type=Path)
    parser.add_argument("--system-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not HEX.fullmatch(args.system_sha256):
            raise StageHold("SYSTEM_SHA256_INVALID")
        safe = run(args.source_context_jsonl, args.system_prompt_file,
                   args.system_sha256, args.output_dir)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private input/error messages never emitted
        print(json.dumps({
            "schema": SCHEMA,
            "status": "GOLD_SOURCE_CONTEXT_STAGE_HOLD",
            "quality_v1_admitted": 0,
            "gpu_started": False,
            "training_authorized": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

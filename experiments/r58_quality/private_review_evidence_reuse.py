#!/usr/bin/env python3
"""Verify whether private historical review evidence matches current private tasks.

Offline and read-only. Matching is identity + serialized-input SHA256 + target
SHA256. It does not validate reviewer judgment or grant quality/training admission.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

DEFAULT_MANIFEST_SCHEMA = "r58_gold195_grok_web_manifest_private_v1"
DEFAULT_TASK_SCHEMA = "r58_gold195_six_dimension_review_task_private_v1"
SAFE_SCHEMA = "r58_private_review_evidence_reuse_safe_v1"
DEFAULT_MAX_FILE_BYTES = 128 * 1024 * 1024
DEFAULT_MAX_RECORDS = 100_000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReuseInputError(ValueError):
    """A private input cannot be safely or unambiguously verified."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_private_bytes(path: Path, repo_root: Path, max_bytes: int) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ReuseInputError("PRIVATE_FILE_PATH_INVALID")
    resolved = path.resolve(strict=True)
    root = repo_root.resolve(strict=True)
    if resolved == root or root in resolved.parents:
        raise ReuseInputError("PRIVATE_FILE_INSIDE_REPOSITORY")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ReuseInputError("PRIVATE_PARENT_INVALID")
    if stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise ReuseInputError("PRIVATE_PARENT_PERMISSIONS_INVALID")
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or not 0 < before.st_size <= max_bytes):
        raise ReuseInputError("PRIVATE_FILE_PERMISSIONS_OR_SIZE_INVALID")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ReuseInputError("PRIVATE_FILE_CHANGED_DURING_READ")
        raw = stream.read(max_bytes + 1)
    if len(raw) != before.st_size or len(raw) > max_bytes:
        raise ReuseInputError("PRIVATE_FILE_SIZE_CHANGED_DURING_READ")
    return raw


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReuseInputError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _strict_json_loads(value: str):
    return json.loads(value, object_pairs_hook=_reject_duplicate_keys)


def _read_jsonl(raw: bytes, max_records: int) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReuseInputError("TASKS_NOT_UTF8") from exc
    rows: list[dict[str, Any]] = []
    try:
        for line in text.splitlines():
            if not line.strip():
                continue
            value = _strict_json_loads(line)
            if not isinstance(value, dict):
                raise ReuseInputError("TASK_ROW_NOT_OBJECT")
            rows.append(value)
            if len(rows) > max_records:
                raise ReuseInputError("TASK_RECORD_LIMIT_EXCEEDED")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReuseInputError("TASK_JSONL_INVALID") from exc
    return rows


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _manifest_index(manifest: Any, expected_schema: str, max_records: int):
    if not isinstance(manifest, dict) or manifest.get("schema") != expected_schema:
        raise ReuseInputError("MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("quality_approved") is not False:
        raise ReuseInputError("MANIFEST_APPROVAL_STATE_INVALID")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases or len(cases) > max_records:
        raise ReuseInputError("MANIFEST_CASE_COLLECTION_INVALID")
    by_id: dict[str, dict[str, str]] = {}
    labels: set[str] = set()
    for record in cases:
        if not isinstance(record, dict):
            raise ReuseInputError("MANIFEST_CASE_NOT_OBJECT")
        case_id, label = record.get("case_id"), record.get("label")
        input_hash, target_hash = (
            record.get("input_messages_sha256"), record.get("target_sha256")
        )
        target_text = record.get("target_text")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ReuseInputError("MANIFEST_CASE_ID_INVALID")
        if not isinstance(label, str) or not label.strip() or label in labels:
            raise ReuseInputError("MANIFEST_LABEL_INVALID_OR_DUPLICATE")
        if case_id in by_id:
            raise ReuseInputError("MANIFEST_CASE_ID_DUPLICATE")
        if not _valid_digest(input_hash) or not _valid_digest(target_hash):
            raise ReuseInputError("MANIFEST_DIGEST_INVALID")
        if not isinstance(target_text, str) or not target_text:
            raise ReuseInputError("MANIFEST_TARGET_TEXT_INVALID")
        if sha256_bytes(target_text.encode("utf-8")) != target_hash:
            raise ReuseInputError("MANIFEST_TARGET_DIGEST_MISMATCH")
        labels.add(label)
        by_id[case_id] = {
            "label": label,
            "input_messages_sha256": input_hash,
            "target_sha256": target_hash,
        }
    return by_id


def _task_index(rows: list[dict[str, Any]], expected_schema: str):
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("schema") != expected_schema:
            raise ReuseInputError("TASK_SCHEMA_MISMATCH")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ReuseInputError("TASK_CASE_ID_INVALID")
        if case_id in by_id:
            raise ReuseInputError("TASK_CASE_ID_DUPLICATE")
        messages, target = row.get("messages"), row.get("target_text")
        if not isinstance(messages, list) or not isinstance(target, str) or not target:
            raise ReuseInputError("TASK_CONTENT_SHAPE_INVALID")
        input_hash, target_hash = (
            row.get("input_messages_sha256"), row.get("target_sha256")
        )
        if not _valid_digest(input_hash) or not _valid_digest(target_hash):
            raise ReuseInputError("TASK_DIGEST_INVALID")
        try:
            computed_input = sha256_bytes(canonical_json(messages))
        except (TypeError, ValueError) as exc:
            raise ReuseInputError("TASK_MESSAGES_NOT_CANONICAL_JSON") from exc
        computed_target = sha256_bytes(target.encode("utf-8"))
        if computed_input != input_hash:
            raise ReuseInputError("TASK_INPUT_DIGEST_MISMATCH")
        if computed_target != target_hash:
            raise ReuseInputError("TASK_TARGET_DIGEST_MISMATCH")
        if "review_results" in row and row["review_results"] != []:
            raise ReuseInputError("TASK_ALREADY_HAS_REVIEW_RESULTS")
        if "review_status" in row and row["review_status"] != "UNREVIEWED":
            raise ReuseInputError("TASK_REVIEW_STATUS_NOT_UNREVIEWED")
        if row.get("quality_v1_admitted", False) is not False:
            raise ReuseInputError("TASK_QUALITY_ADMISSION_STATE_INVALID")
        if row.get("training_authorized", False) is not False:
            raise ReuseInputError("TASK_TRAINING_AUTHORIZATION_STATE_INVALID")
        by_id[case_id] = {
            "input_messages_sha256": input_hash,
            "target_sha256": target_hash,
        }
    return by_id


def compare(manifest: Any, task_rows: list[dict[str, Any]], *,
            manifest_schema: str = DEFAULT_MANIFEST_SCHEMA,
            task_schema: str = DEFAULT_TASK_SCHEMA,
            max_records: int = DEFAULT_MAX_RECORDS) -> dict[str, Any]:
    if len(task_rows) > max_records:
        raise ReuseInputError("TASK_RECORD_LIMIT_EXCEEDED")
    historical = _manifest_index(manifest, manifest_schema, max_records)
    current = _task_index(task_rows, task_schema)
    states = Counter()
    for case_id, old in historical.items():
        new = current.get(case_id)
        if new is None:
            states["CASE_ID_NOT_FOUND"] += 1
        else:
            input_changed = (
                old["input_messages_sha256"] != new["input_messages_sha256"]
            )
            target_changed = old["target_sha256"] != new["target_sha256"]
            if input_changed and target_changed:
                states["INPUT_AND_TARGET_HASH_MISMATCH"] += 1
            elif input_changed:
                states["INPUT_MESSAGES_HASH_MISMATCH"] += 1
            elif target_changed:
                states["TARGET_HASH_MISMATCH"] += 1
            else:
                states["EXACT_MATCH"] += 1
    exact = states["EXACT_MATCH"]
    total = len(historical)
    if exact == total:
        status = "EXACT_REUSE_MATCH__NO_QUALITY_ADMISSION"
    elif exact:
        status = "PARTIAL_REUSE_MATCH__MISMATCHES_HOLD"
    else:
        status = "NO_EXACT_REUSE_MATCH__HOLD"
    return {
        "schema": SAFE_SCHEMA,
        "status": status,
        "historical_cases_checked": total,
        "current_tasks_checked": len(current),
        "exact_matches": exact,
        "mismatches": total - exact,
        "case_states": dict(sorted(states.items())),
        "unmatched_current_tasks": len(current) - sum(
            1 for case_id in current if case_id in historical
        ),
        "historical_review_outputs_read": False,
        "reviewer_judgment_revalidated": False,
        "literary_quality_verified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "r50_accessed": False,
        "network_called": False,
        "private_values_emitted": False,
        "files_written": False,
    }


def audit(manifest_path: Path, tasks_path: Path, repo_root: Path, *,
          manifest_schema: str = DEFAULT_MANIFEST_SCHEMA,
          task_schema: str = DEFAULT_TASK_SCHEMA,
          max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
          max_records: int = DEFAULT_MAX_RECORDS) -> dict[str, Any]:
    if manifest_path.resolve(strict=True) == tasks_path.resolve(strict=True):
        raise ReuseInputError("INPUT_FILES_MUST_BE_DISTINCT")
    manifest_raw = _safe_private_bytes(manifest_path, repo_root, max_file_bytes)
    tasks_raw = _safe_private_bytes(tasks_path, repo_root, max_file_bytes)
    try:
        manifest = _strict_json_loads(manifest_raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReuseInputError("MANIFEST_JSON_INVALID") from exc
    rows = _read_jsonl(tasks_raw, max_records)
    return compare(
        manifest, rows, manifest_schema=manifest_schema,
        task_schema=task_schema, max_records=max_records,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--private-manifest", required=True, type=Path)
    parser.add_argument("--private-tasks", required=True, type=Path)
    parser.add_argument("--manifest-schema", default=DEFAULT_MANIFEST_SCHEMA)
    parser.add_argument("--task-schema", default=DEFAULT_TASK_SCHEMA)
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS)
    args = parser.parse_args()
    try:
        if args.max_file_bytes <= 0 or args.max_records <= 0:
            raise ReuseInputError("LIMIT_ARGUMENT_INVALID")
        receipt = audit(
            args.private_manifest, args.private_tasks, args.repo_root,
            manifest_schema=args.manifest_schema, task_schema=args.task_schema,
            max_file_bytes=args.max_file_bytes, max_records=args.max_records,
        )
        code = 0 if receipt["exact_matches"] == receipt["historical_cases_checked"] else 42
    except ReuseInputError as exc:
        receipt = {
            "schema": SAFE_SCHEMA,
            "status": "PRIVATE_REUSE_INPUT_INVALID__HOLD",
            "reason_code": str(exc),
            "historical_cases_checked": 0,
            "current_tasks_checked": 0,
            "exact_matches": 0,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "r50_accessed": False,
            "private_values_emitted": False,
            "files_written": False,
        }
        code = 42
    except OSError:
        receipt = {
            "schema": SAFE_SCHEMA,
            "status": "PRIVATE_REUSE_IO_ERROR__HOLD",
            "reason_code": "PRIVATE_IO_ERROR",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "r50_accessed": False,
            "private_values_emitted": False,
            "files_written": False,
        }
        code = 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

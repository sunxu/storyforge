"""Offline inventory only for Owner R50 protected inputs: NO exclusion claims.

Never emits source IDs, hashes, contents, paths, keys, field names or excerpts.
Requires explicitly selected files; never searches folders or follows symlinks.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

SCHEMA = "storyforge_r60_r50_metadata_inventory_safe_v1"
MAX_BYTES = 12_000_000
MAX_ROWS = 5000


def check_file(path: Path, *, jsonl: bool) -> tuple[int, int]:
    if path.is_symlink():
        raise ValueError("LINK_HOLD")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or not 0 < st.st_size <= MAX_BYTES:
        raise ValueError("FILE_TYPE_OR_SIZE_HOLD")
    if st.st_mode & 0o077:
        raise ValueError("FILE_MODE_HOLD")
    # Refuse file changes during read; O_NOFOLLOW protects final component.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as file:
        before = os.fstat(file.fileno())
        data = file.read(MAX_BYTES + 1)
        after = os.fstat(file.fileno())
    if (len(data) != st.st_size or (st.st_dev, st.st_ino) != (before.st_dev, before.st_ino)
            or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
        raise ValueError("FILE_CHANGED_HOLD")
    if jsonl:
        lines = data.splitlines()
        if not lines or len(lines) > MAX_ROWS:
            raise ValueError("ROW_COUNT_HOLD")
        for line in lines:
            if not line.strip() or not isinstance(json.loads(line), dict):
                raise ValueError("ROW_SCHEMA_HOLD")
        return len(lines), st.st_size
    obj = json.loads(data)
    if not isinstance(obj, (list, dict)):
        raise ValueError("ROOT_SCHEMA_HOLD")
    count = len(obj)
    if count > MAX_ROWS:
        raise ValueError("ROW_COUNT_HOLD")
    return count, st.st_size


def inventory(case_path: Path, provenance_path: Path, exclusion_path: Path) -> dict:
    result = {
        "schema": SCHEMA,
        "status": "R50_METADATA_INVENTORY_HOLD",
        "reason_code": "UNVERIFIED",
        "source_content_emitted": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
    }
    try:
        paths = [case_path, provenance_path, exclusion_path]
        if len({str(p.resolve(strict=False)) for p in paths}) != 3:
            raise ValueError("DUPLICATE_FILE_HOLD")
        counts = [check_file(p, jsonl=(i < 2 or p.suffix.lower() == ".jsonl"))
                  for i, p in enumerate(paths)]
        result.update(
            status="R50_METADATA_FILES_PARSEABLE__COVERAGE_HOLD",
            reason_code="METADATA_STRUCTURE_ONLY",
            cases_file_rows=counts[0][0],
            provenance_file_rows=counts[1][0],
            exclusion_file_entries=counts[2][0],
            all_files_checked=3,
        )
    except Exception as exc:
        allow = {
            "LINK_HOLD", "FILE_TYPE_OR_SIZE_HOLD", "FILE_MODE_HOLD",
            "FILE_CHANGED_HOLD", "ROW_COUNT_HOLD", "ROW_SCHEMA_HOLD",
            "ROOT_SCHEMA_HOLD", "DUPLICATE_FILE_HOLD",
        }
        result["reason_code"] = (
            str(exc) if isinstance(exc, ValueError) and str(exc) in allow
            else "R50_FILE_OR_FORMAT_HOLD"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--exclusion", required=True, type=Path)
    args = parser.parse_args()
    result = inventory(args.cases, args.provenance, args.exclusion)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "R50_METADATA_FILES_PARSEABLE__COVERAGE_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())

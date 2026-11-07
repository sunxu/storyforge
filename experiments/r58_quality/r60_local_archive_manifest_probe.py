"""R60 S3C: local diagnostic archive filename-only inventory.

No file is opened, parsed, hashed, uploaded or changed. SAFE output contains
only totals by archive category and broad date buckets. Not an input proof.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "r60_local_archive_manifest_probe_safe_v1"
FILE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.[A-Za-z0-9_-]+-\d+\.jsonl$")
CATEGORIES = ("abnormal-snapshots", "latency-metrics")
MAX_FILES = 200_000


def inspect(root: Path) -> dict:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("ARCHIVE_ROOT_INVALID")
    counts = {}
    for category in CATEGORIES:
        parent = root / category
        if parent.is_symlink():
            raise ValueError("SYMLINK_CATEGORY_HOLD")
        if not parent.exists():
            counts[category] = {"status": "NOT_PRESENT", "matching_files": 0}
            continue
        if not parent.is_dir():
            raise ValueError("CATEGORY_NOT_DIRECTORY")
        matches = 0
        years = Counter()
        # Not recursively traversing: source archive uses daily JSONL files
        # directly inside each category. Prevent uncontrolled deep scanning.
        with os.scandir(parent) as entries:
            for entry in entries:
                if entry.is_symlink():
                    raise ValueError("SYMLINK_FILE_HOLD")
                if not entry.is_file(follow_symlinks=False):
                    continue
                m = FILE.fullmatch(entry.name)
                if m is None:
                    continue
                matches += 1
                if matches > MAX_FILES:
                    raise ValueError("FILE_LIMIT_EXCEEDED")
                try:
                    import datetime as dt
                    dt.date(int(m[1]), int(m[2]), int(m[3]))
                except ValueError:
                    raise ValueError("INVALID_DATE_IN_FILENAME") from None
                years[m[1]] += 1
        counts[category] = {
            "status": "MANIFEST_ONLY_SCANNED",
            "matching_files": matches,
            "year_file_counts": dict(sorted(years.items())),
        }
    return {
        "schema": SCHEMA,
        "status": "LOCAL_ARCHIVE_FILENAME_INVENTORY_NOT_INPUT_EVIDENCE",
        "categories": counts,
        "files_opened": 0,
        "business_rows_read": 0,
        "private_values_emitted": False,
        "database_modified": False,
        "r50_accessed": False,
        "actual_sent_payload_verified_count": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.archive_root)
    except (ValueError, OSError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in {
            "ARCHIVE_ROOT_INVALID", "SYMLINK_CATEGORY_HOLD",
            "CATEGORY_NOT_DIRECTORY", "SYMLINK_FILE_HOLD",
            "FILE_LIMIT_EXCEEDED", "INVALID_DATE_IN_FILENAME",
        } else "IO_OR_VALIDATION_HOLD"
        result = {"schema": SCHEMA, "status": "LOCAL_ARCHIVE_MANIFEST_HOLD",
                  "reason_code": reason, "private_values_emitted": False,
                  "database_modified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "LOCAL_ARCHIVE_FILENAME_INVENTORY_NOT_INPUT_EVIDENCE" else 2


if __name__ == "__main__":
    sys.exit(main())

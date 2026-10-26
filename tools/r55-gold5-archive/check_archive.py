#!/usr/bin/env python3
"""Read-only, fail-closed verifier for SHA-frozen R55 Gold5 source archive."""

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

MANIFEST = "docs/evidence/R55_GOLD5_ARCHIVED_SOURCE_MANIFEST_20261026.json"
MANIFEST_SHA256 = "f0c788dd34084679db29b9099ef9d2613c3f5aea66fd68e3d82def9c50940bab"
EXPECTED_RECORDS = 30
EXPECTED_SOURCE_FILES = 30
ALLOWED_DIRS = ("scripts/", "tests/", "docs/", "tools/r55-gold5-subtypes/")
REQUIRED_FALSE = (
    "private_stories",
    "private_verdicts",
    "private_mapping",
    "r50_accessed",
    "training_performed",
)


def verify(root: Path) -> None:
    root = root.resolve(strict=True)
    mf = root / MANIFEST
    raw = mf.read_bytes()
    actual_manifest_sha = hashlib.sha256(raw).hexdigest()
    if actual_manifest_sha != MANIFEST_SHA256:
        raise ValueError("source archive manifest SHA256 changed")
    obj = json.loads(raw)
    if obj.get("schema") != "storyforge-r55-gold5-source-archive-v1":
        raise ValueError("unexpected manifest schema")
    if obj.get("scope") != "SOURCE_CODE_TESTS_GUIDES_ONLY":
        raise ValueError("manifest scope is not source-only")
    if obj.get("source_file_count") != EXPECTED_SOURCE_FILES:
        raise ValueError("expected exactly 30 frozen source/docs/tests")
    if obj.get("total_synthetic_tests") != "191/191 PASS":
        raise ValueError("original test receipt mismatch")
    if any(obj.get(k) is not False for k in REQUIRED_FALSE):
        raise ValueError("source-only/no-private/no-training declarations changed")
    records = obj.get("files")
    if not isinstance(records, list) or len(records) != EXPECTED_RECORDS:
        raise ValueError("unexpected source-file manifest record count")
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("non-object source record")
        rel = row.get("path")
        if not isinstance(rel, str) or not rel.startswith(ALLOWED_DIRS):
            raise ValueError("unexpected source path")
        logical = PurePosixPath(rel)
        if logical.is_absolute() or ".." in logical.parts or "." in logical.parts:
            raise ValueError(f"unsafe source path {rel}")
        if rel in seen:
            raise ValueError(f"duplicate source path {rel}")
        seen.add(rel)
        path = root.joinpath(*logical.parts)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError(f"missing, symlink, or escaped archive file: {rel}")
        b = path.read_bytes()
        if not isinstance(row.get("bytes"), int) or len(b) != row["bytes"]:
            raise ValueError(f"byte-length mismatch: {rel}")
        if hashlib.sha256(b).hexdigest() != row.get("sha256"):
            raise ValueError(f"SHA256 mismatch: {rel}")
    print(
        "R55_GOLD5_ARCHIVED_SOURCE_30_SHA256_PASS__SOURCE_ONLY__NO_R50__NO_TRAINING",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        verify(args.repo)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ARCHIVE_VERIFY_FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

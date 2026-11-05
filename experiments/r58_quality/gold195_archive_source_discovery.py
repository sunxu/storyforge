#!/usr/bin/env python3
"""R58 card-source archive inventory: no extraction, no prose output, no training.

Inspect the two pinned Git LFS ZIP objects after an owner-controlled LFS pull.
The result is a SAFE count-only inventory, not card quality certification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

SOURCES = (
    ("gold108_06_15", "06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip",
     "b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb", 65332700),
    ("early_raw_backup", "StoryForge_v02_Pending_Raw_and_Artifact_Backup_20261012.zip",
     "9c24cc762f91e2ced0766ac50ab178b6992958465f7c71f44eeb75c144bfe2a2", 41511118),
)
SOURCE_ROOT = Path("evaluations/v0.2/source-archives")
MAX_NESTED_BYTES = 90_000_000
MAX_FILES = 5000


def digest_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_zip(stream, counts: Counter, depth=0):
    if depth > 3:
        counts["nested_depth_limit"] += 1
        return
    with zipfile.ZipFile(stream) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise ValueError("too many zip entries")
        for item in infos:
            if item.is_dir():
                continue
            counts["file_members"] += 1
            if counts["file_members"] > MAX_FILES:
                raise ValueError("global member limit")
            name = item.filename.replace("\\", "/")
            # Never extract or print file names. Nested ZIP bytes are limited.
            suffix = Path(name).suffix.lower()
            if suffix == ".zip":
                counts["nested_zips"] += 1
                if item.file_size > MAX_NESTED_BYTES:
                    counts["nested_zip_too_large_to_inspect"] += 1
                    continue
                payload = archive.read(item)
                walk_zip(io.BytesIO(payload), counts, depth + 1)
            elif suffix == ".json":
                counts["json_members"] += 1
                if re.search(r"(?:story[-_ ]?cards?|character[-_ ]?cards?|persona)", name, re.I):
                    counts["card_name_candidates"] += 1
            elif suffix == ".jsonl":
                counts["jsonl_members"] += 1
            else:
                counts["other_members"] += 1


def audit(repo_root: Path):
    result = {
        "schema": "r58_archive_card_source_discovery_safe_v1",
        "status": "PINNED_ARCHIVES_INSPECTED__CARD_CONTENT_NOT_APPROVED",
        "sources": {},
        "story_text_emitted": False,
        "card_text_exported": False,
        "r50_accessed": False,
        "training_admitted": 0,
        "gpu_authorized": False,
    }
    for label, name, expected_sha, expected_size in SOURCES:
        path = repo_root / SOURCE_ROOT / name
        if not path.is_file() or path.is_symlink():
            result["status"] = "ARCHIVES_MISSING__HOLD"
            result["sources"][label] = {"status": "NOT_PRESENT"}
            continue
        if path.stat().st_size != expected_size:
            result["status"] = "LFS_OBJECT_NOT_MATERIALIZED_OR_SIZE_MISMATCH__HOLD"
            result["sources"][label] = {"status": "EXPECTED_LFS_ARCHIVE_NOT_PRESENT"}
            continue
        if digest_file(path) != expected_sha:
            result["status"] = "ARCHIVE_SHA256_MISMATCH__HOLD"
            result["sources"][label] = {"status": "DIGEST_MISMATCH"}
            continue
        counts = Counter()
        walk_zip(path, counts)
        result["sources"][label] = {"status": "PINNED_ZIP_READABLE", "counts": dict(sorted(counts.items()))}
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = audit(args.repo_root)
    except Exception:
        result = {"schema": "r58_archive_card_source_discovery_safe_v1",
                  "status": "UNSAFE_OR_CORRUPT_ARCHIVE__HOLD",
                  "training_admitted": 0, "r50_accessed": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["status"] == "PINNED_ARCHIVES_INSPECTED__CARD_CONTENT_NOT_APPROVED" else 42


if __name__ == "__main__":
    raise SystemExit(main())

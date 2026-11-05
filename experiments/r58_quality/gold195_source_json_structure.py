#!/usr/bin/env python3
"""SAFE schema introspection of verified LFS ZIP source archives; no narrative output."""
from __future__ import annotations
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import zipfile

from gold195_archive_source_discovery import SOURCES, SOURCE_ROOT, digest_file

# Only predeclared technical field names can appear in output.
KEYS = frozenset(("story", "story_id", "story_uuid", "story_card", "story_cards",
    "v2_data", "characters", "character_cards", "character", "persona",
    "current_persona", "personas", "world", "world_info", "system_prompt",
    "runtime_context", "session", "messages", "metadata",
    "created_at", "updated_at"))
MAX_MEMBERS = 7000
MAX_JSON = 35000000
MAX_NESTED = 90000000


def shape(obj, counts):
    queue = [(obj, 0)]
    while queue:
        obj, depth = queue.pop()
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in KEYS:
                    counts["key_" + key] += 1
                    kind = ("dict" if isinstance(value, dict) else
                            "list" if isinstance(value, list) else
                            "string" if isinstance(value, str) else "other")
                    counts["type_" + key + "_" + kind] += 1
                if depth < 3 and isinstance(value, (dict, list)):
                    queue.append((value, depth + 1))
        elif isinstance(obj, list):
            queue.extend((x, depth) for x in obj[:3] if isinstance(x, (dict, list)))


def inspect_zip(source, counts, depth=0):
    if depth > 3:
        counts["depth_limit"] += 1
        return
    with zipfile.ZipFile(source) as z:
        entries = z.infolist()
        if len(entries) > MAX_MEMBERS:
            raise ValueError("too many archive members")
        for entry in entries:
            if entry.is_dir():
                continue
            counts["members"] += 1
            if counts["members"] > MAX_MEMBERS:
                raise ValueError("global member guard")
            suffix = Path(entry.filename).suffix.lower()
            if suffix == ".zip":
                counts["nested_zip"] += 1
                if entry.file_size > MAX_NESTED:
                    counts["nested_oversize"] += 1
                    continue
                inspect_zip(io.BytesIO(z.read(entry)), counts, depth + 1)
            elif suffix in (".json", ".jsonl"):
                if entry.file_size > MAX_JSON:
                    counts["json_oversize"] += 1
                    continue
                try:
                    raw = z.read(entry)
                    if suffix == ".jsonl":
                        raw = next((line for line in raw.splitlines() if line.strip()), b"")
                    if not raw:
                        counts["empty_json"] += 1
                        continue
                    obj = json.loads(raw)
                    counts["json_parsed"] += 1
                    shape(obj, counts)
                except (ValueError, UnicodeError, RecursionError):
                    counts["json_parse_failed"] += 1


def audit(repo):
    result = {"schema": "r58_gold195_source_json_structure_safe_v1",
              "status": "SOURCE_JSON_STRUCTURE_PASS__CARD_APPROVAL_ZERO",
              "sources": {}, "raw_text_emitted": False, "r50_accessed": False,
              "training_admitted": 0}
    for label, name, expected_sha, size in SOURCES:
        path = repo / SOURCE_ROOT / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size != size:
            result["sources"][label] = {"status": "LFS_NOT_MATERIALIZED"}
            result["status"] = "SOURCE_ARCHIVE_MISSING__HOLD"
            continue
        if digest_file(path) != expected_sha:
            result["sources"][label] = {"status": "HASH_MISMATCH"}
            result["status"] = "SOURCE_ARCHIVE_HASH_MISMATCH__HOLD"
            continue
        counts = Counter()
        inspect_zip(path, counts)
        result["sources"][label] = {"status": "SCANNED",
                                    "counts": dict(sorted(counts.items()))}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.repo_root)
    except Exception:
        result = {"schema": "r58_gold195_source_json_structure_safe_v1",
                  "status": "SOURCE_ZIP_OR_SCHEMA_ERROR__HOLD",
                  "training_admitted": 0}
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result["status"] == "SOURCE_JSON_STRUCTURE_PASS__CARD_APPROVAL_ZERO" else 42


if __name__ == "__main__":
    raise SystemExit(main())

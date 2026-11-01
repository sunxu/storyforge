#!/usr/bin/env python3
"""Count-only alignment of frozen Gold195 world IDs with raw story-card snapshots in LFS."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
from gold195_archive_source_discovery import SOURCES, SOURCE_ROOT, digest_file

MAX_JSON = 50_000_000
MAX_NESTED = 90_000_000


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":")).encode()).hexdigest()


def worlds_from_source(source, counts, worlds, depth=0):
    if depth > 3:
        return
    with zipfile.ZipFile(source) as z:
        if len(z.infolist()) > 7000:
            raise ValueError("zip entries")
        for info in z.infolist():
            if info.is_dir():
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix == ".zip":
                if info.file_size <= MAX_NESTED:
                    worlds_from_source(io.BytesIO(z.read(info)), counts, worlds, depth + 1)
                else:
                    counts["large_nested_zip_skipped"] += 1
            elif suffix in (".json", ".jsonl"):
                if info.file_size > MAX_JSON:
                    counts["large_json_skipped"] += 1
                    continue
                try:
                    buf = z.read(info)
                    if suffix == ".jsonl":
                        buf = next((line for line in buf.splitlines() if line.strip()), b"")
                    if not buf:
                        continue
                    data = json.loads(buf)
                    if not isinstance(data, dict):
                        continue
                    story = data.get("story")
                    if not isinstance(story, dict):
                        continue
                    card = story.get("v2_data")
                    if not isinstance(card, dict) or not card:
                        continue
                    identity = story.get("id") or story.get("uuid") or data.get("story_id")
                    if not isinstance(identity, str) or not identity.strip():
                        counts["card_missing_story_identity"] += 1
                        continue
                    worlds[identity].add(sha(card))
                    counts["story_card_object_seen"] += 1
                except (ValueError, UnicodeError, RecursionError):
                    counts["unreadable_json"] += 1


def gold_ids(root):
    from gold195_source_review_packet import ROOTS, index108
    index = index108(root)
    result = {}
    for cohort, rel, expected in ROOTS:
        rows = []
        with (root / rel).open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if cohort == "gold87":
                    ident = item["metadata"].get("story_id")
                else:
                    ident = index[item["id"]].get("story_id")
                rows.append(ident or None)
        if len(rows) != expected:
            raise ValueError("gold count mismatch")
        result[cohort] = rows
    return result


def scan(root):
    gold = gold_ids(root)
    result = {"schema": "r58_gold195_card_source_coverage_safe_v1",
              "status": "CARD_SOURCE_COVERAGE_DIAGNOSTIC__QUALITY_HOLD",
              "archives": {}, "gold": {},
              "card_text_output": False, "story_uuid_output": False,
              "r50_read": False, "training_admitted": 0}
    allworlds = defaultdict(set)
    for cohort, file, known_sha, size in SOURCES:
        path = root / SOURCE_ROOT / file
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != size or digest_file(path) != known_sha):
            result["status"] = "LFS_SOURCE_MISSING_OR_MISMATCH__HOLD"
            result["archives"][cohort] = {"status": "UNAVAILABLE"}
            continue
        counts = Counter()
        worlds = defaultdict(set)
        worlds_from_source(path, counts, worlds)
        for ident, versions in worlds.items():
            allworlds[ident].update(versions)
        counts["distinct_story_ids_with_cards"] = len(worlds)
        counts["story_ids_with_multiple_card_versions"] = sum(
            len(v) > 1 for v in worlds.values())
        result["archives"][cohort] = {"status": "INSPECTED",
                                     "counts": dict(sorted(counts.items()))}
    for cohort, rows in gold.items():
        present = set(x for x in rows if x)
        result["gold"][cohort] = {
            "rows": len(rows), "distinct_story_ids": len(present),
            "rows_with_card_source_id_match": sum(x in allworlds for x in rows),
            "distinct_story_ids_with_card_source_match": len(present & allworlds.keys()),
            "rows_without_card_source_id_match": sum(x not in allworlds for x in rows),
            "rows_in_multi_version_card_worlds": sum(len(allworlds[x]) > 1 for x in rows),
        }
    result["cross_archive_distinct_story_card_ids"] = len(allworlds)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    args = p.parse_args()
    try:
        result = scan(args.repo_root)
    except Exception:
        result = {"schema": "r58_gold195_card_source_coverage_safe_v1",
                  "status": "SOURCE_SCHEMA_UNAVAILABLE__HOLD",
                  "r50_read": False, "training_admitted": 0}
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result["status"] == "CARD_SOURCE_COVERAGE_DIAGNOSTIC__QUALITY_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())

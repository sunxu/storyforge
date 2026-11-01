#!/usr/bin/env python3
"""Read-only source-to-target verification for Gold195; SAFE counts only.

This is a data-shape gate, NOT quality approval or dataset generation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

FROM = {
    "gold87": ("evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl", 87),
    "gold108": ("evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl", 108),
}
INDEX108 = "evaluations/v0.2/gold-quality-108/gold_108_index.csv"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def audit(root: Path):
    index_file = root / INDEX108
    if not index_file.is_file() or index_file.is_symlink():
        raise ValueError("index absent")
    with index_file.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"candidate_id", "target_sha256", "story_id"}.issubset(reader.fieldnames or ()):
            raise ValueError("index schema")
        index_rows = list(reader)
    index = {}
    for entry in index_rows:
        key = entry["candidate_id"]
        if not key or key in index:
            raise ValueError("duplicate index ID")
        index[key] = entry
    result = {
        "schema": "r58_gold195_target_source_preflight_v1",
        "status": "SOURCE_TARGET_PREFLIGHT_PASS__QUALITY_ADMISSION_ZERO",
        "derived_candidate_rows_written": 0,
        "source_rows_modified": 0,
        "r50_accessed": False,
        "quality_v1_admitted": 0,
        "gpu_authorized": False,
        "cohorts": {},
    }
    for name, (relative, expected) in FROM.items():
        file = root / relative
        if not file.is_file() or file.is_symlink():
            raise ValueError("source absent")
        counts = Counter()
        seen = set()
        with file.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                counts["records"] += 1
                row = json.loads(line)
                if not isinstance(row, dict):
                    counts["invalid_row"] += 1
                    continue
                rid = row.get("id")
                if not isinstance(rid, str) or not rid or rid in seen:
                    counts["bad_or_duplicate_source_id"] += 1
                    continue
                seen.add(rid)
                meta = row.get("metadata")
                meta = meta if isinstance(meta, dict) else {}
                messages = row.get("messages")
                if not isinstance(messages, list) or len(messages) < 2 or any(
                    not isinstance(m, dict) or
                    m.get("role") not in ("system", "user", "assistant") or
                    not isinstance(m.get("content"), str) or
                    not m["content"].strip()
                    for m in messages
                ):
                    counts["invalid_message_structure"] += 1
                    continue
                roles = [m["role"] for m in messages]
                if roles[-2:] != ["user", "assistant"]:
                    counts["current_user_target_not_adjacent"] += 1
                else:
                    counts["current_user_target_adjacent"] += 1
                if roles[0] == "assistant":
                    counts["leading_assistant_requires_explicit_derivation"] += 1
                if any(roles[i] == roles[i-1] for i in range(1, len(roles))):
                    counts["role_sequence_not_alternating"] += 1
                target = messages[-1]["content"]
                if name == "gold87":
                    expected_digest = meta.get("target_sha256_utf8")
                    story = meta.get("story_id")
                else:
                    item = index.get(rid)
                    if item is None:
                        counts["source_id_unmatched_index"] += 1
                        continue
                    expected_digest = item.get("target_sha256")
                    story = item.get("story_id")
                    counts["index_rows_linked_to_source"] += 1
                if digest(target) == expected_digest:
                    counts["target_sha256_verified"] += 1
                else:
                    counts["target_sha256_mismatch_or_missing"] += 1
                if not isinstance(story, str) or not story.strip():
                    counts["story_id_missing_hold"] += 1
                else:
                    counts["story_uuid_present_not_world_certified"] += 1
        counts["expected_rows"] = expected
        if counts["records"] != expected:
            counts["frozen_count_mismatch"] += 1
        if name == "gold108" and (len(index) != expected or len(seen) != len(index)):
            counts["source_index_cardinality_mismatch"] += 1
        result["cohorts"][name] = dict(sorted(counts.items()))
        hard_errors = (
            "invalid_row", "bad_or_duplicate_source_id", "invalid_message_structure",
            "current_user_target_not_adjacent", "role_sequence_not_alternating",
            "source_id_unmatched_index", "target_sha256_mismatch_or_missing",
            "frozen_count_mismatch", "source_index_cardinality_mismatch",
        )
        if any(counts[k] for k in hard_errors):
            result["status"] = "SOURCE_TARGET_PREFLIGHT_HOLD"
    result["records_checked"] = sum(c["records"] for c in result["cohorts"].values())
    result["all_target_hashes_verified"] = (
        result["status"] == "SOURCE_TARGET_PREFLIGHT_PASS__QUALITY_ADMISSION_ZERO"
        and sum(c.get("target_sha256_verified", 0) for c in result["cohorts"].values()) == 195
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        outcome = audit(args.repo_root)
    except Exception:
        outcome = {
            "schema": "r58_gold195_target_source_preflight_v1",
            "status": "INPUT_OR_SCHEMA_ERROR__HOLD", "quality_v1_admitted": 0,
            "r50_accessed": False, "source_rows_modified": 0,
        }
    print(json.dumps(outcome, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if outcome["status"] == "SOURCE_TARGET_PREFLIGHT_PASS__QUALITY_ADMISSION_ZERO" else 42


if __name__ == "__main__":
    raise SystemExit(main())

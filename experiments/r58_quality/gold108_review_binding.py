#!/usr/bin/env python3
"""Gold108 original dual-review evidence binder. SAFE counts only, no training admission."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

BASE = Path("evaluations/v0.2/gold-quality-108")
EXPECTED = 108
SHA64 = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_CSV = (
    "blind_id", "candidate_id", "story_number", "story_id",
    "target_sha256", "reviewer1_decision", "reviewer2_decision",
    "reviewer1_scores", "reviewer2_scores",
)
REQUIRED_EVIDENCE = (
    "blind_id", "candidate_id", "story_number",
    "reviewer1_decision", "reviewer2_decision",
    "reviewer1_scores", "reviewer2_scores",
    "reviewer1_evidence", "reviewer2_evidence",
)
STATUS = "HISTORICAL_DUAL_REVIEW_INDEX_BINDING_ONLY__NO_QUALITY_V1_ADMISSION"


def score_ok(raw: object) -> bool:
    if not isinstance(raw, str):
        return False
    parts = raw.split(",")
    return len(parts) == 5 and all(p.strip() in {"4", "5"} for p in parts)


def check(root: Path) -> dict:
    index_path = root / BASE / "gold_108_index.csv"
    evidence_path = root / BASE / "dual_accept_review_evidence_108.jsonl"
    for path in (index_path, evidence_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked source")
    with index_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not set(REQUIRED_CSV).issubset(reader.fieldnames or []):
            raise ValueError("missing index columns")
        indexed = list(reader)
    with evidence_path.open(encoding="utf-8") as f:
        reviewed = [json.loads(line) for line in f if line.strip()]
    errors = Counter()
    world_gaps = Counter()
    if len(indexed) != EXPECTED or len(reviewed) != EXPECTED:
        errors["frozen_count_mismatch"] += 1
    lookup = {}
    for entry in reviewed:
        if not isinstance(entry, dict) or any(k not in entry for k in REQUIRED_EVIDENCE):
            errors["evidence_schema_invalid"] += 1
            continue
        key = entry["candidate_id"]
        if not isinstance(key, str) or not key or key in lookup:
            errors["duplicate_or_invalid_evidence_id"] += 1
            continue
        lookup[key] = entry
    used = set()
    for entry in indexed:
        key = entry["candidate_id"]
        if not key or key in used:
            errors["duplicate_or_invalid_index_id"] += 1
            continue
        used.add(key)
        proof = lookup.get(key)
        if proof is None:
            errors["review_evidence_missing"] += 1
            continue
        if (entry["blind_id"] != proof["blind_id"] or
                str(entry["story_number"]).zfill(2) != str(proof["story_number"]).zfill(2)):
            errors["identity_binding_mismatch"] += 1
        for reviewer in ("reviewer1", "reviewer2"):
            if (entry[reviewer + "_decision"] != "ACCEPT" or
                    proof[reviewer + "_decision"] != "ACCEPT"):
                errors["legacy_review_not_double_accept"] += 1
            if entry[reviewer + "_scores"] != proof[reviewer + "_scores"]:
                errors["legacy_score_binding_mismatch"] += 1
            if not score_ok(entry[reviewer + "_scores"]):
                errors["legacy_score_below_floor_or_malformed"] += 1
            if not isinstance(proof[reviewer + "_evidence"], str) or not proof[reviewer + "_evidence"].strip():
                errors["review_evidence_empty"] += 1
        if not SHA64.fullmatch(entry["target_sha256"] or ""):
            errors["target_hash_missing_or_malformed_in_index"] += 1
        if not isinstance(entry["story_id"], str) or not entry["story_id"].strip():
            world_gaps["index_story_id_missing"] += 1
    if len(used) != len(lookup):
        errors["index_evidence_set_mismatch"] += 1
    return {
        "schema": "storyforge_r58_gold108_legacy_review_binding_v1",
        "status": STATUS if not errors else "LEGACY_EVIDENCE_BINDING_HOLD",
        "index_count": len(indexed),
        "review_evidence_count": len(reviewed),
        "index_rows_with_review_link": len(used & lookup.keys()),
        "historical_double_accept_verified": not bool(errors),
        "errors": dict(sorted(errors.items())),
        "world_identity_gaps": dict(sorted(world_gaps.items())),
        "world_identity_cleared": not bool(world_gaps),
        "old_review_dimensions": 5,
        "new_quality_v1_dimensions_verified": 0,
        "source_record_target_hash_recomputed": False,
        "source_record_unchanged": True,
        "reviewer_independence_proven": False,
        "semantic_world_isolation_proven": False,
        "r50_body_accessed": False,
        "training_admitted": 0,
        "gpu_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = check(args.repo_root)
    except Exception:
        result = {
            "schema": "storyforge_r58_gold108_legacy_review_binding_v1",
            "status": "INPUT_OR_SCHEMA_UNAVAILABLE__HOLD",
            "training_admitted": 0, "r50_body_accessed": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["status"] == STATUS else 42


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only count-only metadata inventory of frozen Gold195. No admission."""
import argparse
from collections import Counter
import json
from pathlib import Path

COHORTS = (
    ("gold87", "evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl", 87),
    ("gold108", "evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl", 108),
)


def scan(path):
    count, worlds, facts = 0, set(), Counter()
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            count += 1
            if not isinstance(row, dict):
                facts["malformed_record"] += 1
                continue
            meta = row.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}
            world = meta.get("story_id")
            if isinstance(world, str) and world.strip():
                worlds.add(world)
            else:
                facts["world_id_missing"] += 1
            msgs = row.get("messages")
            if not isinstance(msgs, list) or not msgs:
                facts["messages_missing"] += 1
                continue
            roles = [m.get("role") if isinstance(m, dict) else None for m in msgs]
            facts["starts_with_system" if roles[0] == "system" else "needs_system_derivation"] += 1
            facts["last_assistant" if roles[-1] == "assistant" else "last_not_assistant"] += 1
            facts["alternating_roles" if all(roles[i] != roles[i - 1] for i in range(1, len(roles))) else "non_alternating_roles"] += 1
            facts["has_target_hash" if isinstance(meta.get("target_sha256_utf8"), str) else "missing_target_hash"] += 1
            facts["split_already_set" if meta.get("split") in ("train", "validation") else "split_not_set"] += 1
            facts["token_check_declared" if meta.get("qwen_token_length_check") not in (None, "PENDING", "NOT_CHECKED") else "token_check_not_declared"] += 1
            facts["mask_check_declared" if meta.get("last_round_label_mask_check") not in (None, "PENDING", "NOT_CHECKED") else "mask_check_not_declared"] += 1
    return {"records": count, "distinct_story_uuids": len(worlds), "structural_counts": dict(sorted(facts.items()))}


def inventory(root):
    result = {
        "schema": "r58_gold195_metadata_preflight_v1",
        "status": "READ_ONLY_DIAGNOSTIC_NOT_QUALITY_ADMISSION",
        "historical_double_review_is_not_quality_v1_six_dimension_review": True,
        "semantic_world_independence_proven": False,
        "protected_test_accessed": False,
        "training_admitted": 0,
        "gpu_authorized": False,
        "cohorts": {},
    }
    total = 0
    for name, relative, expected in COHORTS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            result["status"] = "INPUT_MISSING_OR_UNSAFE__HOLD"
            return result
        cohort = scan(path)
        cohort["expected_records"] = expected
        cohort["count_matches_frozen_manifest"] = cohort["records"] == expected
        result["cohorts"][name] = cohort
        total += cohort["records"]
    result["total_records"] = total
    if total != 195 or any(not c["count_matches_frozen_manifest"] for c in result["cohorts"].values()):
        result["status"] = "FROZEN_COUNT_MISMATCH__HOLD"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inventory(args.repo_root)
    except Exception:
        result = {"schema": "r58_gold195_metadata_preflight_v1", "status": "INPUT_OR_PARSE_ERROR__HOLD", "training_admitted": 0, "protected_test_accessed": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.get("status") == "READ_ONLY_DIAGNOSTIC_NOT_QUALITY_ADMISSION" else 42


if __name__ == "__main__":
    raise SystemExit(main())

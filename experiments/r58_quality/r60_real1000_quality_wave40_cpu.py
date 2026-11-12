"""Prepare next 40 private Real1000 quality review locators; no reviews/calls.

Frozen Real1000 and frozen calibration Sample100 are read and verified. Pick
distinct stories outside the entire Sample100 story set to prevent reuse.
The create-only 0600 manifest contains ONLY private pool positions and bins,
not message text or source IDs. No DB/GPU/remote model, no admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_calibration_sample_cpu as sample
import r60_real1000_technical_profile_cpu as technical
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_quality_wave40_private_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_quality_wave40_safe_v1"
STATUS = "QUALITY_WAVE40_LOCATORS_READY__NOT_REVIEWED"
FILENAME = "R60_REAL1000_QUALITY_WAVE40_PRIVATE.json"
SAMPLE_FILE = sample.FILENAME
QUOTAS = {"300_499": 20, "500_999": 16, "1000_1500": 4}
SALT = b"storyforge-r60-real1000-quality-wave40-v1\x00"


class Hold(ValueError):
    pass


def select(cases: list[dict], pool_sha: str, frozen: dict) -> dict:
    technical.profile(cases)
    if frozen != sample.select(cases, pool_sha):
        raise Hold("CALIBRATION_SAMPLE100_CHANGED_HOLD")
    old_positions = [entry["position"] for entry in frozen["cases"]]
    if len(old_positions) != 100 or len(set(old_positions)) != 100:
        raise Hold("CALIBRATION_POSITIONS_HOLD")
    blocked_stories = {cases[p - 1]["source"]["story_id"] for p in old_positions}
    choices = []
    for position, case in enumerate(cases, 1):
        if case["source"]["story_id"] in blocked_stories:
            continue
        category = sample.bucket(len(case["target_text"]))
        priority = hashlib.sha256(
            SALT + pool_sha.encode("ascii") + b"\x00"
            + case["case_key"].encode("utf-8"),
        ).hexdigest()
        choices.append((priority, position, category, case["source"]["story_id"]))
    selected: list[dict] = []
    used_stories: set[str] = set()
    shortfall: dict[str, int] = {}
    for category, quota in QUOTAS.items():
        count = 0
        for _rank, position, cat, story_id in sorted(choices):
            if cat != category or story_id in used_stories:
                continue
            used_stories.add(story_id)
            selected.append({"position": position, "target_char_bin": cat})
            count += 1
            if count == quota:
                break
        if count < quota:
            shortfall[category] = quota - count
    # Sparse long-target bins must not force a made-up quota: fill remaining
    # positions deterministically from eligible distinct stories; report the
    # actual distribution rather than pretending exact target ratios passed.
    for _rank, position, cat, story_id in sorted(choices):
        if len(selected) == 40:
            break
        if story_id in used_stories:
            continue
        used_stories.add(story_id)
        selected.append({"position": position, "target_char_bin": cat})
    selected.sort(key=lambda x: x["position"])
    if len(selected) != 40 or len(used_stories) != 40:
        raise Hold("WAVE40_COUNT_HOLD")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "pool_sha256": pool_sha,
        "sample100_frozen_binding": True,
        "excludes_all_sample100_stories": True,
        "method": "sha256_rank_distinct_stories_outside_sample100_v1",
        "cases": selected,
        "quota_shortfalls_before_fill": shortfall,
        "quality_review_performed": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expand-dir", type=Path, required=True)
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        private.private_dir(args.sample_dir, create=False)
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise Hold("OUTPUT_ALREADY_EXISTS_HOLD")
        cases, pool_sha = quality.frozen_pool(args.expand_dir)
        frozen = json.loads(private.read_private(
            args.sample_dir / SAMPLE_FILE, 65_536,
        ))
        result = select(cases, pool_sha, frozen)
        private.private_dir(args.output_dir, create=True)
        private.write_new(
            args.output_dir / FILENAME,
            (json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        distribution = Counter(item["target_char_bin"] for item in result["cases"])
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": STATUS,
            "prepared": 40,
            "distinct_new_stories": 40,
            "sample100_story_overlap": 0,
            "distribution": dict(distribution),
            "quota_shortfalls_before_fill": result["quota_shortfalls_before_fill"],
            "quality_review_performed": False,
            "r50_complete_exclusion_verified": False,
            "train_admitted": 0,
            "database_accessed": False,
            "gpu_started": False,
            "model_inference_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - don't leak private input or paths
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "QUALITY_WAVE40_PREP_HOLD",
            "train_admitted": 0,
            "database_accessed": False,
            "gpu_started": False,
            "model_inference_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

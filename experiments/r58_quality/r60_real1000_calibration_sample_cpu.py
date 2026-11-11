"""Select 100 reproducible, story-disjoint R60 calibration cases from frozen1000.

No inference, DB access, or source text in output. Result is an Owner-private
position-only manifest, NOT a model review or train-admission artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_technical_profile_cpu as technical
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_calibration_sample_private_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_calibration_sample_safe_v1"
QUOTAS = {"300_499": 55, "500_999": 38, "1000_1500": 7}
FILENAME = "R60_CALIBRATION_SAMPLE100_PRIVATE.json"
SALT = b"storyforge-r60-frozen1000-calibration-v1\x00"


class SampleHold(ValueError):
    """Insufficient coverage or a mismatching original pool."""


def bucket(length: int) -> str:
    if 300 <= length <= 499:
        return "300_499"
    if 500 <= length <= 999:
        return "500_999"
    if 1000 <= length <= 1500:
        return "1000_1500"
    raise SampleHold("TARGET_LENGTH_HOLD")


def select(cases: list[dict], pool_sha: str) -> dict:
    technical.profile(cases)
    if not isinstance(pool_sha, str) or len(pool_sha) != 64:
        raise SampleHold("POOL_SHA_HOLD")
    entries = []
    for index, case in enumerate(cases, 1):
        source = case["source"]
        category = bucket(len(case["target_text"]))
        rank = hashlib.sha256(
            SALT + pool_sha.encode("ascii") + b"\x00"
            + case["case_key"].encode("utf-8")
        ).hexdigest()
        entries.append((rank, index, category, source["story_id"]))
    chosen: list[dict] = []
    used_stories = set()
    for category, quota in QUOTAS.items():
        eligible = sorted(row for row in entries if row[2] == category)
        for _rank, position, _category, story in eligible:
            if story in used_stories:
                continue
            used_stories.add(story)
            chosen.append({"position": position, "target_char_bin": category})
            if sum(item["target_char_bin"] == category for item in chosen) == quota:
                break
        else:
            raise SampleHold("DISTINCT_STORY_QUOTA_HOLD")
    if len(chosen) != 100 or len(used_stories) != 100:
        raise SampleHold("CALIBRATION_SCOPE_HOLD")
    chosen.sort(key=lambda row: row["position"])
    return {
        "schema": SCHEMA,
        "status": "CALIBRATION_SAMPLE100_PRIVATE__NOT_REVIEWED",
        "pool_sha256": pool_sha,
        "method": "stable_sha256_rank_unique_story_per_bin_v1",
        "cases": chosen,
        "quality_review_performed": False,
        "train_admitted": 0,
    }


def safe(manifest: dict) -> dict:
    bins = Counter(item["target_char_bin"] for item in manifest["cases"])
    return {
        "schema": SAFE_SCHEMA,
        "status": "CALIBRATION_SAMPLE100_READY__NO_REVIEWS",
        "sampled_cases": 100,
        "distinct_stories": 100,
        "target_char_bins": {key: bins[key] for key in QUOTAS},
        "quality_review_performed": False,
        "quality_pass": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expand-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise SampleHold("OUTPUT_EXISTS_HOLD")
        cases, pool_sha = quality.frozen_pool(args.expand_dir)
        manifest = select(cases, pool_sha)
        private.private_dir(args.output_dir, create=True)
        private.write_new(
            args.output_dir / FILENAME,
            (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        print(json.dumps(safe(manifest), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no source text or exception leakage
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "CALIBRATION_SAMPLE100_HOLD",
            "database_accessed": False,
            "gpu_started": False,
            "private_values_emitted": False,
            "quality_pass": 0,
            "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

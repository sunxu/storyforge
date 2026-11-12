"""R60: CPU-only SAFE technical profile of the already frozen real1000 pool.

Reuse the existing immutable page/seed SHA and prompt validation. No Supabase
calls, no model inference, no training admission, no private case output.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_technical_profile_safe_v1"
BINS = ((0, 499, "300_499"), (500, 999, "500_999"), (1000, 1500, "1000_1500"))


class Hold(ValueError):
    """Unsafe inventory or an unrecognized frozen candidate structure."""


def profile(cases: list[dict]) -> dict:
    if len(cases) != 1000:
        raise Hold("EXPECTED_1000_HOLD")
    seen_keys, seen_targets = set(), set()
    stories: Counter = Counter()
    lengths: Counter = Counter()
    exact_chain = 0
    persisted = 0
    missing_actual_system = 0
    world_hold = 0
    r50_hold = 0
    for case in cases:
        if not isinstance(case, dict):
            raise Hold("CASE_TYPE_HOLD")
        key = case.get("case_key")
        source = case.get("source")
        if (
            not isinstance(key, str)
            or not key
            or key in seen_keys
            or not isinstance(source, dict)
            or not isinstance(source.get("story_id"), str)
            or not source["story_id"]
            or not isinstance(source.get("assistant_message_id"), str)
            or not source["assistant_message_id"]
            or source["assistant_message_id"] in seen_targets
        ):
            raise Hold("CASE_SOURCE_OR_DUPLICATE_HOLD")
        seen_keys.add(key)
        seen_targets.add(source["assistant_message_id"])
        stories[source["story_id"]] += 1
        history = case.get("history_messages")
        if (
            not isinstance(history, list)
            or len(history) != 3
            or any(not isinstance(msg, dict) for msg in history)
            or [msg.get("role") for msg in history] != ["user", "assistant", "user"]
            or any(not isinstance(msg.get("content"), str) or not msg["content"]
                   for msg in history)
        ):
            raise Hold("HISTORY_CHAIN_HOLD")
        exact_chain += 1
        target = case.get("target_text")
        if not isinstance(target, str) or not 300 <= len(target) <= 1500:
            raise Hold("TARGET_BOUNDS_HOLD")
        length_bin = next((name for low, high, name in BINS
                           if low <= len(target) <= high), None)
        if length_bin is None:
            raise Hold("TARGET_BIN_HOLD")
        lengths[length_bin] += 1
        if case.get("target_semantics") != "DB_FINAL_PERSISTED_ASSISTANT":
            raise Hold("TARGET_SEMANTICS_HOLD")
        persisted += 1
        if case.get("historical_system_provenance") == "UNKNOWN_NOT_ACTUAL_SENT":
            missing_actual_system += 1
        if case.get("world_component_status") == "UNKNOWN_HOLD":
            world_hold += 1
        if case.get("r50_complete_exclusion_status") == "UNKNOWN_HOLD":
            r50_hold += 1
        if case.get("train_admitted") is not False:
            raise Hold("ADMISSION_STATUS_HOLD")
    if len(stories) > 1000 or max(stories.values(), default=0) > 4:
        raise Hold("STORY_DISTRIBUTION_HOLD")
    return {
        "schema": SCHEMA,
        "status": "REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING",
        "cases_verified": 1000,
        "distinct_stories": len(stories),
        "max_cases_per_story": max(stories.values()),
        "three_prior_messages_verified": exact_chain,
        "persisted_target_verified": persisted,
        "target_char_bins": {
            name: lengths[name] for _, _, name in BINS
        },
        "historical_system_not_verified": missing_actual_system,
        "world_component_unverified": world_hold,
        "r50_exclusion_unverified": r50_hold,
        "quality_pass": 0,
        "quality_review_performed": False,
        "train_admitted": 0,
        "gpu_started": False,
        "database_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expand-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        cases, _pool_sha = quality.frozen_pool(args.expand_dir)
        result = profile(cases)
    except Exception:  # noqa: BLE001 - redact all private-data errors
        result = {
            "schema": SCHEMA,
            "status": "REAL1000_TECHNICAL_PROFILE_HOLD",
            "quality_pass": 0,
            "train_admitted": 0,
            "gpu_started": False,
            "database_accessed": False,
            "private_values_emitted": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 42
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

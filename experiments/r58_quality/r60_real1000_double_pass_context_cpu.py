"""Read-only training-context preflight for frozen Real1000 double-PASS candidates.

Verify exact source-pool and Pilot20 binding. Report unavailable System/world/R50
evidence as HOLD; never treat model agreement as approval to train.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_calibration_sample_cpu as sample
import r60_real1000_double_pass_candidates_cpu as double
import r60_real1000_pilot20_local_review as pilot
import r60_real1000_technical_profile_cpu as technical
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_double_pass_context_safe_v1"


class Hold(ValueError):
    pass


def check(expand_dir: Path, sample_dir: Path, review_dir: Path,
          candidate_file: Path) -> dict:
    cases, pool_sha = quality.frozen_pool(expand_dir)
    technical.profile(cases)
    private.private_dir(sample_dir, create=False)
    frozen = json.loads(private.read_private(sample_dir / sample.FILENAME, 65536))
    if (frozen != sample.select(cases, pool_sha)
            or frozen["pool_sha256"] != pool_sha):
        raise Hold("SAMPLE100_SOURCE_POOL_HOLD")
    config, packets, progress = pilot.get_state(review_dir)
    if progress["processed"] != 20 or config["packets_sha256"] != pilot.sha(
            private.read_private(Path(config["packet_dir"]) /
                                 pilot.pilot.FILENAME, pilot.MAX_PACKETS_BYTES)):
        raise Hold("PILOT20_NOT_FROZEN_HOLD")
    saved = json.loads(private.read_private(candidate_file, 65536))
    if (not isinstance(saved, dict) or saved.get("schema") != double.PRIVATE_SCHEMA
            or saved.get("status") != "DOUBLE_PASS_TRAIN_CANDIDATES__NOT_ADMITTED"
            or saved.get("train_admitted") != 0
            or saved.get("quality_v1_admitted") != 0
            or not isinstance(saved.get("candidates"), list)):
        raise Hold("CANDIDATE_MANIFEST_HOLD")
    positions = [x["pilot_position"] for x in saved["candidates"]]
    if (len(positions) != 3 or len(set(positions)) != 3
            or any(type(i) is not int or not 1 <= i <= 20 for i in positions)
            or any(x.get("status") != "TRAIN_CANDIDATE__NOT_ADMITTED"
                   for x in saved["candidates"])):
        raise Hold("CANDIDATE_POSITIONS_HOLD")

    story_set = set()
    target_set = set()
    lengths = Counter()
    missing = Counter()
    for index in positions:
        packet = packets["packets"][index - 1]
        source_position = packet["sample100_position"]
        if (source_position not in {x["position"] for x in frozen["cases"]}
                or not 1 <= source_position <= len(cases)):
            raise Hold("SOURCE_POSITION_HOLD")
        source = cases[source_position - 1]
        if (packet["history_messages"] != source["history_messages"]
                or packet["assistant_target"] != source["target_text"]):
            raise Hold("SOURCE_PAYLOAD_MISMATCH_HOLD")
        story_set.add(source["source"]["story_id"])
        target_set.add(source["source"]["assistant_message_id"])
        lengths[packet["target_char_bin"]] += 1
        missing["historical_system"] += source.get(
            "historical_system_provenance") == "UNKNOWN_NOT_ACTUAL_SENT"
        missing["world_components"] += source.get(
            "world_component_status") == "UNKNOWN_HOLD"
        missing["r50_exclusion"] += source.get(
            "r50_complete_exclusion_status") == "UNKNOWN_HOLD"
    if len(target_set) != len(positions):
        raise Hold("DUPLICATE_TARGET_HOLD")
    return {
        "schema": SCHEMA,
        "status": "DOUBLE_PASS_CONTEXT_PREFLIGHT_PASS__TRAIN_ADMISSION_HOLD",
        "frozen_pool_cases": len(cases),
        "candidate_count": len(positions),
        "unique_target_count": len(target_set),
        "distinct_story_count": len(story_set),
        "target_length_bins": {x: lengths[x] for x in sample.QUOTAS},
        "historical_system_unverified": missing["historical_system"],
        "world_component_unverified": missing["world_components"],
        "r50_exclusion_unverified": missing["r50_exclusion"],
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expand-dir", type=Path, required=True)
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--candidate-file", type=Path, required=True)
    args = p.parse_args()
    try:
        result = check(args.expand_dir, args.sample_dir, args.review_dir,
                       args.candidate_file)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never emit private content/paths
        reason = str(exc) if isinstance(exc, Hold) else "CONTEXT_PREFLIGHT_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "DOUBLE_PASS_CONTEXT_PREFLIGHT_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0, "train_admitted": 0,
            "model_inference_calls": 0, "database_accessed": False,
            "gpu_job_started": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

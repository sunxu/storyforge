"""CPU-only source/context preflight for the TWO validated common dual-PASS cases.

Check immutable Real1000/Pilot20 binding and the two independent PASS
decisions. Source fields cannot prove historic System/world provenance merely
by being absent or inferred. The five known R50 stories are only a partial
exclusion check, never the complete held-out set.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_calibration_sample_cpu as sample
import r60_real1000_pilot20_local_review as pilot
import r60_real1000_qd20_common_pass_blind_cpu as common
import r60_real1000_r50_known5_exclusion_cpu as r50
import r60_real1000_technical_profile_cpu as technical
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_qd20_common2_context_safe_v1"


class Hold(ValueError):
    pass


def assess(cases: list[dict], frozen: dict, packets: list[dict],
           blind: dict, decisions: dict, expected_blind: dict) -> dict:
    if (len(cases) != 1000 or len(packets) != 20
            or blind != expected_blind
            or common.validate(blind, decisions)["review_decisions"]
            != {"PASS": 2, "HOLD": 0, "REJECT": 0}):
        raise Hold("COMMON2_SOURCE_OR_REVIEW_HOLD")
    # Pilot positions are deliberately excluded from the blind file. Recover
    # each by exact private source payload and require a unique binding.
    bins = Counter()
    missing = Counter()
    known_hits = 0
    story_ids = set()
    target_ids = set()
    for blind_case in blind["cases"]:
        matching = [
            x for x in packets
            if (x.get("history_messages") == blind_case["history_messages"]
                and x.get("assistant_target") == blind_case["assistant_target"])
        ]
        if len(matching) != 1:
            raise Hold("COMMON2_PILOT_BINDING_HOLD")
        packet = matching[0]
        source_position = packet.get("sample100_position")
        if (type(source_position) is not int
                or not 1 <= source_position <= 1000
                or source_position not in {
                    item["position"] for item in frozen["cases"]
                }):
            raise Hold("SAMPLE100_POSITION_HOLD")
        source = cases[source_position - 1]
        if (source["history_messages"] != blind_case["history_messages"]
                or source["target_text"] != blind_case["assistant_target"]):
            raise Hold("REAL1000_EXACT_PAYLOAD_HOLD")
        story_ids.add(source["source"]["story_id"])
        target_ids.add(source["source"]["assistant_message_id"])
        bins[packet["target_char_bin"]] += 1
        # A field with UNKNOWN or not even present cannot be evidence.
        missing["historical_system"] += source.get(
            "historical_system_provenance") != "VERIFIED_ACTUAL_SENT"
        missing["world_components"] += source.get(
            "world_component_status") != "VERIFIED_SOURCE_BOUND"
        missing["r50_complete_exclusion"] += source.get(
            "r50_complete_exclusion_status") != "VERIFIED_FULL_FROZEN"
        known_hits += source["source"]["story_id"] in r50.KNOWN_R50_STORIES
    if len(target_ids) != 2:
        raise Hold("COMMON2_TARGET_DUPLICATE_HOLD")
    return {
        "schema": SCHEMA,
        "status": "QD20_COMMON2_SOURCE_BINDING_PASS__TRAIN_CONTEXT_HOLD",
        "frozen_pool_cases": 1000,
        "pilot_cases": 20,
        "candidate_count": 2,
        "strict_independent_pass": 2,
        "unique_target_count": len(target_ids),
        "distinct_story_count": len(story_ids),
        "target_length_bins": {k: bins[k] for k in sample.QUOTAS},
        "historical_system_unverified": missing["historical_system"],
        "world_component_unverified": missing["world_components"],
        "r50_full_exclusion_unverified": missing["r50_complete_exclusion"],
        "r50_known5_overlap_count": known_hits,
        "r50_known5_reference": r50.REFERENCE_DOC,
        "r50_known5_is_partial_only": True,
        "r50_complete_exclusion_verified": False,
        "training_context_verified": False,
        "quality_ground_truth_established": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }


def run(args: argparse.Namespace) -> dict:
    cases, pool_sha = quality.frozen_pool(args.expand_dir)
    technical.profile(cases)
    private.private_dir(args.sample_dir, create=False)
    frozen = json.loads(private.read_private(
        args.sample_dir / sample.FILENAME, 65536))
    if (frozen != sample.select(cases, pool_sha)
            or frozen["pool_sha256"] != pool_sha):
        raise Hold("FROZEN_SAMPLE100_HOLD")
    cfg, packets, progress = pilot.get_state(args.review_dir)
    if (progress["processed"] != 20 or
            cfg["packets_sha256"] != pilot.sha(private.read_private(
                Path(cfg["packet_dir"]) / pilot.pilot.FILENAME,
                pilot.MAX_PACKETS_BYTES))):
        raise Hold("FROZEN_PILOT20_HOLD")
    expected_blind, _ = common.frozen_input(args)
    private.private_dir(args.output_dir, create=False)
    blind = json.loads(private.read_private(
        args.output_dir / common.BLIND_NAME, 200000))
    decisions = json.loads(private.read_private(
        args.decisions, 200000))
    return assess(cases, frozen, packets["packets"], blind, decisions,
                  expected_blind)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expand-dir", type=Path, required=True)
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--s1-blind-dir", type=Path, required=True)
    p.add_argument("--owner-map-dir", type=Path, required=True)
    p.add_argument("--codex-result", type=Path, required=True)
    p.add_argument("--live-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--decisions", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - private paths/text never logged
        code = str(exc) if isinstance(exc, Hold) else "COMMON2_CONTEXT_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "QD20_COMMON2_CONTEXT_PREFLIGHT_HOLD",
            "reason_code": code,
            "quality_v1_admitted": 0,
            "train_admitted": 0,
            "model_inference_calls": 0,
            "database_accessed": False,
            "gpu_job_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

"""R60 read-only check against the five documented R49/R50 source stories.

This is PARTIAL exclusion evidence only. Never claim complete R50 heldout
exclusion from the five known story UUIDs alone. No private IDs printed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import r60_real1000_double_pass_candidates_cpu as double
import r60_real_private_batch as private
import r60_real_quality_batch as quality
import r60_real1000_pilot20_local_review as pilot

SCHEMA = "storyforge_r60_real1000_r50_known5_exclusion_safe_v1"
REFERENCE_DOC = "docs/evidence/V03_R49_R50_16_20_SOURCE_INTAKE_20261015.md"
KNOWN_R50_STORIES = frozenset({
    "aa09b761-b818-4912-ba17-e91b0b84134c",
    "8becb648-38a4-4f1b-9d5e-14ce4d404b33",
    "52392eca-2bec-4931-b59b-a33dcdff4010",
    "8c75f0ee-b0fe-4903-b01c-be8e787fe2f2",
    "4b280246-0da6-4c67-9fe3-979cd58b53db",
})


class Hold(ValueError):
    pass


def check(cases: list[dict], packet_rows: list[dict],
          manifest: dict) -> dict:
    if len(cases) != 1000 or len(packet_rows) != 20:
        raise Hold("FROZEN_POOL_OR_PILOT_HOLD")
    if (not isinstance(manifest, dict)
            or manifest.get("schema") != double.PRIVATE_SCHEMA
            or manifest.get("status") != "DOUBLE_PASS_TRAIN_CANDIDATES__NOT_ADMITTED"
            or manifest.get("quality_v1_admitted") != 0
            or manifest.get("train_admitted") != 0
            or not isinstance(manifest.get("candidates"), list)):
        raise Hold("CANDIDATE_MANIFEST_HOLD")
    positions = []
    for row in manifest["candidates"]:
        if (not isinstance(row, dict)
                or set(row) != {"pilot_position", "status"}
                or type(row["pilot_position"]) is not int
                or row["status"] != "TRAIN_CANDIDATE__NOT_ADMITTED"):
            raise Hold("CANDIDATE_ENTRY_HOLD")
        positions.append(row["pilot_position"])
    if (len(positions) != 3 or len(set(positions)) != 3
            or any(x not in range(1, 21) for x in positions)):
        raise Hold("CANDIDATE_POSITION_HOLD")
    known_hits = 0
    for pilot_position in positions:
        packet = packet_rows[pilot_position - 1]
        source_position = packet["sample100_position"]
        if type(source_position) is not int or not 1 <= source_position <= 1000:
            raise Hold("SOURCE_POSITION_HOLD")
        source = cases[source_position - 1]
        if (packet["history_messages"] != source["history_messages"]
                or packet["assistant_target"] != source["target_text"]):
            raise Hold("SOURCE_BINDING_HOLD")
        known_hits += source["source"]["story_id"] in KNOWN_R50_STORIES
    return {
        "schema": SCHEMA,
        "status": "R50_KNOWN5_PARTIAL_CHECK_PASS__FULL_EXCLUSION_HOLD"
                  if known_hits == 0 else
                  "R50_KNOWN5_OVERLAP_FOUND__TRAIN_ADMISSION_HOLD",
        "source_reference": REFERENCE_DOC,
        "known_reference_story_count": 5,
        "frozen_pool_cases": 1000,
        "candidate_count": 3,
        "known5_story_overlap_count": known_hits,
        "r50_complete_exclusion_verified": False,
        "further_heldout_sources_required": True,
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
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--candidate-file", type=Path, required=True)
    args = p.parse_args()
    try:
        cases, _pool_sha = quality.frozen_pool(args.expand_dir)
        _config, packets, progress = pilot.get_state(args.review_dir)
        if progress["processed"] != 20:
            raise Hold("PILOT20_INCOMPLETE_HOLD")
        manifest = json.loads(private.read_private(
            args.candidate_file, 65536))
        safe = check(cases, packets["packets"], manifest)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - private values are never logged
        reason = str(exc) if isinstance(exc, Hold) else "R50_KNOWN5_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "R50_KNOWN5_CHECK_HOLD",
            "reason_code": reason,
            "r50_complete_exclusion_verified": False,
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

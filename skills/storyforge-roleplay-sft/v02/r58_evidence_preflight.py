#!/usr/bin/env python3
"""StoryForge R58 Skill v0.2 preview: offline G1/G2 SAFE evidence readiness.

Read only four pinned Git SAFE JSON blobs and this SAFE matrix. Never open
protected tests, private candidate ledgers, HF, Supabase, or training data.
No G1/G2 release can be emitted by this tool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = "storyforge-r58-g1-g2-safe-readiness-matrix-v1"
MATRIX_PATH = "docs/evidence/R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json"
PINS = {
    "known_five": ("8762bd20c0dc20b609988caecfeec26f8d142337",
                   "docs/evidence/R58_G1_KNOWN_FIVE_JOB_CURRENT_PRIMARY_INPUTS_CROSSCHECK_SAFE_20261031.json"),
    "round1": ("740cedf5b5f143b66965f5f7092d1f52f11cd8f8",
               "docs/evidence/R58_ROUND1_METADATA_PILOT_GATE_SAFE_20261030.json"),
    "g1_coverage": ("535bd253ac7dbcd88488fdcfb8a83744f1792775",
                    "docs/evidence/R58_ROUND1_G1_EVIDENCE_COVERAGE_SAFE_20261030.json"),
    "g2_gap": ("507fb5a47d8d9429a9efebe540f65b119f4c4677",
               "docs/evidence/R58_PRIORITY3_PROMPT_ASSEMBLY_GAP_MATRIX_SAFE_20261030.json"),
}
SCOPES = (
    "known_sft_frozen_splits",
    "known_five_update_jobs",
    "r50_five_protected_worlds",
    "gold195_13_source_worlds",
    "legacy_dev20_two_worlds",
    "r04_non_gold_two_worlds",
    "other_protected_worlds",
    "other_historical_parameter_update_jobs",
)


class Hold(ValueError):
    pass


def git_blob(repo: Path, sha: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Hold("invalid source pin")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", sha],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=25,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Hold("pinned source unavailable") from None
    if result.returncode or not 0 < len(result.stdout) <= 150_000:
        raise Hold("pinned source invalid")
    return result.stdout


def safe_json(data: bytes) -> dict:
    if not 0 < len(data) <= 150_000:
        raise Hold("evidence size invalid")
    try:
        obj = json.loads(data)
    except (UnicodeError, ValueError):
        raise Hold("evidence format invalid") from None
    if not isinstance(obj, dict):
        raise Hold("evidence must be an object")
    return obj


def verify(matrix: dict, sources: dict[str, dict]) -> dict:
    if matrix.get("schema") != SCHEMA or matrix.get("status") != (
        "G1_SOURCE_UNIVERSE_HOLD__G2_PROVIDER_REQUEST_HOLD__NO_ADMISSION"
    ):
        raise Hold("matrix schema/status mismatch")
    if matrix.get("citations") != {key: path for key, (_sha, path) in PINS.items()}:
        raise Hold("matrix citation drift")
    owner = matrix.get("owner_scope")
    if not isinstance(owner, dict) or (
        owner.get("original_candidate_worlds"),
        owner.get("known_sft_world_excluded"),
        owner.get("remaining_candidate_worlds_in_hold"),
        owner.get("max_reply_targets"),
        owner.get("owner_policy"),
    ) != (5, 1, 4, 20, "ONE_ROLEPLAY_STORY_UUID_PER_WORLD"):
        raise Hold("candidate scope drift")
    rows = matrix.get("g1_scopes")
    if not isinstance(rows, list) or len(rows) != len(SCOPES):
        raise Hold("G1 scope inventory missing")
    if [row.get("id") for row in rows if isinstance(row, dict)] != list(SCOPES):
        raise Hold("G1 scope IDs changed")
    for row in rows:
        if row.get("universe_complete") is not False or row.get("evidence") is None:
            raise Hold("unproven historical coverage promoted")
        if row.get("scope_observed") is not (row["id"] not in SCOPES[-2:]):
            raise Hold("observed scope mismatch")

    known = sources["known_five"]
    totals = known.get("totals", {})
    limits = known.get("limitations", {})
    if (
        known.get("schema") != "r58_g1_known_five_current_primary_inputs_aggregate_safe_v1"
        or known.get("g1_clearance") != "HOLD"
        or known.get("known_parameter_update_jobs_documented") != 5
        or totals.get("bucket_objects_compared") != 12
        or totals.get("six_known_frozen_split_placements_not_unique") != 184
        or totals.get("known_job_associated_split_placements_not_unique") != 344
        or limits.get("all_actual_sft_runs_and_input_sources_proven_complete") is not False
        or limits.get("all_historical_hf_jobs_classified") is not False
    ):
        raise Hold("known Job provenance mismatch")

    pilot = sources["round1"]
    hist = pilot.get("g1_historical_sft_exact_overlap_owner_20261030", {})
    protected = pilot.get("g1_r50_protected_uuid_probe", {})
    discovery = pilot.get("owner_local_discovery_verified_20261030", {})
    if (
        pilot.get("schema") != "storyforge-r58-round1-metadata-pilot-safe-v1"
        or hist.get("exact_identifier_overlap_count") != 1
        or hist.get("remaining_without_exact_identifier_overlap_count") != 4
        or protected.get("owner_r50_actual_intersection") != 0
        or protected.get("r50_lookup_bounded_remaining") != 4
        or discovery.get("eligible") != 1280
        or pilot.get("train_admitted") != 0
    ):
        raise Hold("Round1 owner scope mismatch")

    coverage = sources["g1_coverage"]
    if (
        coverage.get("schema") != "r58_round1_g1_evidence_coverage_safe_v1"
        or coverage.get("policy", {}).get("unknown_means") != "HOLD"
        or coverage.get("fixed_pilot", {}).get("story_records_under_review") != 5
    ):
        raise Hold("protected universe coverage drift")

    g2 = sources["g2_gap"]
    summary = g2.get("summary", {})
    current_g2 = matrix.get("g2_runtime")
    if (
        g2.get("schema") != "storyforge-r58-priority3-prompt-gap-matrix-safe-v1"
        or summary.get("components") != 19
        or summary.get("blocking_byte_exact_components") != 17
        or summary.get("direct_request_link_verified") is not False
        or summary.get("training_admission") != "HOLD"
        or not isinstance(current_g2, dict)
        or current_g2.get("prompt_components") != 19
        or current_g2.get("byte_exact_blocking_components") != 17
        or current_g2.get("direct_target_to_request_link_verified") is not False
        or current_g2.get("provider_original_request_bytes_verified") is not False
        or current_g2.get("status") != "HOLD"
    ):
        raise Hold("G2 request/provider byte gap drift")

    gate = matrix.get("gate", {})
    if (
        gate.get("g1_clearance") != "HOLD"
        or gate.get("g2_clearance") != "HOLD"
        or gate.get("g3_reviews") != "NOT_STARTED"
        or any(type(gate.get(key)) is not int or gate[key] != 0
               for key in ("train_admitted", "validation_admitted", "teacher_admitted"))
        or any(gate.get(key) is not False for key in (
            "expansion_allowed", "source_registry_complete",
            "all_actual_sft_runs_and_input_sources_proven_complete",
            "new_paid_hf_job_authorized",
        ))
    ):
        raise Hold("missing fail-closed gate")
    if not all(v is False for v in matrix.get("prohibitions", {}).values()) or (
        set(matrix.get("prohibitions", {})) != {
            "raw_story_text_exported", "private_candidate_uuids_exported",
            "r50_test_content_accessed", "job_started",
        }
    ):
        raise Hold("privacy invariant missing")
    return {
        "schema": "storyforge-r58-skill-v02-evidence-preflight-safe-v1",
        "status": "G1_G2_SAFE_EVIDENCE_RECONCILED__BOTH_HOLD",
        "known_update_jobs_current_inputs_matched": 5,
        "hf_bucket_objects_owner_reported_matched": 12,
        "known_frozen_split_placements": 184,
        "scoped_g1_inventory_rows": len(rows),
        "remaining_candidate_worlds_held": 4,
        "g2_blocking_byte_exact_components": 17,
        "direct_target_request_link_proven": False,
        "historical_training_universe_complete": False,
        "other_protected_universe_complete": False,
        "training_admitted": 0,
        "r50_content_read": False,
        "private_story_uuids_exported": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "expansion_allowed": False,
        "hf_job_started": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.repo_root
        if root.is_symlink() or not root.is_dir():
            raise Hold("unsafe Git root")
        target = root / MATRIX_PATH
        if target.is_symlink() or not target.is_file() or target.stat().st_size > 50_000:
            raise Hold("SAFE matrix missing or invalid")
        matrix = safe_json(target.read_bytes())
        docs = {key: safe_json(git_blob(root, sha))
                for key, (sha, _path) in PINS.items()}
        result = verify(matrix, docs)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (Hold, OSError, KeyError, TypeError, ValueError):
        print("R58_SKILL_V02_G1_G2: HOLD (SAFE evidence unavailable or inconsistent)", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

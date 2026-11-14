"""Read-only frozen R60 Base336 world metadata source coverage.

No inference from narrative text, same-name merges, DB requests or raw IDs.
Reports what the 336 validated source records *actually* carry; missing
cards/structured worlds need separate authenticated source evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_world_metadata_coverage_safe_v1"
SOURCE_KEYS = frozenset({
    "story_id", "session_id", "assistant_message_id",
    "prior_user_message_id", "previous_assistant_message_id",
    "previous_user_message_id", "assistant_turn_index",
})
META_FIELDS = (
    "story_title", "world_id", "world_component_id",
    "story_card_id", "character_card_id", "world_settings",
    "story_metadata", "character_card", "story_card",
)


class Hold(ValueError):
    pass


def inspect(cases: list[dict], manifest: dict) -> dict:
    if (len(cases) != 1000 or manifest.get("schema") != quarantine.SCHEMA
            or manifest.get("status") != "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD"
            or manifest.get("r50_complete_exclusion_verified") is not False
            or manifest.get("train_admitted") != 0
            or len(manifest.get("excluded_known5", [])) != 3
            or len(manifest.get("remaining_full_r50_hold", [])) != 336):
        raise Hold("FROZEN_SCOPE_HOLD")
    seen = set()
    worlds = set()
    layouts = Counter()
    coverage = Counter()
    provenance = Counter()
    for entry in manifest["remaining_full_r50_hold"]:
        pos = entry.get("position")
        if (type(pos) is not int or not 1 <= pos <= 1000
                or pos in seen or entry.get("status") !=
                "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD"):
            raise Hold("CANDIDATE_POSITION_HOLD")
        seen.add(pos)
        case = cases[pos - 1]
        source = case.get("source")
        if type(source) is not dict or not SOURCE_KEYS.issubset(source):
            raise Hold("SOURCE_ID_CONTRACT_HOLD")
        for k in SOURCE_KEYS - {"assistant_turn_index"}:
            if type(source[k]) is not str or not source[k]:
                raise Hold("SOURCE_ID_CONTRACT_HOLD")
        if type(source["assistant_turn_index"]) is not int:
            raise Hold("SOURCE_TURN_CONTRACT_HOLD")
        worlds.add(source["story_id"])
        layouts[tuple(sorted(source))] += 1
        for field in META_FIELDS:
            if field in source and source[field] is not None:
                coverage[field] += 1
        for name in ("historical_system_provenance",
                     "normalized_system_provenance",
                     "world_component_status"):
            value = case.get(name)
            if type(value) is not str or not value:
                raise Hold("PROVENANCE_FIELDS_HOLD")
            provenance[name + ":" + value] += 1
    if len(worlds) != 172 or len(seen) != 336:
        raise Hold("CASE_WORLD_COUNT_HOLD")
    # No raw layout names are printed: a future DB schema could have private keys.
    return {
        "schema": SCHEMA,
        "status": "BASE336_SOURCE_METADATA_COVERAGE_PASS__SEMANTIC_SOURCE_HOLD",
        "source_cases": len(seen),
        "story_id_count": len(worlds),
        "source_layout_variants": len(layouts),
        "source_rows_with_expected_id_fields": 336,
        "structured_metadata_field_coverage": {
            field: coverage[field] for field in META_FIELDS
        },
        "source_rows_with_any_structured_world_field": sum(
            any(cases[pos - 1]["source"].get(field) is not None
                for field in META_FIELDS) for pos in seen
        ),
        "source_provenance_class_counts": dict(sorted(provenance.items())),
        "original_story_metadata_authenticated": False,
        "original_character_cards_authenticated": False,
        "semantic_world_alias_complete": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "database_accessed": False,
        "database_modified": False,
        "model_requests": 0,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def run(args: argparse.Namespace) -> dict:
    cases, crosswalk = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(
        cases, crosswalk, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if saved != expected:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    return inspect(cases, saved)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        out = run(args)
        print(json.dumps(out, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private source excerpts in SAFE stdout
        print(json.dumps({
            "schema": SCHEMA,
            "status": "BASE336_WORLD_METADATA_COVERAGE_HOLD",
            "reason_code": "SOURCE_CONTRACT_OR_RUNTIME_HOLD",
            "train_admitted": 0, "database_accessed": False,
            "model_requests": 0, "hf_jobs_submitted": 0,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

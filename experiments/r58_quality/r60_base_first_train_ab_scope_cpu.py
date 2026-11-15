"""R60 first-train A/B risk fast-lane: source-bound, offline, NO admission.

Replays existing V123/R50/reviewer proofs and the exact 8-group roster.
Produces two create-only private scope reports. No DB, models or HF calls.
254 outside the known eight groups is NOT declared safe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import r60_base336_reviewer_provenance_cpu as review
import r60_base336_world_cross_split_private_roster_cpu as roster
import r60_base336_world_review_decisions_template_cpu as decisions
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_base_first_train_ab_scope_private_v1"
SAFE = "storyforge_r60_base_first_train_ab_scope_safe_v1"
A_FILE = "R60_BASE_FIRST_TRAIN_A_KNOWN_WORLD_RISK_PRIVATE.json"
B_FILE = "R60_BASE_FIRST_TRAIN_B_REVIEWER_EVIDENCE_PRIVATE.json"


class Hold(ValueError):
    pass


def analyze(groups: list[dict], manifest: dict, reviewer: dict, *, roster_sha: str) -> tuple[dict, dict, dict]:
    if not isinstance(roster_sha, str) or len(roster_sha) != 64:
        raise Hold("ROSTER_HASH_HOLD")
    if len(groups) != 8 or reviewer.get("cases_checked") != 336 or (
        reviewer.get("provider_execution_independence_verified") is not False
        or reviewer.get("reviewer_independence_verified") is not False
    ):
        raise Hold("REVIEW_SCOPE_HOLD")
    rows = manifest["remaining_full_r50_hold"]
    full_positions = [v["position"] for v in rows]
    if len(full_positions) != 336 or len(set(full_positions)) != 336:
        raise Hold("FROZEN_336_HOLD")
    member_positions = set()
    affected_stories = set()
    for group in groups:
        for member in group["members_PRIVATE"]:
            affected_stories.add(member["story_id_PRIVATE"])
            member_positions.update(member["candidate_positions_1based_PRIVATE"])
    full_set = set(full_positions)
    if (len(affected_stories) != 38 or len(member_positions) != 82
            or not member_positions <= full_set):
        raise Hold("WORLD_82_SCOPE_HOLD")
    outside = sorted(full_set - member_positions)
    if len(outside) != 254:
        raise Hold("OUTSIDE_SCOPE_HOLD")
    base = {
        "schema": SCHEMA,
        "roster_sha256_PRIVATE": roster_sha,
        "train_admitted": 0,
        "actual_training_candidates_approved": False,
        "full_r50_exclusion_verified": False,
    }
    a = {
        **base, "workstream": "A_WORLD_R50",
        "known_world_risk_positions_1based_PRIVATE": sorted(member_positions),
        "not_in_known_eight_groups_positions_1based_PRIVATE": outside,
        "scope_meaning": "NO_MATCH_TO_EIGHT_EXACT_WORLD_GROUPS_ONLY__NOT_WORLD_ISOLATION_PASS",
        "known_world_risk_stories": 38,
        "known_world_risk_cases": 82, "outside_known_risk_cases": 254,
        "codex_world_screening": {
            "generic_template": 7, "insufficient_evidence": 1,
            "confirmed_specific_shared_world": 0,
            "all_eight_isolation_hold": True,
            "source": "OWNER_REPORTED_SAFE_RECEIPT__NOT_REEVALUATED",
        },
        "remaining_gates": [
            "FULL_EVALUATION_PROTECTION", "CROSS_STORY_SEMANTIC_ALIAS",
            "WORLD_AND_ROLE_SOURCE_VERSION", "NEW_COMPONENT_TRAIN_VAL_SPLIT",
        ],
        "world_component_isolation_verified": False,
    }
    b = {
        **base, "workstream": "B_REVIEWER_INDEPENDENCE",
        "bounded_source_receipt_summary": reviewer["side_source_counts"],
        "side_models_distinct_in_config": True,
        "reviewer_source_receipts_verified": True,
        "owner_attestation_present":
            reviewer["v1_pool_config_owner_attestation_present"],
        "provider_execution_independence_verified": False,
        "reviewer_independence_verified": False,
        "execution_evidence_needed": [
            "EACH_SIDE_ACTUAL_PROVIDER_EXECUTION",
            "ISOLATED_REQUEST_CONTEXT",
            "NO_CROSS_REVIEWER_SCORE_OR_TEXT_IN_PROMPT",
            "SOURCE_RECEIPT_TO_EXECUTION_IDENTITY",
        ],
        "candidate_positions_1based_PRIVATE": sorted(full_set),
    }
    safe = {
        "schema": SAFE, "status": "BASE_FIRST_TRAIN_AB_SCOPE_BOUND__BOTH_HOLD",
        "frozen_cases": 336, "known_world_risk_cases": 82,
        "outside_known_world_risk_cases": 254,
        "known_world_risk_stories": 38,
        "reviewer_source_receipts_bound": True,
        "provider_execution_independence_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "real_candidate_contract_verified": False,
        "train_admitted": 0, "gpu_started": False,
        "hf_jobs_submitted": 0, "model_requests": 0,
        "database_accessed": False, "database_modified": False,
        "private_values_emitted": False,
    }
    return a, b, safe


def execute(args: argparse.Namespace) -> dict:
    cases, report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw_cross = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    manifest = quarantine.construct(cases, report, hashlib.sha256(raw_cross).hexdigest())
    previous = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME, quarantine.MAX_PRIVATE_REPORT))
    if manifest != previous:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    conf = json.loads(private.read_private(
        args.old_dir / batch.CONFIG_FILE, batch.MAX_CONFIG_BYTES))
    batch.validate_config(args.old_dir)
    reviewer = review.inspect(report, manifest, conf)
    roster_raw = private.read_private(
        args.roster_dir / roster.FILENAME, decisions.ROSTER_LIMIT)
    groups = decisions.validate(json.loads(roster_raw))
    a, b, safe = analyze(
        groups, manifest, reviewer, roster_sha=hashlib.sha256(roster_raw).hexdigest())
    if (args.output_dir.exists() or args.output_dir.is_symlink()
            or args.output_dir.parent != private.BASE):
        raise Hold("CREATE_ONLY_OUTPUT_HOLD")
    if not args.execute:
        return {**safe, "status": "BASE_FIRST_TRAIN_AB_SCOPE_PRECHECK__NO_WRITES",
                "private_files_created": 0}
    payloads = [
        (A_FILE, (json.dumps(a, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()),
        (B_FILE, (json.dumps(b, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()),
    ]
    if any(len(data) > private.MAX_CAPTURE_BYTES for _, data in payloads):
        raise Hold("OUTPUT_SIZE_HOLD")
    private.private_dir(args.output_dir, create=True)
    for name, data in payloads:
        private.write_new(args.output_dir / name, data)
    return {**safe, "private_files_created": 2}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", required=True, type=Path)
    p.add_argument("--roster-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(execute(args), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - suppress all private paths and content
        print(json.dumps({
            "schema": SAFE, "status": "BASE_FIRST_TRAIN_AB_SCOPE_HOLD",
            "train_admitted": 0, "gpu_started": False,
            "hf_jobs_submitted": 0, "model_requests": 0,
            "database_modified": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

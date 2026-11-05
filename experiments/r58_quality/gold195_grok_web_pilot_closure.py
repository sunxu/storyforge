#!/usr/bin/env python3
"""R58 Grok web pilot closure: 2 provisional dual passes, 1 unresolved HOLD.

Reads only authorized 3-case private material. Never upgrades pilot to
Quality-v1 or authorizes more samples, GPU, or any network calls.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from gold195_grok_web_triage import triage
from gold195_grok_web_followup_validate import followup
from gold195_case02_final_disposition import validate_decision
from gold195_grok_web_validate import read_private_json

SCHEMA = "r58_gold195_grok_web_pilot_closure_safe_v1"


def close(pilot: Path, follow: Path, decision: Path):
    first = triage(pilot)
    second = followup(pilot, follow)
    if len(first["cases"]) != 3:
        raise ValueError("unexpected pilot sample count")
    if any(first["cases"][0]["reviewer_" + who]["state"] != "PROVISIONAL_REVIEW_PASS"
           for who in ("A", "B")):
        raise ValueError("case01 not provisional dual pass")
    if second["review_states"]["case03_A_retry"] != "PROVISIONAL_REVIEW_PASS":
        raise ValueError("case03 A retry not valid")
    if second["review_states"]["case03_B_retry"] != "PROVISIONAL_REVIEW_PASS":
        raise ValueError("case03 B retry not valid")
    if second["review_states"]["case02_arbiter"] != (
        "ARBITER_DISPUTES_SEVERE__MANUAL_RESOLUTION_REQUIRED"
    ):
        raise ValueError("case02 source controversy differs")
    case02 = validate_decision(read_private_json(decision), pilot, follow)
    if case02 != "CASE02_UNRESOLVED__HOLD":
        raise ValueError("this closure specifically freezes the unresolved state")
    return {
        "schema": SCHEMA,
        "status": "THREE_CASE_GROK_WEB_PILOT_CLOSED__CASE02_HOLD",
        "pilot_gold_cases": 3,
        "original_web_reviews": 6,
        "targeted_followup_reviews": 3,
        "case01": "DUAL_PROVISIONAL_REVIEW_PASS__SEMANTIC_HOLD",
        "case02": "SEVERE_DISPUTE_UNRESOLVED__HOLD",
        "case03": "TWO_RETRIES_PROVISIONAL_PASS__SEMANTIC_HOLD",
        "dual_provisional_pass_cases": 2,
        "unresolved_severe_dispute_cases": 1,
        "web_response_validity_issues_observed_initially": 2,
        "web_response_validity_issues_corrected_for_case03": 2,
        "reviewer_independence_independently_proven": False,
        "literary_quality_independently_proven": False,
        "world_card_semantics_approved": False,
        "world_component_isolation_verified": False,
        "remaining_user_first_cases_external_review_authorized": 0,
        "assistant_first_132_context_policy_resolved": False,
        "next_decision": "OWNER_REVIEW_OF_PILOT_RELIABILITY_AND_FUTURE_SCOPE",
        "quality_v1_admitted": 0,
        "gpu_authorized": False,
        "hf_job_started": False,
        "r50_accessed": False,
        "network_called": False,
        "private_text_or_real_ids_emitted": False,
        "source_reviews_modified": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-pilot-dir", type=Path, required=True)
    p.add_argument("--private-followup-dir", type=Path, required=True)
    p.add_argument("--private-decision-input", type=Path, required=True)
    a = p.parse_args()
    try:
        report = close(a.private_pilot_dir, a.private_followup_dir,
                       a.private_decision_input)
        code = 0
    except Exception:
        report = {
            "schema": SCHEMA,
            "status": "PILOT_SOURCE_OR_DISPOSITION_INVALID__HOLD",
            "quality_v1_admitted": 0, "network_called": False,
            "r50_accessed": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

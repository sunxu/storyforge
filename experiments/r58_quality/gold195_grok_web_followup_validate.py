#!/usr/bin/env python3
"""SAFE follow-up verdict checks for Grok web pilot, without training admission.

Checks corrected Case03 A/B against same frozen target, and Case02 independent
arbitration exact quotes. Does not erase any originally flagged severe issue.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from gold195_grok_web_followup import make_packets
from gold195_grok_web_validate import read_private_json, check_review
from gold195_grok_web_triage import triage

ARBITER = ("CONFIRMED_SEVERE", "NOT_SUPPORTED", "UNCERTAIN")


def check_arbiter(obj, target):
    if not isinstance(obj, dict) or set(obj) != {
        "arbiter_verdict", "severe_flag_names", "gold_exact_quotes",
        "rule_or_card_evidence", "analysis", "remaining_uncertainty",
    }:
        return "ARBITER_FORMAT_HOLD"
    if obj["arbiter_verdict"] not in ARBITER:
        return "ARBITER_FORMAT_HOLD"
    for field in ("severe_flag_names", "gold_exact_quotes", "rule_or_card_evidence"):
        values = obj[field]
        if (not isinstance(values, list) or len(values) > 12
                or any(not isinstance(x, str) or not x.strip() or len(x) > 400
                       for x in values)):
            return "ARBITER_FORMAT_HOLD"
    if (not isinstance(obj["analysis"], str) or not obj["analysis"].strip()
            or len(obj["analysis"]) > 3000
            or not isinstance(obj["remaining_uncertainty"], str)
            or len(obj["remaining_uncertainty"]) > 1500):
        return "ARBITER_FORMAT_HOLD"
    if any(len(q) > 120 or q not in target for q in obj["gold_exact_quotes"]):
        return "ARBITER_QUOTE_NOT_IN_GOLD"
    if obj["arbiter_verdict"] == "CONFIRMED_SEVERE":
        if not obj["severe_flag_names"] or not obj["gold_exact_quotes"]:
            return "ARBITER_EVIDENCE_INCOMPLETE_HOLD"
    if obj["arbiter_verdict"] == "NOT_SUPPORTED":
        # No automated override of original severe flags.
        return "ARBITER_DISPUTES_SEVERE__MANUAL_RESOLUTION_REQUIRED"
    if obj["arbiter_verdict"] == "CONFIRMED_SEVERE":
        return "ARBITER_CONFIRMED_SEVERE__HOLD"
    return "ARBITER_UNCERTAIN__HOLD"


def followup(pilot: Path, folder: Path):
    # Verify original exact expected triage; no silent reassignment of cases.
    original = triage(pilot)
    if not (original["cases"][1]["reviewer_A"]["state"] == "SEVERE_FLAG"
            and original["cases"][1]["reviewer_B"]["state"] == "PROVISIONAL_REVIEW_PASS"
            and original["cases"][2]["reviewer_A"]["state"] == "MALFORMED"
            and original["cases"][2]["reviewer_B"]["state"] == "EVIDENCE_QUOTE_NOT_IN_GOLD"):
        raise ValueError("original source state changed")
    if not folder.is_absolute() or folder.is_symlink() or not folder.is_dir():
        raise ValueError("followup folder")
    # This also confirms the named original packets have the expected structure.
    make_packets(pilot)
    from stat import S_IMODE
    if S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("private followup permissions")
    manifest = read_private_json(pilot / "review-manifest.private.json")
    case02 = manifest["cases"][1]["target_text"]
    case03 = manifest["cases"][2]["target_text"]
    results = {}
    for label, path, target in (
        ("case02_arbiter", folder / "case02-independent-severe-arbitration.json", case02),
        ("case03_A_retry", folder / "case03-reviewer-A-retry.json", case03),
        ("case03_B_retry", folder / "case03-reviewer-B-retry.json", case03),
    ):
        if not path.exists():
            state = "NOT_SUBMITTED"
        else:
            try:
                data = read_private_json(path)
                state = (check_arbiter(data, target) if label == "case02_arbiter"
                         else check_review(data, target))
            except Exception:
                state = "INVALID_PRIVATE_JSON_HOLD"
        results[label] = state
    return {
        "schema": "r58_gold195_grok_web_followup_verdict_safe_v1",
        "status": "TARGETED_FOLLOWUP_REVIEW_STATUS__NO_TRAINING_ADMISSION",
        "review_states": results,
        "initial_severe_flag_preserved": True,
        "case03_retries_both_provisional_pass": all(
            results[k] == "PROVISIONAL_REVIEW_PASS"
            for k in ("case03_A_retry", "case03_B_retry")
        ),
        "no_auto_resolution_or_quality_approval": True,
        "story_or_case_ids_emitted": False,
        "quality_v1_admitted": 0, "r50_accessed": False,
        "network_called": False, "gpu_authorized": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-pilot-dir", type=Path, required=True)
    p.add_argument("--private-followup-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        result = followup(args.private_pilot_dir, args.private_followup_dir)
        code = 0
    except Exception:
        result = {
            "schema": "r58_gold195_grok_web_followup_verdict_safe_v1",
            "status": "FOLLOWUP_SOURCE_OR_RESULTS_INVALID__HOLD",
            "quality_v1_admitted": 0, "r50_accessed": False,
            "network_called": False,
        }
        code = 42
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

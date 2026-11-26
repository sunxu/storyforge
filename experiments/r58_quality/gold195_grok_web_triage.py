#!/usr/bin/env python3
"""SAFE case-level triage of 3x2 Grok web pilot reviews.

Do not modify reviews, infer missing content, or admit training rows.
Only emits case01..case03 labels and fixed status/action codes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from gold195_grok_web_validate import audit, read_private_json, check_review

ACTION = {
    "MISSING_REVIEW": "COMPLETE_MISSING_REVIEW",
    "MALFORMED": "RERUN_OR_REEXPORT_JSON_KEEP_ORIGINAL",
    "EVIDENCE_QUOTE_NOT_IN_GOLD": "RECHECK_EXACT_GOLD_QUOTES_KEEP_ORIGINAL",
    "SEVERE_FLAG": "INDEPENDENT_SEVERE_FLAG_ARBITRATION",
    "CARD_CONFLICT_OR_UNCERTAIN": "CARD_FACT_CONFLICT_REVIEW",
    "BELOW_SCORE_FLOOR": "QUALITY_SHORTFALL_REVIEW",
    "PASS_CANNOT_BE_SUPPORTED_WITHOUT_QUOTES": "REQUEST_GOLD_EXACT_QUOTES",
    "PROVISIONAL_REVIEW_PASS": "KEEP_PENDING_INDEPENDENT_QUALITY_CHECK",
}
INVALID = {"MISSING_REVIEW", "MALFORMED", "EVIDENCE_QUOTE_NOT_IN_GOLD"}


def triage(folder: Path):
    # Reuse existing private permissions and count/format guards.
    preliminary = audit(folder)
    manifest = read_private_json(folder / "review-manifest.private.json")
    cases = []
    for index, rec in enumerate(manifest["cases"], 1):
        label = "case%02d" % index
        states = {}
        for who in ("A", "B"):
            path = folder / ("%s-reviewer-%s.json" % (label, who))
            if not path.exists():
                status = "MISSING_REVIEW"
            else:
                try:
                    status = check_review(read_private_json(path), rec["target_text"])
                except Exception:
                    status = "MALFORMED"
            states[who] = {"state": status, "action": ACTION[status]}
        unreliable = any(v["state"] in INVALID for v in states.values())
        severe = any(v["state"] == "SEVERE_FLAG" for v in states.values())
        provisional = all(v["state"] == "PROVISIONAL_REVIEW_PASS"
                          for v in states.values())
        cases.append({
            "label": label, "reviewer_A": states["A"], "reviewer_B": states["B"],
            "retest_needed": unreliable,
            "serious_issue_flagged": severe,
            "two_reviews_provisional_pass": provisional,
            "next_gate": (
                "VERIFY_INVALID_RESPONSES_BEFORE_CONSENSUS" if unreliable
                else "INDEPENDENT_SEVERE_ARBITRATION" if severe
                else "SEMANTIC_CARD_AND_QUALITY_REVIEW_PENDING"
            ),
        })
    return {
        "schema": "r58_gold195_grok_web_case_triage_safe_v1",
        "status": "WEB_REVIEW_TRIAGE_READY__NO_TRAIN_ADMISSION",
        "cases": cases,
        "case_count": len(cases),
        "review_counts": preliminary["review_state_counts"],
        "private_content_or_case_ids_emitted": False,
        "original_reviews_modified": False,
        "reviewer_independence_proven": False,
        "quality_v1_admitted": 0,
        "world_component_verified": False,
        "r50_accessed": False, "network_called": False, "gpu_authorized": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-pilot-dir", type=Path, required=True)
    opts = p.parse_args()
    try:
        result = triage(opts.private_pilot_dir)
        code = 0
    except Exception:
        result = {
            "schema": "r58_gold195_grok_web_case_triage_safe_v1",
            "status": "PRIVATE_REVIEW_DATA_INVALID__HOLD",
            "quality_v1_admitted": 0,
            "r50_accessed": False, "network_called": False,
        }
        code = 42
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

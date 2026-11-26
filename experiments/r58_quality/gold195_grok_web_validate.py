#!/usr/bin/env python3
"""Validate two independent Grok web reviews for each of 3 private Gold cases.

Only compares local files; no network; never certifies a training dataset.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import stat

from gold195_grok_web_export import DIMENSIONS, FLAGS, MANIFEST_SCHEMA

FLOORS = dict(zip(DIMENSIONS, (4, 4, 3, 4, 4, 4)))
MAX_REVIEW_BYTES = 64 * 1024


def read_private_json(path: Path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("review file absent")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size < MAX_REVIEW_BYTES):
        raise ValueError("review permissions or size invalid")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check_review(review, target):
    if not isinstance(review, dict) or set(review) != {
        "scores", "severe_flags", "reasons", "card_design_verdict",
        "card_gold_conflicts", "evidence_quotes",
    }:
        return "MALFORMED"
    scores, flags, reasons = (
        review["scores"], review["severe_flags"], review["reasons"]
    )
    if (not isinstance(scores, dict) or set(scores) != set(DIMENSIONS)
            or any(type(scores[k]) is not int or not 1 <= scores[k] <= 5
                   for k in DIMENSIONS)):
        return "MALFORMED"
    if (not isinstance(flags, dict) or set(flags) != set(FLAGS)
            or any(type(flags[k]) is not bool for k in FLAGS)):
        return "MALFORMED"
    if (not isinstance(reasons, dict) or set(reasons) != set(DIMENSIONS)
            or any(not isinstance(reasons[k], str) or not reasons[k].strip()
                   or len(reasons[k]) > 1600 for k in DIMENSIONS)):
        return "MALFORMED"
    if review["card_design_verdict"] not in (
        "ACCEPTABLE_FOR_OFFLINE_REVIEW", "CONFLICT", "UNCERTAIN"
    ):
        return "MALFORMED"
    for field in ("card_gold_conflicts", "evidence_quotes"):
        values = review[field]
        if (not isinstance(values, list) or len(values) > 12
                or any(not isinstance(item, str) or len(item) > 400
                       for item in values)):
            return "MALFORMED"
    quotes = review["evidence_quotes"]
    if any(not quote.strip() or len(quote) > 120 or quote not in target
           for quote in quotes):
        return "EVIDENCE_QUOTE_NOT_IN_GOLD"
    if any(flags.values()):
        return "SEVERE_FLAG"
    if review["card_design_verdict"] != "ACCEPTABLE_FOR_OFFLINE_REVIEW":
        return "CARD_CONFLICT_OR_UNCERTAIN"
    if any(scores[k] < FLOORS[k] for k in DIMENSIONS):
        return "BELOW_SCORE_FLOOR"
    if not quotes:
        return "PASS_CANNOT_BE_SUPPORTED_WITHOUT_QUOTES"
    return "PROVISIONAL_REVIEW_PASS"


def audit(folder: Path):
    if not folder.is_absolute() or folder.is_symlink() or not folder.is_dir():
        raise ValueError("private folder not accessible")
    if stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("private folder permissions")
    manifest = read_private_json(folder / "review-manifest.private.json")
    if (not isinstance(manifest, dict)
            or manifest.get("schema") != MANIFEST_SCHEMA
            or not isinstance(manifest.get("cases"), list)
            or len(manifest["cases"]) != 3
            or manifest.get("quality_approved") is not False):
        raise ValueError("invalid private manifest")
    counts = Counter()
    by_case = []
    for index, record in enumerate(manifest["cases"], 1):
        label = "case%02d" % index
        if (not isinstance(record, dict) or record.get("label") != label
                or not isinstance(record.get("target_text"), str)
                or not record["target_text"]):
            raise ValueError("invalid manifest case")
        states = []
        for reviewer in ("A", "B"):
            file = folder / (label + "-reviewer-" + reviewer + ".json")
            if not file.is_file():
                state = "MISSING_REVIEW"
            else:
                try:
                    state = check_review(
                        read_private_json(file), record["target_text"])
                except Exception:
                    state = "MALFORMED"
            states.append(state)
            counts[state] += 1
        if all(x == "PROVISIONAL_REVIEW_PASS" for x in states):
            counts["two_reviewers_provisional_pass"] += 1
        elif states[0] != states[1]:
            counts["different_reviewer_outcomes"] += 1
        by_case.append(states)
    return {
        "schema": "r58_gold195_grok_web_review_validation_safe_v1",
        "status": "GROK_WEB_REVIEWS_VALIDATED__NO_TRAINING_ADMISSION",
        "cases_checked": 3, "reviews_expected": 6,
        "review_state_counts": dict(sorted(counts.items())),
        "all_six_reviews_present": counts["MISSING_REVIEW"] == 0,
        "two_reviewers_provisional_pass_cases": counts["two_reviewers_provisional_pass"],
        "case_ids_or_story_text_emitted": False,
        "reviewer_independence_proven_by_software": False,
        "literary_quality_independently_verified": False,
        "world_component_verified": False,
        "quality_v1_admitted": 0, "gpu_authorized": False,
        "r50_accessed": False, "network_called": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-pilot-dir", required=True, type=Path)
    a = p.parse_args()
    try:
        result = audit(a.private_pilot_dir)
        exit_code = 0
    except Exception:
        result = {
            "schema": "r58_gold195_grok_web_review_validation_safe_v1",
            "status": "REVIEW_FILES_OR_MANIFEST_INVALID__HOLD",
            "quality_v1_admitted": 0, "network_called": False,
            "r50_accessed": False,
        }
        exit_code = 42
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

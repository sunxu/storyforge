"""Read-only per-category reconciliation of QD20 disagreement blind evidence.

Rebinds validated, independent-but-self-attested blind decisions to the original
three disagreement categories without exposing private positions or model texts.
A verified independent judgment remains advisory, never training ground truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_qd20_evidence_review_cpu as review
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_qd20_evidence_reconcile_safe_v1"
CATEGORIES = ("NEW_ONLY_DOUBLE_PASS", "OLD_ONLY_DOUBLE_PASS")
DECISIONS = ("PASS", "HOLD", "REJECT")


class Hold(ValueError):
    pass


def reconcile(source: dict, blind: dict, decisions: dict) -> dict:
    # The strict verifier must succeed first: source binding, exact quotes,
    # six scores, severe flags and PASS floor cannot be bypassed here.
    verified = review.verify(source, blind, decisions)
    rows = review.source_cases(source)
    by_index = {d["blind_index"]: d for d in decisions["cases"]}
    cross = Counter()
    for i, source_row in enumerate(rows, 1):
        category = source_row["category"]
        if category not in CATEGORIES:
            raise Hold("UNKNOWN_DISAGREEMENT_CATEGORY_HOLD")
        cross[(category, by_index[i]["decision"])] += 1
    if (len(rows) != 3
            or sum(cross[(CATEGORIES[0], d)] for d in DECISIONS) != 2
            or sum(cross[(CATEGORIES[1], d)] for d in DECISIONS) != 1
            or sum(cross[(c, d)] for c in CATEGORIES for d in DECISIONS) != 3
            or any(
                sum(cross[(c, d)] for c in CATEGORIES)
                != verified["review_decisions"].get(d)
                for d in DECISIONS
            )):
        raise Hold("REVIEW_CATEGORY_BINDING_HOLD")
    return {
        "schema": SCHEMA,
        "status": "QD20_THREE_REVIEW_CROSSWALK_VALIDATED__NOT_GROUND_TRUTH",
        "reviewed_cases": 3,
        "new_only_double_pass_reviews": {
            d: cross[(CATEGORIES[0], d)] for d in DECISIONS
        },
        "old_only_double_pass_reviews": {
            d: cross[(CATEGORIES[1], d)] for d in DECISIONS
        },
        "all_review_decisions": verified["review_decisions"],
        "exact_quote_evidence_cases": verified["exact_quote_evidence_cases"],
        "reviewer_independence_self_attested_not_proven": True,
        "quality_ground_truth_established": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }


def run(source_dir: Path, blind_dir: Path, decisions_path: Path) -> dict:
    source = review.load_source(source_dir)
    private.private_dir(blind_dir, create=False)
    blind = json.loads(private.read_private(
        blind_dir / review.PACK_NAME, 200000))
    decisions = json.loads(private.read_private(decisions_path, 200000))
    return reconcile(source, blind, decisions)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--blind-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.source_dir, args.blind_dir, args.decisions),
                         sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - private paths and text hidden
        code = str(exc) if isinstance(exc, Hold) else "EVIDENCE_CROSSWALK_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "QD20_THREE_REVIEW_CROSSWALK_HOLD",
            "reason_code": code,
            "quality_v1_admitted": 0, "train_admitted": 0,
            "model_inference_calls": 0, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

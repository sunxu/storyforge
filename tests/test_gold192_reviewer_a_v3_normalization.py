"""Synthetic-only tests for verified V3 Reviewer A normalization."""
# ruff: noqa: I001
import json
import unittest

from storyforge_gold_quality.normalize_reviewer_a_v3 import normalize_v3


FIELDS = (
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
)
SCORES = {name: 4 for name in FIELDS}


def fixture():
    cases = []
    for i in range(192):
        cases.append({
            "case_id": f"synthetic-{i:03d}",
            "target_sha256": f"{i + 1:064x}",
            "cohort": "gold87" if i < 87 else "gold108",
        })
    packets = json.dumps({
        "story_uuid": "synthetic-story-uuid",
        "cases": cases,
    }).encode()
    scored = [{
        "case_id": f"synthetic-{i:03d}",
        "decision": "AI_SEMANTIC_PASS_ONLY",
        "scores_1_to_5": dict(SCORES),
        "note": "Synthetic test only",
    } for i in range(31)]
    cases31 = {
        "schema": "r58_gold192_ai_review_31_cases_private_v1",
        "counts": {"ai_semantic_pass_only": 31},
        "cases": scored,
    }
    supplement = {
        "schema": "r58_gold192_ai_review_minimum_supplement_private_v2",
        "case_level_ai_reviews": [dict(row, scores_1_to_5=dict(row["scores_1_to_5"])) for row in scored],
        "case_level_hold_groups": [{
            "reason": "SYNTHETIC_HOLD",
            "story": "Synthetic story",
            "case_ids": [f"synthetic-{i:03d}" for i in range(31, 82)],
        }],
        "reject_groups": [{
            "reason": "SYNTHETIC_REJECT",
            "story": "Synthetic story",
            "case_ids": ["synthetic-082"],
        }],
    }
    safe = {
        "schema": "r58_gold192_ai_semantic_review_safe_v2",
        "counts": {
            "candidate_cases": 192,
            "ai_semantic_pass_only": 140,
            "hold": 51,
            "reject": 1,
        },
    }
    b_decisions = ["PASS"] * 192
    for i, decision in zip(range(83, 185), ["PASS"] * 102):
        b_decisions[i] = decision
    for i, decision in zip(range(185, 191), ["HOLD"] * 6):
        b_decisions[i] = decision
    b_decisions[191] = "REJECT"
    for i in range(28):
        b_decisions[i] = "PASS"
    for i in range(28, 31):
        b_decisions[i] = "HOLD"
    for i in range(31, 78):
        b_decisions[i] = "PASS"
    for i in range(78, 81):
        b_decisions[i] = "HOLD"
    b_decisions[81] = "REJECT"
    b_decisions[82] = "PASS"
    b_cases = [{
        "target_sha256": f"{i + 1:064x}",
        "blind_case_id": f"RB-{i + 1:04d}",
        "decision": b_decisions[i],
        "scores_1_to_5": dict(SCORES),
        "evidence_summary": "Synthetic B rationale",
        "severe_flags": [],
    } for i in range(192)]
    reviewer_b = {
        "schema": "r58_gold192_reviewer_b_results_v1",
        "counts": {"PASS": 178, "HOLD": 12, "REJECT": 2},
        "cases": b_cases,
    }
    return safe, cases31, supplement, packets, reviewer_b


class NormalizeReviewerAV3Tests(unittest.TestCase):
    def test_v3_sources_reconcile_without_fabricated_scores(self):
        report, safe, queue = normalize_v3(*fixture())
        self.assertEqual(len(report["records"]), 192)
        self.assertEqual(report["decision_counts"],
                         {"PASS_ONLY": 140, "HOLD": 51, "REJECT": 1})
        self.assertEqual(report["evidence_granularity_counts"], {
            "case_level_scored_pass": 31,
            "explicit_hold_group_without_scores": 51,
            "explicit_reject_group_without_scores": 1,
            "aggregate_complement_pass_pending_case_evidence": 109,
        })
        self.assertEqual(report["strict_ab_score_comparison_eligible"], 31)
        self.assertEqual(safe["aggregate_only_b_nonpass_priority_count"], 7)
        self.assertEqual(safe["aggregate_only_b_nonpass_priority_decisions"],
                         {"HOLD": 6, "REJECT": 1})
        self.assertEqual(queue["case_count"], 7)
        self.assertTrue(all(x["reviewer_a_scores_1_to_5"] is None
                            and x["reviewer_a_actual_case_level_decision"] is None
                            for x in queue["cases"]))

    def test_supplement_31_must_match_private_31_exactly(self):
        safe, cases31, supplement, packets, reviewer_b = fixture()
        supplement["case_level_ai_reviews"][0]["note"] = "tampered"
        with self.assertRaisesRegex(ValueError, "CASES31_SUPPLEMENT_MISMATCH"):
            normalize_v3(safe, cases31, supplement, packets, reviewer_b)

    def test_hold_group_count_must_be_exact(self):
        safe, cases31, supplement, packets, reviewer_b = fixture()
        supplement["case_level_hold_groups"][0]["case_ids"].pop()
        with self.assertRaisesRegex(ValueError, "EXPLICIT_EVIDENCE_COUNTS_INVALID"):
            normalize_v3(safe, cases31, supplement, packets, reviewer_b)

    def test_reviewer_b_target_mismatch_fails(self):
        safe, cases31, supplement, packets, reviewer_b = fixture()
        reviewer_b["cases"][0]["target_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "REVIEWER_B_TARGET_SET_MISMATCH"):
            normalize_v3(safe, cases31, supplement, packets, reviewer_b)


if __name__ == "__main__":
    unittest.main()

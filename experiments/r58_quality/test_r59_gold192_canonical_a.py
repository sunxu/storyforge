"""Synthetic-only tests for the frozen Canonical Reviewer A V3 contract."""
from __future__ import annotations

import copy
import unittest

try:
    from . import r59_gold192_canonical_a as m
except ImportError:
    import r59_gold192_canonical_a as m

SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def fixture():
    records = []
    for i in range(192):
        if i < 31:
            granularity = "CASE_LEVEL_SCORED_REVIEW"
            decision, strict, scored, aggregate, scores = (
                "PASS_ONLY", "PASS_ONLY", True, False, dict(SCORES)
            )
        elif i < 82:
            granularity = "CASE_ID_IN_EXPLICIT_HOLD_GROUP"
            decision, strict, scored, aggregate, scores = (
                "HOLD", "HOLD", False, False, None
            )
        elif i == 82:
            granularity = "CASE_ID_IN_EXPLICIT_REJECT_GROUP"
            decision, strict, scored, aggregate, scores = (
                "REJECT", "REJECT", False, False, None
            )
        else:
            granularity = "AGGREGATE_COMPLEMENT_ONLY"
            decision, strict, scored, aggregate, scores = (
                "PASS_ONLY", None, False, True, None
            )
        records.append({
            "case_id": f"case-{i:03d}",
            "target_sha256": f"{i + 1:064x}",
            "reported_final_decision": decision,
            "decision_for_strict_ab_decision_comparison": strict,
            "evidence_granularity": granularity,
            "case_level_scored_review_present": scored,
            "aggregate_complement_only": aggregate,
            "scores_1_to_5": scores,
        })
    return {
        "schema": m.A_SCHEMA,
        "status": m.A_STATUS,
        "source_pins": dict(m.A_SOURCE_PINS),
        "records": records,
    }


class CanonicalReviewerAContractTests(unittest.TestCase):
    def test_accepts_frozen_v3_granularity_distribution(self):
        indexed = m.validate_reviewer_a_v3(fixture())
        self.assertEqual(len(indexed), 192)
        self.assertEqual(
            m.EXPECTED_GRANULARITY_COUNTS,
            {
                "CASE_LEVEL_SCORED_REVIEW": 31,
                "CASE_ID_IN_EXPLICIT_HOLD_GROUP": 51,
                "CASE_ID_IN_EXPLICIT_REJECT_GROUP": 1,
                "AGGREGATE_COMPLEMENT_ONLY": 109,
            },
        )

    def test_rejects_superseded_a_schema(self):
        report = fixture()
        report["schema"] = "superseded-r59-a-schema"
        with self.assertRaisesRegex(m.CanonicalReviewerAHold, "CANONICAL_A_V3_REQUIRED"):
            m.validate_reviewer_a_v3(report)

    def test_aggregate_complement_cannot_be_upgraded_by_legacy_pairing_field(self):
        report = fixture()
        row = report["records"][31]
        row["decision_for_strict_ab_pairing"] = "PASS_ONLY"
        row["decision_for_strict_ab_decision_comparison"] = "PASS_ONLY"
        with self.assertRaisesRegex(
            m.CanonicalReviewerAHold, "CANONICAL_A_GRANULARITY_RECORD_INVALID"
        ):
            m.validate_reviewer_a_v3(report)

    def test_scored_case_requires_all_six_integer_scores(self):
        report = fixture()
        report["records"][0]["scores_1_to_5"]["player_agency"] = True
        with self.assertRaisesRegex(
            m.CanonicalReviewerAHold, "CANONICAL_A_GRANULARITY_RECORD_INVALID"
        ):
            m.validate_reviewer_a_v3(report)

    def test_rejects_duplicate_target_or_case_identity(self):
        report = fixture()
        report["records"][1]["target_sha256"] = report["records"][0]["target_sha256"]
        with self.assertRaisesRegex(m.CanonicalReviewerAHold, "CANONICAL_A_IDENTITY_INVALID"):
            m.validate_reviewer_a_v3(report)

    def test_rejects_source_pin_mismatch(self):
        report = fixture()
        report["source_pins"]["cases31"] = "0" * 64
        with self.assertRaisesRegex(m.CanonicalReviewerAHold, "CANONICAL_A_SOURCE_PINS_INVALID"):
            m.validate_reviewer_a_v3(report)

    def test_does_not_mutate_report(self):
        report = fixture()
        before = copy.deepcopy(report)
        m.validate_reviewer_a_v3(report)
        self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()

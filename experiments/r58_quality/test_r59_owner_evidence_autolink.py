"""Synthetic-only tests for Canonical A V3 Owner evidence AutoLink."""
from __future__ import annotations

import json
import unittest

try:
    from .r59_gold192_canonical_a import (
        A_SHA, A_SCHEMA, A_STATUS, A_SOURCE_PINS, B_SHA, B_SCHEMA, B_COUNTS,
        PACKETS_SHA,
    )
    from .r59_owner_evidence_autolink import AutoLinkHold, build
except ImportError:
    from r59_gold192_canonical_a import (
        A_SHA, A_SCHEMA, A_STATUS, A_SOURCE_PINS, B_SHA, B_SCHEMA, B_COUNTS,
        PACKETS_SHA,
    )
    from r59_owner_evidence_autolink import AutoLinkHold, build

PIN_A = "a" * 64
PIN_B = "b" * 64
PIN_C = "c" * 64
SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def packet_case():
    return {
        "case_id": "private-case-1",
        "target_sha256": PIN_A,
        "history": [{"role": "assistant", "content": "private-history"}],
        "current_user_text": "private-user",
        "target_assistant_text": "private-target",
    }


def packets(include_candidate=True):
    rows = []
    for i in range(13):
        rows.append({
            "schema": "private-packet-v1",
            "cases": [packet_case()] if i == 0 and include_candidate else [],
            "world_card": {"world": {"worldSentence": "private-world"}},
            "world_card_sha256": PIN_C,
            "world_card_source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
            "world_card_review_status": "UNREVIEWED",
            "world_card_approved_for_system": False,
        })
    return rows


def reviewer_docs():
    a_records = []
    b_cases = []
    for i in range(192):
        case_id = "private-case-1" if i == 0 else f"private-case-{i + 1}"
        target = PIN_A if i == 0 else f"{i:064x}"
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
        a_records.append({
            "case_id": case_id,
            "target_sha256": target,
            "reported_final_decision": decision,
            "decision_for_strict_ab_decision_comparison": strict,
            "evidence_granularity": granularity,
            "case_level_scored_review_present": scored,
            "aggregate_complement_only": aggregate,
            "scores_1_to_5": scores,
        })
        b_decision = "PASS" if i < 178 else "HOLD" if i < 190 else "REJECT"
        b_cases.append({
            "target_sha256": target,
            "decision": b_decision,
            "scores_1_to_5": dict(SCORES),
            "severe_flags": [],
            "blind_case_id": f"blind-{i:03d}",
        })
    return (
        {
            "schema": A_SCHEMA,
            "status": A_STATUS,
            "source_pins": dict(A_SOURCE_PINS),
            "records": a_records,
        },
        {"schema": B_SCHEMA, "counts": dict(B_COUNTS), "cases": b_cases},
    )


def stage():
    return {
        "schema": "storyforge-quality-v1-source-staging-private-v1",
        "status": "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
        "case_id": "private-case-1",
        "target_sha256": PIN_A,
        "story_id": "private-story-1",
        "session_id": "private-session-1",
    }


def owner():
    return {
        "case_id": "private-case-1",
        "target_sha256": PIN_A,
        "story_id": "private-story-1",
        "session_id": "private-session-1",
        "source_version_sha256": None,
        "world_graph_sha256": None,
        "world_component_id": None,
        "split": None,
        "evidence": {},
    }


class OwnerEvidenceAutolinkTests(unittest.TestCase):
    def test_adds_exact_v3_locators_without_owner_attestations(self):
        a, b = reviewer_docs()
        rows, safe = build(
            packets(), [stage()], a, b, [owner()],
            PACKETS_SHA, "b" * 64, A_SHA, B_SHA,
        )
        row = rows[0]
        self.assertIn("#records[0]", row["reviewer_a_evidence_ref"])
        self.assertIn("#cases[0]", row["reviewer_b_evidence_ref"])
        self.assertIn(".cases[0]", row["packet_case_evidence_ref"])
        self.assertEqual(row["reviewer_a_evidence_granularity"], "CASE_LEVEL_SCORED_REVIEW")
        self.assertTrue(row["reviewer_a_case_level_scored_review_present"])
        self.assertEqual(row["world_card_snapshot_source_kind"],
                         "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST")
        self.assertIsNone(row["source_version_sha256"])
        self.assertIsNone(row["world_graph_sha256"])
        self.assertIsNone(row["split"])
        self.assertEqual(row["evidence"], {})
        self.assertEqual(safe["owner_attestations_created"], 0)
        self.assertEqual(safe["reviewer_a_evidence_granularity_counts"], {
            "CASE_LEVEL_SCORED_REVIEW": 1
        })
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["reviewer_independence_proven"])
        self.assertFalse(safe["training_authorized"])
        rendered = json.dumps(safe)
        self.assertNotIn("private-case-1", rendered)
        self.assertNotIn("private-history", rendered)

    def test_aggregate_complement_locator_is_explicitly_not_case_scored(self):
        a, b = reviewer_docs()
        aggregate = a["records"][83]
        a["records"][0].update({
            "reported_final_decision": "PASS_ONLY",
            "decision_for_strict_ab_decision_comparison": None,
            "evidence_granularity": "AGGREGATE_COMPLEMENT_ONLY",
            "case_level_scored_review_present": False,
            "aggregate_complement_only": True,
            "scores_1_to_5": None,
        })
        aggregate.update({
            "reported_final_decision": "PASS_ONLY",
            "decision_for_strict_ab_decision_comparison": "PASS_ONLY",
            "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW",
            "case_level_scored_review_present": True,
            "aggregate_complement_only": False,
            "scores_1_to_5": dict(SCORES),
        })
        rows, safe = build(
            packets(), [stage()], a, b, [owner()],
            PACKETS_SHA, "b" * 64, A_SHA, B_SHA,
        )
        self.assertEqual(rows[0]["reviewer_a_evidence_granularity"],
                         "AGGREGATE_COMPLEMENT_ONLY")
        self.assertFalse(rows[0]["reviewer_a_case_level_scored_review_present"])
        self.assertEqual(safe["reviewer_a_evidence_granularity_counts"], {
            "AGGREGATE_COMPLEMENT_ONLY": 1
        })

    def test_superseded_reviewer_a_schema_holds(self):
        a, b = reviewer_docs()
        a["schema"] = "superseded-r59-a-schema"
        with self.assertRaisesRegex(AutoLinkHold, "CANONICAL_A_V3_REQUIRED"):
            build(packets(), [stage()], a, b, [owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)

    def test_a_case_identity_mismatch_holds(self):
        a, b = reviewer_docs()
        a["records"][0]["case_id"] = "private-other"
        with self.assertRaises(AutoLinkHold):
            build(packets(), [stage()], a, b, [owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)

    def test_packet_missing_exact_case_holds(self):
        a, b = reviewer_docs()
        with self.assertRaises(AutoLinkHold):
            build(packets(False), [stage()], a, b, [owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)

    def test_duplicate_owner_case_holds(self):
        a, b = reviewer_docs()
        with self.assertRaises(AutoLinkHold):
            build(packets(), [stage()], a, b, [owner(), owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)


if __name__ == "__main__":
    unittest.main()

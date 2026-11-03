import json
import unittest

from r59_gold192_supabase_extract import A_SHA, B_SHA, PACKETS_SHA
from r59_owner_evidence_autolink import (
    AutoLinkHold,
    build,
)

PIN_A = "a" * 64
PIN_B = "b" * 64
PIN_C = "c" * 64


def packet_case():
    return {
        "case_id": "private-case-1",
        "target_sha256": PIN_A,
        "history": [{"role": "assistant", "content": "private-history"}],
        "current_user_text": "private-user",
        "target_assistant_text": "private-target",
    }


def packet():
    return {
        "schema": "private-packet-v1",
        "cases": [packet_case()],
        "world_card": {"world": {"worldSentence": "private-world"}},
        "world_card_sha256": PIN_C,
        "world_card_source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
        "world_card_review_status": "UNREVIEWED",
        "world_card_approved_for_system": False,
    }


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
    def test_adds_exact_locators_without_owner_attestations(self):
        a = {"records": [{"case_id": "private-case-1", "target_sha256": PIN_A}]}
        b = {"cases": [{"target_sha256": PIN_A}]}
        rows, safe = build(
            [packet()], [stage()], a, b, [owner()],
            PACKETS_SHA, "b" * 64, A_SHA, B_SHA,
        )
        row = rows[0]
        self.assertIn("#records[0]", row["reviewer_a_evidence_ref"])
        self.assertIn("#cases[0]", row["reviewer_b_evidence_ref"])
        self.assertIn(".cases[0]", row["packet_case_evidence_ref"])
        self.assertEqual(row["world_card_snapshot_source_kind"],
                         "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST")
        self.assertIsNone(row["source_version_sha256"])
        self.assertIsNone(row["world_graph_sha256"])
        self.assertIsNone(row["split"])
        self.assertEqual(row["evidence"], {})
        self.assertEqual(safe["owner_attestations_created"], 0)
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["reviewer_independence_proven"])
        self.assertFalse(safe["training_authorized"])
        rendered = json.dumps(safe)
        self.assertNotIn("private-case-1", rendered)
        self.assertNotIn("private-history", rendered)

    def test_a_case_identity_mismatch_holds(self):
        a = {"records": [{"case_id": "private-other", "target_sha256": PIN_A}]}
        b = {"cases": [{"target_sha256": PIN_A}]}
        with self.assertRaises(AutoLinkHold):
            build([packet()], [stage()], a, b, [owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)

    def test_packet_missing_exact_case_holds(self):
        a = {"records": [{"case_id": "private-case-1", "target_sha256": PIN_A}]}
        b = {"cases": [{"target_sha256": PIN_A}]}
        with self.assertRaises(AutoLinkHold):
            build([], [stage()], a, b, [owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)

    def test_duplicate_owner_case_holds(self):
        a = {"records": [{"case_id": "private-case-1", "target_sha256": PIN_A}]}
        b = {"cases": [{"target_sha256": PIN_A}]}
        with self.assertRaises(AutoLinkHold):
            build([packet()], [stage()], a, b, [owner(), owner()],
                  PACKETS_SHA, "b" * 64, A_SHA, B_SHA)


if __name__ == "__main__":
    unittest.main()

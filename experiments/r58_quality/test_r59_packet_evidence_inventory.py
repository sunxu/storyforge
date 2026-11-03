import json
import unittest

from r59_packet_evidence_inventory import (
    PacketInventoryHold,
    build_inventory,
)

PIN_A = "a" * 64
PIN_B = "b" * 64
PIN_C = "c" * 64


def case(case_id="private-case-1", target=PIN_A):
    return {
        "case_id": case_id,
        "target_sha256": target,
        "history": [
            {"role": "assistant", "content": "private-history"},
            {"role": "user", "content": "private-user"},
        ],
        "current_user_text": "private-current-user",
        "target_assistant_text": "private-target",
    }


def packet(cases=None):
    return {
        "schema": "private-packet-schema-v1",
        "status": "private-packet-status",
        "cases": [case()] if cases is None else cases,
        "world_card": {"world": {"worldSentence": "private-world"}},
        "world_card_sha256": PIN_C,
        "world_card_source_kind": "EXPORT_SNAPSHOT",
        "world_card_review_status": "UNAPPROVED",
        "world_card_approved_for_system": False,
        "review_protocol": {
            "two_independent_blinded_reviews_required": True,
            "source_world_card_is_unapproved": True,
            "do_not_infer_missing_world_facts": True,
            "check_card_gold_contradictions": True,
        },
        "review_protocol_addendum": {
            "card_is_export_snapshot_not_historical_request": True,
            "do_not_assume_card_was_available_at_target_time": True,
            "preserve_leading_assistant_context_without_silent_deletion": True,
            "review_each_target_against_visible_history_and_card": True,
            "world_card_approval_is_separate_from_sample_quality": True,
        },
    }


def staged(case_id="private-case-1", target=PIN_A):
    return {
        "schema": "storyforge-quality-v1-source-staging-private-v1",
        "status": "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
        "case_id": case_id,
        "target_sha256": target,
    }


class PacketEvidenceInventoryTests(unittest.TestCase):
    def test_exact_association_emits_private_locator_and_aggregate_safe(self):
        safe, private = build_inventory(
            [packet()], [staged()], PIN_A, PIN_B
        )
        self.assertEqual(safe["candidate_exact_matches"], 1)
        self.assertEqual(safe["packet_case_objects"], 1)
        self.assertEqual(safe["packets_with_candidate_matches"], 1)
        self.assertEqual(safe["histories_start_with_assistant"], 1)
        self.assertFalse(safe["source_version_verified"])
        self.assertFalse(safe["historical_snapshot_temporality_proven"])
        self.assertEqual(safe["quality_v1_admitted"], 0)
        rendered = json.dumps(safe)
        self.assertNotIn("private-case-1", rendered)
        self.assertNotIn("private-history", rendered)
        self.assertNotIn(PIN_A, rendered)
        self.assertEqual(private["associations"][0]["packet_row_1based"], 1)
        self.assertEqual(private["associations"][0]["case_index_0based"], 0)

    def test_unmatched_candidate_is_hold(self):
        safe, _ = build_inventory(
            [packet()], [staged("private-other", PIN_B)], PIN_A, PIN_B
        )
        self.assertEqual(safe["candidate_exact_matches"], 0)
        self.assertEqual(safe["candidate_unmatched"], 1)
        self.assertEqual(safe["status"], "PACKET_EVIDENCE_ASSOCIATION_HOLD")

    def test_duplicate_packet_identity_holds(self):
        with self.assertRaises(PacketInventoryHold):
            build_inventory(
                [packet([case(), case()])], [staged()], PIN_A, PIN_B
            )

    def test_duplicate_staged_identity_holds(self):
        with self.assertRaises(PacketInventoryHold):
            build_inventory(
                [packet()], [staged(), staged()], PIN_A, PIN_B
            )

    def test_export_card_never_proves_historical_availability(self):
        safe, private = build_inventory(
            [packet()], [staged()], PIN_A, PIN_B
        )
        self.assertEqual(safe["world_card_approval_counts"], {"false": 1})
        self.assertFalse(safe["historical_snapshot_temporality_proven"])
        self.assertFalse(safe["world_component_isolation_proven"])
        self.assertIs(private["associations"][0]["packet_world_card_approved_for_system"], False)

    def test_invalid_history_message_holds(self):
        bad = case()
        bad["history"] = [{"role": "tool", "content": "private"}]
        with self.assertRaises(PacketInventoryHold):
            build_inventory(
                [packet([bad])], [staged()], PIN_A, PIN_B
            )

    def test_packet_schema_mismatch_holds(self):
        other = packet()
        other["schema"] = "different-schema"
        with self.assertRaises(PacketInventoryHold):
            build_inventory([packet(), other], [staged()], PIN_A, PIN_B)


if __name__ == "__main__":
    unittest.main()

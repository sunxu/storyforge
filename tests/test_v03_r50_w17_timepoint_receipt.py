"""Synthetic-only regression: metadata chronology never certifies runtime card."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

FILE = (Path(__file__).resolve().parents[1] /
        "docs/evidence/V03_R50_W17_TIMEPOINT_METADATA_OWNER_RECEIPT_20261019.json")


class TimepointOwnerReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FILE.read_text(encoding="utf8"))

    def test_cited_w17_source_message_time_integrity(self):
        x = self.data
        self.assertEqual(x["w17_citations_in_review"], 26)
        self.assertEqual(x["w17_citations_with_timestamp"], 26)
        self.assertEqual(x["w17_citations_without_timestamp"], 0)
        self.assertEqual(x["w17_citations_outside_reported_chat_window"], 0)

    def test_timestamps_do_not_prove_effective_card(self):
        x = self.data
        self.assertTrue(x["export_card_last_edit_precedes_first_chat_message"])
        self.assertEqual(x["all_historical_card_fields_valid_at_actual_prompt_cutoff"],
                         "NOT_CERTIFIED")
        self.assertTrue(x["export_card_last_edit_is_only_metadata_not_runtime_prompt_proof"])

    def test_historical_version_absence_keeps_hold(self):
        x = self.data
        self.assertEqual(x["card_metadata"]["historical_content_version_count"], 0)
        self.assertEqual(x["card_metadata"]["moderation_snapshot_count"], 0)
        self.assertEqual(x["full_chat_story_arc_and_transitive_alias_graph"], "HOLD")

    def test_no_unapproved_model_promotion_or_seal(self):
        x = self.data
        self.assertEqual(x["semantic_world_graph_gate"], "HOLD")
        self.assertEqual(x["heldout_final_seal"], "NOT_PERFORMED")
        self.assertFalse(x["r50_46_cases_mutated"])
        self.assertTrue(x["no_private_story_or_case_text_in_git"])


if __name__ == "__main__":
    unittest.main()

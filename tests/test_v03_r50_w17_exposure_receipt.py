"""Synthetic policy invariants for the owner-side W17 receipt."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REPORT = (Path(__file__).resolve().parents[1]
          / "docs/evidence/V03_R50_W17_LITERAL_EXPOSURE_46_OWNER_VERIFIED_20261016.json")


class W17ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text(encoding="utf8"))

    def test_exact_three_pairs_one_literal(self):
        x = self.report["source_scope"]
        self.assertEqual(x["flagged_old_to_r50_pairs"],
                         [[2, 17], [4, 17], [10, 17]])
        self.assertEqual(x["distinct_exact_long_literals"], 1)
        self.assertEqual(x["matched_literal_normalized_length_codepoints"], 322)
        self.assertEqual(x["matched_old_assistant_message_occurrences"], 3)
        self.assertEqual(x["matched_new_assistant_message_occurrences"], 3)
        self.assertEqual(x["distinct_sampled_120char_windows"], 5)
        self.assertTrue(x["sampled_windows_all_explained_by_exact_literal"])

    def test_exact_prompt_exposure_all_zero(self):
        x = self.report["private_prompt_exposure"]
        self.assertEqual(x["total_retained_cases_checked"], 46)
        self.assertEqual(x["w17_retained_case_count"], 10)
        for key in ("w17_cases_containing_shared_long_literal",
                    "w17_cases_containing_shared_120_window"):
            self.assertEqual(x[key], {
                "history": 0, "world_card": 0,
                "long_term_rules": 0, "user_input": 0,
            })
        self.assertIs(x["common_system_contains_literal"], False)
        self.assertIs(x["common_system_contains_120_window"], False)

    def test_semantic_hard_gates_remain_hold(self):
        x = self.report["gate_decisions"]
        self.assertEqual(x["semantic_world_identity_and_alias_graph"], "HOLD")
        self.assertEqual(x["final_heldout_seal"], "NOT_PERFORMED")
        self.assertEqual(x["shared_literal_content_type"],
                         "UNDETERMINED_WITHOUT_READING_ORIGINAL_322_CHARACTER_MESSAGE")
        self.assertFalse(x["model_promotion"])
        self.assertEqual(self.report["verification_level"],
                         "OWNER_LOCAL_OUTPUT_REVIEWED__NO_INDEPENDENT_PRIVATE_RAW_REHASH_BY_ASSISTANT")

    def test_no_private_text_in_receipt(self):
        self.assertNotIn('"content":', REPORT.read_text(encoding="utf8"))
        self.assertEqual(self.report["privacy"][:22], "Counts and source rank")


if __name__ == "__main__":
    unittest.main()

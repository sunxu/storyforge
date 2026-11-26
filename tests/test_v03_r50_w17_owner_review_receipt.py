"""Synthetic-only regression: owner-reported W17 verdict receipt is HOLD.

This does not read private source or impersonate an independent semantic review.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

RECEIPT = (Path(__file__).resolve().parents[1]
           / "docs/evidence/V03_R50_W17_AI_REVIEW_OWNER_REPORT_20261019.json")


class W17OwnerReportedHoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads(RECEIPT.read_text(encoding="utf8"))

    def test_verified_status_but_not_substantive_review_pass(self):
        d = self.value
        self.assertEqual(d["owner_local_status"],
                         "R50_W17_PRIVATE_AI_DECISIONS_SCHEMA_VALIDATED__SEMANTIC_HOLD")
        self.assertEqual(d["semantic_world_alias_independence"], "HOLD")
        self.assertEqual(d["final_heldout_seal"], "NOT_PERFORMED")
        self.assertFalse(d["private_decision_independence_or_reasoning_verified_by_assistant"])

    def test_three_pairs_all_insufficient_26_pointers(self):
        d = self.value
        pairs = d["reviewed_pairs"]
        self.assertEqual([(p["old_rank"], p["new_rank"]) for p in pairs],
                         [(2, 17), (4, 17), (10, 17)])
        self.assertTrue(all(p["decision"] == "INSUFFICIENT_EVIDENCE"
                            for p in pairs))
        self.assertEqual(sum(p["evidence_pointer_count"] for p in pairs), 26)
        self.assertEqual(d["remaining_evidence_item_count"], 7)
        self.assertEqual(d["possible_transitive_link_to_w17"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(d["known_old_world_link"], [4, 7])

    def test_template_is_attributed_ai_opinion_not_semantic_certification(self):
        d = self.value
        self.assertEqual(d["shared_literal_type"]["reviewed_label"],
                         "PLATFORM_TEMPLATE")
        self.assertEqual(d["shared_literal_type"]["assistant_substantive_confirmation"],
                         "NOT_INDEPENDENTLY_READ")
        self.assertEqual(d["owner_local_git_status"],
                         "DRY_RUN_NO_GIT_WRITE__USE_PUSH_ONLY_AFTER_REVIEW")

    def test_only_metadata_not_private_story_text(self):
        d = self.value
        self.assertEqual(d["private_decision_sha256"],
                         "UNAVAILABLE_FROM_SANITIZED_TERMINAL_OUTPUT__USE_ORIGINAL_VALIDATOR_PUSH")
        self.assertFalse(d["private_decision_file_content_available_to_github_connector"])
        self.assertFalse(d["data_admission_or_model_promotion"])
        self.assertEqual(d["r50_case_count_retained"], 46)


if __name__ == "__main__":
    unittest.main()

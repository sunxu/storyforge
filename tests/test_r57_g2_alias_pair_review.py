"""Synthetic-only 55-pair Owner alias review: private UUIDs, fail closed, no approval."""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g2_alias_pair_review", ROOT / "scripts" / "r57_g2_alias_pair_review.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

from test_r57_g2_owner_world_review_roster import fixture


class TestG2AliasPairReview(unittest.TestCase):
    def setUp(self):
        self.payloads = fixture()
        self.original = mod.expected_questions(self.payloads)

    def test_55_manual_pairs_54_to_history_plus_one_candidate_pair(self):
        packet = self.original
        items = packet["questions_PRIVATE"]
        self.assertEqual(len(items), 55)
        self.assertEqual(sum(x["comparison_kind"] == "GOLD_VS_HISTORICAL_SFT"
                             for x in items), 54)
        self.assertEqual(sum(x["comparison_kind"] == "GOLD_VS_GOLD"
                             for x in items), 1)
        self.assertEqual(len({(r["candidate_world_uuid_PRIVATE"],
                               r["compare_world_uuid_PRIVATE"]) for r in items}), 55)
        self.assertEqual({r["owner_decision"] for r in items}, {"UNREVIEWED"})
        self.assertFalse(packet["all_world_independence_certified"])

    def test_fresh_safe_stats_have_no_world_uuids(self):
        report = mod.review_counts(self.original, self.original)
        self.assertEqual(report["unreviewed_pair_count"], 55)
        self.assertEqual(report["reviewed_pair_count"], 0)
        self.assertEqual(report["decision_counts"]["LINKED_WITH_EVIDENCE"], 0)
        self.assertEqual(report["decision_counts"]["DISTINCT_WITH_EVIDENCE"], 0)
        self.assertEqual(report["dataset_v04_admitted"], 0)
        self.assertFalse(report["source_pins_reverified_by_cli"])
        self.assertFalse(report["world_independence_certified"])
        self.assertNotIn(self.original["questions_PRIVATE"][0]["candidate_world_uuid_PRIVATE"],
                         json.dumps(report))
        self.assertNotIn("newworld14", json.dumps(report))
        self.assertNotIn("oldworld", json.dumps(report))

    def test_filled_manual_decision_with_evidence_is_count_only(self):
        packet = json.loads(json.dumps(self.original))
        row = packet["questions_PRIVATE"][0]
        row["owner_decision"] = "LINKED_WITH_EVIDENCE"
        row["evidence_reference_PRIVATE"] = "private-approved-story-card-index-v3"
        row["owner_notes_PRIVATE"] = "Synthetic role collision verified manually"
        report = mod.review_counts(packet, self.original)
        self.assertEqual(report["decision_counts"]["LINKED_WITH_EVIDENCE"], 1)
        self.assertEqual(report["unreviewed_pair_count"], 54)
        self.assertFalse(report["independent_semantic_alias_review_complete"])
        self.assertFalse(report["owner_alias_component_signoff_complete"])
        self.assertNotIn("private-approved-story-card-index-v3", json.dumps(report))

    def test_evidence_is_required_even_for_distinct_verdict(self):
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"][0]["owner_decision"] = "DISTINCT_WITH_EVIDENCE"
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_hold_with_evidence_is_not_owner_approval(self):
        packet = json.loads(json.dumps(self.original))
        row = packet["questions_PRIVATE"][0]
        row["owner_decision"] = "HOLD_INSUFFICIENT_EVIDENCE"
        row["evidence_reference_PRIVATE"] = "private-note-001"
        report = mod.review_counts(packet, self.original)
        self.assertEqual(report["decision_counts"]["HOLD_INSUFFICIENT_EVIDENCE"], 1)
        self.assertFalse(report["world_independence_certified"])

    def test_missing_pair_denied(self):
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"].pop()
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_duplicate_pair_denied(self):
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"][1] = packet["questions_PRIVATE"][0]
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_modified_world_uuid_denied(self):
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"][0]["compare_world_uuid_PRIVATE"] = "synthetic-unknown-world"
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_fabricated_approval_or_training_flag_denied(self):
        for key, value in [
            ("all_world_independence_certified", True),
            ("dataset_v04_admitted", 32),
            ("training_authorized", True),
        ]:
            with self.subTest(key=key):
                packet = json.loads(json.dumps(self.original))
                packet[key] = value
                with self.assertRaises(mod.PairReviewHold):
                    mod.review_counts(packet, self.original)

    def test_protected_evaluation_reference_is_denied(self):
        packet = json.loads(json.dumps(self.original))
        row = packet["questions_PRIVATE"][0]
        row["owner_decision"] = "LINKED_WITH_EVIDENCE"
        row["evidence_reference_PRIVATE"] = "r50-protected-source"
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_unknown_key_or_decision_denied(self):
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"][0]["extra"] = "not allowed"
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"][0]["owner_decision"] = "AUTO_APPROVED"
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_unknown_or_unreviewed_with_fabricated_evidence_denied(self):
        packet = json.loads(json.dumps(self.original))
        packet["questions_PRIVATE"][0]["evidence_reference_PRIVATE"] = "evidence-not-yet-reviewed"
        with self.assertRaises(mod.PairReviewHold):
            mod.review_counts(packet, self.original)

    def test_filename_cannot_escape_private_root_or_use_r50(self):
        self.assertTrue(mod.PAIR_FILE.fullmatch(
            "R57_G2_ALIAS_EDGE_REVIEW_20261026_152600_PRIVATE.json"
        ))
        for name in ["../outside", "R50_PRIVATE.json", "draft.json",
                     "R57_G2_ALIAS_EDGE_REVIEW_20261026_1526_PRIVATE.json"]:
            self.assertFalse(mod.PAIR_FILE.fullmatch(name))


if __name__ == "__main__":
    unittest.main()

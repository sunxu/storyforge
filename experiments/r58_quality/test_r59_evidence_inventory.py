import json
import os
import tempfile
import unittest
from pathlib import Path

from r59_evidence_inventory import (
    STAGED_SCHEMA,
    STAGED_STATUS,
    InventoryHold,
    _read_private,
    build_report,
)


def candidate(case="private-case", target="a" * 64, story="private-story"):
    return {
        "schema": STAGED_SCHEMA, "status": STAGED_STATUS,
        "case_id": case, "target_sha256": target, "story_id": story,
    }


class EvidenceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.staged = [candidate()]
        self.locators = [{
            "case_id": "private-case", "target_sha256": "a" * 64,
            "message_id": "private-message", "turn_index": 7,
        }]
        self.drafts = [{
            "story_id": "private-story", "updated_at": "private-time",
            "v2_data": {
                "world": {}, "components": {}, "character": {},
                "characters": [], "director": {}, "opening": {}, "visual": {},
            },
        }]
        self.exposure = [{
            "case_id": "private-case", "target_sha256": "a" * 64,
            "status": "NOT_FOUND_IN_PINNED_HISTORY",
            "train_exposed": False, "validation_exposed": False,
            "test_exposed": False,
        }]

    def test_exact_associations_and_world_shape(self):
        report = build_report(self.staged, self.locators, self.drafts, self.exposure)
        self.assertEqual(report["source_locator_exact_matches"], 1)
        self.assertEqual(report["candidate_stories_with_draft"], 1)
        self.assertEqual(report["historical_exposure_exact_matches"], 1)
        self.assertEqual(report["world_field_presence"]["world"], 1)
        self.assertFalse(report["exposure_not_found_is_proof_of_non_exposure"])
        self.assertEqual(report["quality_v1_admitted"], 0)
        self.assertFalse(report["private_values_emitted"])

    def test_no_private_identifiers_in_report(self):
        report = build_report(self.staged, self.locators, self.drafts, self.exposure)
        serialized = json.dumps(report)
        for secret in ("private-case", "private-story", "private-message",
                       "private-time", "a" * 64):
            self.assertNotIn(secret, serialized)

    def test_duplicate_candidate_identity_holds(self):
        with self.assertRaises(InventoryHold):
            build_report(self.staged + self.staged, self.locators,
                         self.drafts, self.exposure)

    def test_duplicate_exact_locator_pair_holds(self):
        with self.assertRaises(InventoryHold):
            build_report(self.staged, self.locators * 2,
                         self.drafts, self.exposure)

    def test_multiple_historical_drafts_are_counted_not_rejected(self):
        second = dict(self.drafts[0])
        second["updated_at"] = "another-private-time"
        second["v2_data"] = {"world": {"private": "different"}}
        report = build_report(
            self.staged, self.locators, self.drafts + [second], self.exposure
        )
        self.assertEqual(report["candidate_stories_with_multiple_drafts"], 1)
        self.assertEqual(report["story_draft_records_for_candidate_stories"], 2)
        self.assertEqual(report["stories_with_multiple_v2_snapshots"], 1)
        self.assertEqual(report["stories_with_multiple_world_component_snapshots"], 1)
        self.assertFalse(report["snapshot_fingerprints_emitted"])

    def test_not_found_does_not_prove_non_exposure(self):
        report = build_report(self.staged, self.locators, self.drafts, self.exposure)
        self.assertEqual(report["historical_exposure_status_counts"],
                         {"NOT_FOUND_IN_PINNED_HISTORY": 1})
        self.assertFalse(report["protected_set_completeness_proven"])

    def test_private_file_mode_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            os.chmod(path, 0o644)
            with self.assertRaises(InventoryHold):
                _read_private(path)
            os.chmod(path, 0o600)
            self.assertTrue(_read_private(path))

    def test_hold_rows_are_not_candidates(self):
        hold = {
            "schema": STAGED_SCHEMA, "status": "SOURCE_STRUCTURE_HOLD",
            "case_id": "held", "target_sha256": "b" * 64,
            "story_id": "private-story",
        }
        report = build_report(self.staged + [hold], self.locators,
                              self.drafts, self.exposure)
        self.assertEqual(report["staged_rows_read"], 2)
        self.assertEqual(report["staged_candidates"], 1)


if __name__ == "__main__":
    unittest.main()

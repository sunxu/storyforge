#!/usr/bin/env python3
"""Synthetic-only checks for existing private filename receipt re-use."""
from __future__ import annotations

import unittest

from r58_g1_existing_filename_candidates_review_sheet_safe_20261101 import (
    EXPECTED_COUNTS,
    SOURCE_BASE,
    Hold,
    make_review,
    validate_source_path,
)


def synthetic_manifest() -> dict:
    common = [str(SOURCE_BASE / "r52/world_isolation" / f"metadata_{i}.json")
              for i in range(8)]
    other = [str(SOURCE_BASE / "r57/private" / f"dev_metadata_{i}.json")
             for i in range(14)]
    return {
        "schema": "r58_g1_filename_candidates_private_v1",
        "protected_set_contents_accessed": False,
        "candidate_paths_by_scope": {
            "semantic_world_graph": common,
            "r50_protected_worlds": [],
            "prior_sft_exposure": common[:2],
            "r55_r57_dev_worlds": common[:5] + other,
            "other_protected_or_holdout": [],
        },
    }


class TestExistingFilenameCandidateReview(unittest.TestCase):
    def test_frozen_counts_and_private_selection(self):
        safe, private = make_review(synthetic_manifest())
        self.assertEqual(safe["candidate_counts_by_scope"], EXPECTED_COUNTS)
        self.assertEqual(safe["unique_private_candidate_path_count"], 22)
        self.assertEqual(safe["scope_candidate_rows"], 29)
        self.assertEqual(safe["private_review_rows_owner_approved"], 0)
        self.assertEqual(len(private["entries_PRIVATE"]), 29)
        self.assertTrue(all(not x["owner_approved_metadata_only_source"]
                            for x in private["entries_PRIVATE"]))
        self.assertTrue(all(x["review_status"] == "UNREVIEWED_FILENAME_ONLY"
                            for x in private["entries_PRIVATE"]))
        self.assertFalse(safe["actual_source_index_contents_read"])
        self.assertFalse(safe["existing_private_inventory_modified"])
        self.assertEqual(safe["g1_clearance"], "HOLD")

    def test_reject_protected_scope_appearing(self):
        m = synthetic_manifest()
        m["candidate_paths_by_scope"]["r50_protected_worlds"].append(
            str(SOURCE_BASE / "r57/private/r50_metadata.json"))
        with self.assertRaises(Hold):
            make_review(m)

    def test_reject_scope_or_unique_count_drift(self):
        m = synthetic_manifest()
        m["candidate_paths_by_scope"]["r55_r57_dev_worlds"][-1] = (
            m["candidate_paths_by_scope"]["semantic_world_graph"][6]
        )
        with self.assertRaises(Hold):
            make_review(m)
        m = synthetic_manifest()
        m["candidate_paths_by_scope"].pop("other_protected_or_holdout")
        with self.assertRaises(Hold):
            make_review(m)

    def test_reject_bad_metadata_receipt(self):
        m = synthetic_manifest()
        m["protected_set_contents_accessed"] = True
        with self.assertRaises(Hold):
            make_review(m)

    def test_reject_private_traversal_and_outside_source(self):
        for value in (
            str(SOURCE_BASE / "r50/private/story.json"),
            str(SOURCE_BASE / "r57/private/../secret.json"),
            "relative/source.json",
            "not a string",
        ):
            with self.subTest(value=value):
                with self.assertRaises(Hold):
                    validate_source_path(value)
        with self.assertRaises(Hold):
            validate_source_path(str(SOURCE_BASE / "r52/world_review/notes.zip"))

    def test_safe_aggregate_contains_no_paths_or_private_filenames(self):
        safe, private = make_review(synthetic_manifest())
        import json
        output = json.dumps(safe)
        self.assertNotIn(str(SOURCE_BASE), output)
        self.assertNotIn("metadata_0.json", output)
        self.assertIn("source_reference_PRIVATE", private["entries_PRIVATE"][0])

    def test_refuse_duplicate_within_scope(self):
        m = synthetic_manifest()
        m["candidate_paths_by_scope"]["semantic_world_graph"][1] = (
            m["candidate_paths_by_scope"]["semantic_world_graph"][0]
        )
        with self.assertRaises(Hold):
            make_review(m)


if __name__ == "__main__":
    unittest.main()

"""Count-only consistency assertions on Owner-returned R57 eight-source evidence.

These tests DO NOT repeat the owner's private raw-byte audit. They only check
that public aggregate arithmetic and evidence boundaries cannot silently drift.
"""

import itertools
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT / "docs" / "evidence" /
    "R57_G2_EIGHT_SOURCE_OWNER_EXACT_REPLAY_SAFE_20261026.json"
)
NAMES = {
    "GOLD87", "GOLD108", "V01_TRAIN", "V01_VALIDATION",
    "R46_TRAIN", "R46_VALIDATION", "R54_TRAIN", "R54_VALIDATION",
}


class TestR57OwnerEightSourceReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECEIPT.read_text(encoding="utf-8"))
        pairs = cls.record["pairwise"]["nonzero_target"]
        cls.pairmap = {
            frozenset((row["left"], row["right"])): row["count"]
            for row in pairs
        }

    def overlap(self, left, right):
        return self.pairmap.get(frozenset((left, right)), 0)

    def test_eight_historical_rows_and_28_pairs(self):
        record = self.record
        self.assertEqual(set(record["sources"]), NAMES)
        self.assertEqual(record["sources"], {
            "GOLD87": 87, "GOLD108": 108,
            "V01_TRAIN": 65, "V01_VALIDATION": 15,
            "R46_TRAIN": 49, "R46_VALIDATION": 15,
            "R54_TRAIN": 31, "R54_VALIDATION": 9,
        })
        self.assertEqual(record["pairwise"]["total_pairs"], 28)
        self.assertEqual(len(self.pairmap), 7)
        self.assertEqual(
            len(tuple(itertools.combinations(NAMES, 2))), 28
        )
        for key, count in self.pairmap.items():
            a, b = key
            self.assertTrue(key <= NAMES)
            self.assertLessEqual(count, min(record["sources"][a], record["sources"][b]))
            self.assertGreater(count, 0)

    def test_all_old_train_and_validation_targets_are_inside_gold(self):
        self.assertEqual(
            self.overlap("GOLD87", "R46_TRAIN") +
            self.overlap("GOLD108", "R46_TRAIN"), 49
        )
        self.assertEqual(
            self.overlap("GOLD87", "R46_VALIDATION") +
            self.overlap("GOLD108", "R46_VALIDATION"), 15
        )
        self.assertEqual(self.overlap("GOLD108", "R54_TRAIN"), 31)
        self.assertEqual(self.overlap("GOLD108", "R54_VALIDATION"), 9)
        self.assertEqual(self.overlap("GOLD87", "R54_TRAIN"), 0)
        self.assertEqual(self.overlap("GOLD87", "R54_VALIDATION"), 0)

    def test_14_9_8_and_five_identical_full_sequences(self):
        source = self.record["frozen_historical_replay"]
        self.assertEqual(
            [source["r54_train_in_r46_train"],
             source["r54_train_in_r46_validation"],
             source["r54_train_absent_from_r46_splits"]],
            [14, 9, 8],
        )
        self.assertEqual(sum((
            source["r54_train_in_r46_train"],
            source["r54_train_in_r46_validation"],
            source["r54_train_absent_from_r46_splits"],
        )), 31)
        self.assertEqual(self.overlap("R46_TRAIN", "R54_TRAIN"), 14)
        self.assertEqual(self.overlap("R46_VALIDATION", "R54_TRAIN"), 9)
        self.assertEqual(
            source["exact_full_role_content_sequences_between_r46_and_r54_train"], 5
        )
        self.assertEqual(
            len([r for r in self.record["pairwise"]["nonzero_target"]
                 if r.get("role_content_full_exact", 0) > 0]), 1
        )

    def test_gold_pool_unique_exposures_are_consistent(self):
        g87 = self.record["gold_pools"]["GOLD87"]
        g108 = self.record["gold_pools"]["GOLD108"]
        total = self.record["gold_totals"]

        # Two historical train pools are disjoint inside GOLD87.
        self.assertEqual(g87["ever_train_exact_targets"], 20)
        self.assertEqual(g87["ever_validation_exact_targets"], 0)
        self.assertEqual(g87["both_train_and_validation_exact"], 0)

        # GOLD108: R46 Train29 + R54 Train31 - shared14 = 46.
        self.assertEqual(g108["ever_train_exact_targets"], 29 + 31 - 14)
        # GOLD108: R46 Val15 + R54 Val9; no intersection.
        self.assertEqual(g108["ever_validation_exact_targets"], 15 + 9)
        # R46 Val9 later in R54 Train -> seen in both kinds of split.
        self.assertEqual(g108["both_train_and_validation_exact"], 9)

        for bucket in (g87, g108, total):
            self.assertEqual(
                bucket["any_historical_exact_target_exposure"],
                bucket["ever_train_exact_targets"] +
                bucket["ever_validation_exact_targets"] -
                bucket["both_train_and_validation_exact"],
            )
            self.assertEqual(
                bucket["no_historical_exact_target_match"],
                bucket["rows"] - bucket["any_historical_exact_target_exposure"],
            )
        self.assertEqual(total["rows"], g87["rows"] + g108["rows"])
        for col in (
            "ever_train_exact_targets",
            "ever_validation_exact_targets",
            "both_train_and_validation_exact",
            "any_historical_exact_target_exposure",
            "no_historical_exact_target_match",
        ):
            self.assertEqual(total[col], g87[col] + g108[col])
        self.assertEqual(
            (total["ever_train_exact_targets"],
             total["ever_validation_exact_targets"],
             total["both_train_and_validation_exact"],
             total["any_historical_exact_target_exposure"],
             total["no_historical_exact_target_match"]),
            (66, 24, 9, 81, 114),
        )
        self.assertEqual(g87["no_historical_exact_target_match"], 67)
        self.assertEqual(g108["no_historical_exact_target_match"], 47)

    def test_audit_is_owner_returned_not_private_byte_attestation(self):
        record = self.record
        self.assertIn("OWNER_RETURNED", record["evidence_tier"])
        self.assertTrue(record["byte_pins_checked_by_owner_cli"])
        self.assertFalse(record["authenticated_source_bytes_read_by_assistant"])
        limits = record["limits"]
        self.assertFalse(limits["world_alias_component_mapping_verified"])
        self.assertFalse(limits["independent_rights_age_consent_quality_admission_done"])
        self.assertFalse(limits["r50_content_accessed"])
        self.assertFalse(limits["training_authorized"])
        self.assertFalse(limits["gpu_training_started"])
        self.assertEqual(limits["v04_admitted_samples"], 0)
        self.assertTrue(limits["r55_four_hold_cases_unchanged"])


if __name__ == "__main__":
    unittest.main()

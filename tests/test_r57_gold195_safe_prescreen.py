"""Synthetic-logic validation of R57 count-only Gold195 primary-read receipt."""

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs" / "evidence" / "R57_G2_G3_GOLD195_METADATA_PRESCREEN_SAFE_20261026.json"


class TestGold195SafeMetadataReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.sources = {x["id"]: x for x in cls.data["sources"]}

    def test_expected_only_four_nonprotected_sources(self):
        self.assertEqual(set(self.sources), {
            "GOLD87", "GOLD108", "V01_TRAIN", "V01_VALIDATION"
        })
        self.assertEqual({k: self.sources[k]["rows"] for k in self.sources},
                         {"GOLD87": 87, "GOLD108": 108,
                          "V01_TRAIN": 65, "V01_VALIDATION": 15})

    def test_all_195_targets_recomputed_and_declared_digest_rechecks_match(self):
        a, b = self.sources["GOLD87"], self.sources["GOLD108"]
        self.assertEqual(a["target_digest_verified"] + b["target_digest_verified"], 195)
        self.assertEqual(a["target_digest_mismatch"] + b["target_digest_mismatch"], 0)
        self.assertEqual(a["training_admission_pending"] + b["training_admission_pending"], 195)
        self.assertEqual(self.data["gold195"]["recomputed_unique_target_sha256"], 195)

    def test_mixed_source_fields_account_for_all_gold108(self):
        d = self.sources["GOLD108"]
        self.assertEqual(d["metadata_story_id_and_target_sha256_rows"], 105)
        self.assertEqual(d["metadata_source_story_id_and_target_content_sha256_rows"], 3)
        self.assertEqual(105 + 3, d["rows"])
        self.assertEqual(d["alternate_three_with_new_uuid"], 0)
        self.assertEqual(self.data["gold195"]["distinct_story_uuid"], 13)

    def test_legacy_reviews_missing_and_not_promoted(self):
        self.assertEqual(self.sources["GOLD87"]["independent_gold_review_not_run"], 87)
        self.assertEqual(
            self.sources["GOLD108"]["explicit_independent_ab_review_not_run"] +
            self.sources["GOLD108"]["independent_ab_review_field_missing"], 108
        )
        self.assertEqual(self.data["gold195"]["dataset_v04_admitted"], 0)
        self.assertEqual(self.data["gold195"]["g3_actual_sampled"], 0)
        self.assertTrue(self.data["limits"]["independent_review_complete"] is False)

    def test_exposure_and_privacy_boundary(self):
        pair = self.data["pairwise"]
        self.assertEqual(pair["exact_target_sha256_matches_across_all_six_pairs"], 0)
        self.assertEqual(pair["world_uuid_overlap_gold87_v01_train"], 1)
        self.assertEqual(pair["other_five_pairwise_world_uuid_overlaps"], 0)
        limits = self.data["limits"]
        self.assertFalse(limits["protected_r50_content_accessed"])
        self.assertFalse(limits["actual_r46_r54_trainer_source_read"])
        self.assertFalse(limits["alias_world_component_graph_verified"])
        self.assertFalse(limits["train_or_gpu_started"])


if __name__ == "__main__":
    unittest.main()

"""Synthetic-only tests for G2 target-anchored UUID mapping, with no private data."""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g2_target_anchored_world_audit",
    ROOT / "scripts" / "r57_g2_target_anchored_world_audit.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

from test_r57_g3_private_exposure_ledger import fake_eight_sources  # noqa: E402


class TestTargetAnchoredWorldAudit(unittest.TestCase):
    def setUp(self):
        self.data = fake_eight_sources()

    def test_all_compiled_trainer_targets_uniquely_linked(self):
        result = mod.audit(self.data)
        self.assertEqual(result["compiled_trainer_rows_uniquely_mapped_to_gold195"], {
            "R46_TRAIN": 49, "R46_VALIDATION": 15,
            "R54_TRAIN": 31, "R54_VALIDATION": 9,
        })
        self.assertEqual(result["gold_target_exposure_totals"], {
            "TRAIN_ONLY": 57, "VALIDATION_ONLY": 15,
            "BOTH_TRAIN_AND_VALIDATION": 9, "NO_EXACT_TARGET_IN_PRIOR_SFT": 114,
        })
        self.assertIn("SEMANTIC_ALIAS_HOLD", result["status"])

    def test_28_uuid_pairs_and_one_known_v01_world(self):
        result = mod.audit(self.data)
        self.assertEqual(len(result["pairwise_exact_uuid_overlap"]), 28)
        hits = next(row for row in result["pairwise_exact_uuid_overlap"]
                    if (row["a"], row["b"]) == ("GOLD87", "V01_TRAIN"))
        self.assertEqual(hits["shared_exact_story_uuids"], 1)
        self.assertEqual(hits["a_rows_with_shared_story_uuid"], 21)
        self.assertEqual(result["within_run_train_val_uuid_overlap"]["V01"][
            "train_validation_shared_story_uuid_count"
        ], 0)
        self.assertFalse(result["world_isolation_certified"])

    def test_no_exact_match_can_still_share_a_training_world(self):
        result = mod.audit(self.data)
        pool = result["gold_target_exposure_cross_uuid_counts"]
        g87 = pool["GOLD87"]["NO_EXACT_TARGET_IN_PRIOR_SFT"]
        g108 = pool["GOLD108"]["NO_EXACT_TARGET_IN_PRIOR_SFT"]
        self.assertEqual((g87["rows"], g108["rows"]), (67, 47))
        self.assertEqual(g87["also_historical_train_world_uuid"], 1)
        self.assertEqual(g108["also_historical_train_world_uuid"], 47)
        self.assertEqual(g87["also_any_historical_world_uuid"] +
                         g108["also_any_historical_world_uuid"], 48)

    def test_missing_gold_target_in_compiled_validation_blocks(self):
        rows = [json.loads(line) for line in self.data["R54_VALIDATION"].splitlines()]
        rows[0]["messages"][-1]["content"] = "other synthetic target not in any Gold"
        self.data["R54_VALIDATION"] = (
            "".join(json.dumps(x) + "\n" for x in rows).encode("utf-8")
        )
        with self.assertRaises(mod.WorldJoinHold):
            mod.audit(self.data)

    def test_missing_v01_source_story_uuid_blocks(self):
        rows = [json.loads(line) for line in self.data["V01_TRAIN"].splitlines()]
        rows[0]["metadata"].pop("story_id")
        self.data["V01_TRAIN"] = (
            "".join(json.dumps(x) + "\n" for x in rows).encode("utf-8")
        )
        with self.assertRaises(mod.WorldJoinHold):
            mod.audit(self.data)

    def test_incomplete_eight_sources_blocks(self):
        self.data.pop("R54_VALIDATION")
        with self.assertRaises(mod.WorldJoinHold):
            mod.audit(self.data)

    def test_report_has_no_private_identifiers_or_historical_hashes(self):
        result = mod.audit(self.data)
        safe = json.dumps(result)
        self.assertNotIn("same-v01-world", safe)
        self.assertNotIn("g108-synthetic-answer", safe)
        self.assertNotIn("other-world-0", safe)
        self.assertNotIn("source_row_ordinal", safe)
        self.assertFalse(result["source_byte_pins_verified_by_cli"])
        self.assertFalse(result["r50_content_accessed"])
        self.assertFalse(result["training_authorized"])
        self.assertEqual(result["dataset_v04_admitted"], 0)


if __name__ == "__main__":
    unittest.main()

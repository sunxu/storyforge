"""Synthetic-only R57 G3 exact exposure ledger regressions; no story text."""

import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g3_private_exposure_ledger",
    ROOT / "scripts" / "r57_g3_private_exposure_ledger.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _item(source, target, question, ordinal):
    record = {
        "messages": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": target},
        ],
    }
    if source == "GOLD87":
        record["metadata"] = {
            "story_id": "same-v01-world" if ordinal < 21 else f"other-world-{ordinal % 4}",
            "training_admission": "PENDING_NOT_APPROVED",
            "target_sha256_utf8": _digest(target),
        }
    elif source == "GOLD108":
        meta = {"training_admission": "PENDING_NOT_APPROVED"}
        if ordinal < 90:
            meta.update({"story_id": f"gold108-world-{ordinal%8}", "target_sha256": _digest(target)})
        elif ordinal < 105:
            meta.update({"story_id": f"gold108-world-{ordinal%8}", "target_sha256_utf8": _digest(target)})
        else:
            meta.update({
                "source_story_id": f"gold108-world-{ordinal%8}",
                "target_content_sha256": _digest(target),
            })
        record["metadata"] = meta
    elif source.startswith("V01_"):
        record["metadata"] = {
            "story_id": "same-v01-world" if source == "V01_TRAIN" and ordinal == 0
            else f"v01-other-{source}-{ordinal}",
        }
    return record


def _wire(items):
    return "".join(json.dumps(x) + "\n" for x in items).encode("utf-8")


def fake_eight_sources():
    gold87 = [f"g87-synthetic-answer-{i}" for i in range(87)]
    gold108 = [f"g108-synthetic-answer-{i}" for i in range(108)]
    old_v01_train = [f"v01-train-synthetic-{i}" for i in range(65)]
    old_v01_val = [f"v01-validation-synthetic-{i}" for i in range(15)]
    r46_train_targets = gold87[:20] + gold108[:29]
    r46_val_targets = gold108[29:44]
    r54_train_targets = gold108[:14] + gold108[29:38] + gold108[44:52]
    r54_val_targets = gold108[52:61]
    labels = {
        "GOLD87": gold87,
        "GOLD108": gold108,
        "V01_TRAIN": old_v01_train,
        "V01_VALIDATION": old_v01_val,
        "R46_TRAIN": r46_train_targets,
        "R46_VALIDATION": r46_val_targets,
        "R54_TRAIN": r54_train_targets,
        "R54_VALIDATION": r54_val_targets,
    }
    prepared = {}
    for source, targets in labels.items():
        items = []
        for i, target in enumerate(targets):
            # 5 of 14 R54 train target repeats have the same role/content history
            # as corresponding R46 train rows; other target repeats have new context.
            if source == "R54_TRAIN" and i < 5:
                query = f"r46-target-input-{20 + i}"
            elif source == "R46_TRAIN":
                query = f"r46-target-input-{i}"
            else:
                query = f"synthetic-query-{source}-{i}"
            items.append(_item(source, target, query, i))
        prepared[source] = _wire(items)
    return prepared


class TestG3PrivateExposureLedger(unittest.TestCase):
    def setUp(self):
        self.sources = fake_eight_sources()

    def test_expected_target_membership_57_15_9_114(self):
        private, safe = mod.prepare_ledger(self.sources)
        self.assertEqual(safe["category_counts"], {
            "TRAIN_ONLY": 57, "VALIDATION_ONLY": 15,
            "BOTH_TRAIN_AND_VALIDATION": 9, "NO_EXACT_TARGET_IN_PRIOR_SFT": 114,
        })
        self.assertEqual(
            (safe["historical_ever_train_exact"],
             safe["historical_ever_validation_exact"],
             safe["no_exact_target_match"]), (66, 24, 114),
        )
        self.assertEqual(safe["gold195_rows"], 195)
        self.assertEqual(len(private["rows"]), 195)

    def test_gold87_and_gold108_pool_breakdowns(self):
        _, safe = mod.prepare_ledger(self.sources)
        self.assertEqual(safe["by_gold_pool"]["GOLD87"]["categories"], {
            "TRAIN_ONLY": 20, "VALIDATION_ONLY": 0,
            "BOTH_TRAIN_AND_VALIDATION": 0, "NO_EXACT_TARGET_IN_PRIOR_SFT": 67,
        })
        self.assertEqual(safe["by_gold_pool"]["GOLD108"]["categories"], {
            "TRAIN_ONLY": 37, "VALIDATION_ONLY": 15,
            "BOTH_TRAIN_AND_VALIDATION": 9, "NO_EXACT_TARGET_IN_PRIOR_SFT": 47,
        })
        self.assertEqual(safe["by_gold_pool"]["GOLD87"]["same_uuid_as_v01_train_rows"], 21)

    def test_private_rows_halt_all_195_and_have_source_ordinals(self):
        ledger, _ = mod.prepare_ledger(self.sources)
        self.assertEqual(
            {row["dataset_v04_decision"] for row in ledger["rows"]},
            {"HOLD_NOT_REVIEWED"},
        )
        self.assertEqual(
            sum(row["historical_exact_target_class"] == "BOTH_TRAIN_AND_VALIDATION"
                for row in ledger["rows"]), 9,
        )
        self.assertEqual(ledger["rows"][0]["source_row_ordinal_1_based"], 1)
        self.assertEqual(ledger["rows"][87]["gold_source"], "GOLD108")
        self.assertTrue(all(not x["world_alias_graph_verified"] for x in ledger["rows"]))

    def test_safe_stdout_contains_no_target_digest_or_story_uuid(self):
        private, safe = mod.prepare_ledger(self.sources)
        public = json.dumps(safe)
        self.assertNotIn(private["rows"][0]["target_sha256_private"], public)
        self.assertNotIn("same-v01-world", public)
        self.assertNotIn("g108-synthetic-answer", public)
        self.assertFalse(safe["source_byte_pins_verified_by_cli"])

    def test_direct_synthetic_sources_fail_real_frozen_byte_pins(self):
        with self.assertRaises(mod.exact.ExactReplayHold):
            mod.exact.verify_source_pin("R46_TRAIN", self.sources["R46_TRAIN"])

    def test_changing_five_repeated_message_histories_blocks(self):
        rows = [json.loads(x) for x in self.sources["R54_TRAIN"].splitlines()]
        rows[0]["messages"][0]["content"] = "tamper-test-history"
        self.sources["R54_TRAIN"] = _wire(rows)
        with self.assertRaises(mod.LedgerHold):
            mod.prepare_ledger(self.sources)

    def test_changing_14_9_8_blocks(self):
        rows = [json.loads(x) for x in self.sources["R54_TRAIN"].splitlines()]
        rows[30]["messages"][-1]["content"] = rows[0]["messages"][-1]["content"]
        self.sources["R54_TRAIN"] = _wire(rows)
        with self.assertRaises(mod.exact.ExactReplayHold):
            mod.prepare_ledger(self.sources)

    def test_approved_gold_metadata_is_not_accepted(self):
        rows = [json.loads(x) for x in self.sources["GOLD87"].splitlines()]
        rows[0]["metadata"]["training_admission"] = "APPROVED"
        self.sources["GOLD87"] = _wire(rows)
        with self.assertRaises(mod.LedgerHold):
            mod.prepare_ledger(self.sources)

    def test_v01_missing_world_metadata_blocks(self):
        rows = [json.loads(x) for x in self.sources["V01_TRAIN"].splitlines()]
        rows[0]["metadata"].pop("story_id")
        self.sources["V01_TRAIN"] = _wire(rows)
        with self.assertRaises(mod.LedgerHold):
            mod.prepare_ledger(self.sources)

    def test_private_ledger_filename_is_constrained(self):
        self.assertTrue(mod.LEDGER_FILENAME.fullmatch(
            "R57_G3_EXACT_TARGET_EXPOSURE_20261026_PRIVATE.json"
        ))
        for filename in ("R57_G3_PRIVATE.json", "../R57_G3_FOO_PRIVATE.json",
                         "R57_G3_FOO_PRIVATE.json/unsafe", "R50_20261026_PRIVATE.json"):
            self.assertIsNone(mod.LEDGER_FILENAME.fullmatch(filename))


if __name__ == "__main__":
    unittest.main()

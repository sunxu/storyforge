"""Synthetic-only tests for Gold195 real-source-safe metadata prescreen."""

import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "r57_gold195_g3_prescreen", ROOT / "scripts" / "r57_gold195_g3_prescreen.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def synthetic_row(pool, index, world, *, target=None):
    target = target or f"{pool}:fictitious-answer-{index}"
    meta = {"story_id": world}
    if pool == "GOLD87":
        meta.update({
            "target_sha256_utf8": digest(target),
            "training_admission": "PENDING_NOT_APPROVED",
            "source_sha256": digest(f"source:{index}"),
            "independent_gold_review": "NOT_RUN",
            "qwen_token_length_check": "NOT_RUN",
            "last_round_label_mask_check": "NOT_RUN",
            "story_card_status": "EXACT_TARGET_TIME_VERSION_UNVERIFIED",
        })
    elif pool == "GOLD108":
        meta["training_admission"] = "PENDING_NOT_APPROVED"
        if index < 90:
            meta["target_sha256"] = digest(target)
        elif index < 105:
            meta["target_sha256_utf8"] = digest(target)
        else:
            meta.pop("story_id")
            meta["source_story_id"] = world
            meta["target_content_sha256"] = digest(target)
        if index < 101:
            meta["source_archive_sha256"] = digest(f"source:{index}")
        if index < 71:
            meta["independent_ab_review"] = "NOT_RUN"
            meta["qwen_16384_token_check"] = "NOT_RUN"
            meta["last_round_loss_mask_audit"] = "NOT_RUN_HISTORY_ASSISTANT_MUST_BE_MASKED"
            meta["story_card_as_of_target"] = "NOT_AVAILABLE_NOT_INJECTED"
        elif index < 84:
            meta["independent_gold_review"] = "NOT_RUN"
            meta["qwen_token_length_check"] = "NOT_RUN"
            meta["last_round_label_mask_check"] = "NOT_RUN"
            meta["story_card_status"] = "EXPORT_TIME_STATE_ONLY_UNVERIFIED"
    return {"metadata": meta, "messages": [
        {"role": "user", "content": f"synthetic query {index}"},
        {"role": "assistant", "content": target},
    ]}


def synthetic_four():
    gold87 = [
        synthetic_row("GOLD87", i, "shared-train" if i < 21 else f"g87-world-{(i-21)%4}")
        for i in range(87)
    ]
    gold108 = [synthetic_row("GOLD108", i, f"g108-world-{i%8}") for i in range(108)]
    train = [synthetic_row("V01_TRAIN", i, "shared-train" if i == 0 else
                           f"baseline-train-world-{i%14}") for i in range(65)]
    val = [synthetic_row("V01_VALIDATION", i, f"baseline-val-world-{i%2}")
           for i in range(15)]
    return {"GOLD87": gold87, "GOLD108": gold108,
            "V01_TRAIN": train, "V01_VALIDATION": val}


def packed(groups):
    return {
        pool: ("".join(json.dumps(row) + "\n" for row in items)).encode("utf-8")
        for pool, items in groups.items()
    }


class TestGold195RiskPrescreen(unittest.TestCase):
    def test_expected_synthetic_evidence_gaps(self):
        safe = mod.prescreen(packed(synthetic_four()))
        self.assertEqual(safe["gold195_distinct_exact_targets"], 195)
        self.assertEqual(safe["gold195_distinct_world_uuids"], 13)
        self.assertEqual(safe["gold195_source_sha_field_present"], 188)
        self.assertEqual(safe["gold195_source_sha_field_absent"], 7)
        self.assertEqual(safe["per_pool"]["GOLD87"]["same_uuid_as_v01_train_rows"], 21)
        self.assertEqual(safe["gold_exact_target_seen_in_v01"], {"train": 0, "validation": 0})
        for gate in mod.FLAGS:
            self.assertEqual(safe["gold195_review_signals"][gate]["explicit_pending"], 171)
            self.assertEqual(safe["gold195_review_signals"][gate]["absent"], 24)
            self.assertEqual(safe["gold195_review_signals"][gate]["other_unverified"], 0)
        self.assertEqual(safe["v04_admitted_samples"], 0)
        self.assertFalse(safe["source_file_byte_pins_checked_by_cli"])

    def test_ignores_original_text_and_hashes_in_public_summary(self):
        inputs = packed(synthetic_four())
        out = json.dumps(mod.prescreen(inputs))
        self.assertNotIn("fictitious-answer", out)
        self.assertNotIn("synthetic query", out)
        self.assertNotIn("shared-train", out)
        self.assertNotIn(digest("GOLD87:fictitious-answer-1"), out)
        self.assertNotIn("C_fictional", out)

    def test_requires_all_four(self):
        data = packed(synthetic_four())
        data.pop("V01_VALIDATION")
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(data)

    def test_reject_changed_gold_target_digest(self):
        groups = synthetic_four()
        groups["GOLD108"][107]["metadata"]["target_content_sha256"] = "0" * 64
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(packed(groups))

    def test_reject_target_schema_swapped_from_90_15_3(self):
        groups = synthetic_four()
        r = groups["GOLD108"][91]
        r["metadata"]["target_sha256"] = r["metadata"].pop("target_sha256_utf8")
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(packed(groups))

    def test_reject_unapproved_to_approved_metadata_drift(self):
        groups = synthetic_four()
        groups["GOLD87"][0]["metadata"]["training_admission"] = "ACCEPT"
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(packed(groups))

    def test_reject_gold_cross_pool_duplicate_target(self):
        groups = synthetic_four()
        old = groups["GOLD87"][0]["messages"][-1]["content"]
        groups["GOLD108"][0]["messages"][-1]["content"] = old
        groups["GOLD108"][0]["metadata"]["target_sha256"] = digest(old)
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(packed(groups))

    def test_reject_zeroed_world_identifier(self):
        groups = synthetic_four()
        groups["GOLD87"][0]["metadata"]["story_id"] = ""
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(packed(groups))

    def test_reject_target_exposed_to_baseline(self):
        groups = synthetic_four()
        old = groups["V01_TRAIN"][1]["messages"][-1]["content"]
        groups["GOLD87"][0]["messages"][-1]["content"] = old
        groups["GOLD87"][0]["metadata"]["target_sha256_utf8"] = digest(old)
        with self.assertRaises(mod.PrescreenHold):
            mod.prescreen(packed(groups))

    def test_unverified_approval_claim_never_auto_admits(self):
        groups = synthetic_four()
        groups["GOLD108"][0]["metadata"]["independent_ab_review"] = "APPROVED"
        safe = mod.prescreen(packed(groups))
        self.assertEqual(safe["gold195_review_signals"]["independent_review"]["other_unverified"], 1)
        self.assertEqual(safe["v04_admitted_samples"], 0)

    def test_source_sha_field_missing_is_hold_not_fabricated(self):
        safe = mod.prescreen(packed(synthetic_four()))
        self.assertFalse(safe["source_sha_field_original_bytes_verified"])
        self.assertEqual(safe["gold195_source_sha_field_absent"], 7)

    def test_source_message_not_assistant_denied(self):
        groups = synthetic_four()
        groups["GOLD87"][0]["messages"][-1]["role"] = "user"
        with self.assertRaises(mod.frozen.ExportHold):
            mod.prescreen(packed(groups))


if __name__ == "__main__":
    unittest.main()

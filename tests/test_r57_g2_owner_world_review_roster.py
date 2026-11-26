"""Synthetic eight-source regressions for private 29-world alias review inventory."""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g2_owner_world_review_roster",
    ROOT / "scripts" / "r57_g2_owner_world_review_roster.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

from test_r57_g3_private_exposure_ledger import fake_eight_sources


def fixture():
    data = fake_eight_sources()
    g87 = [json.loads(x) for x in data["GOLD87"].splitlines()]
    # 10+24 R46-covered, 21 V01-covered, 14+18 entirely unused by old SFT.
    for i, row in enumerate(g87):
        world = (
            "r46world10" if i < 10 else "r46world24" if i < 34 else
            "v01world21" if i < 55 else "newworld14" if i < 69 else
            "newworld18"
        )
        row["metadata"]["story_id"] = world
    data["GOLD87"] = ("".join(json.dumps(x) + "\n" for x in g87)).encode()
    v01_train = [json.loads(x) for x in data["V01_TRAIN"].splitlines()]
    for i, row in enumerate(v01_train):
        row["metadata"]["story_id"] = "v01world21" if i == 0 else f"oldworld-{i % 14}"
    data["V01_TRAIN"] = (
        "".join(json.dumps(x) + "\n" for x in v01_train)
    ).encode()
    v01_val = [json.loads(x) for x in data["V01_VALIDATION"].splitlines()]
    for i, row in enumerate(v01_val):
        row["metadata"]["story_id"] = f"valworld-{i % 2}"
    data["V01_VALIDATION"] = (
        "".join(json.dumps(x) + "\n" for x in v01_val)
    ).encode()
    return data


class TestWorldAliasReviewRoster(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def test_29_distinct_worlds_and_two_gold_unexposed_worlds(self):
        private, safe = mod.build_roster(self.data)
        self.assertEqual(len(private["worlds"]), 29)
        self.assertEqual(safe["gold_world_uuids"], 13)
        self.assertEqual(safe["world_uuid_count"], 29)
        self.assertEqual(safe["gold_world_uuids_without_historical_sft_uuid"], 2)
        self.assertEqual(safe["gold_rows_without_target_and_world_uuid_exact_match"], 32)
        self.assertEqual(safe["gold_rows_without_target_exact_match"], 114)
        self.assertEqual(safe["compiled_rows_uniquely_matched_to_gold"], 104)

    def test_two_unseen_worlds_only_with_14_and_18_gold(self):
        private, safe = mod.build_roster(self.data)
        never = sorted(
            x["gold_final_targets_without_previous_exact_match"]
            for x in private["worlds"]
            if not x["same_exact_uuid_seen_in_previous_sft"]
            and x["gold_final_targets_without_previous_exact_match"]
        )
        self.assertEqual(never, [14, 18])
        self.assertEqual(safe["gold_rows_without_target_and_world_uuid_exact_match"], 32)

    def test_all_29_decisions_unset_and_195_gold_remain_unadmitted(self):
        private, safe = mod.build_roster(self.data)
        self.assertEqual(
            {x["owner_alias_semantic_review_status"] for x in private["worlds"]},
            {"PENDING_NOT_VERIFIED"},
        )
        self.assertEqual(
            {x["owner_declared_component_token_PRIVATE"] for x in private["worlds"]},
            {None},
        )
        self.assertEqual(
            {x["dataset_v04_decision"] for x in private["worlds"]},
            {"HOLD_NOT_REVIEWED"},
        )
        self.assertEqual(safe["v04_admitted"], 0)
        self.assertFalse(safe["world_component_isolation_certified"])
        self.assertFalse(safe["owner_alias_signoff_completed"])

    def test_safe_stdout_has_no_world_uuid_or_target_hash(self):
        private, safe = mod.build_roster(self.data)
        text = json.dumps(safe)
        self.assertNotIn("newworld14", text)
        self.assertNotIn("oldworld-", text)
        self.assertNotIn("gold108-world-", text)
        self.assertNotIn(private["worlds"][0]["source_story_uuid_PRIVATE"], text)

    def test_missing_compiled_target_causes_hold(self):
        r = [json.loads(x) for x in self.data["R54_VALIDATION"].splitlines()]
        r[0]["messages"][-1]["content"] = "unmatched-synthetic-response"
        self.data["R54_VALIDATION"] = (
            "".join(json.dumps(x) + "\n" for x in r)
        ).encode()
        with self.assertRaises(mod.anchored.WorldJoinHold):
            mod.build_roster(self.data)

    def test_fabricated_all_distinct_worlds_cannot_be_treated_as_valid(self):
        rows = [json.loads(x) for x in self.data["GOLD87"].splitlines()]
        rows[-1]["metadata"]["story_id"] = "fabricated_extra_world"
        self.data["GOLD87"] = (
            "".join(json.dumps(x) + "\n" for x in rows)
        ).encode()
        with self.assertRaises(mod.WorldRosterHold):
            mod.build_roster(self.data)

    def test_unsafe_private_filename_denied(self):
        self.assertIsNotNone(mod.PRIVATE_NAME.fullmatch(
            "R57_G2_WORLD_ALIAS_REVIEW_20261026_153000_PRIVATE.json"
        ))
        for name in ("../private.json", "R50_20261026_PRIVATE.json",
                     "R57_G2_WORLD_ALIAS_REVIEW_20261026_PRIVATE.json"):
            self.assertIsNone(mod.PRIVATE_NAME.fullmatch(name))


if __name__ == "__main__":
    unittest.main()

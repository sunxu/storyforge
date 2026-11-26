"""Synthetic-only evidence-index checks; no story titles enter the safe output."""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g2_alias_name_hints", ROOT / "scripts" / "r57_g2_alias_name_hints.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

from test_r57_g2_owner_world_review_roster import fixture


def synthetic_evidence():
    packets = fixture()
    for source in ("GOLD87", "GOLD108", "V01_TRAIN", "V01_VALIDATION"):
        rows = [json.loads(row) for row in packets[source].splitlines()]
        for i, record in enumerate(rows):
            meta = record["metadata"]
            if source.startswith("V01_"):
                meta["story_title"] = "Synthetic SFT story card"
            elif source == "GOLD87":
                meta["source_file"] = f"private-story-file-{meta['story_id']}.jsonl"
            elif i < 71:
                meta["story_title"] = "Synthetic Gold108 novella"
                meta["source_jsonl_member"] = "fictional-archive-member.jsonl"
        packets[source] = ("".join(json.dumps(r) + "\n" for r in rows)).encode("utf-8")
    return packets


class TestAliasNameHints(unittest.TestCase):
    def setUp(self):
        self.payloads = synthetic_evidence()

    def test_frozen_29_worlds_55_pairs_zero_auto_decision(self):
        private, safe = mod.build_index(self.payloads)
        self.assertEqual(len(private["worlds_PRIVATE"]), 29)
        self.assertEqual(len(private["pair_name_hints_PRIVATE"]), 55)
        self.assertEqual(safe["observed_world_uuids"], 29)
        self.assertEqual(safe["historical_sft_world_uuids"], 27)
        self.assertEqual(safe["candidate_gold_world_uuids"], 2)
        self.assertEqual(safe["candidate_gold_row_counts_sorted"], [14, 18])
        self.assertEqual(safe["pairs_decided_automatically"], 0)
        self.assertFalse(safe["world_isolation_certified"])

    def test_evidence_is_only_hints_and_55_unreviewed(self):
        private, safe = mod.build_index(self.payloads)
        self.assertTrue(all(
            row["manual_alias_verdict"] == "UNREVIEWED"
            and not row["automatic_link_inference"]
            for row in private["pair_name_hints_PRIVATE"]
        ))
        self.assertEqual(
            {row["owner_world_alias_decision"] for row in private["worlds_PRIVATE"]},
            {"UNREVIEWED"},
        )
        self.assertEqual(
            {row["owner_canonical_title_PRIVATE"] for row in private["worlds_PRIVATE"]},
            {None},
        )
        self.assertFalse(private["aliases_or_world_links_inferred"])
        self.assertEqual(safe["dataset_v04_admitted"], 0)

    def test_candidate_title_file_hints_present_but_not_approved(self):
        private, safe = mod.build_index(self.payloads)
        candidates = [x for x in private["worlds_PRIVATE"]
                      if x["candidate_unseen_exact_uuid_gold_rows"]]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(safe["candidate_worlds_with_source_file_hints"], 2)
        self.assertEqual(sorted(len(x["source_file_references_PRIVATE"]) for x in candidates),
                         [1, 1])
        self.assertTrue(all(not x["suggested_story_titles_PRIVATE"] for x in candidates))

    def test_v01_training_story_title_is_a_hint_not_link_proof(self):
        private, safe = mod.build_index(self.payloads)
        self.assertTrue(any(
            "Synthetic SFT story card" in x["suggested_story_titles_PRIVATE"]
            for x in private["worlds_PRIVATE"]
        ))
        self.assertGreater(safe["worlds_with_explicit_story_title_hint"], 0)
        self.assertEqual(safe["pairs_decided_automatically"], 0)

    def test_safe_stdout_contains_no_paths_titles_or_uuid(self):
        private, safe = mod.build_index(self.payloads)
        summary = json.dumps(safe, ensure_ascii=False)
        for private_token in (
            "Synthetic SFT story card", "fictional-archive-member",
            "newworld14", "newworld18", "private-story-file-",
            private["worlds_PRIVATE"][0]["world_uuid_PRIVATE"],
        ):
            self.assertNotIn(private_token, summary)
        self.assertFalse(safe["source_pins_reverified_by_cli"])
        self.assertFalse(safe["r50_content_accessed"])
        self.assertFalse(safe["training_authorized"])

    def test_missing_metadata_does_not_fabricate_title_or_story_id(self):
        rows = [json.loads(r) for r in self.payloads["GOLD108"].splitlines()]
        rows[0]["metadata"].pop("story_title", None)
        rows[0]["metadata"].pop("source_jsonl_member", None)
        self.payloads["GOLD108"] = (
            "".join(json.dumps(r) + "\n" for r in rows)
        ).encode("utf-8")
        private, safe = mod.build_index(self.payloads)
        self.assertEqual(len(private["worlds_PRIVATE"]), 29)
        self.assertFalse(safe["world_isolation_certified"])

    def test_disallow_unrecognized_source_world(self):
        rows = [json.loads(r) for r in self.payloads["V01_TRAIN"].splitlines()]
        rows[0]["metadata"]["story_id"] = "fabricated-new-world-id"
        self.payloads["V01_TRAIN"] = (
            "".join(json.dumps(r) + "\n" for r in rows)
        ).encode("utf-8")
        with self.assertRaises((mod.roster.WorldRosterHold, mod.NameHintsHold)):
            mod.build_index(self.payloads)

    def test_reject_wrong_hint_type_or_control_sequence(self):
        for invalid in ({"not": "a title"}, "line\ncontrol", "x" * 513):
            with self.subTest(invalid=str(invalid)[:15]):
                data = synthetic_evidence()
                rows = [json.loads(r) for r in data["V01_TRAIN"].splitlines()]
                rows[0]["metadata"]["story_title"] = invalid
                data["V01_TRAIN"] = (
                    "".join(json.dumps(r) + "\n" for r in rows)
                ).encode("utf-8")
                with self.assertRaises(mod.NameHintsHold):
                    mod.build_index(data)

    def test_incomplete_private_eight_sources_is_blocked(self):
        del self.payloads["R54_TRAIN"]
        with self.assertRaises(mod.anchored.WorldJoinHold):
            mod.build_index(self.payloads)

    def test_unapproved_path_basename_blocked(self):
        self.assertTrue(mod.PRIVATE_NAME.fullmatch(
            "R57_G2_WORLD_NAME_HINTS_20261026_154000_PRIVATE.json"
        ))
        for bad in ("../story.json", "r50-private.json",
                    "R57_G2_WORLD_NAME_HINTS_20261026_PRIVATE.json"):
            self.assertFalse(mod.PRIVATE_NAME.fullmatch(bad))


if __name__ == "__main__":
    unittest.main()

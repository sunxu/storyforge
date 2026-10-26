"""CPU synthetic-only tests for Owner-local Gold32 source metadata locator."""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g2_private_candidate_source_locator",
    ROOT / "scripts" / "r57_g2_private_candidate_source_locator.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

from test_r57_g2_owner_world_review_roster import fixture


def source_fixture():
    payloads = fixture()
    rows = [json.loads(line) for line in payloads["GOLD87"].splitlines()]
    for i, row in enumerate(rows):
        row["metadata"]["source_file"] = "synthetic-story-origin.jsonl"
        row["metadata"]["source_json_pointer"] = f"/messages/{i}"
        row["metadata"]["selection_title_zh"] = f"仅测试用候选标签-{i}"
        row["metadata"]["source_sha256"] = "b" * 64
    payloads["GOLD87"] = (
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    ).encode("utf-8")
    return payloads


class TestR57CandidateSourceLocator(unittest.TestCase):
    def setUp(self):
        self.payloads = source_fixture()

    def test_two_worlds_32_cases_private_only(self):
        private, safe = mod.prepare_locator(self.payloads)
        self.assertEqual(
            sorted(row["gold87_rows"] for row in private["candidate_worlds_PRIVATE"]),
            [14, 18],
        )
        self.assertEqual(safe["candidate_unseen_exact_uuid_worlds"], 2)
        self.assertEqual(safe["candidate_gold87_rows"], 32)
        self.assertEqual(safe["selection_label_metadata_present_count"], 32)
        self.assertEqual(safe["source_file_metadata_present_count"], 32)
        self.assertEqual(safe["source_json_pointer_metadata_present_count"], 32)
        self.assertEqual(safe["source_sha_metadata_present_not_independently_rehashed_count"], 32)

    def test_private_pointers_have_no_story_content_and_remain_hold(self):
        private, safe = mod.prepare_locator(self.payloads)
        self.assertEqual(
            {row["dataset_v04_decision"] for row in private["candidate_worlds_PRIVATE"]},
            {"HOLD_NOT_REVIEWED"},
        )
        self.assertEqual(
            {row["owner_semantic_alias_review_status"] for row in private["candidate_worlds_PRIVATE"]},
            {"PENDING_NOT_VERIFIED"},
        )
        self.assertTrue(all(
            "source_json_pointer_PRIVATE" in item
            for row in private["candidate_worlds_PRIVATE"]
            for item in row["source_locations_PRIVATE"]
        ))
        self.assertNotIn("messages", json.dumps(private))
        self.assertFalse(safe["original_story_files_opened"])
        self.assertEqual(safe["v04_admitted"], 0)
        self.assertFalse(safe["world_isolation_certified"])

    def test_safe_report_does_not_contain_private_paths_uuids_or_labels(self):
        private, safe = mod.prepare_locator(self.payloads)
        text = json.dumps(safe, ensure_ascii=False)
        self.assertNotIn("synthetic-story-origin", text)
        self.assertNotIn("仅测试用候选", text)
        self.assertNotIn("newworld14", text)
        self.assertNotIn("newworld18", text)
        self.assertNotIn(private["candidate_worlds_PRIVATE"][0]["source_story_uuid_PRIVATE"], text)
        self.assertFalse(safe["source_byte_pins_reverified_by_cli"])
        self.assertFalse(safe["training_authorized"])
        self.assertFalse(safe["r50_content_accessed"])

    def test_missing_primary_source_file_metadata_blocks(self):
        rows = [json.loads(line) for line in self.payloads["GOLD87"].splitlines()]
        rows[55]["metadata"].pop("source_file")
        self.payloads["GOLD87"] = (
            "".join(json.dumps(row) + "\n" for row in rows)
        ).encode()
        with self.assertRaises(mod.LocatorHold):
            mod.prepare_locator(self.payloads)

    def test_missing_case_title_or_json_pointer_blocks(self):
        for key in ("selection_title_zh", "source_json_pointer", "source_sha256"):
            with self.subTest(field=key):
                data = source_fixture()
                rows = [json.loads(line) for line in data["GOLD87"].splitlines()]
                rows[69]["metadata"][key] = ""
                data["GOLD87"] = (
                    "".join(json.dumps(row) + "\n" for row in rows)
                ).encode()
                with self.assertRaises(mod.LocatorHold):
                    mod.prepare_locator(data)

    def test_corrupt_world_exposure_blocks(self):
        rows = [json.loads(line) for line in self.payloads["GOLD87"].splitlines()]
        rows[-1]["metadata"]["story_id"] = "fabricated-extra-uuid"
        self.payloads["GOLD87"] = (
            "".join(json.dumps(row) + "\n" for row in rows)
        ).encode()
        with self.assertRaises(mod.roster.WorldRosterHold):
            mod.prepare_locator(self.payloads)

    def test_filename_must_be_private_basename(self):
        self.assertTrue(mod.PRIVATE_NAME.fullmatch(
            "R57_G2_CANDIDATE_SOURCE_LOCATOR_20261026_160000_PRIVATE.json"
        ))
        for bad in (
            "../untrusted.json", "R50_SOURCE.json",
            "R57_G2_CANDIDATE_SOURCE_LOCATOR_20261026_PRIVATE.json",
            "R57_G2_CANDIDATE_SOURCE_LOCATOR_20261026_160000_PRIVATE.json/escape",
        ):
            self.assertFalse(mod.PRIVATE_NAME.fullmatch(bad))


if __name__ == "__main__":
    unittest.main()

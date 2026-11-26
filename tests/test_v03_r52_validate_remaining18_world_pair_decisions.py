"""Synthetic-only review validator tests for six-pair world batches."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v03_r52_pack_priority_full_source_pairs import fixtures, file
from test_v03_r52_pack_remaining18_full_source_pairs import run as build
import v03_r52_validate_remaining18_world_pair_decisions as validator


def fixture(root):
    src, out, repo = fixtures(root)
    build(src, out, repo)
    zip_path = out / "R52_REMAINING_18_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip"
    safe = out / "R52_REMAINING_18_SOURCE_PACKAGE_SAFE_RECEIPT.json"
    with zipfile.ZipFile(zip_path) as z:
        cases = [json.loads(x) for x in z.read(
            "R52_PRIVATE_REMAINING_18_BATCH_01_PAIR_TASKS.jsonl").splitlines()]
        stories = {}
        for name in z.namelist():
            if name.startswith("R52_PRIVATE_FULL_ORIGINAL_STORY_"):
                w = json.loads(z.read(name))
                stories[w["story_rank"]] = w
    rows = []
    for c in cases:
        citations = [{
            "scope": "FULL_ORIGINAL", "story_rank": r,
            "original_source_array_index": 0,
            "source_body_sha256": stories[r]["original_root_messages"][0][
                "source_body_sha256"],
        } for r in (c["left_rank"], c["right_rank"])]
        rows.append({
            "schema": validator.RESULT_SCHEMA,
            "batch_number": 1,
            "left_rank": c["left_rank"],
            "right_rank": c["right_rank"],
            "left_source_story_id": c["left_source_story_id"],
            "right_source_story_id": c["right_source_story_id"],
            "left_original_jsonl_sha256": c["left_original_jsonl_sha256"],
            "right_original_jsonl_sha256": c["right_original_jsonl_sha256"],
            "review_route": "NO_LINK_OBSERVED_IN_FULL_AVAILABLE_SOURCE__HOLD",
            "rationale": "Synthetic only: narrative pair is not certified independent. " * 3,
            "source_citations": citations,
            "training_admission": validator.pack.HOLD,
            "split": None,
            "world_component_certified": False,
            "r50_sealed_heldout_opened": False,
        })
    decision = out / "test_six_private_results.jsonl"
    file(decision, "".join(json.dumps(r) + "\n" for r in rows))
    return src, out, zip_path, safe, decision


def check(src, zip_path, safe, decisions):
    all_hash = validator.pack.sha(validator.pack.private_file(
        src / "R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"))
    priority_hash = validator.pack.sha(validator.pack.private_file(
        src / "R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"))
    with patch.object(validator.pack, "EXPECTED_ALL21_SHA", all_hash), \
         patch.object(validator.pack, "EXPECTED_PRIORITY3_SHA", priority_hash):
        return validator.verify(zip_path, safe, decisions, 1)


class ValidateWorldPairs(unittest.TestCase):
    def test_six_pairs_and_two_sided_citations(self):
        with tempfile.TemporaryDirectory() as d:
            src, _, zp, receipt, decisions = fixture(Path(d))
            r = check(src, zp, receipt, decisions)
            self.assertEqual(r["pairs_validated"], 6)
            self.assertEqual(r["source_citations_validated"], 12)
            self.assertEqual(r["train_admitted"], 0)
            self.assertEqual(r["world_components_certified"], 0)

    def test_tamper_source_citation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src, _, zp, receipt, decisions = fixture(Path(d))
            cases = [json.loads(x) for x in decisions.read_text().splitlines()]
            cases[0]["source_citations"][1]["source_body_sha256"] = "a" * 64
            file(decisions, "".join(json.dumps(r) + "\n" for r in cases))
            with self.assertRaisesRegex(
                validator.pack.PackHold, "CITATION_SHA_MISMATCH_OR_DUPLICATED"):
                check(src, zp, receipt, decisions)

    def test_receipt_archive_hash_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src, _, zp, receipt, decisions = fixture(Path(d))
            obj = json.loads(receipt.read_text())
            obj["archive_sha256"] = "f" * 64
            file(receipt, json.dumps(obj))
            with self.assertRaisesRegex(
                validator.pack.PackHold, "SOURCE_RECEIPT_OR_PACKAGE_PIN_CHANGED"):
                check(src, zp, receipt, decisions)


if __name__ == "__main__":
    unittest.main()

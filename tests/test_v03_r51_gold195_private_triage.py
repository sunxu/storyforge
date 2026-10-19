"""Synthetic tests for R51 private, source-grounded HOLD workpaper."""
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))
import v03_r51_gold195_private_triage as triage  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "readiness_test_fixtures",
    BASE / "tests" / "test_v03_r51_gold195_readiness.py",
)
assert spec and spec.loader
fixtures_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures_module)


class R51PrivateTriageTests(unittest.TestCase):
    def test_full_synthetic_pool_stays_unapproved(self):
        a, b, index = fixtures_module.fixtures()
        work, report = triage.make_rows(a, b, index)
        self.assertEqual(len(work), 195)
        self.assertEqual(report["train_admitted"], 0)
        self.assertEqual(report["validation_admitted"], 0)
        self.assertEqual(report["context_only_routes_decided"], 0)
        self.assertTrue(all(row["triage_route"] == triage.UNDECIDED
                            for row in work))
        self.assertTrue(all(row["holds"][0] == "CONTENT_OR_RIGHTS_HOLD"
                            and row["training_admission"] == "PENDING_NOT_APPROVED"
                            and row["split"] is None for row in work))
        self.assertEqual(len({r["candidate_id"] for r in work}), 195)
        self.assertNotIn("synthetic assistant completion", json.dumps(report))

    def test_overlap_flags_and_pointer_hold(self):
        a, b, index = fixtures_module.fixtures()
        work, report = triage.make_rows(a, b, index)
        self.assertEqual(report["age_unspecified"], 10)
        self.assertEqual(report["flag_intersections"]["card_and_age"], 10)
        self.assertIn("SOURCE_POINTER_RECONCILIATION_HOLD", work[-1]["holds"])
        self.assertFalse(any("CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD"
                             in r["holds"] for r in work))
        self.assertNotIn("content", work[0]["source_reference"])
        self.assertTrue(work[0]["history_fingerprints"])

    def test_source_mutation_rejected(self):
        a, b, index = fixtures_module.fixtures()
        b[0]["messages"][-1]["content"] = "synthetic tamper"
        with self.assertRaisesRegex(ValueError, "TARGET_SHA256_MISMATCH"):
            triage.make_rows(a, b, index)

    def test_private_exclusive_write_and_permissions(self):
        a, b, index = fixtures_module.fixtures()
        work, _ = triage.make_rows(a, b, index)
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "private"
            parent.mkdir(mode=0o700)
            out = parent / "r51.jsonl"
            triage.write_private(out, work, Path(temp) / "gitrepo")
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
            self.assertEqual(len(out.read_text().splitlines()), 195)
            with self.assertRaises(FileExistsError):
                triage.write_private(out, work, Path(temp) / "gitrepo")
            with self.assertRaisesRegex(ValueError, "INSIDE_GIT_REPOSITORY"):
                triage.write_private(Path(temp) / "gitrepo" / "test.jsonl",
                                     work, Path(temp) / "gitrepo")

    def test_world_names_and_original_prose_not_in_public_counts(self):
        a, b, index = fixtures_module.fixtures()
        a[0]["metadata"]["review_notes_zh"] = "synthetic private note"
        _, summary = triage.make_rows(a, b, index)
        raw = json.dumps(summary)
        self.assertNotIn("synthetic private note", raw)
        self.assertNotIn("candidate_id", raw)
        self.assertNotIn("original_target_sha256", raw)


if __name__ == "__main__":
    unittest.main()

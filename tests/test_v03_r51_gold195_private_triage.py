"""Synthetic tests for R51 private, source-grounded HOLD workpaper."""
import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))
import v03_r51_gold195_private_triage as triage

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
        # Unlike the minimal fixtures, real Gold87 carries direct pointers.
        for k, row in enumerate(a):
            row["metadata"]["source_json_pointer"] = f"/synthetic/{k}"
        for row in b:
            row["metadata"]["source_message_array_index"] = 1
        b[-1]["metadata"].pop("source_message_array_index")
        work, report = triage.make_rows(a, b, index)
        self.assertEqual(report["age_unspecified"], 10)
        self.assertEqual(report["flag_intersections"]["card_and_age"], 10)
        self.assertIn("SOURCE_POINTER_RECONCILIATION_HOLD", work[-1]["holds"])
        self.assertFalse(any("CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD"
                             in r["holds"] for r in work))
        self.assertNotIn("content", work[0]["source_reference"])
        self.assertTrue(work[0]["history_fingerprints"])

    def test_unflagged_metadata_never_auto_approves(self):
        a, b, index = fixtures_module.fixtures()
        a[0]["metadata"]["story_card_status"] = "NO_EXPLICIT_MARKER"
        a[0]["metadata"]["source_json_pointer"] = "/synthetic/1"
        work, _ = triage.make_rows(a, b, index)
        self.assertEqual(work[0]["metadata_risks"], [])
        self.assertEqual(work[0]["holds"], ["CONTENT_OR_RIGHTS_HOLD"])
        self.assertEqual(work[0]["triage_route"], triage.UNDECIDED)


    def test_owner_v2_owner_declaration_and_pointer_crosslink(self):
        a, b, index = fixtures_module.fixtures()
        for k, row in enumerate(a):
            row["metadata"]["source_json_pointer"] = f"/synthetic/{k}"
        for row in b:
            row["metadata"]["source_message_array_index"] = 7
        b[-1]["metadata"].pop("source_message_array_index")
        work, _ = triage.make_rows(a, b, index)
        target = work[-1]
        audit = [{
            "candidate_id": target["candidate_id"],
            "story_id": target["source_story_id"],
            "target_message_id": target["original_target_message_id"],
            "target_sha256": target["original_target_sha256"],
            "story_number": str(target["source_rank"]),
            "target_timestamp_utc": "2026-01-01T00:00:00Z",
            "training_admission": "PENDING_NOT_APPROVED",
            "target_time_card_version_present": "false",
            "exported_story_postdates_target": "true",
        }]
        receipt = triage.owner_v2_crosslink(work, audit)
        self.assertEqual(receipt["prior_r02_missing_pointer_anchor_links"], 1)
        self.assertEqual(receipt["owner_attested_age_consent_content"], 195)
        self.assertEqual(receipt["age_unspecified_original_flags_preserved"], 10)
        self.assertEqual(receipt["prior_r02_card_snapshot_postdates_target"], 1)
        self.assertEqual(work[-1]["source_review"]["source_pointer_verified"], "PENDING")
        self.assertEqual(work[-1]["source_review"]["rights_and_license"], "PENDING")
        self.assertIn("SOURCE_POINTER_RECONCILIATION_HOLD", work[-1]["holds"])
        self.assertTrue(all(x["training_admission"] == "PENDING_NOT_APPROVED"
                            and x["split"] is None for x in work))

    def test_owner_v2_rejects_unmatched_source_target_sha(self):
        a, b, index = fixtures_module.fixtures()
        for k, row in enumerate(a):
            row["metadata"]["source_json_pointer"] = f"/synthetic/{k}"
        for row in b:
            row["metadata"]["source_message_array_index"] = 7
        b[-1]["metadata"].pop("source_message_array_index")
        work, _ = triage.make_rows(a, b, index)
        target = work[-1]
        audit = [{
            "candidate_id": target["candidate_id"],
            "story_id": target["source_story_id"],
            "target_message_id": target["original_target_message_id"],
            "target_sha256": "0" * 64,
            "story_number": str(target["source_rank"]),
            "target_timestamp_utc": "2026-01-01T00:00:00Z",
            "training_admission": "PENDING_NOT_APPROVED",
            "target_time_card_version_present": "false",
            "exported_story_postdates_target": "false",
        }]
        with self.assertRaisesRegex(ValueError, "R02_SOURCE_AUDIT_CROSSLINK_MISMATCH"):
            triage.owner_v2_crosslink(work, audit)

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
        self.assertNotIn(a[0]["id"], raw)
        self.assertNotIn("original_target_sha256", raw)


if __name__ == "__main__":
    unittest.main()

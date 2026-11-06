from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from storyforge_gold_quality.manifest import ManifestError, load_events, safe_report
from storyforge_gold_quality.review_reconciliation import (
    RECONCILIATION_KIND,
    import_review_reconciliation,
)


def fixture():
    return {
        "schema": "r60_gold72_reviewer_a_b2_crosswalk_safe_v1",
        "status": "A_B2_CROSSWALK_COMPLETE__ADMISSION_HOLD",
        "candidate_count": 72,
        "staging_sha256": "1" * 64,
        "source_context_sha256": "2" * 64,
        "reviewer_a_v3_report_sha256": "3" * 64,
        "reviewer_b2_blind_input_sha256": "4" * 64,
        "reviewer_b2_instructions_sha256": "5" * 64,
        "reviewer_b2_owner_map_sha256": "6" * 64,
        "reviewer_b2_result_sha256": "7" * 64,
        "reviewer_b2_execution_record_sha256": "8" * 64,
        "reviewer_a_evidence_granularity": {
            "CASE_LEVEL_SCORED_PASS": 50,
            "AGGREGATE_COMPLEMENT_PASS_ONLY": 10,
            "EXPLICIT_HOLD": 8,
            "EXPLICIT_REJECT": 4,
        },
        "reviewer_b2_decisions": {"PASS": 51, "HOLD": 16, "REJECT": 5},
        "a_b2_pair_counts": {
            "CASE_LEVEL_SCORED_PASS__B2_PASS": 40,
            "CASE_LEVEL_SCORED_PASS__B2_HOLD": 8,
            "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
            "AGGREGATE_COMPLEMENT_PASS_ONLY__B2_PASS": 10,
            "EXPLICIT_HOLD__B2_PASS": 1,
            "EXPLICIT_HOLD__B2_HOLD": 6,
            "EXPLICIT_HOLD__B2_REJECT": 1,
            "EXPLICIT_REJECT__B2_HOLD": 2,
            "EXPLICIT_REJECT__B2_REJECT": 2,
        },
        "a_b2_comparable_decision_cases": 62,
        "a_b2_semantic_decision_disagreements": 12,
        "a_b2_semantic_decision_agreements": 50,
        "a_case_level_scored_pass_and_b2_pass_no_severe_flags": 40,
        "a_aggregate_only_pass_and_b2_pass_no_severe_flags": 10,
        "a_explicit_nonpass_b2_pass": 1,
        "score_comparable_cases": 50,
        "score_comparison_by_dimension": {
            field: {
                "exact_matches": 30,
                "mean_absolute_difference": 0.5,
                "comparable_cases": 50,
            }
            for field in (
                "chinese_prose", "character_consistency", "npc_initiative",
                "player_agency", "narrative_continuity", "rule_fidelity",
            )
        },
        "reviewer_a_two_independent_blinded_reviews_met": False,
        "reviewer_b2_execution_attestation_self_reported": True,
        "reviewer_b2_independence_verified": False,
        "cryptographic_independence_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


class ReviewReconciliationImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir(mode=0o700)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.receipt = self.private / "crosswalk-safe.json"
        self.manifest = self.private / "manifest.jsonl"
        self.write_receipt(fixture())

    def tearDown(self):
        self.tmp.cleanup()

    def write_receipt(self, data):
        self.receipt.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        self.receipt.chmod(0o600)

    def args(self, **overrides):
        values = {
            "batch": "gold72",
            "kind": RECONCILIATION_KIND,
            "input": self.receipt,
            "manifest": self.manifest,
            "repo_root": self.repo,
        }
        values.update(overrides)
        return Namespace(**values)

    def test_valid_receipt_appends_one_batch_level_event(self):
        result = import_review_reconciliation(self.args())
        events = load_events(self.manifest)
        self.assertEqual(result["status"], "CANONICAL_RECONCILIATION_APPENDED")
        self.assertEqual(result["events_appended"], 1)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["batch_id"], "gold72")
        self.assertEqual(event["event_type"], "REVIEW_RECONCILIATION")
        self.assertEqual(event["payload"]["candidate_count"], 72)
        self.assertNotIn("case_id", event["payload"])
        self.assertNotIn("target_sha256", event["payload"])
        self.assertEqual(result["quality_v1_admitted"], 0)
        self.assertFalse(result["training_authorized"])

    def test_safe_report_exposes_only_aggregate_metrics(self):
        import_review_reconciliation(self.args())
        report = json.dumps(safe_report(load_events(self.manifest)), sort_keys=True)
        self.assertIn('"gold72"', report)
        self.assertIn('"decision_disagreements": 12', report)
        for secret in ("source_receipt_sha256", "staging_sha256", "1" * 64, "7" * 64):
            self.assertNotIn(secret, report)

    def test_same_receipt_is_idempotent(self):
        first = import_review_reconciliation(self.args())
        second = import_review_reconciliation(self.args())
        self.assertEqual(first["events_appended"], 1)
        self.assertEqual(second["status"], "CANONICAL_RECONCILIATION_ALREADY_IMPORTED")
        self.assertEqual(second["events_appended"], 0)
        self.assertEqual(len(load_events(self.manifest)), 1)

    def test_different_receipt_for_same_canonical_batch_fails_closed(self):
        import_review_reconciliation(self.args())
        data = fixture()
        data["reviewer_b2_result_sha256"] = "9" * 64
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_SOURCE_ALREADY_PINNED"):
            import_review_reconciliation(self.args())
        self.assertEqual(len(load_events(self.manifest)), 1)

    def test_non_allowlisted_batch_or_kind_fails_closed(self):
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_KIND_NOT_ALLOWLISTED"):
            import_review_reconciliation(self.args(batch="gold192"))
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_KIND_NOT_ALLOWLISTED"):
            import_review_reconciliation(self.args(kind="arbitrary"))

    def test_schema_status_and_exact_fields_are_required(self):
        for field, value in (
            ("schema", "wrong"),
            ("status", "PENDING"),
        ):
            data = fixture()
            data[field] = value
            self.write_receipt(data)
            with self.subTest(field=field), self.assertRaises(ManifestError):
                import_review_reconciliation(self.args())
        data = fixture()
        data["private_case_ids"] = ["must-not-import"]
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_SAFE_FIELDS_INVALID"):
            import_review_reconciliation(self.args())

    def test_all_source_pins_must_be_sha256(self):
        data = fixture()
        data["reviewer_a_v3_report_sha256"] = "not-a-hash"
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_SOURCE_PIN_INVALID"):
            import_review_reconciliation(self.args())

    def test_candidate_count_and_decision_totals_are_fixed(self):
        data = fixture()
        data["candidate_count"] = 71
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_CANDIDATE_COUNT_INVALID"):
            import_review_reconciliation(self.args())
        data = fixture()
        data["reviewer_b2_decisions"]["PASS"] = 50
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_ROW_TOTAL_INVALID"):
            import_review_reconciliation(self.args())

    def test_pair_counts_must_bind_all_72_cases(self):
        data = fixture()
        data["a_b2_pair_counts"]["EXPLICIT_HOLD__B2_HOLD"] = 5
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_PAIR_TOTAL_INVALID"):
            import_review_reconciliation(self.args())

    def test_agreement_and_disagreement_counts_must_reconcile(self):
        data = fixture()
        data["a_b2_semantic_decision_agreements"] = 49
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_AGREEMENT_TOTAL_INVALID"):
            import_review_reconciliation(self.args())

    def test_aggregate_only_cases_are_not_counted_as_strict_comparisons(self):
        data = fixture()
        data["a_b2_comparable_decision_cases"] = 72
        data["a_b2_semantic_decision_agreements"] = 60
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_COMPARABLE_PAIR_TOTAL_INVALID"):
            import_review_reconciliation(self.args())

    def test_all_six_score_metrics_must_be_consistent(self):
        data = fixture()
        data["score_comparison_by_dimension"]["player_agency"]["comparable_cases"] = 49
        self.write_receipt(data)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_SCORE_METRIC_INVALID"):
            import_review_reconciliation(self.args())

    def test_independence_and_admission_flags_cannot_be_promoted(self):
        for field, value in (
            ("reviewer_b2_independence_verified", True),
            ("cryptographic_independence_proven", True),
            ("reviewer_a_two_independent_blinded_reviews_met", True),
            ("training_authorized", True),
            ("gpu_started", True),
            ("r50_accessed", True),
            ("private_values_emitted", True),
        ):
            data = fixture()
            data[field] = value
            self.write_receipt(data)
            with self.subTest(field=field), self.assertRaisesRegex(
                ManifestError, "RECONCILIATION_NON_ADMISSION_FLAGS_INVALID"
            ):
                import_review_reconciliation(self.args())

    def test_input_must_be_private_and_outside_checkout(self):
        in_repo = self.repo / "crosswalk-safe.json"
        in_repo.write_text(self.receipt.read_text(encoding="utf-8"), encoding="utf-8")
        in_repo.chmod(0o600)
        self.repo.chmod(0o755)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_INPUT_PARENT_PERMISSIONS_INVALID"):
            import_review_reconciliation(self.args(input=in_repo))
        self.repo.chmod(0o700)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_INPUT_MUST_BE_PRIVATE"):
            import_review_reconciliation(self.args(input=in_repo))

    def test_input_parent_permissions_are_enforced(self):
        public = self.root / "public"
        public.mkdir(mode=0o755)
        source = public / "crosswalk-safe.json"
        source.write_text(self.receipt.read_text(encoding="utf-8"), encoding="utf-8")
        source.chmod(0o600)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_INPUT_PARENT_PERMISSIONS_INVALID"):
            import_review_reconciliation(self.args(input=source))

    def test_symlink_input_is_rejected(self):
        link = self.private / "crosswalk-link.json"
        link.symlink_to(self.receipt)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_INPUT_NOT_REGULAR_FILE"):
            import_review_reconciliation(self.args(input=link))

    def test_duplicate_json_keys_are_rejected(self):
        self.receipt.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
        self.receipt.chmod(0o600)
        with self.assertRaisesRegex(ManifestError, "RECONCILIATION_DUPLICATE_JSON_KEY"):
            import_review_reconciliation(self.args())

    def test_manifest_append_is_append_only_and_receipt_hash_is_private(self):
        import_review_reconciliation(self.args())
        raw = self.manifest.read_text(encoding="utf-8")
        self.assertIn("source_receipt_sha256", raw)
        self.assertIn("source_pins", raw)
        self.assertNotIn("case_id", raw)
        self.assertNotIn("target_sha256", raw)
        self.assertEqual(self.manifest.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()

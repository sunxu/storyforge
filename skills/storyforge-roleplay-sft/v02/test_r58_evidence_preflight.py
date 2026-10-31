"""Synthetic-only tests for R58 Skill v0.2 G1/G2 SAFE preflight."""
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SRC = Path(__file__).with_name("r58_evidence_preflight.py")
spec = importlib.util.spec_from_file_location("r58_v02_preflight", SRC)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    rows = [
        {"id": key, "evidence": "SCOPED", "scope_observed": i < 6,
         "universe_complete": False}
        for i, key in enumerate(module.SCOPES)
    ]
    matrix = {
        "schema": module.SCHEMA,
        "status": "G1_SOURCE_UNIVERSE_HOLD__G2_PROVIDER_REQUEST_HOLD__NO_ADMISSION",
        "citations": {key: path for key, (_sha, path) in module.PINS.items()},
        "owner_scope": {
            "original_candidate_worlds": 5, "known_sft_world_excluded": 1,
            "remaining_candidate_worlds_in_hold": 4, "max_reply_targets": 20,
            "owner_policy": "ONE_ROLEPLAY_STORY_UUID_PER_WORLD",
        },
        "g1_scopes": rows,
        "g2_runtime": {
            "prompt_components": 19, "byte_exact_blocking_components": 17,
            "direct_target_to_request_link_verified": False,
            "provider_original_request_bytes_verified": False, "status": "HOLD",
        },
        "gate": {
            "g1_clearance": "HOLD", "g2_clearance": "HOLD", "g3_reviews": "NOT_STARTED",
            "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
            "expansion_allowed": False, "source_registry_complete": False,
            "all_actual_sft_runs_and_input_sources_proven_complete": False,
            "new_paid_hf_job_authorized": False,
        },
        "prohibitions": {
            "raw_story_text_exported": False, "private_candidate_uuids_exported": False,
            "r50_test_content_accessed": False, "job_started": False,
        },
    }
    docs = {
        "known_five": {
            "schema": "r58_g1_known_five_current_primary_inputs_aggregate_safe_v1",
            "g1_clearance": "HOLD", "known_parameter_update_jobs_documented": 5,
            "totals": {"bucket_objects_compared": 12,
                       "six_known_frozen_split_placements_not_unique": 184,
                       "known_job_associated_split_placements_not_unique": 344},
            "limitations": {"all_actual_sft_runs_and_input_sources_proven_complete": False,
                            "all_historical_hf_jobs_classified": False},
        },
        "round1": {
            "schema": "storyforge-r58-round1-metadata-pilot-safe-v1",
            "g1_historical_sft_exact_overlap_owner_20261030": {
                "exact_identifier_overlap_count": 1,
                "remaining_without_exact_identifier_overlap_count": 4},
            "g1_r50_protected_uuid_probe": {
                "owner_r50_actual_intersection": 0, "r50_lookup_bounded_remaining": 4},
            "owner_local_discovery_verified_20261030": {"eligible": 1280},
            "train_admitted": 0,
        },
        "g1_coverage": {
            "schema": "r58_round1_g1_evidence_coverage_safe_v1",
            "policy": {"unknown_means": "HOLD"},
            "fixed_pilot": {"story_records_under_review": 5},
        },
        "g2_gap": {
            "schema": "storyforge-r58-priority3-prompt-gap-matrix-safe-v1",
            "summary": {"components": 19, "blocking_byte_exact_components": 17,
                        "direct_request_link_verified": False,
                        "training_admission": "HOLD"},
        },
    }
    return matrix, docs


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.matrix, self.docs = fixture()

    def run_verify(self):
        return module.verify(self.matrix, self.docs)

    def test_01_known_evidence_stays_hold(self):
        r = self.run_verify()
        self.assertEqual(r["status"], "G1_G2_SAFE_EVIDENCE_RECONCILED__BOTH_HOLD")
        self.assertEqual((r["g1_clearance"], r["g2_clearance"]), ("HOLD", "HOLD"))
        self.assertEqual(r["training_admitted"], 0)

    def test_02_all_scopes_required(self):
        self.matrix["g1_scopes"].pop()
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_03_cannot_claim_universe_complete(self):
        self.matrix["g1_scopes"][0]["universe_complete"] = True
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_04_cannot_promote_g1(self):
        self.matrix["gate"]["g1_clearance"] = "PASS"
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_05_cannot_promote_g2(self):
        self.matrix["gate"]["g2_clearance"] = "PASS"
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_06_cannot_admit_cases(self):
        self.matrix["gate"]["train_admitted"] = 1
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_07_changed_old_job_receipt_holds(self):
        self.docs["known_five"]["totals"]["bucket_objects_compared"] = 11
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_08_missing_protected_check_holds(self):
        del self.docs["round1"]["g1_r50_protected_uuid_probe"]
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_09_request_link_claim_holds(self):
        self.matrix["g2_runtime"]["direct_target_to_request_link_verified"] = True
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_10_no_private_claims_allowed(self):
        self.matrix["prohibitions"]["r50_test_content_accessed"] = True
        with self.assertRaises(module.Hold):
            self.run_verify()

    def test_11_json_must_be_object(self):
        with self.assertRaises(module.Hold):
            module.safe_json(b"[]")

    def test_12_cli_without_git_fails_closed_without_path_disclosure(self):
        with tempfile.TemporaryDirectory() as root:
            err, out = io.StringIO(), io.StringIO()
            with redirect_stderr(err), redirect_stdout(out):
                code = module.main(["--repo-root", root])
            self.assertEqual(code, 42)
            self.assertEqual(out.getvalue(), "")
            self.assertNotIn(root, err.getvalue())


if __name__ == "__main__":
    unittest.main()

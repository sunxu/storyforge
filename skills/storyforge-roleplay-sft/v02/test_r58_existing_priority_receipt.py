"""Synthetic-only tests for checking pre-existing HF priority metadata."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import r58_existing_priority_receipt as m


def fixture():
    priority = {
        "schema": m.PRIORITY_SCHEMA,
        "status": "ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED",
        "namespace": "adradar", "hf_job_id_PRIVATE": "a" * 24,
        "stage": "CANCELED", "indicator_classes": ["TRAINING_LOSS_GRAD_TELEMETRY"],
        "prior_gpu_log_sha256_PRIVATE": "b" * 64,
        "update_proof_status": "PENDING_PRIMARY_RUN_ARTIFACT",
        "training_input_sha256_status": "NOT_VERIFIED",
        "train_validation_usage_status": "NOT_VERIFIED",
        "r50_content_accessed_this_step": False,
        "g1_clearance": "HOLD", "expansion_allowed": False,
    }
    receipt = {
        "schema": m.RECEIPT_SCHEMA,
        "status": "CANCELED_GPU_PROVIDER_METADATA_ONLY__NO_UPDATE_PROOF",
        "namespace": "adradar", "hf_job_id_PRIVATE": "a" * 24,
        "prior_gpu_log_sha256_PRIVATE": "b" * 64,
        "provider_started_at_present": True, "provider_finished_at_present": True,
        "command_intent_class": "NOT_ACCESSED_NO_OWNER_OPT_IN",
        "no_optimizer_update_proof": True, "primary_inputs_not_verified": True,
        "g1_clearance": "HOLD", "expansion_allowed": False,
    }
    return priority, receipt


class ExistingReceiptTests(unittest.TestCase):
    def setUp(self):
        self.priority, self.receipt = fixture()

    def test_accept_matching_receipts_but_keep_hold(self):
        result = m.verify(self.priority, self.receipt)
        self.assertEqual(result["g1_clearance"], "HOLD")
        self.assertTrue(result["job_id_and_log_sha_match_private_priority"])
        self.assertFalse(result["actual_optimizer_update_proven"])
        self.assertFalse(result["confirmed_no_optimizer_update"])
        self.assertFalse(result["actual_training_input_sha256_verified"])

    def test_never_print_private_job_id_or_hash(self):
        result = json.dumps(m.verify(self.priority, self.receipt))
        self.assertNotIn("a" * 24, result)
        self.assertNotIn("b" * 64, result)
        self.assertNotIn("hf_job_id_PRIVATE", result)

    def test_mismatched_job_fails(self):
        self.receipt["hf_job_id_PRIVATE"] = "c" * 24
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_mismatched_prior_log_digest_fails(self):
        self.receipt["prior_gpu_log_sha256_PRIVATE"] = "c" * 64
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_extra_raw_command_field_fails(self):
        self.receipt["command"] = "private content"
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_source_training_status_drift_fails(self):
        self.priority["update_proof_status"] = "PASS"
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_source_r50_read_claim_fails(self):
        self.priority["r50_content_accessed_this_step"] = True
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_unsafe_update_proof_claim_fails(self):
        self.receipt["no_optimizer_update_proof"] = False
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_changed_clearance_fails(self):
        self.receipt["g1_clearance"] = "PASS"
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_command_intent_still_no_proof(self):
        self.receipt["command_intent_class"] = "POTENTIAL_TRAINING_COMMAND_INTENT"
        r = m.verify(self.priority, self.receipt)
        self.assertFalse(r["actual_optimizer_update_proven"])

    def test_invalid_command_intent_fails(self):
        self.receipt["command_intent_class"] = "secret shell text"
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_reject_missing_timestamp_bools(self):
        self.receipt["provider_finished_at_present"] = None
        with self.assertRaises(m.Hold):
            m.verify(self.priority, self.receipt)

    def test_reject_reused_same_path(self):
        out, err = io.StringIO(), io.StringIO()
        path = Path("/some/PRIVATE.json")
        with redirect_stdout(out), redirect_stderr(err):
            code = m.main(["--private-priority-ledger", str(path),
                           "--existing-private-metadata", str(path)])
        self.assertEqual(code, 42)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn(str(path), err.getvalue())

    def test_cli_reads_preexisting_files_without_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".storyforge-r58-private"
            root.mkdir(mode=0o700)
            priority = root / "priority.json"
            receipt = root / "receipt.json"
            for path, body in ((priority, self.priority), (receipt, self.receipt)):
                path.write_text(json.dumps(body), encoding="utf-8")
                path.chmod(0o600)
            before = (priority.read_bytes(), receipt.read_bytes())
            out = io.StringIO()
            with patch.object(Path, "home", return_value=Path(tmp)), redirect_stdout(out):
                code = m.main(["--private-priority-ledger", str(priority),
                               "--existing-private-metadata", str(receipt)])
            self.assertEqual(code, 0)
            self.assertEqual((priority.read_bytes(), receipt.read_bytes()), before)
            self.assertEqual(json.loads(out.getvalue())["g1_clearance"], "HOLD")


if __name__ == "__main__":
    unittest.main()

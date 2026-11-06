"""Synthetic-only fail-closed tests for the C execution receipt builder."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.r58_quality import r60_reviewer_c_audit as audit
from experiments.r58_quality import r60_reviewer_c_receipt_builder as builder
from experiments.r58_quality.test_r60_reviewer_c_audit import fixture


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()


def answers(*, mode="STATELESS_API", session="req-synthetic", start="2026-11-06T09:00:00Z",
            end="2026-11-06T09:05:00Z", flags=None):
    confirmations = ["YES"] * 10
    for position, value in (flags or {}).items():
        confirmations[position] = value
    return "\n".join([mode, "synthetic-provider", "synthetic-model", "synthetic-version",
                       session, start, end, *confirmations]) + "\n"


class ReceiptBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir(mode=0o700)
        self.private = self.root / "owner_private"
        self.private.mkdir(mode=0o700)
        blind, instructions, mapping, result, _receipt, execution = fixture()
        self.data = {
            "blind_input": blind, "instructions": instructions, "owner_map": mapping,
            "result": result, "execution_record": execution,
        }
        self._refresh_package()
        for key, value in self.data.items():
            self._write(key, value)
        self.args = argparse.Namespace(**{
            **{key: self.private / key for key in builder.LIMITS},
            "output": self.private / "receipt.json",
            "draft_output": self.private / "draft.json",
            "repo_root": self.repo,
            "validate_only": False,
        })

    def _write(self, key, data):
        self.data[key] = data
        path = self.private / key
        path.write_bytes(data)
        path.chmod(0o600)

    def _refresh_package(self):
        template = {
            "schema": audit.EXECUTION_SCHEMA, "reviewer": "C",
            "status": "PENDING_INDEPENDENT_REVIEW_EXECUTION",
            "blind_input_sha256": sha(self.data["blind_input"]),
            "instructions_sha256": sha(self.data["instructions"]),
            "attestations": {key: None for key in audit.ATTESTATIONS},
            "owner_verification": {key: False for key in audit.OWNER_VERIFICATION},
            "limitations": ["Synthetic data; not evidence of reviewer independence."],
        }
        self.data["receipt_template"] = encoded(template)
        safe = {
            "schema": builder.PACKAGE_SCHEMA, "status": builder.PACKAGE_STATUS,
            "candidate_count": 40,
            "blind_input_sha256": sha(self.data["blind_input"]),
            "instructions_sha256": sha(self.data["instructions"]),
            "owner_map_sha256": sha(self.data["owner_map"]),
            "execution_receipt_template_sha256": sha(self.data["receipt_template"]),
        }
        self.data["package_safe"] = encoded(safe)
        for key in ("package_safe", "receipt_template"):
            if (self.private / key).exists():
                self._write(key, self.data[key])

    def _change_json(self, key, mutate, *, refresh=False):
        value = json.loads(self.data[key])
        mutate(value)
        self._write(key, encoded(value))
        if refresh:
            self._refresh_package()

    def _execute(self, response=None):
        with (patch("sys.stdin", io.StringIO(response or answers())),
              contextlib.redirect_stderr(io.StringIO())):
            return builder.run(self.args)

    def _hold(self, reason, response=None):
        existed_before = self.args.output.exists()
        with self.assertRaisesRegex((builder.ReceiptHold, audit.AuditHold), reason):
            self._execute(response)
        if not existed_before:
            self.assertFalse(self.args.output.exists())

    def test_valid_receipt_integrates_with_existing_audit(self):
        safe = self._execute()
        self.assertEqual(safe["status"], "C_EXECUTION_RECEIPT_CREATED__SELF_ATTESTED_NOT_PROVEN")
        receipt = json.loads(self.args.output.read_bytes())
        self.assertEqual(receipt["status"], "EXECUTION_COMPLETE")
        self.assertEqual(set(receipt["attestations"]), audit.ATTESTATIONS)
        self.assertEqual(set(receipt["owner_verification"]), audit.OWNER_VERIFICATION)
        self.assertEqual(receipt["blind_input_sha256"], sha(self.data["blind_input"]))
        self.assertEqual(receipt["instructions_sha256"], sha(self.data["instructions"]))
        self.assertEqual(receipt["result_sha256"], sha(self.data["result"]))
        self.assertEqual(receipt["transcript_or_provider_record_sha256"], sha(self.data["execution_record"]))
        self.assertEqual(os.stat(self.args.output).st_mode & 0o777, 0o600)
        accepted = audit.audit(self.data["blind_input"], self.data["instructions"],
                               self.data["owner_map"], self.data["result"],
                               self.args.output.read_bytes(), self.data["execution_record"])
        self.assertEqual(accepted["status"], "C_RESULT_BINDING_VALID__EXECUTION_ATTESTATION_PRESENT_NOT_PROVEN")
        self.assertFalse(accepted["cryptographic_independence_proven"])
        self.assertFalse(accepted["reviewer_c_independence_verified"])
        self.assertEqual(accepted["quality_v1_admitted"], 0)
        self.assertEqual(self.args.output.parent.stat().st_mode & 0o777, 0o700)

    def test_validate_only_never_requests_attestations_or_writes(self):
        self.args.validate_only = True
        with patch("sys.stdin", io.StringIO("")):
            result = self._execute()
        self.assertEqual(result["case_bindings_valid"], 40)
        self.assertEqual(result["status"], "C_RECEIPT_INPUTS_VALID__OWNER_CONFIRMATION_PENDING")
        self.assertFalse(self.args.output.exists())

    def test_package_safe_pin_mismatch(self):
        self._write("instructions", b"tampered synthetic instructions")
        self._hold("C_PACKAGE_PIN_MISMATCH")
        self._write("instructions", self.data["instructions"])

    def test_blind_case_count_and_duplicate_ids_and_target_sha(self):
        for mutation, reason in (
            (lambda x: x["cases"].pop(), "C_BLIND_CASE_COUNT_INVALID"),
            (lambda x: x["cases"][1].update(blind_case_id=x["cases"][0]["blind_case_id"]), "C_BLIND_ID_DUPLICATE"),
            (lambda x: x["cases"][1].update(target_sha256=x["cases"][0]["target_sha256"]), "C_BLIND_TARGET_SHA_DUPLICATE"),
        ):
            original = self.data["blind_input"]
            self._change_json("blind_input", mutation, refresh=True)
            self._hold(reason)
            self._write("blind_input", original)
            self._refresh_package()

    def test_owner_map_join_mismatch(self):
        self._change_json("owner_map", lambda x: x["mapping"][0].update(target_sha256="f" * 64), refresh=True)
        self._hold("C_BLIND_OWNER_MAP_SET_MISMATCH")

    def test_result_schema_count_join_scores_and_counts(self):
        for mutation, reason in (
            (lambda x: x.update(schema="wrong"), "C_RESULT_SCHEMA_INVALID"),
            (lambda x: x["cases"].pop(), "C_RESULT_CASE_COUNT_INVALID"),
            (lambda x: x["cases"][0].update(target_sha256="f" * 64), "C_RESULT_OWNER_MAP_SET_MISMATCH"),
            (lambda x: x["cases"][0]["scores_1_to_5"].update(chinese_prose=True), "C_RESULT_SCORES_INVALID"),
            (lambda x: x["cases"][0].update(severe_flags="a"), "C_RESULT_SEVERE_FLAGS_INVALID"),
            (lambda x: x.update(counts={"PASS": 71, "HOLD": 1, "REJECT": 0}), "C_RESULT_COUNTS_INVALID"),
            (lambda x: x["cases"][0]["scores_1_to_5"].update(player_agency=2), "C_PASS_GATE_VIOLATION"),
            (lambda x: x["cases"][0].update(severe_flags=["Synthetic severe flag"]), "C_PASS_GATE_VIOLATION"),
        ):
            original = self.data["result"]
            self._change_json("result", mutation)
            self._hold(reason)
            self._write("result", original)

    def test_execution_record_missing_symlink_directory_empty_oversize_or_results(self):
        path = self.args.execution_record
        original = self.data["execution_record"]
        for bad in ("missing", "symlink", "directory", "empty", "oversize"):
            path.unlink()
            if bad == "symlink":
                path.symlink_to(self.args.result)
            elif bad == "directory":
                path.mkdir()
            elif bad == "empty":
                path.write_bytes(b"")
            elif bad == "oversize":
                with path.open("wb") as stream:
                    stream.truncate(builder.LIMITS["execution_record"] + 1)
            self._hold("INPUT_NOT_REGULAR_OR_SIZE_INVALID")
            if path.is_dir() and not path.is_symlink():
                path.rmdir()
            elif path.exists() or path.is_symlink():
                path.unlink()
            path.write_bytes(original)
        self._write("execution_record", self.data["result"])
        self._hold("C_EXECUTION_RECORD_EQUALS_RESULT")

    def test_timestamps_mode_and_session_fail_closed_to_draft(self):
        for kw in (
            {"start": "2026-11-06T09:00:00"},
            {"start": "2026-11-06T10:00:00Z"},
            {"mode": "INVALID"},
            {"session": builder.SENTINEL},
        ):
            result = self._execute(answers(**kw))
            self.assertEqual(result["status"], "C_RECEIPT_HOLD")
            self.assertFalse(self.args.output.exists())
            draft = json.loads(self.args.draft_output.read_bytes())
            self.assertEqual(draft["status"], "PENDING_OWNER_CONFIRMATION")
            self.args.draft_output.unlink()

    def test_any_attestation_no_unknown_or_owner_unconfirmed_holds(self):
        for index in range(10):
            for response in ("NO", "UNKNOWN", ""):
                result = self._execute(answers(flags={index: response}))
                self.assertEqual(result["status"], "C_RECEIPT_HOLD")
                self.assertFalse(self.args.output.exists())
                draft = json.loads(self.args.draft_output.read_bytes())
                self.assertNotEqual(draft["status"], "EXECUTION_COMPLETE")
                self.args.draft_output.unlink()

    def test_temporary_chat_sentinel_records_limitations(self):
        result = self._execute(answers(mode="CHATGPT_TEMPORARY_CHAT", session=builder.SENTINEL))
        self.assertEqual(result["status"], "C_EXECUTION_RECEIPT_CREATED__SELF_ATTESTED_NOT_PROVEN")
        receipt = json.loads(self.args.output.read_bytes())
        self.assertEqual(receipt["session_or_request_id"], builder.SENTINEL)
        self.assertTrue(any("not a real ID" in item for item in receipt["limitations"]))

    def test_create_only_output_and_private_location(self):
        self.args.output.write_text("prior")
        self._hold("C_OUTPUT_PATH_INVALID_OR_EXISTS")
        self.assertEqual(self.args.output.read_text(), "prior")
        self.args.output.unlink()
        self.args.output = self.repo / "receipt.json"
        self._hold("C_OUTPUT_LOCATION_INVALID")

    def test_package_template_with_preset_confirmations_is_rejected(self):
        original = self.data["receipt_template"]
        self._change_json("receipt_template", lambda x: x["attestations"].update(
            reviewer_a_materials_not_provided=True))
        safe = json.loads(self.data["package_safe"])
        safe["execution_receipt_template_sha256"] = sha(self.data["receipt_template"])
        self._write("package_safe", encoded(safe))
        self._hold("C_RECEIPT_TEMPLATE_PRECONFIRMED")
        self._write("receipt_template", original)

    def test_no_private_summary_in_stdout(self):
        self.args.validate_only = True
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = builder.main_with_args(self.args) if hasattr(builder, "main_with_args") else builder.run(self.args)
        self.assertNotIn("private-0000", out.getvalue())
        self.assertNotIn("Synthetic-only review evidence", out.getvalue())
        self.assertIsNotNone(rc)


if __name__ == "__main__":
    unittest.main()

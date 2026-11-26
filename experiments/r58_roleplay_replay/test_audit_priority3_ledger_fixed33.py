"""Only synthetic fixed-source selection tests. No network/real credentials."""
import os
import json
import subprocess
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
import uuid

from capture_priority3 import capture, Hold
from test_capture_priority3 import row, encode
from audit_priority3_ledger_fixed33 import fixed_rows, query_text, aggregate


class TestFixedLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parent = Path(self.tmp.name) / "private"
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [row("AUTHOR", 1), row("CURRENT_PUBLIC", 2),
                     row("OLD_PUBLIC", 3)]
        for k, case in enumerate(self.rows):
            case["prior_checkpoint"]["snapshot"]["last_summary_turn"] = 20
            for i, msg in enumerate(case["history24"]):
                msg["id"] = str(uuid.UUID(int=k * 100 + i + 1))
                msg["role"] = "assistant" if i % 2 == 0 else "user"
                msg["mutation_revision"] = 2 if i % 2 == 0 else 0

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        capture(encode(self.rows), self.parent, "freeze1")
        return self.parent / "freeze1"

    def test_selected_count(self):
        rows = fixed_rows(self.freeze())
        self.assertEqual(len(rows), 33)
        self.assertEqual(len({x["msgid"] for x in rows}), 33)

    def test_readonly_query(self):
        sql = query_text(fixed_rows(self.freeze()))
        self.assertIn("BEGIN READ ONLY;", sql)
        self.assertIn("v2_chat_message_ledger", sql)
        self.assertNotIn("test target", sql)
        self.assertNotIn("fiction", sql)

    def test_private_source_unmodified(self):
        folder = self.freeze()
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        fixed_rows(folder)
        self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_invalid_id_fails_closed(self):
        self.rows[0]["history24"][-1]["id"] = "not-a-uuid"
        with self.assertRaises(Hold):
            fixed_rows(self.freeze())

    def test_tamper_fails_closed(self):
        folder = self.freeze()
        source = folder / "source.private.jsonl"
        source.write_bytes(source.read_bytes().replace(b"test target", b"other text", 1))
        os.chmod(source, 0o600)
        with self.assertRaises(Hold):
            fixed_rows(folder)

    @staticmethod
    def _sample_safe_db_result():
        cases = []
        for cohort, updates in (("AUTHOR", 0), ("CURRENT_PUBLIC", 5),
                                ("OLD_PUBLIC", 5)):
            cases.append({
                "cohort": cohort, "messages": 11, "assistants": 5,
                "users": 6, "missing_current": 0, "revision_drift": 0,
                "content_drift": 0, "ledger_through_target": 11 + 2*updates,
                "ledger_after_target": 0, "prior_completed_text_variants": 0,
                "ledger_insert_before_target": 11,
                "ledger_update_before_before_target": updates,
                "ledger_update_after_before_target": updates,
                "ledger_delete_before_target": 0, "ledger_other_before_target": 0,
                "assistant_insert_before_target": 5,
                "user_insert_before_target": 6,
                "assistant_update_before_target": updates,
                "assistant_update_after_before_target": updates,
                "private_unexpected_value": "DO_NOT_ECHO_PRIVATE",
            })
        return {"readonly": "on", "reader": True, "cases": cases}

    def _run_mock(self, response):
        with patch.dict(os.environ, {
            "PGHOST": "aws-1-ap-southeast-1.pooler.supabase.com",
            "PGUSER": "r58_export_reader.cckbpebhzmyasmttnfwp",
            "PGPASSWORD": "test-only",
        }), patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=["psql"], returncode=0,
            stdout=json.dumps(response) + "\n", stderr="untrusted-db-error",
        )) as runner:
            result = aggregate(self.freeze())
            self.assertTrue(runner.call_args.kwargs["capture_output"])
            self.assertIn("BEGIN READ ONLY", runner.call_args.kwargs["input"])
            return result

    def test_operation_breakdown_11_and_21(self):
        result = self._run_mock(self._sample_safe_db_result())
        self.assertEqual(result["status"],
                         "R58_LEDGER_FIXED33_DIAGNOSTIC_PASS__ASOF_PROMPT_HOLD")
        self.assertEqual([c["ledger_through_target"] for c in result["cases"]],
                         [11, 21, 21])
        self.assertEqual(result["training_admission"], "HOLD")

    def test_unexpected_private_db_field_not_echoed(self):
        result = self._run_mock(self._sample_safe_db_result())
        self.assertNotIn("DO_NOT_ECHO_PRIVATE", json.dumps(result))
        self.assertNotIn("private_unexpected_value", json.dumps(result))

    def test_unexplained_ledger_operation_count_is_hold(self):
        response = self._sample_safe_db_result()
        response["cases"][0]["ledger_through_target"] = 12
        result = self._run_mock(response)
        self.assertEqual(result["status"],
                         "R58_LEDGER_FIXED33_OPERATION_CLASSIFICATION_HOLD")

    def test_unsupported_host_rejected_before_network(self):
        with patch.dict(os.environ, {
            "PGHOST": "untrusted.example.invalid",
            "PGUSER": "r58_export_reader",
            "PGPASSWORD": "test-only",
        }), patch("subprocess.run") as runner:
            with self.assertRaisesRegex(Hold, "unexpected DB host"):
                aggregate(self.freeze())
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""Synthetic-only tests for the fixed-target request timeline probe."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import uuid

from capture_priority3 import capture, Hold
from test_capture_priority3 import row, encode
from audit_priority3_request_timeline import fixed_targets, query_sql, project, audit


def fake_result(compatible=1):
    return {"role_correct": True, "transaction_read_only": "on", "cases": [
        {
            "cohort": cohort, "target_found": True, "target_created_matches": True,
            "terminal_events_in_window": 1,
            "events_with_matching_metric": 1,
            "events_with_one_metric": 1,
            "timing_compatible_joined_events": compatible,
            "missing_duration_events": 0,
            "excess_candidates": False,
        }
        for cohort in ("AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC")
    ]}


class TestRequestTimeline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = Path(self.temp.name) / "private"
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [row("AUTHOR", 1), row("CURRENT_PUBLIC", 2),
                     row("OLD_PUBLIC", 3)]
        for n, item in enumerate(self.rows):
            item["case"]["target_message_id"] = str(uuid.UUID(int=n + 1))

    def tearDown(self):
        self.temp.cleanup()

    def freeze(self):
        capture(encode(self.rows), self.parent, "frozen")
        return self.parent / "frozen"

    def test_scope_three_frozen_targets(self):
        rows = fixed_targets(self.freeze())
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r["target_id"] for r in rows}), 3)

    def test_readonly_sql_scope_has_no_story_body(self):
        sql = query_sql(fixed_targets(self.freeze()))
        self.assertIn("BEGIN READ ONLY;", sql)
        self.assertIn("v2_chat_request_events", sql)
        self.assertIn("lm.request_id=ev.request_id", sql)
        self.assertIn("LIMIT 101", sql)
        self.assertNotIn("fiction", sql)
        self.assertNotIn("test target", sql)

    def test_unique_candidate_still_holds_exact_target_link(self):
        result = project(fake_result())
        self.assertIn("UNIQUE_CANDIDATE_3_OF_3", result["status"])
        self.assertFalse(result["exact_target_message_to_request_join"])
        self.assertFalse(result["request_start_time_certified"])
        self.assertEqual(result["training_admission"], "HOLD")

    def test_ambiguous_or_missing_candidate_holds(self):
        result = project(fake_result(compatible=0))
        self.assertEqual(result["status"], "R58_REQUEST_TIMELINE_CORRELATION_HOLD")

    def test_duplicate_or_absent_group_is_rejected(self):
        result = fake_result()
        result["cases"][2]["cohort"] = "AUTHOR"
        with self.assertRaises(Hold):
            project(result)

    def test_readonly_role_guard(self):
        result = fake_result()
        result["role_correct"] = False
        with self.assertRaises(Hold):
            project(result)

    def test_unexpected_private_fields_do_not_escape(self):
        data = fake_result()
        data["private_id"] = "SECRET_PARENT"
        data["cases"][0]["private_value"] = "SECRET_DETAIL"
        text = json.dumps(project(data))
        self.assertNotIn("SECRET_PARENT", text)
        self.assertNotIn("SECRET_DETAIL", text)

    def test_aggregate_inconsistency_rejected(self):
        data = fake_result()
        data["cases"][1]["events_with_matching_metric"] = 2
        with self.assertRaises(Hold):
            project(data)

    def test_private_source_immutable(self):
        folder = self.freeze()
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        fixed_targets(folder)
        self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_bad_host_holds_before_network(self):
        with patch.dict(os.environ, {
            "PGHOST": "untrusted.invalid", "PGUSER": "r58_export_reader",
            "PGPASSWORD": "synthetic-test-only",
        }), patch("subprocess.run") as psql:
            with self.assertRaises(Hold):
                audit(self.freeze())
            psql.assert_not_called()

    def test_mocked_psql_safe_projection(self):
        with patch.dict(os.environ, {
            "PGHOST": "aws-1-ap-southeast-1.pooler.supabase.com",
            "PGUSER": "r58_export_reader.cckbpebhzmyasmttnfwp",
            "PGPASSWORD": "synthetic-test-only",
        }), patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=["psql"], returncode=0, stdout=json.dumps(fake_result()) + "\n",
            stderr="secret-error-not-for-output",
        )) as psql:
            result = audit(self.freeze())
            self.assertTrue(psql.call_args.kwargs["capture_output"])
            self.assertEqual(result["training_admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()

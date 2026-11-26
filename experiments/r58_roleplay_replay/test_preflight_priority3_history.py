"""R58: tests use synthetic sources only; no Supabase / HF / R50 / network."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from capture_priority3 import capture, Hold
from preflight_priority3_history import preflight
from test_capture_priority3 import row, encode


class TestHistoryPreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = Path(self.temp.name) / "private"
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [
            row("AUTHOR", 1),
            row("CURRENT_PUBLIC", 2),
            row("OLD_PUBLIC", 3),
        ]
        for rec in self.rows:
            rec["prior_checkpoint"]["snapshot"]["last_summary_turn"] = 20
            rec["untrusted_nearby_metric"] = {"history_msg_count": "11"}
            rec["target"]["metadata"] = {}
            for i, msg in enumerate(rec["history24"]):
                msg["role"] = "assistant" if i % 2 == 0 else "user"
                msg["metadata"] = {}
                msg["mutation_revision"] = 0
        for rec in self.rows[1:]:
            rec["target"]["metadata"] = {"v2EventRuntimeBefore": {"revision": 1}}
            rec["history24"][-2]["metadata"] = {
                "v2EventRuntimeAfter": {"revision": 1}
            }

    def tearDown(self):
        self.temp.cleanup()

    def make_capture(self):
        capture(encode(self.rows), self.parent, "freeze1")
        return self.parent / "freeze1"

    def test_matching_history_and_event_structure(self):
        result = preflight(self.make_capture())
        self.assertEqual(result["source_11_message_structure_pass"], 3)
        self.assertEqual(result["nearby_metric_count_11"], 3)
        self.assertEqual(result["event_chain_direct_match"], 2)
        self.assertEqual(result["event_chain_metadata_absent"], 1)
        self.assertEqual(result["event_chain_holds"], 0)
        self.assertIn("STRUCTURE_PASS", result["status"])
        self.assertEqual(result["training_admission"], "HOLD")

    def test_zero_summary_cursor_not_falsely_promoted(self):
        self.rows[0]["prior_checkpoint"]["snapshot"]["last_summary_turn"] = 0
        result = preflight(self.make_capture())
        self.assertEqual(result["source_11_message_structure_pass"], 2)
        self.assertEqual(result["status"], "R58_HISTORY_STRUCTURE_OR_EVENT_CHAIN_HOLD")

    def test_previous_assistant_event_chain_mismatch(self):
        self.rows[2]["history24"][-2]["metadata"]["v2EventRuntimeAfter"] = {"revision": 99}
        result = preflight(self.make_capture())
        self.assertEqual(result["event_chain_direct_match"], 1)
        self.assertEqual(result["event_chain_holds"], 1)
        self.assertEqual(result["status"], "R58_HISTORY_STRUCTURE_OR_EVENT_CHAIN_HOLD")

    def test_nearby_metric_mismatch(self):
        self.rows[1]["untrusted_nearby_metric"]["history_msg_count"] = "10"
        result = preflight(self.make_capture())
        self.assertEqual(result["nearby_metric_count_11"], 2)
        self.assertEqual(result["status"], "R58_HISTORY_STRUCTURE_OR_EVENT_CHAIN_HOLD")

    def test_continue_user_row_flag(self):
        self.rows[1]["history24"][-1]["metadata"] = {"type": "continue"}
        result = preflight(self.make_capture())
        current = next(v for v in result["cases"] if v["cohort"] == "CURRENT_PUBLIC")
        self.assertTrue(current["continue_row_in_conditional_window"])

    def test_structured_scrub_risk_flag(self):
        self.rows[2]["history24"][-2]["content"] = "<text>synthetic</text>"
        result = preflight(self.make_capture())
        old = next(v for v in result["cases"] if v["cohort"] == "OLD_PUBLIC")
        self.assertTrue(old["assistant_structured_scrub_may_apply"])

    def test_mutation_risk_flag(self):
        self.rows[0]["history24"][-1]["mutation_revision"] = 3
        result = preflight(self.make_capture())
        author = next(v for v in result["cases"] if v["cohort"] == "AUTHOR")
        self.assertEqual(author["mutated_rows_in_conditional_window"], 1)

    def test_no_secret_ids_content_or_hashes_in_output(self):
        result = preflight(self.make_capture())
        output = json.dumps(result)
        for text in ["story-1", "session-1", "target-1", "submission-1",
                     "test target", "fiction", "raw_jsonl_sha256"]:
            self.assertNotIn(text, output)

    def test_private_bundle_not_modified(self):
        folder = self.make_capture()
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        preflight(folder)
        after = {p.name: p.read_bytes() for p in folder.iterdir()}
        self.assertEqual(before, after)

    def test_corrupted_source_file_fail_closed(self):
        folder = self.make_capture()
        f = folder / "source.private.jsonl"
        f.write_bytes(f.read_bytes().replace(b"test target", b"other value", 1))
        os.chmod(f, 0o600)
        with self.assertRaises(Hold):
            preflight(folder)


if __name__ == "__main__":
    unittest.main()

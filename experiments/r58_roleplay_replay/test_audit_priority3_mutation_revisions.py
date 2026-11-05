"""Synthetic-only tests: mutation revision does not imply text edit."""
from pathlib import Path
import json
import os
import tempfile
import unittest

from audit_priority3_mutation_revisions import audit
from capture_priority3 import capture, Hold
from test_capture_priority3 import row, encode


class TestMutationRevisionRoleAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parent = Path(self.tmp.name) / "private"
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [row("AUTHOR", 1), row("CURRENT_PUBLIC", 2), row("OLD_PUBLIC", 3)]
        for rec in self.rows:
            rec["prior_checkpoint"]["snapshot"]["last_summary_turn"] = 20
            rec["untrusted_nearby_metric"] = {"history_msg_count": "11"}
            rec["target"]["metadata"] = {}
            for idx, msg in enumerate(rec["history24"]):
                msg["role"] = "assistant" if idx % 2 == 0 else "user"
                msg["metadata"] = {}
                msg["mutation_revision"] = 1 if idx % 2 == 0 else 0
        for rec in self.rows[1:]:
            rec["target"]["metadata"] = {"v2EventRuntimeBefore": {"revision": 1}}
            rec["history24"][-2]["metadata"] = {"v2EventRuntimeAfter": {"revision": 1}}

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        capture(encode(self.rows), self.parent, "freeze1")
        return self.parent / "freeze1"

    def test_five_positive_assistants_not_automatically_text_edits(self):
        out = audit(self.freeze())
        self.assertEqual(len(out["cases"]), 3)
        for case in out["cases"]:
            self.assertEqual(case["revision_positive_rows"], 5)
            self.assertEqual(case["role_counts"]["assistant"], {"total": 5, "revision_positive": 5})
            self.assertEqual(case["role_counts"]["user"], {"total": 6, "revision_positive": 0})
            self.assertEqual(case["historical_content_unchanged"], "HOLD")
            self.assertEqual(case["status_only_or_stream_finalization"], "POSSIBLE_NOT_VERIFIED")

    def test_positive_user_revision_detected(self):
        self.rows[0]["history24"][-1]["mutation_revision"] = 2
        out = audit(self.freeze())
        author = next(c for c in out["cases"] if c["cohort"] == "AUTHOR")
        self.assertEqual(author["role_counts"]["user"]["revision_positive"], 1)
        self.assertEqual(author["revision_positive_rows"], 6)

    def test_assistant_revision_zero_detected(self):
        self.rows[1]["history24"][-2]["mutation_revision"] = 0
        out = audit(self.freeze())
        case = next(c for c in out["cases"] if c["cohort"] == "CURRENT_PUBLIC")
        self.assertEqual(case["role_counts"]["assistant"]["revision_positive"], 4)

    def test_bad_revision_type_holds(self):
        self.rows[2]["history24"][-2]["mutation_revision"] = "1"
        with self.assertRaisesRegex(Hold, "type invalid"):
            audit(self.freeze())

    def test_non_eleven_window_holds(self):
        self.rows[1]["prior_checkpoint"]["snapshot"]["last_summary_turn"] = 0
        with self.assertRaisesRegex(Hold, "11-message"):
            audit(self.freeze())

    def test_no_private_ids_text_or_hashes_in_output(self):
        out = json.dumps(audit(self.freeze()))
        for private in ("story-1", "submission-1", "session-1",
                        "test target", "fiction", "raw_jsonl_sha256"):
            self.assertNotIn(private, out)

    def test_immutable_source(self):
        folder = self.freeze()
        a = {f.name: f.read_bytes() for f in folder.iterdir()}
        audit(folder)
        b = {f.name: f.read_bytes() for f in folder.iterdir()}
        self.assertEqual(a, b)

    def test_corrupted_source_holds(self):
        folder = self.freeze()
        source = folder / "source.private.jsonl"
        source.write_bytes(source.read_bytes().replace(b"test target", b"corrupt data", 1))
        os.chmod(source, 0o600)
        with self.assertRaises(Hold):
            audit(folder)


if __name__ == "__main__":
    unittest.main()

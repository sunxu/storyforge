"""Only synthetic fixed-source selection tests. No network/real credentials."""
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from capture_priority3 import capture, Hold
from test_capture_priority3 import row, encode
from audit_priority3_ledger_fixed33 import fixed_rows, query_text


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


if __name__ == "__main__":
    unittest.main()

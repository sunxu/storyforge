"""Synthetic-only R58 request-key inventory checks."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from capture_priority3 import capture, Hold
from test_capture_priority3 import row, encode
from inventory_priority3_request_keys import inventory


class TestRequestKeys(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = Path(self.temp.name) / "private"
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [row("AUTHOR", 1), row("CURRENT_PUBLIC", 2),
                     row("OLD_PUBLIC", 3)]

    def tearDown(self):
        self.temp.cleanup()

    def freeze(self):
        capture(encode(self.rows), self.parent, "frozen")
        return self.parent / "frozen"

    def test_no_known_key_all_false(self):
        out = inventory(self.freeze())
        self.assertEqual(len(out["cases"]), 3)
        self.assertFalse(out["exact_target_request_join_verified"])
        self.assertEqual(out["training_admission"], "HOLD")

    def test_detects_key_without_exposing_value(self):
        self.rows[1]["target"]["metadata"] = {
            "requestId": "SECRET_SAMPLE_VALUE"
        }
        out = inventory(self.freeze())
        current = next(c for c in out["cases"] if c["cohort"] == "CURRENT_PUBLIC")
        self.assertTrue(current["known_request_key_present"]["requestId"])
        self.assertNotIn("SECRET_SAMPLE_VALUE", json.dumps(out))

    def test_source_immutable(self):
        folder = self.freeze()
        before = {x.name: x.read_bytes() for x in folder.iterdir()}
        inventory(folder)
        self.assertEqual(before, {x.name: x.read_bytes() for x in folder.iterdir()})

    def test_checksum_tamper_holds(self):
        folder = self.freeze()
        path = folder / "source.private.jsonl"
        path.write_bytes(path.read_bytes().replace(b"test target", b"not original", 1))
        os.chmod(path, 0o600)
        with self.assertRaises(Hold):
            inventory(folder)


if __name__ == "__main__":
    unittest.main()

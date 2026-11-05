"""R58 revision-depth profiler synthetic-only tests (no narrative/user data)."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from capture_priority3 import capture, Hold
from profile_priority3_revision_depth import check
from test_capture_priority3 import row, encode


class TestRevisionDepth(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "private"
        self.root.mkdir(mode=0o700)
        os.chmod(self.root, 0o700)
        self.rows = [row("AUTHOR", 1), row("CURRENT_PUBLIC", 2), row("OLD_PUBLIC", 3)]
        for case in self.rows:
            case["prior_checkpoint"]["snapshot"]["last_summary_turn"] = 20
            for i, msg in enumerate(case["history24"]):
                msg["role"] = "assistant" if i % 2 == 0 else "user"
                msg["mutation_revision"] = 1 if i % 2 == 0 else 0

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        capture(encode(self.rows), self.root, "freeze1")
        return self.root / "freeze1"

    def test_five_revision_one_assistants(self):
        out = check(self.freeze())
        self.assertEqual(len(out["cases"]), 3)
        for item in out["cases"]:
            a = item["role_counts"]["assistant"]
            u = item["role_counts"]["user"]
            self.assertEqual(a["revision_1"], 5)
            self.assertEqual(a["revision_2_plus"], 0)
            self.assertEqual(u["revision_0"], 6)
            self.assertEqual(item["historical_content_as_of_request"], "HOLD")

    def test_revision_two_plus_visible(self):
        self.rows[0]["history24"][-2]["mutation_revision"] = 4
        out = check(self.freeze())
        author = next(x for x in out["cases"] if x["cohort"] == "AUTHOR")
        self.assertEqual(author["role_counts"]["assistant"]["revision_1"], 4)
        self.assertEqual(author["role_counts"]["assistant"]["revision_2_plus"], 1)

    def test_user_revision_visible(self):
        self.rows[1]["history24"][-1]["mutation_revision"] = 1
        out = check(self.freeze())
        current = next(x for x in out["cases"] if x["cohort"] == "CURRENT_PUBLIC")
        self.assertEqual(current["role_counts"]["user"]["revision_1"], 1)

    def test_invalid_revision_rejected(self):
        self.rows[2]["history24"][-2]["mutation_revision"] = "1"
        with self.assertRaisesRegex(Hold, "source revision data invalid"):
            check(self.freeze())

    def test_no_private_identifiers_or_text(self):
        output = json.dumps(check(self.freeze()))
        for value in ("story-1", "target-1", "session-1",
                      "submission-1", "fiction", "test target", "sha256"):
            self.assertNotIn(value, output)

    def test_source_is_not_modified(self):
        folder = self.freeze()
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        check(folder)
        after = {p.name: p.read_bytes() for p in folder.iterdir()}
        self.assertEqual(before, after)

    def test_modified_capture_rejected(self):
        folder = self.freeze()
        path = folder / "source.private.jsonl"
        path.write_bytes(path.read_bytes().replace(b"test target", b"bad target", 1))
        os.chmod(path, 0o600)
        with self.assertRaises(Hold):
            check(folder)


if __name__ == "__main__":
    unittest.main()

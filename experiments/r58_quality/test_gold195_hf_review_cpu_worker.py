import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_hf_review_cpu_stage import prep
from gold195_hf_review_cpu_worker import verify_stage, load_rows, preflight
from gold195_hf_review_batch import input_record
from gold195_assistant_first_full132 import build
from test_gold195_assistant_first_semantic_pilot import example


class DummyTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return [3] * (100 + len(messages[0]["content"]) // 40)


class HFCPU132Tests(unittest.TestCase):
    def setUp(self):
        self.rows = [input_record(x) for x in build([example(i) for i in range(132)])[1]]

    def test_cpu_worker_132_and_token_counts(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "input.jsonl"
            p.write_bytes(b"".join(json.dumps(r, ensure_ascii=False).encode()+b"\n" for r in self.rows))
            rows = load_rows(p)
            data = preflight(rows, DummyTokenizer())
            self.assertEqual(data["cases_total"], 132)
            self.assertEqual(data["fits_context"] + data["token_hold"], 132)
            self.assertEqual(data["max_output_tokens"], 1200)

    def test_stage_manifest_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = Path(__file__).resolve().parents[2]
            private = root / "private"
            private.mkdir(mode=0o700)
            source = private / "input132.private.jsonl"
            source.write_bytes(b"".join(json.dumps(r, ensure_ascii=False).encode()+b"\n" for r in self.rows))
            source.chmod(0o600)
            output = private / "stage"
            prep(repo, source, output)
            self.assertEqual(len(verify_stage(output)), 3)
            self.assertTrue(all((output / f).stat().st_mode & 0o777 == 0o600
                                for f in ("SHA256SUMS.txt", "private/input132.private.jsonl")))
            with self.assertRaises(ValueError):
                prep(repo, source, output)
            with (output / "private/input132.private.jsonl").open("ab") as f:
                f.write(b"x")
            with self.assertRaises(ValueError):
                verify_stage(output)


if __name__ == "__main__":
    unittest.main()

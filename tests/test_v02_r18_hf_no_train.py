"""R18 offline fail-closed tests (no HF model download and no training)."""
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from collections import UserDict
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/v02_r18_hf_no_train.py"
spec = importlib.util.spec_from_file_location("v02_r18_no_train", SCRIPT)
r18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r18)


class TestR18NoTrain(unittest.TestCase):
    def test_sha256_reference(self):
        self.assertEqual(
            r18.digest(b"a"),
            "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        )

    def test_transformers_v5_batch_encoding(self):
        cases = [
            [101, 202],
            [[101, 202]],
            {"input_ids": [101, 202]},
            UserDict({"input_ids": [101, 202], "attention_mask": [1, 1]}),
            {"input_ids": [[101, 202]], "attention_mask": [[1, 1]]},
        ]
        for output in cases:
            with self.subTest(kind=type(output).__name__):
                self.assertEqual(r18.ids(output), [101, 202])

    def test_invalid_token_shapes_fail_closed(self):
        cases = [
            {},
            {"attention_mask": [1, 1]},
            {"input_ids": [[1], [2]]},
            {"input_ids": []},
            {"input_ids": [101, "bad"]},
            {"input_ids": [101, True]},
            b"not tokens",
        ]
        for output in cases:
            with self.subTest(value=repr(output)), self.assertRaises(ValueError):
                r18.ids(output)

    def test_fake_archive_refused(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "wrong.zip"
            with zipfile.ZipFile(f, "w") as z:
                z.writestr("baseline/invalid.txt", "not approved")
            with self.assertRaises(ValueError):
                r18.frozen(f)

    def test_failed_input_never_passes(self):
        with tempfile.TemporaryDirectory() as td:
            old = sys.argv
            sys.argv = [
                str(SCRIPT), "--r17-zip", str(Path(td) / "missing.zip"),
                "--output-dir", str(Path(td) / "output"), "--stage", "token",
            ]
            try:
                self.assertEqual(r18.main(), 2)
                report = json.loads(
                    (Path(td) / "output/r18_actual_no_train_report.json").read_text()
                )
                self.assertEqual(report["status"], "BLOCKED")
                self.assertFalse(report["training_performed"])
                self.assertEqual(report["rows"], [])
            finally:
                sys.argv = old


if __name__ == "__main__":
    unittest.main()

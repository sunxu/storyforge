"""R57 synthetic CLI safety regressions: no real records, no sealed data."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "r57_v04_admission_gate.py"


class TestR57ReadOnlyBoundaries(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.manifest = self.root / "synthetic_private_manifest.json"
        self.manifest.write_text(
            json.dumps({
                "schema": "storyforge-r57-v04-private-intake-v1",
                "no_r50_content_accessed": True,
                "training_authorized": False,
                "records": [],
            }),
            encoding="utf-8",
        )
        self.original = self.manifest.read_bytes()

    def run_gate(self, output=None, manifest=None):
        cmd = [
            sys.executable, str(SCRIPT),
            "--mode", "draft", "--private-manifest", str(manifest or self.manifest),
        ]
        if output is not None:
            cmd += ["--safe-out", str(output)]
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def test_new_report_is_count_only_and_no_input_mutation(self):
        out = self.root / "new_receipt.json"
        process = self.run_gate(out)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["record_count"], 0)
        self.assertEqual(report["admitted_total"], 0)
        self.assertNotIn("synthetic_private_manifest", json.dumps(report))
        self.assertEqual(self.manifest.read_bytes(), self.original)
        if os.name == "posix":
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)

    def test_existing_receipt_is_never_overwritten(self):
        out = self.root / "existing_receipt.json"
        out.write_text("SENTINEL KEEP\n", encoding="utf-8")
        process = self.run_gate(out)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(out.read_text(encoding="utf-8"), "SENTINEL KEEP\n")
        self.assertEqual(self.manifest.read_bytes(), self.original)

    def test_output_symlink_cannot_overwrite_target(self):
        protected = self.root / "do_not_modify.txt"
        protected.write_text("PRIVATE SENTINEL\n", encoding="utf-8")
        out = self.root / "receipt_symlink.json"
        out.symlink_to(protected)
        process = self.run_gate(out)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(protected.read_text(encoding="utf-8"), "PRIVATE SENTINEL\n")
        self.assertTrue(out.is_symlink())

    def test_input_symlink_is_rejected_without_output(self):
        regular = self.root / "original.json"
        regular.write_bytes(self.original)
        self.manifest.unlink()
        self.manifest.symlink_to(regular)
        out = self.root / "new_receipt.json"
        process = self.run_gate(out)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(out.exists())
        self.assertEqual(regular.read_bytes(), self.original)

    def test_sparse_oversize_manifest_rejected_before_json_load(self):
        huge = self.root / "oversize_metadata.json"
        with huge.open("wb") as f:
            f.truncate(64 * 1024 * 1024 + 1)
        out = self.root / "new_receipt.json"
        process = self.run_gate(out, huge)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(out.exists())

    def test_directory_input_is_rejected(self):
        out = self.root / "new_receipt.json"
        process = self.run_gate(out, self.root)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(out.exists())

    def test_invalid_json_produces_no_receipt(self):
        malformed = self.root / "malformed.json"
        malformed.write_text("{invalid-json", encoding="utf-8")
        out = self.root / "new_receipt.json"
        process = self.run_gate(out, malformed)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(out.exists())

    def test_cli_stdout_only_mode_keeps_input_unchanged(self):
        process = self.run_gate()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertFalse(list(self.root.glob("*receipt*")))
        self.assertEqual(self.manifest.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()

"""Synthetic-only tests for local filename metadata inventory."""
import json
import tempfile
import unittest
from pathlib import Path

from experiments.r58_quality.r60_local_archive_manifest_probe import inspect


class ArchiveManifestProbeTests(unittest.TestCase):
    def test_filename_only_counts_and_no_private_values(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            abnormal = root / "abnormal-snapshots"
            abnormal.mkdir()
            (abnormal / "2026-08-09.instance-1.jsonl").write_text("private-content")
            (abnormal / "2026-10-11.instance-2.jsonl").write_text("private-content")
            (abnormal / "unrelated.jsonl").write_text("private-content")
            out = inspect(root)
            self.assertEqual(out["categories"]["abnormal-snapshots"]["matching_files"], 2)
            self.assertEqual(out["categories"]["latency-metrics"]["status"], "NOT_PRESENT")
            self.assertEqual(out["files_opened"], 0)
            self.assertNotIn("private-content", json.dumps(out))
            self.assertNotIn(d, json.dumps(out))
            self.assertEqual(out["quality_v1_admitted"], 0)

    def test_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "abnormal-snapshots").symlink_to(root)
            with self.assertRaisesRegex(ValueError, "SYMLINK_CATEGORY_HOLD"):
                inspect(root)

    def test_invalid_date_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "latency-metrics").mkdir()
            (root / "latency-metrics" / "2026-99-09.process-1.jsonl").touch()
            with self.assertRaisesRegex(ValueError, "INVALID_DATE_IN_FILENAME"):
                inspect(root)


if __name__ == "__main__":
    unittest.main()

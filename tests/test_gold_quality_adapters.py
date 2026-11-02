"""Synthetic-only tests for allowlisted, count-only R58 adapters."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from storyforge_gold_quality.adapters import available_checks, run_safe_check
from storyforge_gold_quality.manifest import ManifestError


class SafeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.script = self.root / "experiments/r58_quality/gold108_review_binding.py"
        self.script.parent.mkdir(parents=True)
        self.script.write_text("# test fixture only\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_known_allowlist(self):
        self.assertEqual(len(available_checks()), 3)

    def test_reject_unknown_script_without_execution(self):
        with patch("storyforge_gold_quality.adapters.subprocess.run") as runner:
            with self.assertRaisesRegex(ManifestError, "NOT_ALLOWLISTED"):
                run_safe_check(self.root, "../../private/script.py")
            runner.assert_not_called()

    def test_verified_counts_only(self):
        data = {
            "schema": "storyforge_r58_gold108_legacy_review_binding_v1",
            "status": "HISTORICAL_DUAL_REVIEW_INDEX_BINDING_ONLY__NO_QUALITY_V1_ADMISSION",
            "index_count": 108, "review_evidence_count": 108,
            "SECRET_STORY_UUID": "sensitive",
        }
        fake = subprocess.CompletedProcess([], 0, stdout=json.dumps(data), stderr="secret")
        with patch("storyforge_gold_quality.adapters.subprocess.run", return_value=fake):
            result = run_safe_check(self.root, "gold108-legacy-binding")
        self.assertEqual(result["counts"], {"index_count": 108, "review_evidence_count": 108})
        self.assertNotIn("SECRET_STORY_UUID", json.dumps(result))
        self.assertFalse(result["training_authorized"])

    def test_fail_closed_on_bad_status(self):
        fake = subprocess.CompletedProcess([], 0, stdout=json.dumps({
            "schema": "storyforge_r58_gold108_legacy_review_binding_v1",
            "status": "HOLD", "index_count": 108, "review_evidence_count": 108,
        }), stderr="")
        with (patch("storyforge_gold_quality.adapters.subprocess.run", return_value=fake),
              self.assertRaisesRegex(ManifestError, "BAD_STATUS")):
            run_safe_check(self.root, "gold108-legacy-binding")

    def test_timeout_holds(self):
        with (patch("storyforge_gold_quality.adapters.subprocess.run",
                    side_effect=subprocess.TimeoutExpired("tool", 60)),
              self.assertRaisesRegex(ManifestError, "EXECUTION_UNAVAILABLE")):
            run_safe_check(self.root, "gold108-legacy-binding")

    def test_symlink_script_refused(self):
        self.script.unlink()
        outside = self.root / "outside.py"
        outside.write_text("# outside\n")
        self.script.symlink_to(outside)
        with patch("storyforge_gold_quality.adapters.subprocess.run") as runner:
            with self.assertRaisesRegex(ManifestError, "SCRIPT_UNAVAILABLE"):
                run_safe_check(self.root, "gold108-legacy-binding")
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()

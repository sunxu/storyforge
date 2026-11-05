"""Synthetic shell and fail-closed consent checks; never launches Codex."""
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

RUNNER = (Path(__file__).resolve().parents[1] / "scripts"
          / "v03_r50_run_seven_gap_ai_review.sh")


class SevenGapPrivateRunnerTests(unittest.TestCase):
    def test_shell_syntax(self):
        result = subprocess.run(["bash", "-n", str(RUNNER)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_refuses_all_remote_model_calls(self):
        env = dict(os.environ)
        env.pop("STORYFORGE_AUTHORIZE_PRIVATE_AI_TRANSFER", None)
        result = subprocess.run(["bash", str(RUNNER)], env=env,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("R50_PRIVATE_AI_TRANSFER_NOT_AUTHORIZED__NO_MODEL_CALL",
                      result.stderr)
        self.assertNotIn("R50_CODEX_REMOTE_REVIEW_START", result.stdout)

    def test_no_unrestricted_sandbox_or_unvalidated_publication(self):
        text = RUNNER.read_text(encoding="utf8")
        self.assertIn("--sandbox read-only", text)
        self.assertIn("--output-last-message", text)
        self.assertIn("v03_r50_verify_seven_gap_workpaper.py", text)
        self.assertIn("os.link(source, target)", text)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("hf jobs run", text)


if __name__ == "__main__":
    unittest.main()

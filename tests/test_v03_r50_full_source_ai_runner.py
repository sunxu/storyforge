"""No-model-call synthetic regression for full-source AI runner."""
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/v03_r50_run_full_source_ai_review.sh"


class FullSourceRunnerTests(unittest.TestCase):
    def test_bash_syntax(self):
        out = subprocess.run(["bash", "-n", str(SCRIPT)],
                             capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_explicit_consent_required_before_any_remote_operation(self):
        env = dict(os.environ)
        env.pop("STORYFORGE_AUTHORIZE_PRIVATE_AI_TRANSFER", None)
        out = subprocess.run(["bash", str(SCRIPT)],
                             capture_output=True, text=True,
                             env=env, check=False)
        self.assertEqual(out.returncode, 2)
        self.assertIn("R50_PRIVATE_AI_TRANSFER_NOT_AUTHORIZED__NO_MODEL_CALL",
                      out.stderr)
        self.assertNotIn("R50_CODEX_REMOTE_REVIEW_START", out.stdout)

    def test_schema_and_prevalidator_before_atomic_publish(self):
        content = SCRIPT.read_text(encoding="utf8")
        self.assertIn("--sandbox read-only", content)
        self.assertIn("v03_r50_verify_w17_full_source_review.py", content)
        self.assertIn('--dossiers-dir "$PACKETS"', content)
        self.assertIn("os.link(source, target)", content)
        self.assertIn("PRIVATE_FULL_MANIFEST_SHA_MISMATCH", content)
        self.assertNotIn("hf jobs run", content)
        self.assertNotIn("git push", content)


if __name__ == "__main__":
    unittest.main()

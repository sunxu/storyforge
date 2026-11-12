"""Synthetic CLI regression: legacy submit cannot send another HF Job."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r60_common2_hf_cpu_submit.sh"


def test_legacy_submit_fails_before_marker_or_hf_job(tmp_path):
    fake_hf = tmp_path / "hf"
    fake_hf.write_text("#!/bin/sh\nprintf 'UNEXPECTED_HF_CALL\\n' >&2\nexit 99\n")
    fake_hf.chmod(0o755)
    stage = tmp_path / "frozen-stage"
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env.get('PATH', '')}"
    result = subprocess.run(
        ["bash", str(SCRIPT), "submit", "example", str(stage)],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 42
    assert "R60_COMMON2_LEGACY_CLI_SUBMIT_DISABLED_MOUNT_POLICY_HOLD" in result.stderr
    assert "UNEXPECTED_HF_CALL" not in result.stderr
    assert not (tmp_path / "frozen-stage.cpu-submit-attempted").exists()

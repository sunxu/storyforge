"""Run private R60 expansion's synthetic-only tests within normal GitHub CI."""
import subprocess
import sys
from pathlib import Path


def test_r60_expansion_synthetic_suite():
    suite = (Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
             / "test_r60_real_expand_private.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(suite)],
        capture_output=True, text=True, timeout=90, check=False,
    )
    assert result.returncode == 0, result.stdout[-5000:] + result.stderr[-2500:]
    assert "26 passed" in result.stdout

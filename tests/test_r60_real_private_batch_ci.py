"""Run R60's quarantined synthetic private-pipeline suite in normal CI pytest."""
import subprocess
import sys
from pathlib import Path


def test_r60_real_private_batch_synthetic_suite():
    suite = (Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
             / "test_r60_real_private_batch.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(suite)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert "15 passed" in result.stdout

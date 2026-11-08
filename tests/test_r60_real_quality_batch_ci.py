"""Run 14 synthetic-only R60 real-history quality batch checks in default CI."""
import subprocess
import sys
from pathlib import Path


def test_r60_real_quality_batch_synthetic_suite():
    suite = (Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
             / "test_r60_real_quality_batch.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(suite)],
        capture_output=True, text=True, timeout=100, check=False,
    )
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-3000:]
    assert "14 passed" in result.stdout

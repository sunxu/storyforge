"""Run synthetic-only R60 AI reviewer tests in default CI pytest collection."""
import subprocess
import sys
from pathlib import Path


def test_r60_real_ai_review_synthetic_suite():
    suite = (Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
             / "test_r60_real_ai_dual_review.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(suite)],
        capture_output=True, text=True, timeout=70, check=False,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2500:]
    assert "13 passed" in result.stdout

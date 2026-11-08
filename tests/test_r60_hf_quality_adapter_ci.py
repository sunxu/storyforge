"""Run synthetic R60/Quality Pipeline HF adapter tests in default CI."""
import subprocess
import sys
from pathlib import Path


def test_r60_hf_quality_adapter_synthetic_suite():
    source = (Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
              / "test_r60_hf_quality_adapter.py")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", str(source)],
                            capture_output=True, text=True, timeout=120,
                            check=False)
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-3000:]
    assert "3 passed" in result.stdout

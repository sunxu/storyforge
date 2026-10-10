"""Regression test for original v0.1 Validation 1536 answer-key unblinding."""

import json
import subprocess
import sys
from pathlib import Path


def test_validation_1536_original_key_unblind() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "evaluations/v0.1/validation-1536/unblind.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True,
                            text=True, check=True)
    report = json.loads(result.stdout)
    assert report["status"] == "VALIDATION_1536_ORIGINAL_KEY_AND_SCORER_REPRO_PASS"
    assert report["votes"] == {"base": 28, "adapter": 30, "tie": 2}
    assert report["strict_majority"] == {
        "base": 5, "adapter": 5, "no_majority": 5
    }
    assert report["plurality"] == {"base": 5, "adapter": 6, "equal_top": 4}
    assert report["means"]["base"]["overall"] == 3.79
    assert report["means"]["adapter"]["overall"] == 3.923333
    assert report["raw_hf_inference_bytes_in_git"] is False

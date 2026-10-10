"""Run standard-library-only v0.1 Validation 1536 archive audit in CI."""
import json
import subprocess
import sys
from pathlib import Path


def test_validation_1536_archive_reproduces() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "evaluations/v0.1/validation-1536/reproduce.py"
    out = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=True
    )
    report = json.loads(out.stdout)
    assert report["status"] == "VALIDATION_1536_REVIEW_ARCHIVE_PASS"
    assert report["reviewer_files"] == 4
    assert report["total_rating_rows"] == 60
    assert report["samples"] == 15
    assert report["anonymous_preference_votes"] == {"A": 29, "B": 29, "TIE": 2}
    assert report["model_answer_key"] == "NOT_VERIFIED"

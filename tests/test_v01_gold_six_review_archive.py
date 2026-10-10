"""Ensure archived v0.1 Gold-reference ratings are reproducible in CI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_v01_gold_six_review_reproducibility() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "evaluations/v0.1/gold-reference/2026-10-10/reproduce.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(proc.stdout)
    assert report["status"] == "SIX_REVIEW_REPRO_PASS"
    assert report["results"]["GOLD_BASE"]["votes"] == {
        "gold": 38, "model": 22, "tie": 0
    }
    assert report["results"]["GOLD_ADAPTER"]["votes"] == {
        "gold": 45, "model": 15, "tie": 0
    }
    assert report["results"]["GOLD_BASE"]["majority"] == {
        "gold": 14, "model": 6
    }
    assert report["results"]["GOLD_ADAPTER"]["majority"] == {
        "gold": 16, "model": 4
    }

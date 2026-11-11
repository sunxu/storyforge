"""Synthetic double-PASS training candidate selection tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_double_pass_candidates_cpu as candidates


def row(i, *, claude="HOLD", codex="HOLD", kind="VALID_ADVISORY"):
    return {
        "pilot_position": i,
        "claude_review_kind": kind,
        "claude_decision_raw": claude,
        "codex_decision": codex,
        "claude_scores": {k: 4 for k in candidates.private.FLOORS},
        "codex_scores": {k: 4 for k in candidates.private.FLOORS},
        "claude_severe_flags": {k: False for k in candidates.private.SEVERE},
        "codex_severe_flags": {k: False for k in candidates.private.SEVERE},
    }


def test_only_strict_valid_double_pass_admitted_as_candidate():
    rows = [row(i) for i in range(1, 21)]
    for i in (2, 8, 17):
        rows[i - 1] = row(i, claude="PASS", codex="PASS")
    rows[3] = row(4, claude="PASS", codex="PASS",
                  kind="PASS_BELOW_FLOOR_CONFLICT")
    rows[5] = row(6, claude="PASS", codex="HOLD")
    safe, manifest = candidates.select(rows, comparison_sha256="a" * 64)
    assert safe["double_pass_candidates"] == 3
    assert safe["not_double_pass"] == 17
    assert [x["pilot_position"] for x in manifest["candidates"]] == [2, 8, 17]
    assert safe["train_admitted"] == 0
    assert manifest["historical_system_verified"] is False


def test_below_floor_never_candidate():
    rows = [row(i) for i in range(1, 21)]
    rows[0] = row(1, claude="PASS", codex="PASS")
    rows[0]["codex_scores"]["player_agency"] = 3
    safe, _ = candidates.select(rows, comparison_sha256="b" * 64)
    assert safe["double_pass_candidates"] == 0


def test_duplicate_or_incomplete_rows_are_rejected():
    rows = [row(i) for i in range(1, 21)]
    rows[-1]["pilot_position"] = 19
    try:
        candidates.select(rows, comparison_sha256="c" * 64)
    except candidates.Hold as exc:
        assert str(exc) == "COMPARE_ROWS_HOLD"
    else:
        raise AssertionError("duplicate row must fail")

"""Synthetic tests for partial-vs-complete dual-provider comparison."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_compare_cpu as comparison


def row(p, pass_old=False):
    return {
        "pilot_position": p,
        "claude_review_kind": "VALID_ADVISORY",
        "claude_decision_raw": "PASS" if pass_old else "HOLD",
        "codex_decision": "PASS" if pass_old else "HOLD",
        "claude_scores": {k: 4 for k in comparison.private.FLOORS},
        "codex_scores": {k: 4 for k in comparison.private.FLOORS},
        "claude_severe_flags": {k: False for k in comparison.private.SEVERE},
        "codex_severe_flags": {k: False for k in comparison.private.SEVERE},
    }


def receipt(decision):
    return {"result": {"decision": decision}}


def test_partial_cross_comparison():
    old = [row(p, p in (1, 2, 3)) for p in range(1, 21)]
    new = {}
    for p in range(1, 15):
        new[(p, "qwen")] = receipt("PASS" if p in (1, 4, 5, 6) else "REJECT")
        new[(p, "deepseek")] = receipt("PASS" if p in (1, 4, 5, 6) else "HOLD")
    for p in range(15, 20):
        new[(p, "qwen")] = receipt("PASS")
    safe = comparison.compare_rows(old, new)
    assert safe["complete_new_pairs"] == 14
    assert safe["old_claude_codex_double_pass"] == 3
    assert safe["new_qwen_deepseek_double_pass_in_complete_pairs"] == 4
    assert safe["double_pass_intersection_on_complete_pairs"] == 1
    assert safe["new_double_pass_not_old_double_pass"] == 3
    assert safe["old_double_pass_but_new_not_double_pass_on_complete_pairs"] == 2
    assert safe["train_admitted"] == 0


def test_incomplete_input_rejected():
    try:
        comparison.compare_rows([row(p) for p in range(1, 20)], {})
    except comparison.Hold as exc:
        assert str(exc) == "OLD_COMPARE_ROWS_HOLD"
    else:
        raise AssertionError("incomplete old reviews must fail")

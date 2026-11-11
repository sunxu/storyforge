"""Synthetic tests for fail-closed QD20 quality nomination."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_conservative_close_cpu as close


def current():
    analysis = {
        "cases": 20,
        "complete_new_pairs": 14,
        "new_qwen_deepseek_double_pass_in_complete_pairs": 4,
        "old_claude_codex_double_pass": 3,
        "double_pass_intersection_on_complete_pairs": 2,
        "new_double_pass_not_old_double_pass": 2,
        "old_double_pass_but_new_not_double_pass_on_complete_pairs": 1,
        "old_double_pass_missing_new_provider_review": 0,
        "old_and_new_review_sets_are_not_ground_truth": True,
    }
    inspect = {
        "cases": 20, "complete_provider_reviews": 34,
        "complete_two_provider_pairs": 14,
        "remaining_provider_reviews": 6,
        "double_pass_on_completed_pairs": 4,
    }
    diagnostics = {
        "model_inference_calls_this_run": 0,
        "private_failed_model_snapshots": 5,
        "offline_replay_outcomes": {"STILL_INVALID_UNCHANGED": 5},
    }
    return analysis, inspect, diagnostics


def test_partial_closeout_never_invents_model_votes():
    safe = close.closeout(*current())
    assert safe["new_strict_double_pass_nominations"] == 4
    assert safe["nominations_in_both_model_pairs"] == 2
    assert safe["cases_excluded_for_missing_provider_reviews"] == 6
    assert safe["provider_reviews_unavailable"] == 6
    assert safe["missing_reviews_imputed_as_hold"] == 0
    assert safe["missing_reviews_imputed_as_pass"] == 0
    assert safe["trial_claimed_complete"] is False
    assert safe["train_admitted"] == 0
    assert safe["quality_ground_truth_established"] is False


def test_inconsistent_saved_counts_fail_closed():
    data = current()
    data[1]["remaining_provider_reviews"] = 7
    try:
        close.closeout(*data)
    except close.Hold as exc:
        assert str(exc) == "CLOSEOUT_INPUT_MISMATCH_HOLD"
    else:
        raise AssertionError("inconsistent receipt counts must hold")


def test_complete_still_not_training_admission():
    a, b, c = current()
    a["complete_new_pairs"] = 20
    b["complete_provider_reviews"] = 40
    b["complete_two_provider_pairs"] = 20
    b["remaining_provider_reviews"] = 0
    safe = close.closeout(a, b, c)
    assert safe["trial_claimed_complete"] is True
    assert safe["train_admitted"] == 0

"""Synthetic no-inference tests for R60 training draft and low-cost budget."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_double_pass_sft_draft_cpu as draft
import r60_real1000_lowcost20_budget_cpu as budget


def packets():
    history = [
        {"role": "user", "content": "进入房间"},
        {"role": "assistant", "content": "她看向门口"},
        {"role": "user", "content": "询问情况"},
    ]
    return [{
        "history_messages": history,
        "assistant_target": "人物继续行动，场景自然展开。" * 15,
    } for _ in range(20)]


def test_training_system_is_constructed_and_not_admitted():
    result = draft.make(packets(), [3, 6, 12])
    assert result["candidate_count"] == 3
    assert result["train_admitted"] == 0
    assert all(len(x["messages"]) == 5 for x in result["samples"])
    assert all(x["messages"][0]["role"] == "system"
               for x in result["samples"])
    assert all(x["system_provenance"] ==
               "TRAINING_CONSTRUCTED_CONTEXT__NOT_HISTORICAL"
               for x in result["samples"])
    assert all(x["training_admitted"] is False for x in result["samples"])


def test_duplicate_draft_positions_hold():
    try:
        draft.make(packets(), [1, 1, 2])
    except draft.Hold as exc:
        assert str(exc) == "DRAFT_POSITION_HOLD"
    else:
        raise AssertionError("duplicates must be blocked")


def test_budget_preview_is_non_inference_and_cost_scales():
    a = budget.calculate(packets(), input_ratio=2,
                         input_price_a=0.2, output_price_a=0.8,
                         input_price_b=1, output_price_b=4,
                         max_output_tokens=1024)
    b = budget.calculate(packets(), input_ratio=2,
                         input_price_a=0.4, output_price_a=1.6,
                         input_price_b=2, output_price_b=8,
                         max_output_tokens=1024)
    assert a["pilot_cases"] == 20
    assert a["model_inference_calls"] == 0
    assert a["actual_tokenizer_measurement"] is False
    assert b["estimated_total_cost_in_caller_currency"] == round(
        a["estimated_total_cost_in_caller_currency"] * 2, 8)


def test_invalid_budget_args_blocked():
    try:
        budget.calculate(packets(), input_ratio=0.1,
                         input_price_a=0.2, output_price_a=0.8,
                         input_price_b=0.1, output_price_b=0.5,
                         max_output_tokens=1024)
    except budget.Hold as exc:
        assert str(exc) == "BUDGET_ARGS_HOLD"
    else:
        raise AssertionError("invalid ratio must hold")

"""Synthetic tests for blind evidence and non-exact quote blocking."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_evidence_review_cpu as gate


def source():
    return {
        "schema": gate.evidence.PRIVATE_SCHEMA,
        "status": "DISAGREEMENT_EVIDENCE_FOR_OWNER__NO_ADJUDICATION",
        "cases": [{
            "pilot_position": i,
            "category": ("NEW_ONLY_DOUBLE_PASS" if i < 3
                         else "OLD_ONLY_DOUBLE_PASS"),
            "prior_messages": [
                {"role": "user", "content": "玩家询问守卫情况"},
                {"role": "assistant", "content": "守卫看了看四周"},
                {"role": "user", "content": "玩家选择保持沉默"},
            ],
            "assistant_target": "守卫点头离开房间，留下灯光。",
            "owner_evidence_decision": "NOT_REVIEWED",
            "train_admitted": False,
        } for i in range(1, 4)],
        "train_admitted": 0,
    }


def completed(blind, template):
    result = copy.deepcopy(template)
    result["reviewer_independent_of_model_votes"] = True
    for row in result["cases"]:
        row.update({
            "decision": "HOLD",
            "scores": {k: 4 for k in gate.DIMENSIONS},
            "severe_flags": {k: False for k in gate.private.SEVERE},
            "quote_source": "history_user_3",
            "exact_quote": "玩家选择保持沉默",
            "reason_cn": "仅见玩家在当前消息选择沉默，无法核验完整世界规则。",
        })
    return result


def test_blind_packet_strips_all_previous_model_votes():
    src = source()
    src["cases"][0]["old_claude_codex"] = {"claude": "REJECT"}
    src["cases"][0]["new_qwen_deepseek"] = {"qwen": "PASS"}
    blind, template = gate.prepare(src)
    assert len(blind["cases"]) == 3
    assert "PASS" not in str(blind)
    assert "old_claude_codex" not in str(blind)
    assert template["reviewer_independent_of_model_votes"] is False
    report = gate.verify(src, blind, completed(blind, template))
    assert report["exact_quote_evidence_cases"] == 3
    assert report["quality_v1_admitted"] == 0


def test_nonexact_quote_rejected():
    src = source()
    blind, template = gate.prepare(src)
    result = completed(blind, template)
    result["cases"][0]["exact_quote"] = "根本不存在这句话"
    try:
        gate.verify(src, blind, result)
    except gate.Hold as exc:
        assert str(exc) == "REVIEW_NONEXACT_QUOTE_HOLD"
    else:
        raise AssertionError("non-exact evidence must fail")


def test_pass_below_floor_rejected():
    src = source()
    blind, template = gate.prepare(src)
    result = completed(blind, template)
    result["cases"][0]["decision"] = "PASS"
    result["cases"][0]["scores"]["player_agency"] = 2
    try:
        gate.verify(src, blind, result)
    except gate.Hold as exc:
        assert str(exc) == "PASS_CONTRACT_CONFLICT_HOLD"
    else:
        raise AssertionError("below-floor PASS must fail")


def test_severe_flag_requires_reject():
    src = source()
    blind, template = gate.prepare(src)
    result = completed(blind, template)
    result["cases"][0]["severe_flags"]["hard_fact_or_ban"] = True
    try:
        gate.verify(src, blind, result)
    except gate.Hold as exc:
        assert str(exc) == "SEVERE_FLAG_DECISION_CONFLICT_HOLD"
    else:
        raise AssertionError("severe flag must reject")


def test_forged_blind_input_rejected():
    src = source()
    blind, template = gate.prepare(src)
    blind["cases"][0]["assistant_target"] = "被篡改的文本"
    try:
        gate.verify(src, blind, completed(blind, template))
    except gate.Hold as exc:
        assert str(exc) == "BLIND_OR_REVIEW_CONTRACT_HOLD"
    else:
        raise AssertionError("tampered blind source must fail")

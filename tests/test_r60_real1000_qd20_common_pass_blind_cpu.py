"""Synthetic checks for two shared dual-PASS reviews without any external model."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_common_pass_blind_cpu as common


def sample():
    rows = []
    receipts = {}
    packets = []
    for pos in range(1, 21):
        both = pos in (2, 4, 6)
        row = {
            "pilot_position": pos,
            "claude_review_kind": "VALID_ADVISORY",
            "claude_decision_raw": "PASS" if both else "HOLD",
            "codex_decision": "PASS" if both else "HOLD",
            "claude_scores": {k: 5 for k in common.private.FLOORS},
            "codex_scores": {k: 5 for k in common.private.FLOORS},
            "claude_severe_flags": {
                k: False for k in common.private.SEVERE
            },
            "codex_severe_flags": {
                k: False for k in common.private.SEVERE
            },
        }
        rows.append(row)
        packets.append({
            "pilot_position": pos,
            "history_messages": [
                {"role": "user", "content": "玩家拿起一封信"},
                {"role": "assistant", "content": "门外风声渐大"},
                {"role": "user", "content": "玩家观察门外"},
            ],
            "assistant_target": "守卫看了一眼信封，转身退开。",
        })
        if pos <= 14:
            for model in common.live.MODELS:
                receipts[(pos, model)] = {
                    "result": {
                        "decision": "PASS" if pos in (2, 4, 10, 12)
                        else "HOLD",
                    },
                }
    return rows, receipts, packets


def completed(blind, template):
    result = copy.deepcopy(template)
    result["reviewer_independent_of_model_votes"] = True
    for item in result["cases"]:
        item.update({
            "decision": "HOLD",
            "scores": {k: 4 for k in common.private.FLOORS},
            "severe_flags": {k: False for k in common.private.SEVERE},
            "quote_source": "assistant_target",
            "exact_quote": "守卫看了一眼信封",
            "reason_cn": "这只能支持局部事实，无法独立核验整段故事背景。",
        })
    return result


def test_common_two_selection_is_blind_and_frozen():
    old, receipts, packets = sample()
    blind, template = common.extract(old, receipts, packets, "frozen-sha")
    assert len(blind["cases"]) == 2
    assert [x["blind_index"] for x in blind["cases"]] == [1, 2]
    assert "pilot_position" not in str(blind)
    assert "claude" not in str(blind).lower()
    assert "qwen" not in str(blind).lower()
    assert template["reviewer_independent_of_model_votes"] is False
    report = common.validate(blind, completed(blind, template))
    assert report["review_decisions"] == {"PASS": 0, "HOLD": 2, "REJECT": 0}


def test_nonexact_quote_rejected():
    old, receipts, packets = sample()
    blind, template = common.extract(old, receipts, packets, "frozen-sha")
    result = completed(blind, template)
    result["cases"][0]["exact_quote"] = "守卫根本没说过这些"
    try:
        common.validate(blind, result)
    except common.Hold as exc:
        assert str(exc) == "COMMON2_NONEXACT_QUOTE_HOLD"
    else:
        raise AssertionError("nonexact quote cannot be accepted")


def test_pass_with_low_score_rejected():
    old, receipts, packets = sample()
    blind, template = common.extract(old, receipts, packets, "frozen-sha")
    result = completed(blind, template)
    result["cases"][0]["decision"] = "PASS"
    key = next(iter(common.private.FLOORS))
    result["cases"][0]["scores"][key] = 1
    try:
        common.validate(blind, result)
    except common.Hold as exc:
        assert str(exc) == "COMMON2_PASS_BELOW_FLOOR_HOLD"
    else:
        raise AssertionError("pass below floor cannot be accepted")


def test_tampered_blind_hash_rejected():
    old, receipts, packets = sample()
    blind, template = common.extract(old, receipts, packets, "frozen-sha")
    result = completed(blind, template)
    result["blind_sha256"] = "tampered"
    try:
        common.validate(blind, result)
    except common.Hold as exc:
        assert str(exc) == "COMMON2_REVIEW_BINDING_HOLD"
    else:
        raise AssertionError("blind hash mismatch cannot be accepted")

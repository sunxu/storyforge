"""Synthetic source-binding and train-context HOLD tests for common2."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_common2_context_cpu as target
import r60_real1000_qd20_common_pass_blind_cpu as common
import r60_real1000_qd20_evidence_review_cpu as review


def fixture():
    cases = []
    for n in range(1, 1001):
        cases.append({
            "history_messages": [
                {"role": "user", "content": f"玩家在房间里观察{n}"},
                {"role": "assistant", "content": "守卫点亮一盏灯"},
                {"role": "user", "content": "玩家选择安静等待"},
            ],
            "target_text": f"守卫继续询问{n}随后退开",
            "source": {
                "story_id": f"non-r50-story-{n}",
                "assistant_message_id": f"message-{n}",
            },
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
        })
    packets = [{
        "pilot_position": p,
        "sample100_position": p,
        "history_messages": cases[p - 1]["history_messages"],
        "assistant_target": cases[p - 1]["target_text"],
        "target_char_bin": next(iter(target.sample.QUOTAS)),
    } for p in range(1, 21)]
    blind = {
        "schema": common.BLIND_SCHEMA,
        "status": "COMMON2_BLIND_NO_MODEL_VOTES",
        "frozen_source_sha256": "frozen",
        "cases": [{
            "blind_index": i,
            "history_messages": packets[pos - 1]["history_messages"],
            "assistant_target": packets[pos - 1]["assistant_target"],
        } for i, pos in enumerate((2, 4), 1)],
    }
    template = {
        "schema": common.DECISION_SCHEMA,
        "blind_sha256": target.pilot.sha(target.pilot.canonical(blind)),
        "reviewer_independent_of_model_votes": True,
        "cases": [{
            "blind_index": index,
            "decision": "PASS",
            "scores": {k: 5 for k in target.private.FLOORS},
            "severe_flags": {k: False for k in target.private.SEVERE},
            "quote_source": "history_user_3",
            "exact_quote": "玩家选择安静等待",
            "reason_cn": "审查仅限当前消息内容，无法证明完整世界设定已恢复。",
        } for index in (1, 2)],
        "train_admitted": 0,
    }
    frozen = {"cases": [{"position": p} for p in range(1, 1001)]}
    return cases, frozen, packets, blind, template


def test_two_validated_pass_still_held_for_missing_context():
    cases, frozen, packets, blind, decisions = fixture()
    safe = target.assess(cases, frozen, packets, blind, decisions,
                         copy.deepcopy(blind))
    assert safe["candidate_count"] == 2
    assert safe["strict_independent_pass"] == 2
    assert safe["historical_system_unverified"] == 2
    assert safe["world_component_unverified"] == 2
    assert safe["r50_full_exclusion_unverified"] == 2
    assert safe["r50_known5_overlap_count"] == 0
    assert safe["r50_complete_exclusion_verified"] is False
    assert safe["train_admitted"] == 0
    assert safe["private_values_emitted"] is False


def test_tampered_blind_fails_closed():
    cases, frozen, packets, blind, decisions = fixture()
    wrong = copy.deepcopy(blind)
    wrong["cases"][0]["assistant_target"] = "无关回复"
    try:
        target.assess(cases, frozen, packets, blind, decisions, wrong)
    except target.Hold as exc:
        assert str(exc) == "COMMON2_SOURCE_OR_REVIEW_HOLD"
    else:
        raise AssertionError("tampered blind should be rejected")


def test_target_mismatch_fails_closed():
    cases, frozen, packets, blind, decisions = fixture()
    cases[1]["target_text"] = "修改过的文本"
    try:
        target.assess(cases, frozen, packets, blind, decisions, blind)
    except target.Hold as exc:
        assert str(exc) == "REAL1000_EXACT_PAYLOAD_HOLD"
    else:
        raise AssertionError("source mismatch should be rejected")


def test_severe_flag_pass_rejected():
    cases, frozen, packets, blind, decisions = fixture()
    key = next(iter(target.private.SEVERE))
    decisions["cases"][0]["severe_flags"][key] = True
    try:
        target.assess(cases, frozen, packets, blind, decisions, blind)
    except common.Hold as exc:
        assert str(exc) == "COMMON2_PASS_BELOW_FLOOR_HOLD"
    else:
        raise AssertionError("invalid PASS should be rejected")

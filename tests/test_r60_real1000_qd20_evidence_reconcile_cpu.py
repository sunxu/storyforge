"""Synthetic validation of blind evidence crosswalk without leaking positions."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_evidence_reconcile_cpu as cross
import r60_real1000_qd20_evidence_review_cpu as review


def fixture():
    source = {
        "schema": review.evidence.PRIVATE_SCHEMA,
        "status": "DISAGREEMENT_EVIDENCE_FOR_OWNER__NO_ADJUDICATION",
        "cases": [{
            "pilot_position": index,
            "category": ("NEW_ONLY_DOUBLE_PASS" if index < 3
                         else "OLD_ONLY_DOUBLE_PASS"),
            "prior_messages": [
                {"role": "user", "content": "玩家查看前方"},
                {"role": "assistant", "content": "前方站着守卫"},
                {"role": "user", "content": "玩家选择沉默"},
            ],
            "assistant_target": "守卫低声询问来意，然后后退一步。",
            "owner_evidence_decision": "NOT_REVIEWED",
            "train_admitted": False,
        } for index in range(1, 4)],
        "train_admitted": 0,
    }
    blind, template = review.prepare(source)
    decisions = copy.deepcopy(template)
    decisions["reviewer_independent_of_model_votes"] = True
    for item, decision in zip(decisions["cases"], ["HOLD", "REJECT", "HOLD"]):
        item.update({
            "decision": decision,
            "scores": {key: 4 for key in review.DIMENSIONS},
            "severe_flags": {key: False for key in review.private.SEVERE},
            "quote_source": "assistant_target",
            "exact_quote": "守卫低声询问来意",
            "reason_cn": "这里只能验证局部剧情连续性，缺少明确世界设定信息。",
        })
    return source, blind, decisions


def test_safe_crosswalk_counts_without_ids():
    safe = cross.reconcile(*fixture())
    assert safe["new_only_double_pass_reviews"] == {
        "PASS": 0, "HOLD": 1, "REJECT": 1,
    }
    assert safe["old_only_double_pass_reviews"] == {
        "PASS": 0, "HOLD": 1, "REJECT": 0,
    }
    assert safe["reviewed_cases"] == 3
    assert safe["train_admitted"] == 0
    assert "pilot_position" not in str(safe)


def test_bad_quote_still_blocked():
    a, b, c = fixture()
    c["cases"][0]["exact_quote"] = "引用与原始文本不匹配"
    try:
        cross.reconcile(a, b, c)
    except review.Hold as exc:
        assert str(exc) == "REVIEW_NONEXACT_QUOTE_HOLD"
    else:
        raise AssertionError("crosswalk must use strict review gate")

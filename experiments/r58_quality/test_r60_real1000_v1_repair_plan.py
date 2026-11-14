"""Synthetic-only tests for V1 read-only repair planner."""
from __future__ import annotations

import json

import pytest

import r60_real1000_v1_repair_plan as plan
import r60_real_private_batch as private


def _case(i):
    return {
        "case_key": f"private-{i}",
        "history_messages_sha256": f"history-{i}",
        "assistant_target_sha256": f"target-{i}",
    }


def _review(side, decision="PASS"):
    return {
        "reviewer_key": f"ai-model-{side}",
        "decision": decision,
        "scores": dict(private.FLOORS),
        "severe_flags": {name: False for name in private.SEVERE},
    }


def _receipt(i, reviews, holds, reason):
    case = _case(i)
    return {
        "position": i, "pool_sha256": "synthetic-source",
        "case_key": case["case_key"],
        "history_messages_sha256": case["history_messages_sha256"],
        "assistant_target_sha256": case["assistant_target_sha256"],
        "reviews": reviews, "attempt_holds": holds,
        "quality_decision": "HOLD",
        "quality_reason_code": reason,
        "receipt_sha256": f"immutable-{i}",
    }


def test_priority_counts_and_missing_slot_identity(monkeypatch):
    monkeypatch.setattr(plan, "EXPECTED", 5)
    cases = [_case(i) for i in range(1, 6)]
    records = [
        _receipt(1, [_review("a"), _review("b")], [],
                 "INDEPENDENCE_NOT_ATTESTED"),
        _receipt(2, [_review("a")],
                 ["MODEL_HTTP_401_HOLD"], "TWO_INDEPENDENT_REVIEWS_REQUIRED"),
        _receipt(3, [_review("b", "HOLD")],
                 ["QUALITY_FLOOR_DECISION_INCONSISTENT"],
                 "TWO_INDEPENDENT_REVIEWS_REQUIRED"),
        _receipt(4, [], ["MODEL_HTTP_401_HOLD", "MODEL_JSON_INVALID"],
                 "TWO_INDEPENDENT_REVIEWS_REQUIRED"),
        _receipt(5, [_review("a"), _review("b", "REJECT")], [],
                 "SEVERE_OR_REVIEWER_REJECT"),
    ]
    result = plan.build(cases, records, "synthetic-source")
    assert result["priorities"] == {
        "BOTH_MISSING_LOW_PRIORITY": 1,
        "EXISTING_REJECT_REVIEW": 1,
        "READY_DUAL_PASS_NEEDS_ATTESTATION": 1,
        "SINGLE_OTHER_DEFER": 1,
        "SINGLE_PASS_REPAIR_FIRST": 1,
    }
    assert result["missing_slots_by_side"] == {"a": 2, "b": 2}
    assert [row["priority"] for row in result["entries"]] == [
        "READY_DUAL_PASS_NEEDS_ATTESTATION",
        "SINGLE_PASS_REPAIR_FIRST",
        "SINGLE_OTHER_DEFER",
        "EXISTING_REJECT_REVIEW",
        "BOTH_MISSING_LOW_PRIORITY",
    ]
    both_failed = result["entries"][-1]["missing_slots"]
    assert {x["side"] for x in both_failed} == {"a", "b"}
    assert {x["reason_code"] for x in both_failed} == {
        "UNASSIGNED_TWO_FAILURES",
    }
    assert result["train_admitted"] == 0
    assert plan._safe(result, status="PREFLIGHT")["model_requests"] == 0


def test_refuses_case_source_drift(monkeypatch):
    monkeypatch.setattr(plan, "EXPECTED", 1)
    record = _receipt(1, [_review("a")], ["MODEL_JSON_INVALID"],
                      "TWO_INDEPENDENT_REVIEWS_REQUIRED")
    record["assistant_target_sha256"] = "tampered"
    with pytest.raises(plan.Hold, match="CASE_IDENTITY_HOLD"):
        plan.build([_case(1)], [record], "synthetic-source")


def test_refuses_duplicate_or_ambiguous_slot(monkeypatch):
    monkeypatch.setattr(plan, "EXPECTED", 1)
    bad = _receipt(1, [_review("a"), _review("a")], [],
                   "REVIEW_INCOMPLETE")
    with pytest.raises(plan.Hold, match="REVIEW_SIDE_INTEGRITY_HOLD"):
        plan.build([_case(1)], [bad], "synthetic-source")
    missing = _receipt(1, [], ["MODEL_JSON_INVALID"],
                       "TWO_INDEPENDENT_REVIEWS_REQUIRED")
    with pytest.raises(plan.Hold, match="MISSING_SLOT_INTEGRITY_HOLD"):
        plan.build([_case(1)], [missing], "synthetic-source")


def test_serialized_private_manifest_has_no_target_body(monkeypatch):
    monkeypatch.setattr(plan, "EXPECTED", 1)
    c = _case(1)
    result = plan.build(
        [c],
        [_receipt(1, [_review("a")], ["MODEL_HTTP_401_HOLD"],
                  "TWO_INDEPENDENT_REVIEWS_REQUIRED")],
        "synthetic-source",
    )
    assert "target_text" not in json.dumps(result, ensure_ascii=False)
    assert result["entries"][0]["missing_slots"][0]["side"] == "b"

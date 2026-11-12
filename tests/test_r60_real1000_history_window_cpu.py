"""Synthetic checks for private history window SAFE assessor."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/r58_quality"))
import r60_real1000_history_window_cpu as probe


def fixture() -> dict:
    cases = []
    for n in (103, 243):
        history = [
            {
                "id": f"synthetic-{n}-{i}",
                "role": "user" if (i % 2 == n % 2) else "assistant",
                "content": "合成消息" * (i % 4 + 1),
                "turn_index": i,
            }
            for i in range(n)
        ]
        # Both odd lengths must terminate user/assistant/user.
        assert [m["role"] for m in history[-3:]] == ["user", "assistant", "user"]
        cases.append({
            "history_messages": history,
            "message_count_before_target": n,
            "last_three_exact_source_match": True,
            "actual_sent_prompt_verified": False,
            "historical_system_verified": False,
            "historical_world_components_verified": False,
            "r50_full_exclusion_verified": False,
        })
    return {
        "schema": probe.INPUT_SCHEMA, "status": probe.INPUT_STATUS,
        "train_admitted": 0, "cases": cases,
    }


def test_source_bound_windows_are_safe_not_admitted():
    result = probe.assess(fixture())
    assert result["full_history_message_counts"] == [103, 243]
    assert result["windows"]["12"]["message_counts_min"] == 12
    assert result["windows"]["12"]["last_three_preserved_count"] == 2
    assert result["windows"]["12"]["window_starts_with_user_count"] == 0
    assert result["train_admitted"] == 0
    assert result["tokenizer_verified"] is False
    assert "synthetic-103" not in str(result)
    assert "合成消息" not in str(result)


def test_reject_unverified_source_or_privilege():
    x = fixture()
    x["cases"][0]["last_three_exact_source_match"] = False
    try:
        probe.assess(x)
    except probe.Hold as exc:
        assert str(exc) == "EVIDENCE_FLAGS_HOLD"
    else:
        raise AssertionError("unbound sources must HOLD")


def test_reject_corrupt_message_order():
    x = fixture()
    x["cases"][0]["history_messages"][1]["turn_index"] = 0
    try:
        probe.assess(x)
    except probe.Hold as exc:
        assert str(exc) == "MESSAGE_TURN_ORDER_HOLD"
    else:
        raise AssertionError("bad turn indices must HOLD")


def test_reject_duplicate_message_ids():
    x = fixture()
    x["cases"][1]["history_messages"][1]["id"] = x["cases"][1]["history_messages"][0]["id"]
    try:
        probe.assess(x)
    except probe.Hold as exc:
        assert str(exc) == "MESSAGE_SOURCE_HOLD"
    else:
        raise AssertionError("duplicate ids must HOLD")

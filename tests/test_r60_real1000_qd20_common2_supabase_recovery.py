"""Offline tests of read-only persisted history recovery and exact binding."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_qd20_common2_supabase_recovery as target


def source_case():
    history = [
        {"role": "user", "content": "玩家选择站在房间一侧"},
        {"role": "assistant", "content": "守卫缓缓抬头望向门口"},
        {"role": "user", "content": "玩家决定保持安静"},
    ]
    return {
        "source": {
            "story_id": "story-local-private-1",
            "session_id": "session-local-private-1",
            "assistant_message_id": "aid",
            "prior_user_message_id": "uid",
            "previous_assistant_message_id": "pid",
            "previous_user_message_id": "puid",
            "assistant_turn_index": 8,
        },
        "history_messages": history,
        "target_text": "守卫静静放下手中的灯",
    }


def test_full_persisted_history_and_exact_three_messages():
    case = source_case()
    rows_desc = [
        ("uid", "user", "玩家决定保持安静", 7, "t7"),
        ("pid", "assistant", "守卫缓缓抬头望向门口", 6, "t6"),
        ("puid", "user", "玩家选择站在房间一侧", 5, "t5"),
        ("early", "assistant", "更早的一条已完成消息", 4, "t4"),
    ]
    result = target.validate_history(case, rows_desc)
    assert result["message_count_before_target"] == 4
    assert result["last_three_exact_source_match"] is True
    assert result["actual_sent_prompt_verified"] is False
    assert result["history_messages"][0]["id"] == "early"


def test_wrong_prior_history_rejected():
    case = source_case()
    rows = [
        ("uid", "user", "被编辑的目标前用户消息", 7, "t7"),
        ("pid", "assistant", "守卫缓缓抬头望向门口", 6, "t6"),
        ("puid", "user", "玩家选择站在房间一侧", 5, "t5"),
    ]
    try:
        target.validate_history(case, rows)
    except target.Hold as exc:
        assert str(exc) == "HISTORICAL_THREE_MESSAGES_MISMATCH_HOLD"
    else:
        raise AssertionError("history must exactly match frozen R60 sample")


def test_history_over_limit_does_not_claim_complete():
    case = source_case()
    rows = [("id" + str(i), "user", "消息", i, "t")
            for i in range(target.MAX_HISTORY + 1)]
    try:
        target.validate_history(case, rows)
    except target.Hold as exc:
        assert str(exc) == "HISTORY_OVER_LIMIT_HOLD"
    else:
        raise AssertionError("truncated history is not complete")


def test_source_selection_unique_exact_target():
    case = source_case()
    cases = [case, *[{"source": {}} for _ in range(999)]]
    packet = {
        "history_messages": case["history_messages"],
        "assistant_target": case["target_text"],
        "sample100_position": 1,
    }
    packets = [packet, *[
        {"history_messages": [{"role": "user", "content": f"other-{i}"}],
         "assistant_target": f"other-{i}", "sample100_position": i}
        for i in range(2, 21)
    ]]
    blind = {
        "cases": [
            {"history_messages": case["history_messages"],
             "assistant_target": case["target_text"]},
            {"history_messages": packets[1]["history_messages"],
             "assistant_target": packets[1]["assistant_target"]},
        ],
    }
    try:
        target.select_sources(cases, packets, blind)
    except target.Hold as exc:
        assert str(exc) == "SOURCE_TEXT_BINDING_HOLD"
    else:
        raise AssertionError("unknown second case must not silently bind")


def test_large_history_writer_and_empty_directory_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(target.private, "BASE", tmp_path)
    source = {"schema": "synthetic", "cases": [{"history_messages": [
        {"content": "示例历史消息" * 9000},
    ]}]}
    directory = tmp_path / "recovery"
    directory.mkdir(mode=0o700)
    target.write_recovery(directory, source)
    written = directory / target.FILENAME
    assert written.stat().st_size > target.private.MAX_CAPTURE_BYTES
    assert written.stat().st_mode & 0o777 == 0o600
    try:
        target.write_recovery(directory, source)
    except target.Hold as exc:
        assert str(exc) == "RECOVERY_OUTPUT_NOT_EMPTY_HOLD"
    else:
        raise AssertionError("a previous result must never be overwritten")


def test_recovery_size_limit_does_not_create_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(target.private, "BASE", tmp_path)
    monkeypatch.setattr(target, "MAX_RECOVERY_BYTES", 30)
    directory = tmp_path / "recovery"
    try:
        target.write_recovery(directory, {"cases": ["some case data"]})
    except target.Hold as exc:
        assert str(exc) == "RECOVERY_PAYLOAD_OVER_LIMIT_HOLD"
    else:
        raise AssertionError("size should be rejected")
    assert not directory.exists()

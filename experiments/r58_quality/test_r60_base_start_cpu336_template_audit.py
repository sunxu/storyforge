"""No-model synthetic unit checks for R60 Base CPU336 template auditor."""
from types import SimpleNamespace

import pytest
import r60_base_start_cpu336_template_audit as target
import r60_real1000_r50_known5_quarantine as quarantine


def sample():
    cases = []
    for i in range(1, 1001):
        history = [
            {"role": "user", "content": "先前的话"},
            {"role": "assistant", "content": "先前回复"},
            {"role": "user", "content": "现在怎么办"},
        ]
        cases.append({
            "source": {"story_id": (
                min(quarantine.known.KNOWN_R50_STORIES)
                if i <= 3 else f"world-{i}")},
            "history_messages": history,
            "target_text": "新的回复",
            "history_messages_sha256": target.private.digest(history),
            "assistant_target_sha256": target.private.digest("新的回复"),
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
        })
    manifest = {
        "schema": quarantine.SCHEMA,
        "status": "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD",
        "excluded_known5": [
            {"position": i, "reason_code": "R50_KNOWN5_SOURCE_STORY_OVERLAP"}
            for i in range(1, 4)
        ],
        "remaining_full_r50_hold": [
            {"position": i, "status": "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD"}
            for i in range(4, 340)
        ],
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
    }
    return cases, manifest


def test_in_memory_input_no_system_and_no_future():
    cases, manifest = sample()
    rows = target.prepare(cases, manifest)
    assert len(rows) == 336
    assert [m["role"] for m in rows[0]["messages"]] == [
        "user", "assistant", "user", "assistant"]
    assert rows[0]["messages"][-1]["content"] == "新的回复"
    assert all(m["role"] != "system" for row in rows
               for m in row["messages"])


def test_rejects_invalid_source_shape():
    cases, manifest = sample()
    cases[3]["history_messages"][0]["role"] = "assistant"
    with pytest.raises(target.Hold, match="STATIC_SHAPE_REQUIRED_HOLD"):
        target.prepare(cases, manifest)


def test_bounded_stats_and_count_guard():
    assert target._stats([5] * 336) == {
        "min": 5, "median": 5, "p95": 5, "max": 5}
    with pytest.raises(target.Hold, match="RESULT_COUNT_OR_FORMAT_HOLD"):
        target._stats([1, 2])


def test_preflight_no_snapshot_leaks(monkeypatch, capsys):
    args = SimpleNamespace(
        snapshot=__import__("pathlib").Path("/does-not-exist"),
        stage="both", old_dir=None, plan_dir=None, v2_dir=None,
        v3_dir=None, audit_dir=None, quarantine_dir=None)
    # A wrong snapshot fails before any private material is loaded.
    with pytest.raises(target.Hold, match="PINNED_LOCAL_SNAPSHOT_HOLD"):
        target.run(args)
    assert capsys.readouterr().out == ""

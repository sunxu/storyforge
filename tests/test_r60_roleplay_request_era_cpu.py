"""Offline no-private-output tests for target-era classifier."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/r58_quality"))
import r60_roleplay_request_era_cpu as probe


def fixture():
    def case(date: str, n: int):
        return {
            "target_created_at": date,
            "last_three_exact_source_match": True,
            "actual_sent_prompt_verified": False,
            "historical_system_verified": False,
            "historical_world_components_verified": False,
            "r50_full_exclusion_verified": False,
            "message_count_before_target": n,
            "history_messages": [{"role": "user", "content": "合成输入"} for _ in range(n)],
            "assistant_message_id": "PRIVATE_SYNTHETIC",
        }
    return {
        "schema": probe.INPUT_SCHEMA,
        "status": "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT",
        "train_admitted": 0,
        "cases": [
            case("2026-10-01 12:00:00+00:00", 103),
            case("2026-11-11 12:00:00+00:00", 243),
        ],
    }


def test_era_counts_and_no_ids_or_exact_dates():
    result = probe.assess(fixture())
    assert result["before_20261110_release_count"] == 1
    assert result["at_or_after_20261110_release_count"] == 1
    assert result["history_message_count_by_case"] == [103, 243]
    assert result["actual_sent_prompt_verified"] is False
    assert result["train_admitted"] == 0
    assert "PRIVATE_SYNTHETIC" not in str(result)
    assert "target_created_at" not in str(result)


def test_untrusted_timestamp_rejected():
    f = fixture()
    f["cases"][0]["target_created_at"] = "2026-10-01T12:00:00"
    try:
        probe.assess(f)
    except probe.Hold as exc:
        assert str(exc) == "TARGET_TIMESTAMP_TIMEZONE_HOLD"
    else:
        raise AssertionError("naive timestamps may not classify production era")


def test_evidence_flag_tampering_rejected():
    f = fixture()
    f["cases"][1]["actual_sent_prompt_verified"] = True
    try:
        probe.assess(f)
    except probe.Hold as exc:
        assert str(exc) == "RECOVERY_EVIDENCE_FLAGS_HOLD"
    else:
        raise AssertionError("claimed sent prompt requires new evidence")


def test_history_count_mismatch_rejected():
    f = fixture()
    f["cases"][0]["message_count_before_target"] = 3
    try:
        probe.assess(f)
    except probe.Hold as exc:
        assert str(exc) == "RECOVERY_HISTORY_COUNT_HOLD"
    else:
        raise AssertionError("inconsistent recovery counts must fail closed")

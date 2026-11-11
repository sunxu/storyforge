"""Synthetic regressions for the frozen real1000 CPU technical profile."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "experiments/r58_quality"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location(
    "r60_real1000_technical_profile_cpu", SRC / "r60_real1000_technical_profile_cpu.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def cases():
    rows = []
    for i in range(1000):
        rows.append({
            "case_key": f"case-{i}",
            "source": {
                "story_id": f"story-{i // 4}",
                "assistant_message_id": f"message-{i}",
            },
            "history_messages": [
                {"role": "user", "content": "一句话"},
                {"role": "assistant", "content": "角色回应"},
                {"role": "user", "content": "继续"},
            ],
            "target_text": "中文" * (150 + i % 601),
            "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
            "train_admitted": False,
        })
    return rows


def test_safe_profile_does_not_claim_training_admission():
    report = mod.profile(cases())
    assert report["status"] == "REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING"
    assert report["cases_verified"] == 1000
    assert report["distinct_stories"] == 250
    assert report["three_prior_messages_verified"] == 1000
    assert sum(report["target_char_bins"].values()) == 1000
    assert report["historical_system_not_verified"] == 1000
    assert report["quality_review_performed"] is False
    assert report["train_admitted"] == 0


def test_wrong_count_holds():
    rows = cases()
    try:
        mod.profile(rows[:-1])
    except mod.Hold:
        return
    raise AssertionError("expected HOLD")


def test_duplicate_target_holds():
    rows = cases()
    rows[2]["source"]["assistant_message_id"] = rows[1]["source"]["assistant_message_id"]
    try:
        mod.profile(rows)
    except mod.Hold:
        return
    raise AssertionError("expected HOLD")


def test_incorrect_role_holds():
    rows = cases()
    rows[0]["history_messages"][1]["role"] = "user"
    try:
        mod.profile(rows)
    except mod.Hold:
        return
    raise AssertionError("expected HOLD")


def test_system_and_world_metadata_are_not_technical_gates():
    rows = cases()
    rows[0]["historical_system_provenance"] = "VERIFIED"
    rows[1]["world_component_status"] = "VERIFIED"
    rows[2]["r50_complete_exclusion_status"] = "VERIFIED"
    result = mod.profile(rows)
    assert result["historical_system_not_verified"] == 999
    assert result["world_component_unverified"] == 999
    assert result["r50_exclusion_unverified"] == 999
    assert result["train_admitted"] == 0


def test_story_cap_holds():
    rows = cases()
    rows[4]["source"]["story_id"] = "story-0"
    try:
        mod.profile(rows)
    except mod.Hold:
        return
    raise AssertionError("expected HOLD")

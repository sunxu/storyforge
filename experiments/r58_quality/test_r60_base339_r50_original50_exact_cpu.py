"""Synthetic R50 exact overlap regression; no real private sources."""
import pytest

import r60_base339_r50_original50_exact_cpu as audit
from test_r60_base_start_cpu336_template_audit import sample


def sources():
    cases, manifest = sample()
    for i, row in enumerate(cases, 1):
        row["source"].update({
            "session_id": f"session-{i}",
            "assistant_message_id": f"assistant-{i}",
            "prior_user_message_id": f"user-{i}",
            "previous_assistant_message_id": f"previous-assistant-{i}",
            "previous_user_message_id": f"previous-user-{i}",
        })
    original = [
        {"source_story_id": cases[0]["source"]["story_id"],
         "source_session_id": "session-1",
         "cutoff_message_id": "assistant-1",
         "history_message_ids": ["user-1"]},
    ]
    original += [
        {"source_story_id": f"protected-{i}",
         "source_session_id": f"protected-session-{i}",
         "cutoff_message_id": f"protected-assistant-{i}",
         "history_message_ids": [f"protected-user-{i}"]}
        for i in range(49)
    ]
    return cases, manifest, original


def test_frozen_known5_excluded_and_336_remain_held():
    cases, manifest, original = sources()
    result = audit.evaluate(cases, manifest, original)
    assert result["status"] == (
        "R50_ORIGINAL50_EXACT_HELD_KEYS_DISJOINT__OTHER_GATES_HOLD"
    )
    assert result["all_candidate_exact_story_overlap"] == 3
    assert result["remaining_336_exact_key_overlap"] == 0
    assert result["r50_complete_exclusion_verified"] is False
    assert result["train_admitted"] == 0


def test_same_story_different_ids_in_held_is_rejected():
    cases, manifest, original = sources()
    original[1]["source_story_id"] = cases[8]["source"]["story_id"]
    result = audit.evaluate(cases, manifest, original)
    assert result["remaining_336_exact_key_overlap"] == 1
    assert result["remaining_336_exact_keys_disjoint_verified"] is False


def test_hidden_same_message_in_held_is_rejected():
    cases, manifest, original = sources()
    original[1]["cutoff_message_id"] = cases[8]["source"]["previous_user_message_id"]
    result = audit.evaluate(cases, manifest, original)
    assert result["remaining_336_exact_key_overlap"] == 1
    assert result["all_candidate_exact_message_overlap"] >= 1


def test_missing_source_ids_and_bad_manifest_fail_closed():
    cases, manifest, original = sources()
    del cases[5]["source"]["session_id"]
    with pytest.raises(ValueError, match="SOURCE_ID_SCHEMA_HOLD"):
        audit.evaluate(cases, manifest, original)
    cases, manifest, original = sources()
    manifest["train_admitted"] = 1
    with pytest.raises(audit.Hold, match="QUARANTINE_CONTRACT_HOLD"):
        audit.evaluate(cases, manifest, original)

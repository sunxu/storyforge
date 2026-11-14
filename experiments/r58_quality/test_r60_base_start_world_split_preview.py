"""Synthetic tests; no private records, training or GPU."""
import pytest

import r60_base_start_world_split_preview as split
import r60_real1000_r50_known5_quarantine as quarantine


def sample():
    known = sorted(quarantine.known.KNOWN_R50_STORIES)[0]
    cases = []
    for i in range(1, 1001):
        cases.append({"source": {
            "story_id": known if i <= 3 else f"world-{(i - 4) // 3}",
        }})
    excluded = [
        {"position": i, "reason_code": "R50_KNOWN5_SOURCE_STORY_OVERLAP"}
        for i in range(1, 4)
    ]
    held = [
        {"position": i, "status": "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD"}
        for i in range(4, 340)
    ]
    return cases, {
        "schema": quarantine.SCHEMA,
        "status": "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD",
        "excluded_known5": excluded, "remaining_full_r50_hold": held,
        "r50_complete_exclusion_verified": False, "train_admitted": 0,
    }


def test_base_split_deterministic_disjoint_and_all_held():
    cases, manifest = sample()
    first = split.preview(cases, manifest)
    second = split.preview(cases, manifest)
    assert first == second
    assert first["known5_excluded_cases"] == 3
    assert first["held_candidate_cases"] == 336
    assert first["provisional_train_cases"] + first["provisional_validation_cases"] == 336
    assert first["train_validation_story_disjoint"] is True
    assert first["inherit_previous_adapter"] is False
    assert first["training_dataset_created"] is False
    assert first["train_admitted"] == 0
    assert first["r50_complete_exclusion_verified"] is False


def test_known5_held_candidate_fails_closed():
    cases, manifest = sample()
    cases[3]["source"]["story_id"] = cases[0]["source"]["story_id"]
    with pytest.raises(split.Hold, match="KNOWN5_HELD_CROSSOVER_HOLD"):
        split.preview(cases, manifest)


def test_quarantine_drift_rejected():
    cases, manifest = sample()
    manifest["remaining_full_r50_hold"][0]["status"] = "TRAIN_READY"
    with pytest.raises(split.Hold, match="QUARANTINE_HELD_HOLD"):
        split.preview(cases, manifest)


def test_rejects_training_admission_flag():
    cases, manifest = sample()
    manifest["train_admitted"] = 1
    with pytest.raises(split.Hold, match="QUARANTINE_CONTRACT_HOLD"):
        split.preview(cases, manifest)

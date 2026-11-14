"""Synthetic-only Base SFT shape tests; all rows remain unadmitted."""
import pytest
import r60_base_start_sft_shape_cpu as shape
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private


def sample():
    known = min(quarantine.known.KNOWN_R50_STORIES)
    cases = []
    for i in range(1, 1001):
        history = [
            {"role": "user", "content": "开头"},
            {"role": "assistant", "content": "回应"},
            {"role": "user", "content": "继续"},
        ]
        cases.append({
            "source": {"story_id": known if i <= 3 else f"story-{i}"},
            "history_messages": history,
            "target_text": "下一段",
            "history_messages_sha256": private.digest(history),
            "assistant_target_sha256": private.digest("下一段"),
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
        })
    return cases, {
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


def test_valid_source_bound_shape_all_held():
    cases, manifest = sample()
    result = shape.inspect(cases, manifest)
    assert result["status"] == "BASE_SFT_STATIC_SHAPE_PASS__ALL_HELD"
    assert result["validated_three_message_cases"] == 336
    assert result["historical_system_provenance_counts"] == {
        "UNKNOWN_NOT_ACTUAL_SENT": 336
    }
    assert result["training_dataset_created"] is False
    assert result["actual_collator_last_assistant_mask_verified"] is False
    assert result["train_admitted"] == 0


def test_wrong_role_fails_closed():
    cases, manifest = sample()
    cases[4]["history_messages"][0]["role"] = "assistant"
    result = shape.inspect(cases, manifest)
    assert result["static_failure_counts"] == {"ROLE_SEQUENCE": 1}
    assert result["status"] == "BASE_SFT_STATIC_SHAPE_HOLD"


def test_target_hash_drift_fails_closed():
    cases, manifest = sample()
    cases[4]["assistant_target_sha256"] = "changed"
    result = shape.inspect(cases, manifest)
    assert result["static_failure_counts"] == {"SOURCE_HASH": 1}


def test_malformed_quarantine_rejected():
    cases, manifest = sample()
    manifest["train_admitted"] = 1
    with pytest.raises(shape.split.Hold, match="QUARANTINE_CONTRACT_HOLD"):
        shape.inspect(cases, manifest)

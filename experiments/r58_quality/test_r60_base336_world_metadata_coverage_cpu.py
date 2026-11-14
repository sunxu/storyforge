"""Synthetic metadata coverage tests; no real story content."""
import pytest
import r60_base336_world_metadata_coverage_cpu as coverage
from test_r60_base_start_cpu336_template_audit import sample


def synthetic():
    cases, manifest = sample()
    for item in manifest["remaining_full_r50_hold"]:
        source = cases[item["position"] - 1]["source"]
        pos = item["position"]
        source.update({
            "story_id": f"world-{(pos - 4) % 172}",
            "session_id": f"session-{pos}",
            "assistant_message_id": f"assistant-{pos}",
            "prior_user_message_id": f"prior-user-{pos}",
            "previous_assistant_message_id": f"prior-assistant-{pos}",
            "previous_user_message_id": f"earlier-user-{pos}",
            "assistant_turn_index": pos + 4,
        })
        cases[pos - 1].update(
            normalized_system_provenance="RECONSTRUCTED_NOT_ACTUAL_SENT",
            world_component_status="UNKNOWN_HOLD",
        )
    return cases, manifest


def test_true_missing_metadata_is_reported_as_zero_not_fabricated():
    cases, manifest = synthetic()
    out = coverage.inspect(cases, manifest)
    assert out["source_cases"] == 336
    assert out["story_id_count"] == 172
    assert out["source_rows_with_any_structured_world_field"] == 0
    assert all(x == 0 for x in
               out["structured_metadata_field_coverage"].values())
    assert out["world_component_isolation_verified"] is False
    assert out["train_admitted"] == 0


def test_present_title_is_hint_not_world_certificate():
    cases, manifest = synthetic()
    cases[3]["source"]["story_title"] = "测试标题"
    out = coverage.inspect(cases, manifest)
    assert out["structured_metadata_field_coverage"]["story_title"] == 1
    assert out["source_rows_with_any_structured_world_field"] == 1
    assert out["original_story_metadata_authenticated"] is False


def test_missing_provenance_must_hold():
    cases, manifest = synthetic()
    del cases[3]["world_component_status"]
    with pytest.raises(coverage.Hold, match="PROVENANCE_FIELDS_HOLD"):
        coverage.inspect(cases, manifest)


def test_missing_story_source_field_must_hold():
    cases, manifest = synthetic()
    del cases[4]["source"]["assistant_turn_index"]
    with pytest.raises(coverage.Hold, match="SOURCE_ID_CONTRACT_HOLD"):
        coverage.inspect(cases, manifest)

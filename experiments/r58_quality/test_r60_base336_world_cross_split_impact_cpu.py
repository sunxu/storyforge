"""Safe impact counts: synthetic-only no actual database rows."""
import pytest
import r60_base336_world_cross_split_impact_cpu as subject
from test_r60_base336_story_db_locator_cpu import cohort


def test_candidate_counts_bound_to_frozen_336():
    cases, manifest = cohort()
    stories = sorted({cases[x["position"] - 1]["source"]["story_id"]
                      for x in manifest["remaining_full_r50_hold"]})
    counts = subject.candidate_counts(cases, manifest, stories)
    assert len(counts) == 172 and sum(counts) == 336


def test_safe_impacted_cases_can_be_more_than_stories():
    out = subject.verify([
        ("current", 6, 4, 12, 8),
        ("current_plus_versions", 7, 5, 15, 10),
    ])
    assert out["cross_split_affected"]["current"]["train_cases"] == 12
    assert out["old_276_60_preview_valid_for_admission"] is False
    assert out["world_component_isolation_verified"] is False
    assert out["train_admitted"] == 0


def test_no_group_count_is_zero_not_undefined():
    out = subject.verify([])
    assert out["cross_split_affected"]["current"]["train_stories"] == 0
    assert out["cross_split_affected"]["current_plus_versions"]["validation_cases"] == 0


def test_versions_cannot_lose_current_affected_stories():
    with pytest.raises(subject.Hold, match="IMPACT_MONOTONICITY_HOLD"):
        subject.verify([
            ("current", 7, 5, 15, 10),
            ("current_plus_versions", 6, 4, 14, 8),
        ])


def test_cases_must_not_exceed_336():
    with pytest.raises(subject.Hold, match="IMPACT_RESULT_BOUNDS_HOLD"):
        subject.verify([("current", 4, 4, 300, 100)])


def test_types_fail_closed():
    with pytest.raises(subject.Hold, match="IMPACT_RESULT_TYPE_HOLD"):
        subject.verify([("current", True, 1, 2, 1)])

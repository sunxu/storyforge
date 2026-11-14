"""Synthetic safe equality screen: no real JSON, IDs, SQL calls or GPU."""
import pytest
import r60_base336_world_exact_value_cpu as subject


def test_zero_world_matches_does_not_certify_semantic_aliases():
    counts = subject.verify([
        ("current", 172, 0, 0, 0),
        ("current_plus_versions", 172, 0, 0, 0),
    ])
    assert counts["world_equality_counts"]["current"]["cross_story_groups"] == 0
    assert counts["world_definition_semantic_alias_verified"] is False
    assert counts["train_admitted"] == 0


def test_crossing_equal_world_is_only_provisional_evidence():
    counts = subject.verify([
        ("current", 171, 1, 1, 1),
        ("current_plus_versions", 170, 2, 2, 1),
    ])
    assert counts["world_equality_counts"]["current"]["train_validation_crossing_groups"] == 1
    assert counts["world_component_isolation_verified"] is False


def test_rejects_crossing_more_than_shared_groups():
    with pytest.raises(subject.Hold, match="WORLD_EQUALITY_BOUNDS_HOLD"):
        subject.verify([
            ("current", 171, 0, 0, 1),
            ("current_plus_versions", 172, 0, 0, 0),
        ])


def test_rejects_invalid_result_type():
    with pytest.raises(subject.Hold, match="WORLD_EQUALITY_TYPE_HOLD"):
        subject.verify([
            ("current", 172, True, 0, 0),
            ("current_plus_versions", 172, 0, 0, 0),
        ])


def test_rejects_duplicate_origin():
    with pytest.raises(subject.Hold, match="WORLD_EQUALITY_RESULT_HOLD"):
        subject.verify([
            ("current", 172, 0, 0, 0),
            ("current", 172, 0, 0, 0),
        ])


def test_split_has_frozen_scope_and_determinism():
    stories = [f"synthetic-story-{i}" for i in range(172)]
    assert subject.split_labels(stories) == subject.split_labels(stories)
    assert set(subject.split_labels(stories)) == {"train", "validation"}
    with pytest.raises(subject.Hold, match="STORY_SCOPE_HOLD"):
        subject.split_labels(stories[:-1])

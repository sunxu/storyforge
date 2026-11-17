"""Synthetic-only tests for reusable semantic world isolation helpers."""
from __future__ import annotations

import json

import pytest

from storyforge_dataset.world_isolation import (
    WorldIsolationError,
    component_split_conflicts,
    validate_component_review_assignments,
)


def row(source, component, split, decision="PASS", *, version=True, reviewed=True):
    return {
        "source_key": source,
        "split": split,
        "semantic_component_id": component,
        "source_evidence_ref": f"evidence-{source}",
        "source_snapshot_sha256": "a" * 64,
        "source_version_verified": version,
        "semantic_review_completed": reviewed,
        "decision": decision,
    }


def test_component_split_conflict_is_structural_only():
    conflicts = component_split_conflicts([
        {"world_component_id": "private-component-1", "split": "train"},
        {"world_component_id": "private-component-1", "split": "validation"},
        {"world_component_id": "private-component-2", "split": "train"},
    ])
    assert conflicts == {
        "private-component-1": frozenset({"train", "validation"})
    }


def test_same_component_within_one_split_is_not_a_split_collision():
    assert component_split_conflicts([
        {"world_component_id": "component", "split": "train"},
        {"world_component_id": "component", "split": "train"},
    ]) == {}


def test_missing_or_invalid_assignments_are_not_inferred():
    assert component_split_conflicts([
        {"world_component_id": "", "split": "train"},
        {"world_component_id": "component", "split": "unknown"},
        {"split": "validation"},
    ]) == {}


def test_invalid_split_configuration_fails_closed():
    with pytest.raises(WorldIsolationError, match="WORLD_SPLIT_ARGUMENT_HOLD"):
        component_split_conflicts([], relevant_splits=("train", "train"))


def test_complete_review_assignments_pass_structure_only():
    result = validate_component_review_assignments(
        [row("story-a", "world-a", "train"),
         row("story-b", "world-b", "validation")],
        expected_source_keys=("story-a", "story-b"),
    )
    assert result["status"] == (
        "WORLD_COMPONENT_ASSIGNMENT_STRUCTURE_PASS__NO_DECLARED_SPLIT_COLLISION"
    )
    assert result["component_assignment_structure_pass"] is True
    assert result["world_component_isolation_verified"] is False
    assert result["reviewer_independence_independently_proven"] is False
    assert result["historical_actual_sent_version_verified"] is False
    assert result["train_admitted"] == 0


def test_cross_split_semantic_component_holds():
    result = validate_component_review_assignments([
        row("story-a", "same-semantic-world", "train"),
        row("story-b", "same-semantic-world", "validation"),
    ], expected_source_keys=("story-a", "story-b"))
    assert result["status"] == "WORLD_COMPONENT_REVIEW_HOLD"
    assert result["cross_split_component_count"] == 1
    assert result["component_assignment_structure_pass"] is False
    assert result["world_component_isolation_verified"] is False


def test_unreviewed_or_unverified_source_holds():
    result = validate_component_review_assignments([
        row("story-a", "world-a", "train", decision="HOLD", reviewed=False),
        row("story-b", "world-b", "validation", version=False),
    ], expected_source_keys=("story-a", "story-b"))
    assert result["status"] == "WORLD_COMPONENT_REVIEW_HOLD"
    assert result["unresolved_source_records"] == 2


def test_duplicate_or_missing_source_coverage_holds():
    with pytest.raises(WorldIsolationError, match="WORLD_REVIEW_ROW_VALUE_HOLD"):
        validate_component_review_assignments([
            row("story-a", "world-a", "train"),
            row("story-a", "world-b", "validation"),
        ], expected_source_keys=("story-a",))
    with pytest.raises(WorldIsolationError, match="WORLD_REVIEW_SOURCE_COVERAGE_HOLD"):
        validate_component_review_assignments(
            [row("story-a", "world-a", "train")],
            expected_source_keys=("story-a", "story-b"),
        )


def test_review_contract_rejects_unknown_fields_and_malformed_values():
    bad = row("story-a", "world-a", "train")
    bad["source_version_verified"] = 1
    with pytest.raises(WorldIsolationError, match="WORLD_REVIEW_ROW_VALUE_HOLD"):
        validate_component_review_assignments([bad], expected_source_keys=("story-a",))
    bad = row("story-a", "world-a", "train")
    bad["unreviewed_extra"] = True
    with pytest.raises(WorldIsolationError, match="WORLD_REVIEW_ROW_SCHEMA_HOLD"):
        validate_component_review_assignments([bad], expected_source_keys=("story-a",))
    bad = row("story-a", "world-a", "train")
    bad["decision"] = ["PASS"]
    with pytest.raises(WorldIsolationError, match="WORLD_REVIEW_ROW_VALUE_HOLD"):
        validate_component_review_assignments([bad], expected_source_keys=("story-a",))
    bad = row("story-a", "world-a", "train")
    bad["source_snapshot_sha256"] = "not-a-hash"
    with pytest.raises(WorldIsolationError, match="WORLD_REVIEW_ROW_VALUE_HOLD"):
        validate_component_review_assignments([bad], expected_source_keys=("story-a",))


def test_safe_summary_does_not_emit_private_identifiers():
    marker = "PRIVATE_WORLD_COMPONENT_CANARY"
    result = validate_component_review_assignments([
        row("PRIVATE_STORY_CANARY", marker, "train"),
    ], expected_source_keys=("PRIVATE_STORY_CANARY",))
    encoded = json.dumps(result)
    assert marker not in encoded
    assert "PRIVATE_STORY_CANARY" not in encoded
    assert result["private_values_emitted"] is False

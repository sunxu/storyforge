"""Reusable structural gates for semantic world-component split isolation.

This module never infers semantic identity from story IDs, exact JSON equality,
hashes, names, or timestamps. A reviewer must first assign a source-bound
semantic_component_id. These helpers only validate and compare those declared
assignments; SAFE callers must not emit the private component IDs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping

DEFAULT_SPLITS = ("train", "validation")
REVIEW_SPLITS = frozenset(DEFAULT_SPLITS)
REVIEW_DECISIONS = frozenset({"PASS", "HOLD", "REJECT"})
REVIEW_ROW_KEYS = frozenset({
    "source_key",
    "split",
    "semantic_component_id",
    "source_evidence_ref",
    "source_version_verified",
    "semantic_review_completed",
    "decision",
})


class WorldIsolationError(ValueError):
    """A fixed, non-sensitive world-isolation contract failure."""


def component_split_conflicts(
    rows: Iterable[Mapping[str, object]],
    *,
    component_field: str = "world_component_id",
    split_field: str = "split",
    relevant_splits: Iterable[str] = DEFAULT_SPLITS,
) -> dict[str, frozenset[str]]:
    """Return declared components that occur in more than one relevant split.

    The returned keys are private identifiers for internal callers only.
    Missing/invalid component assignments are ignored here and must be rejected
    by the caller's source/structure gate.
    """
    splits = tuple(relevant_splits)
    if (not splits or len(set(splits)) != len(splits)
            or any(type(value) is not str or not value for value in splits)
            or type(component_field) is not str or not component_field
            or type(split_field) is not str or not split_field):
        raise WorldIsolationError("WORLD_SPLIT_ARGUMENT_HOLD")

    allowed = frozenset(splits)
    seen: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        component = row.get(component_field)
        split = row.get(split_field)
        if (type(component) is str and component.strip()
                and type(split) is str and split in allowed):
            seen[component].add(split)
    return {
        component: frozenset(values)
        for component, values in seen.items()
        if len(values) > 1
    }


def validate_component_review_assignments(
    rows: object,
    *,
    expected_source_keys: Iterable[str] | None = None,
) -> dict:
    """Validate reviewer-authored semantic component assignments.

    A PASS means only that the submitted assignment set is complete, source-
    bound by declaration, and has no declared Train/Validation collision. It
    does not prove reviewer independence, historical prompt replay, protected
    set completeness, rights, or training authorization.
    """
    if type(rows) is not list or not rows:
        raise WorldIsolationError("WORLD_REVIEW_ROWS_HOLD")

    seen_sources: set[str] = set()
    normalized: list[dict[str, str]] = []
    decisions: Counter[str] = Counter()
    unresolved = 0
    for row in rows:
        if type(row) is not dict or set(row) != REVIEW_ROW_KEYS:
            raise WorldIsolationError("WORLD_REVIEW_ROW_SCHEMA_HOLD")
        source = row.get("source_key")
        component = row.get("semantic_component_id")
        split = row.get("split")
        evidence = row.get("source_evidence_ref")
        decision = row.get("decision")
        if (type(source) is not str or not source.strip() or source in seen_sources
                or type(component) is not str or not component.strip()
                or type(split) is not str or split not in REVIEW_SPLITS
                or type(evidence) is not str or not evidence.strip()
                or type(row.get("source_version_verified")) is not bool
                or type(row.get("semantic_review_completed")) is not bool
                or type(decision) is not str or decision not in REVIEW_DECISIONS):
            raise WorldIsolationError("WORLD_REVIEW_ROW_VALUE_HOLD")
        seen_sources.add(source)
        decisions[decision] += 1
        if (decision != "PASS" or row["source_version_verified"] is not True
                or row["semantic_review_completed"] is not True):
            unresolved += 1
        normalized.append({
            "source_key": source,
            "semantic_component_id": component,
            "split": split,
        })

    if expected_source_keys is not None:
        expected = tuple(expected_source_keys)
        if (not expected or any(type(key) is not str or not key.strip()
                                for key in expected)
                or len(set(expected)) != len(expected)
                or set(expected) != seen_sources):
            raise WorldIsolationError("WORLD_REVIEW_SOURCE_COVERAGE_HOLD")

    conflicts = component_split_conflicts(
        normalized, component_field="semantic_component_id"
    )
    return {
        "schema": "storyforge_world_component_review_safe_v1",
        "status": (
            "WORLD_COMPONENT_REVIEW_PASS__NO_DECLARED_SPLIT_COLLISION"
            if not unresolved and not conflicts
            else "WORLD_COMPONENT_REVIEW_HOLD"
        ),
        "source_records": len(normalized),
        "review_decision_counts": {
            key: decisions[key] for key in ("PASS", "HOLD", "REJECT")
        },
        "unresolved_source_records": unresolved,
        "cross_split_component_count": len(conflicts),
        "world_component_isolation_verified": bool(
            not unresolved and not conflicts
        ),
        "reviewer_independence_independently_proven": False,
        "historical_actual_sent_version_verified": False,
        "protected_metadata_exclusion_verified": False,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "private_values_emitted": False,
    }

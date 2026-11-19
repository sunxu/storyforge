"""Synthetic-only smoke tests for Base336 preview; no private Story data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import r60_base336_component_conflict_preview_cpu as audit


def fixture_data():
    train = [f"train-{i}" for i in range(28)]
    val = [f"val-{i}" for i in range(10)]
    names = train + val
    components = [
        [train[0], val[0]], [train[1], val[1]],
        [train[2], val[2]], [train[3], val[3]],
        [train[4], train[5], val[4]],
        [train[6], train[7], train[8], train[9], val[5]],
    ]
    affected = set().union(*map(set, components))
    pos = 1
    positions = {}
    for sid in names:
        count = (3 if sid in names[:3] else 2) if sid in affected else (3 if sid in names[16:19] else 2)
        positions[sid] = set(range(pos, pos + count))
        pos += count
    # Preserve 35 cases in 16 linked stories while 22 isolated hold 47 cases.
    assert pos == 83
    assert sum(len(positions[x]) for x in affected) == 35
    stories = {sid: {"split": "train" if sid.startswith("train") else "validation"} for sid in names}
    edges = []
    for comp in components:
        base = comp[-1]
        for sid in comp[:-1]:
            edges.append({"source_a_PRIVATE": sid, "source_b_PRIVATE": base,
                          "split_a": stories[sid]["split"], "split_b": stories[base]["split"],
                          "cross_split": True})
    assert len(edges) == 10
    for i in range(16):
        a, b = train[i], train[i + 1]
        edges.append({"source_a_PRIVATE": a, "source_b_PRIVATE": b,
                      "split_a": "train", "split_b": "train", "cross_split": False})
    for n, edge in enumerate(edges, 1):
        edge["edge_ordinal"] = n
    return {"edges_PRIVATE": edges}, stories, positions


def test_component_preview_counts_only():
    packet, stories, positions = fixture_data()
    private, safe = audit.build(packet, stories, positions, b_safe_present=False)
    assert safe["candidate_cross_split_edges"] == 10
    assert safe["candidate_cross_split_components"] == 6
    assert safe["candidate_affected_stories"] == 16
    assert safe["candidate_affected_cases"] == 35
    assert safe["component_story_sizes"] == [2, 2, 2, 2, 3, 5]
    assert safe["p2_c"] == "HOLD" and safe["train_admitted"] == 0
    assert not safe["semantic_component_identity_owner_certified"]
    assert len(private["cross_split_components_PRIVATE"]) == 6


def test_split_drift_holds():
    packet, stories, positions = fixture_data()
    packet["edges_PRIVATE"][0]["split_b"] = "train"
    with pytest.raises(audit.Hold, match="EDGE_SPLIT_HOLD"):
        audit.build(packet, stories, positions, False)


def test_b_safe_self_attestation_is_not_independence(tmp_path: Path):
    path = tmp_path / "b-safe.json"
    receipt = {"schema": "storyforge_r60_base336_independent_review_safe_v1",
               "status": "REVIEW_FORMS_COMPLETE__OWNER_INDEPENDENCE_CHECK_PENDING",
               "review_edges_expected": 10, "review_edges_filled": 10,
               "decision_counts": {"SAME_SEMANTIC_COMPONENT": 10,
                                   "INDEPENDENT_TEMPLATE_ONLY": 0,
                                   "INSUFFICIENT_EVIDENCE": 0, "PENDING": 0},
               "reference_binding_verified_for_filled": 10,
               "source_versions_reviewed_count": 10,
               "reviewer_independence_independently_verified": False,
               "source_version_actual_sent_verified": False,
               "p2_c": "HOLD", "train_admitted": 0}
    path.write_text(json.dumps(receipt))
    assert audit.check_b_safe(path)
    receipt["reviewer_independence_independently_verified"] = True
    path.write_text(json.dumps(receipt))
    with pytest.raises(audit.Hold, match="B_SAFE_INDEPENDENCE_HOLD"):
        audit.check_b_safe(path)


def test_create_only(tmp_path: Path):
    p = tmp_path / "safe.json"
    audit.write_new(p, {"status": "HOLD"})
    with pytest.raises(FileExistsError):
        audit.write_new(p, {"status": "PASS"})

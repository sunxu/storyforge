"""Synthetic-only forward evidence gate: no external model calls."""
import copy
from datetime import datetime, timezone

import pytest
import r60_forward_evidence_gate_v1 as gate

H = "a" * 64


def source():
    return {
        "schema": gate.SCHEMA,
        "source_snapshot_frozen": True,
        "historical_cutoff_verified": True,
        "source_sha256": H,
        "case_sha256": H,
        "source_revision_sha256": H,
        "history_sha256": H,
        "target_sha256": H,
        "story_key_private": "synthetic-story-1",
    }


def protection():
    return {
        "manifest_frozen": True,
        "covers_all_protected_sets": True,
        "exact_identity_disjoint": True,
        "semantic_overlap_cleared": True,
        "manifest_sha256": H,
        "case_sha256": H,
    }


def world():
    return {
        "source_bound_roles_and_world": True,
        "semantic_components_adjudicated": True,
        "all_uncertain_links_quarantined": True,
        "train_validation_component_disjoint": True,
        "case_sha256": H,
        "component_manifest_sha256": H,
        "component_key_private": "synthetic-component",
        "split": "train",
    }


def executions(seal):
    rows = []
    for side in ("a", "b"):
        rows.append({
            "side": side,
            "case_sha256": H,
            "pre_review_seal_sha256": seal["pre_review_seal_sha256"],
            "input_sha256": H,
            "review_prompt_sha256": H,
            "response_sha256": H,
            "provider": "provider-" + side,
            "model_id": "model-" + side,
            "provider_request_id": "req-" + side + "-abcdef",
            "provider_request_id_origin": "PROVIDER_RESPONSE",
            "provider_evidence_authenticated": True,
            "http_status": 200,
            "review_decision": "PASS",
            "review_criteria_frozen": True,
            "other_reviewer_output_in_request": False,
            "isolated_context_verified": True,
            "started_at_utc": "2026-11-15T01:00:00Z",
            "finished_at_utc": "2026-11-15T01:00:01Z",
        })
    return rows


def test_two_gates_produce_hold_only():
    seal = gate.require_pre_review(source(), protection(), world())
    out = gate.require_post_review(seal, executions(seal))
    assert out["status"] == "FORWARD_EVIDENCE_BOUND__TRAIN_HOLD"
    assert out["train_admitted"] == 0


@pytest.mark.parametrize(("scope", "key", "reason"), [
    ("source", "historical_cutoff_verified", "FROZEN_SOURCE_HOLD"),
    ("protection", "covers_all_protected_sets", "EVALUATION_PROTECTION_HOLD"),
    ("protection", "semantic_overlap_cleared", "EVALUATION_PROTECTION_HOLD"),
    ("world", "semantic_components_adjudicated", "WORLD_COMPONENT_HOLD"),
    ("world", "all_uncertain_links_quarantined", "WORLD_COMPONENT_HOLD"),
])
def test_missing_pre_review_fact_rejected(scope, key, reason):
    parts = {"source": source(), "protection": protection(), "world": world()}
    parts[scope][key] = False
    with pytest.raises(gate.Hold, match=reason):
        gate.require_pre_review(parts["source"], parts["protection"], parts["world"])


@pytest.mark.parametrize(("key", "value", "reason"), [
    ("provider_request_id_origin", "LOCAL_RANDOM", "AUTHENTICATED_PROVIDER_EVIDENCE_HOLD"),
    ("provider_evidence_authenticated", False, "AUTHENTICATED_PROVIDER_EVIDENCE_HOLD"),
    ("isolated_context_verified", False, "REVIEW_EXECUTION_HOLD"),
    ("other_reviewer_output_in_request", True, "REVIEW_EXECUTION_HOLD"),
    ("pre_review_seal_sha256", H, "EXECUTION_BINDING_HOLD"),
    ("finished_at_utc", "2026-11-14T01:00:00Z", "EXECUTION_TIME_HOLD"),
])
def test_execution_fails_closed(key, value, reason):
    seal = gate.require_pre_review(source(), protection(), world())
    rows = executions(seal)
    rows[0][key] = value
    with pytest.raises(gate.Hold, match=reason):
        gate.require_post_review(seal, rows)


def test_reused_provider_id_disallowed():
    seal = gate.require_pre_review(source(), protection(), world())
    rows = executions(seal)
    rows[1]["provider"] = rows[0]["provider"]
    rows[1]["provider_request_id"] = rows[0]["provider_request_id"]
    with pytest.raises(gate.Hold, match="EXECUTION_INDEPENDENCE_HOLD"):
        gate.require_post_review(seal, rows)


def test_seal_tampering_rejected():
    seal = gate.require_pre_review(source(), protection(), world())
    altered = copy.deepcopy(seal)
    altered["split"] = "validation"
    with pytest.raises(gate.Hold, match="PRE_REVIEW_SEAL_HOLD"):
        gate.require_post_review(altered, executions(altered))


def test_datetime_parsing_requires_utc_z():
    assert gate._utc("2026-11-15T01:00:00Z") == datetime(
        2026, 11, 15, 1, tzinfo=timezone.utc)
    with pytest.raises(gate.Hold, match="TIMESTAMP_HOLD"):
        gate._utc("2026-11-15T01:00:00+08:00")

"""Synthetic comparison tests; no private P2-B examples are used."""
import pytest

from scripts import r60_p2b_dual_review_materials_v1 as review


def _assessment(verdict: str) -> dict:
    return {
        "verdict": verdict,
        "evidence": [],
        "rule_basis": [],
        "reasoning_summary": "Synthetic reasoning for comparison only.",
        "missing_context": [],
    }


def test_comparison_counts_all_90_and_keeps_owner_gate():
    packets = [{
        "calibration_id": f"synthetic-{i}",
        "visible_history": [], "target_text": "synthetic target",
        "verified_world_components": [],
    } for i in range(30)]
    codex = {}
    claude = {}
    for packet in packets:
        cid = packet["calibration_id"]
        codex[cid] = {"assessments": {
            dim: _assessment("NOT_SUPPORTED") for dim in review.DIMENSIONS
        }}
        claude[cid] = {"assessments": {
            dim: _assessment("NOT_SUPPORTED") for dim in review.DIMENSIONS
        }}
    claude["synthetic-0"]["assessments"]["safety"] = _assessment("SUPPORTED")

    comparison, disagreements, safe, owner_packets, candidates, checks = review.build(
        packets, codex, claude,
    )

    assert comparison["dimension_count"] == 90
    assert comparison["agreement_count"] == 89
    assert comparison["disagreement_count"] == 1
    assert comparison["by_dimension"]["safety"]["disagree"] == 1
    assert len(disagreements) == 1
    assert len(owner_packets) == len(candidates) == 30
    assert len(checks) == 90
    assert all(row["status"] == "OWNER_CONFIRMATION_PENDING" for row in candidates)
    assert all(row["semantic_entailment_verified_by_owner"] is False for row in checks)
    assert safe["status"] == "P2B_AI_DUAL_REVIEW_COMPLETE__OWNER_CONFIRMATION_PENDING"


def test_create_only_output_set_can_resume_exact_bytes(tmp_path):
    path = tmp_path / "safe.json"
    items = [(path, {"case_count": 30}, False)]
    review.write_set_once(items)
    first = path.read_bytes()
    review.write_set_once(items)
    assert path.read_bytes() == first
    with pytest.raises(review.Hold, match="EXISTING_OUTPUT_BINDING_HOLD"):
        review.write_set_once([(path, {"case_count": 29}, False)])
    assert path.read_bytes() == first

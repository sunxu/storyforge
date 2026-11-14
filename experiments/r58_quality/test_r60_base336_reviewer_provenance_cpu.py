"""Synthetic-only 336 frozen reviewer evidence aggregation."""
import pytest
import r60_base336_reviewer_provenance_cpu as reviewer
import r60_real_quality_batch as batch
from test_r60_base_start_cpu336_template_audit import sample


def build():
    _, manifest = sample()
    rows = []
    for pos in range(1, 340):
        rows.append({
            "position": pos,
            "side_evidence": {
                "a": {"source": "V1", "decision": "PASS",
                      "source_receipt_sha256": "a" * 64},
                "b": {"source": "V3", "decision": "PASS",
                      "source_receipt_sha256": "b" * 64},
            },
        })
    cfg = {
        "schema": batch.SCHEMA,
        "expected_cases": 1000,
        "model_a": "claude",
        "model_b": "deepseek",
        "owner_attested_independent_ai": False,
    }
    return {"candidate_count": 339, "entries": rows}, manifest, cfg


def test_all_336_bound_distinct_models_not_independence():
    report, manifest, cfg = build()
    safe = reviewer.inspect(report, manifest, cfg)
    assert safe["cases_checked"] == 336
    assert safe["distinct_configured_model_ids"] is True
    assert safe["side_source_counts"] == {"a_V1": 336, "b_V3": 336}
    assert safe["reviewer_independence_verified"] is False
    assert safe["provider_execution_independence_verified"] is False
    assert safe["train_admitted"] == 0


def test_attestation_only_not_proof():
    report, manifest, cfg = build()
    cfg["owner_attested_independent_ai"] = True
    safe = reviewer.inspect(report, manifest, cfg)
    assert safe["v1_pool_config_owner_attestation_present"] is True
    assert safe["reviewer_independence_verified"] is False


def test_duplicate_model_ids_are_rejected():
    report, manifest, cfg = build()
    cfg["model_b"] = "CLAUDE"
    with pytest.raises(reviewer.Hold, match="REVIEWER_MODEL_BINDING_HOLD"):
        reviewer.inspect(report, manifest, cfg)


def test_missing_side_evidence_is_rejected():
    report, manifest, cfg = build()
    del report["entries"][10]["side_evidence"]["b"]
    with pytest.raises(reviewer.Hold, match="REVIEWER_SIDES_HOLD"):
        reviewer.inspect(report, manifest, cfg)


def test_duplicate_position_is_rejected():
    report, manifest, cfg = build()
    manifest["remaining_full_r50_hold"][1]["position"] = 4
    with pytest.raises(reviewer.Hold, match="REVIEWER_POSITION_HOLD"):
        reviewer.inspect(report, manifest, cfg)

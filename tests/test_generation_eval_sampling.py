import json
from pathlib import Path

import pytest

from storyforge_dataset.generation_eval.sampling import (
    SamplingDecisionError,
    assess_sampling_decision,
)


def load_candidate():
    path = Path(__file__).parents[1] / (
        "experiments/r60_quality/r60_sampling_decision_candidate_v1.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_sampling_design_is_valid_but_never_freezes_or_authorizes():
    result = assess_sampling_decision(load_candidate())
    assert result.status == "SAMPLING_DECISION_VALID__PROFILE_FREEZE_PENDING"
    assert result.ready_for_profile_freeze is False
    assert result.blockers == ()
    safe = result.to_safe_dict()
    assert safe["inference_started"] is False
    assert safe["gpu_started"] is False
    assert safe["training_started"] is False


def test_locked_set_cannot_be_used_for_sampling_tuning():
    candidate = load_candidate()
    candidate["model_profiles"]["challenger"]["variants"][
        "development_sampling_sensitivity"
    ]["evaluation_split"] = "p4_locked30"
    result = assess_sampling_decision(candidate)
    assert "CHALLENGER_VARIANT_SPLIT_INVALID" in result.blockers


def test_greedy_variant_cannot_carry_sampling_parameters():
    candidate = load_candidate()
    candidate["model_profiles"]["challenger"]["variants"]["primary"][
        "sampling"
    ] = {"do_sample": False, "temperature": 0.6}
    result = assess_sampling_decision(candidate)
    assert "CHALLENGER_SAMPLING_POLICY_MISMATCH" in result.blockers


def test_exact_model_revision_is_required():
    candidate = load_candidate()
    candidate["model_profiles"]["B"]["revision"] = "main"
    result = assess_sampling_decision(candidate)
    assert "B_MODEL_PIN_MISMATCH" in result.blockers


def test_sampling_policy_cannot_drift_silently():
    candidate = load_candidate()
    candidate["model_profiles"]["A"]["variants"]["primary"]["sampling"][
        "temperature"
    ] = 0.8
    result = assess_sampling_decision(candidate)
    assert "A_SAMPLING_POLICY_MISMATCH" in result.blockers


def test_sampling_decision_requires_exact_roles():
    candidate = load_candidate()
    del candidate["model_profiles"]["B"]
    with pytest.raises(SamplingDecisionError, match="SAMPLING_MODEL_SET_INVALID"):
        assess_sampling_decision(candidate)


def test_authorization_flags_must_remain_closed():
    candidate = load_candidate()
    candidate["gpu_authorized"] = True
    result = assess_sampling_decision(candidate)
    assert "GPU_AUTHORIZED_MUST_REMAIN_FALSE" in result.blockers
    assert result.ready_for_profile_freeze is False

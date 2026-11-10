import json
from pathlib import Path

import pytest

from storyforge_dataset.generation_eval.profiles import (
    EXPECTED_MODELS,
    assess_profile,
    load_profile,
)


def candidate_profile():
    models = {}
    for role, (model, revision) in EXPECTED_MODELS.items():
        models[role] = {
            "model": model,
            "revision": revision,
            "enable_thinking": True if role == "A" else None,
            "sampling": None,
            "chat_template_sha256": "a" * 64,
        }
    return {
        "schema": "storyforge_r60_p3_model_profiles_v1",
        "status": "TEMPLATE_SOURCE_DECISIONS_OWNER_APPROVED__GENERATION_PROFILE_PENDING",
        "model_profiles": models,
        "context_ceiling_tokens": None,
        "input_budget_tokens": None,
        "generation_budget_tokens": None,
        "seed": None,
        "runtime_digest": None,
        "tokenizer_hashes": None,
        "profile_freeze_authorized": False,
        "inference_authorized": False,
        "gpu_authorized": False,
        "training_authorized": False,
    }


def test_candidate_profile_is_held_not_guessed():
    result = assess_profile(candidate_profile())
    assert result.ready is False
    assert result.status == "P4_PROFILE_INCOMPLETE_HOLD"
    assert "B_SAMPLING_UNSET" in result.blockers
    assert "CHALLENGER_SAMPLING_UNSET" in result.blockers
    assert "GPU_NOT_AUTHORIZED" in result.blockers
    assert result.inference_started is False


def test_all_explicitly_frozen_profiles_can_become_ready():
    profile = candidate_profile()
    profile.update({
        "context_ceiling_tokens": 32768,
        "input_budget_tokens": 28672,
        "generation_budget_tokens": 4096,
        "seed": 20261110,
        "runtime_digest": "sha256:" + "b" * 64,
        "tokenizer_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "profile_freeze_authorized": True,
        "inference_authorized": True,
        "gpu_authorized": True,
    })
    for item in profile["model_profiles"].values():
        item["sampling"] = {"do_sample": True, "temperature": 0.7, "top_p": 0.9}
    assert assess_profile(profile).ready is True


def test_wrong_model_revision_is_rejected():
    profile = candidate_profile()
    profile["model_profiles"]["B"]["revision"] = "main"
    with pytest.raises(ValueError, match="P4_MODEL_PIN_MISMATCH"):
        assess_profile(profile)


def test_load_profile_checks_schema_and_model_pins(tmp_path: Path):
    profile = candidate_profile()
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    assert load_profile(path)["schema"] == "storyforge_r60_p3_model_profiles_v1"
    profile["schema"] = "wrong"
    path.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(ValueError, match="P4_PROFILE_SCHEMA_INVALID"):
        load_profile(path)


def test_safe_assessment_contains_no_model_or_prompt_values():
    safe = assess_profile(candidate_profile()).to_safe_dict()
    encoded = json.dumps(safe)
    assert "Qwen" not in encoded
    assert "zai-org" not in encoded
    assert safe["private_values_emitted"] is False
    assert safe["gpu_started"] is False
    assert safe["training_started"] is False


def test_budget_mismatch_and_greedy_sampling_conflict_are_blockers():
    profile = candidate_profile()
    profile.update({
        "context_ceiling_tokens": 32768,
        "input_budget_tokens": 28000,
        "generation_budget_tokens": 4000,
        "seed": 1,
        "runtime_digest": "sha256:" + "b" * 64,
        "tokenizer_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "profile_freeze_authorized": True,
        "inference_authorized": True,
        "gpu_authorized": True,
    })
    for item in profile["model_profiles"].values():
        item["sampling"] = {"do_sample": False, "temperature": 0.7, "top_p": 0.9}
    result = assess_profile(profile)
    assert "CONTEXT_BUDGET_SUM_MISMATCH" in result.blockers
    assert "A_GREEDY_PROFILE_CONFLICT" in result.blockers


def test_repository_p3_candidate_remains_held_until_profile_freeze():
    repo_root = Path(__file__).parents[1]
    candidate = repo_root / "experiments/r60_quality/p3_model_profiles_candidate_v1.json"
    result = assess_profile(load_profile(candidate))
    assert result.ready is False
    assert "PROFILE_FREEZE_NOT_AUTHORIZED" in result.blockers
    assert "INFERENCE_NOT_AUTHORIZED" in result.blockers
    assert "GPU_NOT_AUTHORIZED" in result.blockers
    assert "B_SAMPLING_UNSET" in result.blockers
    assert "CHALLENGER_SAMPLING_UNSET" in result.blockers

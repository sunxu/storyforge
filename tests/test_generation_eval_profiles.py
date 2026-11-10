import hashlib
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
            "thinking_mode": "api_flag" if role == "A" else ("template_default" if role == "B" else "explicit_generation_prefix"),
            "generation_prefix": "<think>" if role == "challenger" else None,
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



def valid_manifest_fields():
    files = {
        "A": ["config.json", "generation_config.json", "merges.txt", "tokenizer.json",
              "tokenizer_config.json", "vocab.json"],
        "B": ["chat_template.jinja", "config.json", "generation_config.json",
              "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"],
        "challenger": ["chat_template.jinja", "config.json", "generation_config.json",
                       "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"],
    }
    return {
        "p3_download_safe_sha256": "a" * 64,
        "tokenizer_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "tokenizer_file_hashes": {
            role: {name: "c" * 64 for name in names} for role, names in files.items()
        },
        "generation_config_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "eos_token_ids": {
            "A": [151645, 151643],
            "B": [151329, 151336, 151338],
            "challenger": [151329, 151336, 151338],
        },
        "pad_token_ids": {"A": 151643, "B": 151329, "challenger": 151329},
        "custom_stop_sequences": {"A": [], "B": [], "challenger": []},
        "finish_reason_policy": {
            "eos_source": "pinned_generation_config_eos_token_id",
            "length_definition": "max_new_tokens_exhausted_without_eos",
            "unexpected_stop_action": "hold",
        },
        "truncation_policy": "reject_over_budget_no_silent_prompt_truncation",
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
        "dependency_lock_sha256": "d" * 64,
        "evaluation_prompt_sha256": "e" * 64,
        "output_schema_sha256": "f" * 64,
        **valid_manifest_fields(),
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


def test_tokenizer_file_manifest_mismatch_is_a_blocker():
    profile = candidate_profile()
    profile.update(valid_manifest_fields())
    profile["tokenizer_file_hashes"]["A"]["tokenizer.json"] = "d" * 64
    result = assess_profile(profile)
    assert "TOKENIZER_HASH_MANIFEST_MISMATCH" in result.blockers


def test_generation_config_hash_must_match_file_manifest():
    profile = candidate_profile()
    profile.update(valid_manifest_fields())
    profile["generation_config_hashes"]["A"] = "d" * 64
    result = assess_profile(profile)
    assert "GENERATION_CONFIG_HASH_MANIFEST_MISMATCH" in result.blockers


def test_eos_token_ids_must_match_pinned_generation_config():
    profile = candidate_profile()
    profile.update(valid_manifest_fields())
    profile["eos_token_ids"]["challenger"] = [151329]
    result = assess_profile(profile)
    assert "EOS_TOKEN_IDS_REVISION_MISMATCH" in result.blockers


def test_custom_stop_sequences_are_not_silently_ignored():
    profile = candidate_profile()
    profile.update(valid_manifest_fields())
    profile["custom_stop_sequences"]["A"] = ["</custom>"]
    result = assess_profile(profile)
    assert "CUSTOM_STOP_SEQUENCES_UNSUPPORTED_OR_UNEXPECTED" in result.blockers


def test_p4_candidate_binds_p3_file_and_stop_token_evidence_but_stays_held():
    repo_root = Path(__file__).parents[1]
    candidate_path = (
        repo_root / "experiments/r60_quality/p4_generation_profile_candidate_v1.json"
    )
    profile = load_profile(candidate_path)
    result = assess_profile(profile)
    assert result.ready is False
    assert "RUNTIME_DIGEST_UNSET" not in result.blockers
    assert "DEPENDENCY_LOCK_HASH_UNSET" not in result.blockers
    lock_path = repo_root / profile["dependency_lock_path"]
    assert hashlib.sha256(lock_path.read_bytes()).hexdigest() == profile["dependency_lock_sha256"]
    assert "PROFILE_FREEZE_NOT_AUTHORIZED" in result.blockers
    assert "INFERENCE_NOT_AUTHORIZED" in result.blockers
    assert "GPU_NOT_AUTHORIZED" in result.blockers
    assert "TOKENIZER_FILE_HASHES_INVALID" not in result.blockers
    assert "GENERATION_CONFIG_HASH_MANIFEST_MISMATCH" not in result.blockers
    assert "EOS_TOKEN_IDS_REVISION_MISMATCH" not in result.blockers


def test_p4_candidate_has_scoped_runtime_smoke_authorization_only():
    repo_root = Path(__file__).parents[1]
    candidate = load_profile(
        repo_root / "experiments/r60_quality/p4_generation_profile_candidate_v1.json"
    )
    result = assess_profile(candidate, purpose="runtime_smoke")
    assert result.ready is False
    assert "RUNTIME_SMOKE_NOT_AUTHORIZED" in result.blockers
    assert assess_profile(candidate).ready is False
    assert "PROFILE_FREEZE_NOT_AUTHORIZED" in assess_profile(candidate).blockers
    assert candidate["profile_freeze_authorized"] is False
    assert candidate["inference_authorized"] is False
    assert candidate["gpu_authorized"] is False
    assert candidate["training_authorized"] is False
    assert candidate["runtime_smoke_authorization_status"] == "CONSUMED_2026-11-10"


def test_freeze_review_is_independent_of_inference_and_gpu_authorization():
    repo_root = Path(__file__).parents[1]
    profile = load_profile(repo_root / "experiments/r60_quality/p4_generation_profile_candidate_v1.json")
    result = assess_profile(profile, purpose="freeze_review")
    assert result.ready is False
    assert "EVALUATION_PROMPT_HASH_UNSET" in result.blockers
    assert "OUTPUT_SCHEMA_HASH_UNSET" not in result.blockers
    assert "EVALUATION_CONTRACT_NOT_OWNER_APPROVED" in result.blockers
    assert "INFERENCE_AUTHORIZATION_MUST_REMAIN_FALSE" not in result.blockers
    assert "GPU_AUTHORIZATION_MUST_REMAIN_FALSE" not in result.blockers


def test_runtime_smoke_authorization_does_not_allow_training():
    profile = candidate_profile()
    profile.update(valid_manifest_fields())
    profile["runtime_smoke_authorized"] = True
    profile["training_authorized"] = True
    result = assess_profile(profile, purpose="runtime_smoke")
    assert "TRAINING_AUTHORIZATION_MUST_REMAIN_DISABLED" in result.blockers


def test_runtime_smoke_requires_its_own_explicit_authorization():
    profile = candidate_profile()
    profile.update(valid_manifest_fields())
    result = assess_profile(profile, purpose="runtime_smoke")
    assert result.ready is False
    assert "RUNTIME_SMOKE_NOT_AUTHORIZED" in result.blockers

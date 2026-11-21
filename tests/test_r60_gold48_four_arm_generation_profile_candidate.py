"""Static Gold48 profile preregistration contract: no HF/model/backend import."""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / (
    "experiments/r60_quality/gold48_four_arm_generation_profile_candidate_v1.json"
)
REV = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_profile_is_four_arm_scoped_prereg_not_inference_authorization():
    p = load()
    assert p["schema"] == "storyforge_r60_gold48_four_arm_generation_profile_candidate_v1"
    assert p["status"] == "OWNER_REVIEW_PENDING__MODEL_RUNTIME_COMPATIBILITY_HOLD"
    assert p["dataset"]["freeze_status_required"] == (
        "GOLD48_FROZEN_SCOPED__GENERATION_PROFILE_PENDING"
    )
    assert p["dataset"]["scoped_owner_freeze_safe_required"] == (
        "GOLD48_SCOPED_OWNER_FREEZE_COMPLETE__GENERATION_PROFILE_PENDING"
    )
    assert p["dataset"]["reconstructed_message_count"] == 48
    assert p["dataset"]["main_analysis_case_count"] == 48
    assert p["dataset"]["sensitivity_case_count"] == 42
    assert p["dataset"]["session_count"] == 25
    assert p["dataset"]["historical_actual_sent_verified"] is False
    assert p["dataset"]["full_protected_universe_independence_verified"] is False
    assert p["dataset"]["model_visible_replies"].startswith("NONE__")
    assert p["owner_generation_profile_freeze"] is False
    assert p["inference_authorized"] is False
    assert p["gpu_authorized_by_this_document"] is False
    assert p["training_authorized"] is False
    assert p["model_generation_started"] is False


def test_all_four_models_use_pinned_qwen35_and_distinct_adapters():
    p = load()
    assert set(p["arms"]) == {
        "base", "r46_v02", "r54_v03a", "r60_base336",
    }
    base = p["base_model"]
    assert base["model"] == "Qwen/Qwen3.8-27B"
    assert base["revision"] == REV
    assert base["model_type"] == "qwen3_5"
    assert base["architecture"] == "Qwen3_5ForConditionalGeneration"
    assert base["eos_token_ids"] == [248046, 248044]
    assert base["pad_token_id"] == 248044
    assert base["generation_model_architecture_runtime_verified"] is False
    adapters = []
    for key, arm in p["arms"].items():
        assert arm["base_revision"] == REV
        assert arm["model"] == base["model"]
        assert arm["enable_thinking"] is False
        assert arm["sampling"] == p["generation"]["sampling"]
        assert arm["adapter_runtime_reload_in_selected_inference_image_verified"] is False
        if key == "base":
            assert arm["adapter_kind"] == "NONE"
            assert arm["adapter_checkpoint"] is None
        else:
            assert arm["adapter_kind"] == "PEFT_LORA"
            assert arm["adapter_sha256_from_existing_private_release_receipt_required"]
            assert arm["adapter_checkpoint"].startswith(
                "hf://buckets/adradar/storyforge-training/"
            )
            adapters.append(arm["adapter_checkpoint"])
    assert len(set(adapters)) == 3
    assert adapters[0].endswith("checkpoint-7")
    assert adapters[1].endswith("checkpoint-16")
    assert adapters[2].endswith("checkpoint-37")


def test_no_truncation_and_frozen_trial_design():
    p = load()
    cfg = p["generation"]
    assert cfg["context_ceiling_tokens"] == 32768
    assert cfg["max_input_tokens"] == 30720
    assert cfg["max_new_tokens"] == 2048
    assert cfg["max_input_tokens"] + cfg["max_new_tokens"] == 32768
    assert cfg["thinking_mode"] == "disabled"
    assert cfg["chat_template_args"] == {
        "enable_thinking": False,
        "add_generation_prompt": True,
    }
    assert cfg["sampling"] == {
        "do_sample": True, "temperature": 0.7,
        "top_p": 0.8, "top_k": 20, "min_p": 0.0,
    }
    assert cfg["seed_base"] == 42
    assert cfg["prompt_truncation"] == "FORBIDDEN"
    assert cfg["custom_stop_sequences"] == []
    assert p["blind_review"]["generation_reply_count_expected"] == 192
    assert p["blind_review"]["historical_original_reference_count"] == 48
    assert p["blind_review"]["five_answer_sources_total"] == 240
    assert p["blind_review"]["stratified_sensitivity_case_count"] == 42
    assert len(p["blind_review"]["dimensions"]) == 6
    assert len(p["blind_review"]["severe_flags"]) == 3
    assert len(p["pre_generation_blockers"]) >= 5
    assert "QWEN3_5_INFERENCE_RUNTIME_IMAGE_AND_TRANSFORMERS_DEPENDENCY_LOCK_PENDING" in (
        p["pre_generation_blockers"]
    )
    assert p["existing_reuse"]["legacy_p4_backend_without_adapter_extension_sufficient"] is False

"""Strict validation and readiness assessment for frozen P4 model profiles.

This module is deliberately CPU-only: it parses configuration and never imports
Transformers, PyTorch, Hugging Face Hub, or submits a Job.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROFILE_SCHEMA = "storyforge_r60_p3_model_profiles_v1"
EXPECTED_MODELS = {
    "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
    "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
    "challenger": ("zai-org/GLM-Z1-32B-0414", "8eb2858992c1f749e2a6d4075455decc2484722d"),
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_TOKENIZER_FILES = {
    "A": {"config.json", "generation_config.json", "merges.txt", "tokenizer.json",
          "tokenizer_config.json", "vocab.json"},
    "B": {"chat_template.jinja", "config.json", "generation_config.json",
          "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"},
    "challenger": {"chat_template.jinja", "config.json", "generation_config.json",
                   "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"},
}
EXPECTED_FINISH_REASON_POLICY = {
    "eos_source": "pinned_generation_config_eos_token_id",
    "length_definition": "max_new_tokens_exhausted_without_eos",
    "unexpected_stop_action": "hold",
}
EXPECTED_EOS_TOKEN_IDS = {
    "A": [151645, 151643],
    "B": [151329, 151336, 151338],
    "challenger": [151329, 151336, 151338],
}
EXPECTED_PAD_TOKEN_IDS = {"A": 151643, "B": 151329, "challenger": 151329}
EXPECTED_CUSTOM_STOP_SEQUENCES = {"A": [], "B": [], "challenger": []}
EXPECTED_TRUNCATION_POLICY = "reject_over_budget_no_silent_prompt_truncation"


@dataclass(frozen=True)
class ProfileAssessment:
    status: str
    ready: bool
    model_count: int
    roles: tuple[str, ...]
    blockers: tuple[str, ...]
    private_values_emitted: bool = False
    inference_started: bool = False
    gpu_started: bool = False
    training_started: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "schema": "storyforge_r60_generation_profile_assessment_safe_v1",
            "status": self.status,
            "ready": self.ready,
            "model_count": self.model_count,
            "roles": list(self.roles),
            "blockers": list(self.blockers),
            "private_values_emitted": False,
            "inference_started": False,
            "gpu_started": False,
            "training_started": False,
        }


def load_profile(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON profile and enforce its top-level contract."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != PROFILE_SCHEMA:
        raise ValueError("P4_PROFILE_SCHEMA_INVALID")
    models = value.get("model_profiles")
    if not isinstance(models, dict) or set(models) != set(EXPECTED_MODELS):
        raise ValueError("P4_MODEL_SET_INVALID")
    for role, expected in EXPECTED_MODELS.items():
        item = models[role]
        if not isinstance(item, dict):
            raise TypeError("P4_MODEL_PROFILE_INVALID")
        if (item.get("model"), item.get("revision")) != expected:
            raise ValueError("P4_MODEL_PIN_MISMATCH")
    return value


def assess_profile(
    profile: dict[str, Any], *, purpose: str = "generation"
) -> ProfileAssessment:
    """Assess a profile for production generation or a separately scoped smoke.

    Runtime Smoke authorization does not freeze the production profile and does
    not authorize the general generation worker or training.
    """
    if purpose not in {"generation", "runtime_smoke", "freeze_review"}:
        raise ValueError("P4_ASSESSMENT_PURPOSE_INVALID")
    if not isinstance(profile, dict) or profile.get("schema") != PROFILE_SCHEMA:
        raise ValueError("P4_PROFILE_SCHEMA_INVALID")
    models = profile.get("model_profiles")
    if not isinstance(models, dict) or set(models) != set(EXPECTED_MODELS):
        raise ValueError("P4_MODEL_SET_INVALID")

    blockers: list[str] = []
    if purpose == "generation":
        for flag, code in (
            ("profile_freeze_authorized", "PROFILE_FREEZE_NOT_AUTHORIZED"),
            ("inference_authorized", "INFERENCE_NOT_AUTHORIZED"),
            ("gpu_authorized", "GPU_NOT_AUTHORIZED"),
        ):
            if profile.get(flag) is not True:
                blockers.append(code)
    elif purpose == "runtime_smoke" and profile.get("runtime_smoke_authorized") is not True:
        blockers.append("RUNTIME_SMOKE_NOT_AUTHORIZED")
    if purpose == "freeze_review":
        for flag, code in (
            ("profile_freeze_authorized", "PROFILE_FREEZE_ALREADY_SET_IN_REVIEW"),
            ("inference_authorized", "INFERENCE_AUTHORIZATION_MUST_REMAIN_FALSE"),
            ("gpu_authorized", "GPU_AUTHORIZATION_MUST_REMAIN_FALSE"),
        ):
            if profile.get(flag) is not False:
                blockers.append(code)
    if profile.get("training_authorized") is not False:
        blockers.append("TRAINING_AUTHORIZATION_MUST_REMAIN_DISABLED")

    for field, code in (
        ("context_ceiling_tokens", "CONTEXT_CEILING_UNSET"),
        ("input_budget_tokens", "INPUT_BUDGET_UNSET"),
        ("generation_budget_tokens", "GENERATION_BUDGET_UNSET"),
        ("seed", "SEED_UNSET"),
        ("runtime_digest", "RUNTIME_DIGEST_UNSET"),
        ("dependency_lock_sha256", "DEPENDENCY_LOCK_HASH_UNSET"),
        ("tokenizer_hashes", "TOKENIZER_HASHES_UNSET"),
        ("tokenizer_file_hashes", "TOKENIZER_FILE_HASHES_UNSET"),
        ("generation_config_hashes", "GENERATION_CONFIG_HASHES_UNSET"),
        ("eos_token_ids", "EOS_TOKEN_IDS_UNSET"),
        ("pad_token_ids", "PAD_TOKEN_IDS_UNSET"),
        ("custom_stop_sequences", "CUSTOM_STOP_SEQUENCES_UNSET"),
        ("p3_download_safe_sha256", "P3_DOWNLOAD_SAFE_HASH_UNSET"),
        ("evaluation_prompt_sha256", "EVALUATION_PROMPT_HASH_UNSET"),
        ("output_schema_sha256", "OUTPUT_SCHEMA_HASH_UNSET"),
    ):
        value = profile.get(field)
        if value is None or value == "":
            blockers.append(code)

    ceiling = profile.get("context_ceiling_tokens")
    input_budget = profile.get("input_budget_tokens")
    output_budget = profile.get("generation_budget_tokens")
    if all(isinstance(v, int) and not isinstance(v, bool) and v > 0
           for v in (ceiling, input_budget, output_budget)):
        if input_budget + output_budget != ceiling:
            blockers.append("CONTEXT_BUDGET_SUM_MISMATCH")
    elif ceiling is not None or input_budget is not None or output_budget is not None:
        blockers.append("CONTEXT_BUDGET_INVALID")

    seed = profile.get("seed")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool) or seed < 0):
        blockers.append("SEED_INVALID")

    runtime_digest = profile.get("runtime_digest")
    if runtime_digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", str(runtime_digest)):
        blockers.append("RUNTIME_DIGEST_INVALID")

    lock_hash = profile.get("dependency_lock_sha256")
    if lock_hash is not None and (not isinstance(lock_hash, str) or not SHA256_RE.fullmatch(lock_hash)):
        blockers.append("DEPENDENCY_LOCK_HASH_INVALID")

    tokenizer_hashes = profile.get("tokenizer_hashes")
    if tokenizer_hashes is not None and (
        not isinstance(tokenizer_hashes, dict)
        or set(tokenizer_hashes) != set(EXPECTED_MODELS)
        or any(not isinstance(value, str) or not SHA256_RE.fullmatch(value)
               for value in tokenizer_hashes.values())
    ):
        blockers.append("TOKENIZER_HASHES_INVALID")

    tokenizer_file_hashes = profile.get("tokenizer_file_hashes")
    if tokenizer_file_hashes is not None:
        if (
            not isinstance(tokenizer_file_hashes, dict)
            or set(tokenizer_file_hashes) != set(EXPECTED_MODELS)
            or any(
                not isinstance(tokenizer_file_hashes[role], dict)
                or set(tokenizer_file_hashes[role]) != EXPECTED_TOKENIZER_FILES[role]
                or any(
                    not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                    for digest in tokenizer_file_hashes[role].values()
                )
                for role in EXPECTED_MODELS
            )
        ):
            blockers.append("TOKENIZER_FILE_HASHES_INVALID")
        elif (
            isinstance(tokenizer_hashes, dict)
            and set(tokenizer_hashes) == set(EXPECTED_MODELS)
            and any(
                tokenizer_hashes[role] != tokenizer_file_hashes[role]["tokenizer.json"]
                for role in EXPECTED_MODELS
            )
        ):
            blockers.append("TOKENIZER_HASH_MANIFEST_MISMATCH")

    generation_config_hashes = profile.get("generation_config_hashes")
    if generation_config_hashes is not None and (
        not isinstance(generation_config_hashes, dict)
        or set(generation_config_hashes) != set(EXPECTED_MODELS)
        or any(not isinstance(value, str) or not SHA256_RE.fullmatch(value)
               for value in generation_config_hashes.values())
    ):
        blockers.append("GENERATION_CONFIG_HASHES_INVALID")
    elif (
        isinstance(tokenizer_file_hashes, dict)
        and isinstance(generation_config_hashes, dict)
        and set(tokenizer_file_hashes) == set(EXPECTED_MODELS)
        and set(generation_config_hashes) == set(EXPECTED_MODELS)
        and all(
            isinstance(tokenizer_file_hashes[role], dict)
            and set(tokenizer_file_hashes[role]) == EXPECTED_TOKENIZER_FILES[role]
            for role in EXPECTED_MODELS
        )
        and any(
            generation_config_hashes[role]
            != tokenizer_file_hashes[role]["generation_config.json"]
            for role in EXPECTED_MODELS
        )
    ):
        blockers.append("GENERATION_CONFIG_HASH_MANIFEST_MISMATCH")

    eos_token_ids = profile.get("eos_token_ids")
    if eos_token_ids is not None and (
        not isinstance(eos_token_ids, dict)
        or set(eos_token_ids) != set(EXPECTED_MODELS)
        or any(
            not isinstance(values, list) or not values
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in values
            )
            or len(set(values)) != len(values)
            for values in eos_token_ids.values()
        )
    ):
        blockers.append("EOS_TOKEN_IDS_INVALID")
    elif isinstance(eos_token_ids, dict) and eos_token_ids != EXPECTED_EOS_TOKEN_IDS:
        blockers.append("EOS_TOKEN_IDS_REVISION_MISMATCH")

    pad_token_ids = profile.get("pad_token_ids")
    if pad_token_ids is not None and (
        not isinstance(pad_token_ids, dict)
        or set(pad_token_ids) != set(EXPECTED_MODELS)
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in pad_token_ids.values()
        )
    ):
        blockers.append("PAD_TOKEN_IDS_INVALID")
    elif isinstance(pad_token_ids, dict) and pad_token_ids != EXPECTED_PAD_TOKEN_IDS:
        blockers.append("PAD_TOKEN_IDS_REVISION_MISMATCH")

    custom_stop_sequences = profile.get("custom_stop_sequences")
    if custom_stop_sequences is not None and custom_stop_sequences != EXPECTED_CUSTOM_STOP_SEQUENCES:
        blockers.append("CUSTOM_STOP_SEQUENCES_UNSUPPORTED_OR_UNEXPECTED")

    for field, code in (("evaluation_prompt_sha256", "EVALUATION_PROMPT_HASH_INVALID"), ("output_schema_sha256", "OUTPUT_SCHEMA_HASH_INVALID")):
        value = profile.get(field)
        if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
            blockers.append(code)

    p3_safe_hash = profile.get("p3_download_safe_sha256")
    if p3_safe_hash is not None and (
        not isinstance(p3_safe_hash, str) or not SHA256_RE.fullmatch(p3_safe_hash)
    ):
        blockers.append("P3_DOWNLOAD_SAFE_HASH_INVALID")

    if profile.get("finish_reason_policy") != EXPECTED_FINISH_REASON_POLICY:
        blockers.append("FINISH_REASON_POLICY_INVALID")
    if profile.get("truncation_policy") != EXPECTED_TRUNCATION_POLICY:
        blockers.append("TRUNCATION_POLICY_INVALID")

    for role, expected in EXPECTED_MODELS.items():
        item = models[role]
        if not isinstance(item, dict) or (item.get("model"), item.get("revision")) != expected:
            raise ValueError("P4_MODEL_PIN_MISMATCH")
        sampling = item.get("sampling")
        if not isinstance(sampling, dict):
            blockers.append(f"{role.upper()}_SAMPLING_UNSET")
        else:
            do_sample = sampling.get("do_sample")
            if not isinstance(do_sample, bool):
                blockers.append(f"{role.upper()}_SAMPLING_INVALID")
            if do_sample is True:
                temperature = sampling.get("temperature")
                top_p = sampling.get("top_p")
                if (not isinstance(temperature, (int, float)) or isinstance(temperature, bool)
                        or not math.isfinite(float(temperature)) or temperature <= 0
                        or not isinstance(top_p, (int, float)) or isinstance(top_p, bool)
                        or not math.isfinite(float(top_p)) or not 0 < top_p <= 1):
                    blockers.append(f"{role.upper()}_SAMPLING_INVALID")
            elif do_sample is False and any(
                key in sampling for key in ("temperature", "top_p", "top_k", "min_p")
            ):
                blockers.append(f"{role.upper()}_GREEDY_PROFILE_CONFLICT")
            if "top_k" in sampling and (
                not isinstance(sampling["top_k"], int) or isinstance(sampling["top_k"], bool)
                or sampling["top_k"] < 1
            ):
                blockers.append(f"{role.upper()}_SAMPLING_INVALID")
            if "min_p" in sampling and (
                not isinstance(sampling["min_p"], (int, float)) or isinstance(sampling["min_p"], bool)
                or not math.isfinite(float(sampling["min_p"])) or not 0 <= sampling["min_p"] < 1
            ):
                blockers.append(f"{role.upper()}_SAMPLING_INVALID")
        if role == "A" and (item.get("enable_thinking") is not True or item.get("thinking_mode") != "api_flag"):
            blockers.append("A_THINKING_MODE_UNSET")
        if role == "B" and (item.get("thinking_mode") != "template_default" or item.get("generation_prefix") is not None):
            blockers.append("B_THINKING_MODE_INVALID")
        if role == "challenger" and (
            item.get("thinking_mode") != "explicit_generation_prefix"
            or item.get("generation_prefix") != "<think>"
            or item.get("enable_thinking") is not None
        ):
            blockers.append("CHALLENGER_THINKING_PREFIX_INVALID")
        if role != "A" and item.get("enable_thinking") not in (True, False, None):
            raise ValueError("P4_THINKING_MODE_INVALID")
        template_sha = item.get("chat_template_sha256")
        if not isinstance(template_sha, str) or not SHA256_RE.fullmatch(template_sha):
            blockers.append(f"{role.upper()}_TEMPLATE_HASH_INVALID")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    ready_status = (
        "P4_PROFILE_READY_FOR_RUNTIME_SMOKE"
        if purpose == "runtime_smoke"
        else "P4_PROFILE_READY_FOR_FREEZE_REVIEW" if purpose == "freeze_review"
        else "P4_PROFILE_READY_FOR_OWNER_REVIEW"
    )
    return ProfileAssessment(
        status=ready_status if ready else "P4_PROFILE_INCOMPLETE_HOLD",
        ready=ready,
        model_count=len(models),
        roles=tuple(sorted(models)),
        blockers=tuple(blockers),
    )

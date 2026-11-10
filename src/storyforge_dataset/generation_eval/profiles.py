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
            raise ValueError("P4_MODEL_PROFILE_INVALID")
        if (item.get("model"), item.get("revision")) != expected:
            raise ValueError("P4_MODEL_PIN_MISMATCH")
    return value


def assess_profile(profile: dict[str, Any]) -> ProfileAssessment:
    """Return whether a candidate is fully frozen and explicitly authorized.

    Missing model-specific generation settings are blockers, never guessed or
    inherited from another model. This keeps the profile validator fail-closed.
    """
    if not isinstance(profile, dict) or profile.get("schema") != PROFILE_SCHEMA:
        raise ValueError("P4_PROFILE_SCHEMA_INVALID")
    models = profile.get("model_profiles")
    if not isinstance(models, dict) or set(models) != set(EXPECTED_MODELS):
        raise ValueError("P4_MODEL_SET_INVALID")

    blockers: list[str] = []
    for flag, code in (
        ("profile_freeze_authorized", "PROFILE_FREEZE_NOT_AUTHORIZED"),
        ("inference_authorized", "INFERENCE_NOT_AUTHORIZED"),
        ("gpu_authorized", "GPU_NOT_AUTHORIZED"),
    ):
        if profile.get(flag) is not True:
            blockers.append(code)

    for field, code in (
        ("context_ceiling_tokens", "CONTEXT_CEILING_UNSET"),
        ("input_budget_tokens", "INPUT_BUDGET_UNSET"),
        ("generation_budget_tokens", "GENERATION_BUDGET_UNSET"),
        ("seed", "SEED_UNSET"),
        ("runtime_digest", "RUNTIME_DIGEST_UNSET"),
        ("tokenizer_hashes", "TOKENIZER_HASHES_UNSET"),
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

    tokenizer_hashes = profile.get("tokenizer_hashes")
    if tokenizer_hashes is not None:
        if not isinstance(tokenizer_hashes, dict) or set(tokenizer_hashes) != set(EXPECTED_MODELS):
            blockers.append("TOKENIZER_HASHES_INVALID")
        elif any(not isinstance(value, str) or not SHA256_RE.fullmatch(value)
                 for value in tokenizer_hashes.values()):
            blockers.append("TOKENIZER_HASHES_INVALID")

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
        if role == "A" and item.get("enable_thinking") is not True:
            blockers.append("A_THINKING_MODE_UNSET")
        if role != "A" and item.get("enable_thinking") not in (True, False, None):
            raise ValueError("P4_THINKING_MODE_INVALID")
        template_sha = item.get("chat_template_sha256")
        if not isinstance(template_sha, str) or not SHA256_RE.fullmatch(template_sha):
            blockers.append(f"{role.upper()}_TEMPLATE_HASH_INVALID")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return ProfileAssessment(
        status="P4_PROFILE_READY_FOR_OWNER_REVIEW" if ready else "P4_PROFILE_INCOMPLETE_HOLD",
        ready=ready,
        model_count=len(models),
        roles=tuple(sorted(models)),
        blockers=tuple(blockers),
    )

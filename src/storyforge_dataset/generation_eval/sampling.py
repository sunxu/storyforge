"""Validate the R60 P4 sampling experiment design without loading model runtimes.

This module records an experiment proposal, not a frozen generation profile.
It is deliberately CPU-only and has no network, Transformers, or torch imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "storyforge_r60_sampling_decision_candidate_v1"
EXPECTED_MODELS = {
    "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
    "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
    "challenger": ("zai-org/GLM-Z1-32B-0414", "8eb2858992c1f749e2a6d4075455decc2484722d"),
}
EXPECTED_VARIANTS = {
    "A": {"primary"},
    "B": {"primary", "development_greedy_sensitivity"},
    "challenger": {"primary", "development_sampling_sensitivity"},
}
EXPECTED_SAMPLING = {
    ("A", "primary"): {
        "do_sample": True, "temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0,
    },
    ("B", "primary"): {
        "do_sample": True, "temperature": 1.0, "top_p": 1.0, "top_k": 50,
    },
    ("B", "development_greedy_sensitivity"): {"do_sample": False},
    ("challenger", "primary"): {"do_sample": False},
    ("challenger", "development_sampling_sensitivity"): {
        "do_sample": True, "temperature": 0.6, "top_p": 0.95, "top_k": 40,
    },
}


class SamplingDecisionError(ValueError):
    """A sampling experiment proposal violates the R60 contract."""


@dataclass(frozen=True)
class SamplingAssessment:
    status: str
    ready_for_profile_freeze: bool
    blockers: tuple[str, ...]
    private_values_emitted: bool = False
    inference_started: bool = False
    gpu_started: bool = False
    training_started: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "schema": "storyforge_r60_sampling_decision_assessment_safe_v1",
            "status": self.status,
            "ready_for_profile_freeze": self.ready_for_profile_freeze,
            "blockers": list(self.blockers),
            "private_values_emitted": False,
            "inference_started": False,
            "gpu_started": False,
            "training_started": False,
        }


def assess_sampling_decision(document: dict[str, Any]) -> SamplingAssessment:
    """Validate exact model pins, sampling variants and development-only tuning."""
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise SamplingDecisionError("SAMPLING_DECISION_SCHEMA_INVALID")
    if document.get("status") != "OWNER_ACCEPTED_EXPERIMENT_DESIGN__PROFILE_NOT_FROZEN":
        raise SamplingDecisionError("SAMPLING_DECISION_STATUS_INVALID")

    models = document.get("model_profiles")
    if not isinstance(models, dict) or set(models) != set(EXPECTED_MODELS):
        raise SamplingDecisionError("SAMPLING_MODEL_SET_INVALID")

    controls = document.get("execution_controls")
    if not isinstance(controls, dict):
        raise SamplingDecisionError("SAMPLING_EXECUTION_CONTROLS_INVALID")

    blockers: list[str] = []
    for role, expected_pin in EXPECTED_MODELS.items():
        model = models[role]
        if not isinstance(model, dict):
            raise SamplingDecisionError("SAMPLING_MODEL_PROFILE_INVALID")
        if (model.get("model"), model.get("revision")) != expected_pin:
            blockers.append(f"{role.upper()}_MODEL_PIN_MISMATCH")
        variants = model.get("variants")
        if not isinstance(variants, dict) or set(variants) != EXPECTED_VARIANTS[role]:
            blockers.append(f"{role.upper()}_VARIANT_SET_INVALID")
            continue
        for name, variant in variants.items():
            if not isinstance(variant, dict):
                blockers.append(f"{role.upper()}_VARIANT_INVALID")
                continue
            expected_split = "development20" if name != "primary" else "p4_locked30"
            if variant.get("evaluation_split") != expected_split:
                blockers.append(f"{role.upper()}_VARIANT_SPLIT_INVALID")
            if variant.get("sampling") != EXPECTED_SAMPLING[(role, name)]:
                blockers.append(f"{role.upper()}_SAMPLING_POLICY_MISMATCH")

    for flag in ("profile_freeze_authorized", "inference_authorized", "gpu_authorized"):
        if document.get(flag) is not False:
            blockers.append(f"{flag.upper()}_MUST_REMAIN_FALSE")
    if document.get("training_authorized") is not False:
        blockers.append("TRAINING_AUTHORIZATION_MUST_REMAIN_FALSE")
    if controls.get("development_only_tuning") is not True:
        blockers.append("DEVELOPMENT_ONLY_TUNING_REQUIRED")
    if controls.get("locked_reference_accessed") is not False:
        blockers.append("LOCKED_REFERENCE_ACCESS_FORBIDDEN")
    if controls.get("seed") != 42:
        blockers.append("BASE_SEED_MISMATCH")
    if (
        controls.get("context_ceiling_tokens") != 32768
        or controls.get("input_budget_tokens") != 28672
        or controls.get("generation_budget_tokens") != 4096
    ):
        blockers.append("TOKEN_BUDGET_CONTRACT_MISMATCH")

    blockers = list(dict.fromkeys(blockers))
    return SamplingAssessment(
        status="SAMPLING_DECISION_VALID__PROFILE_FREEZE_PENDING" if not blockers
        else "SAMPLING_DECISION_HOLD",
        ready_for_profile_freeze=False,
        blockers=tuple(blockers),
    )

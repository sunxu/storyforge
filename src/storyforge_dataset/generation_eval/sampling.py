"""Validate the R60 P4 sampling experiment design without loading model runtimes.

This module records an experiment proposal, not a frozen generation profile.
It is deliberately CPU-only and has no network, Transformers, or torch imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "storyforge_r60_sampling_decision_candidate_v1"
ROLES = frozenset({"A", "B", "challenger"})
EXPECTED_VARIANTS = {
    "A": {"primary"},
    "B": {"primary", "development_greedy_sensitivity"},
    "challenger": {"primary", "development_sampling_sensitivity"},
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
    """Validate role coverage, model pins, modes and development-only variants."""
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise SamplingDecisionError("SAMPLING_DECISION_SCHEMA_INVALID")
    if document.get("status") != "OWNER_ACCEPTED_EXPERIMENT_DESIGN__PROFILE_NOT_FROZEN":
        raise SamplingDecisionError("SAMPLING_DECISION_STATUS_INVALID")

    models = document.get("model_profiles")
    if not isinstance(models, dict) or set(models) != ROLES:
        raise SamplingDecisionError("SAMPLING_MODEL_SET_INVALID")

    blockers: list[str] = []
    for role in ("A", "B", "challenger"):
        model = models[role]
        if not isinstance(model, dict):
            raise SamplingDecisionError("SAMPLING_MODEL_PROFILE_INVALID")
        if not isinstance(model.get("model"), str) or not isinstance(model.get("revision"), str):
            blockers.append(f"{role.upper()}_MODEL_PIN_MISSING")
        variants = model.get("variants")
        if not isinstance(variants, dict) or set(variants) != EXPECTED_VARIANTS[role]:
            blockers.append(f"{role.upper()}_VARIANT_SET_INVALID")
            continue
        for name, variant in variants.items():
            if not isinstance(variant, dict):
                blockers.append(f"{role.upper()}_VARIANT_INVALID")
                continue
            if variant.get("evaluation_split") != (
                "development20" if name != "primary" else "p4_locked30"
            ):
                blockers.append(f"{role.upper()}_VARIANT_SPLIT_INVALID")
            sampling = variant.get("sampling")
            if not isinstance(sampling, dict) or not isinstance(sampling.get("do_sample"), bool):
                blockers.append(f"{role.upper()}_SAMPLING_INVALID")
                continue
            do_sample = sampling["do_sample"]
            if do_sample:
                for key in ("temperature", "top_p"):
                    value = sampling.get(key)
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        blockers.append(f"{role.upper()}_SAMPLING_INVALID")
                        break
                else:
                    if sampling["temperature"] <= 0 or not 0 < sampling["top_p"] <= 1:
                        blockers.append(f"{role.upper()}_SAMPLING_INVALID")
                if "top_k" in sampling and (
                    not isinstance(sampling["top_k"], int)
                    or isinstance(sampling["top_k"], bool)
                    or sampling["top_k"] < 1
                ):
                    blockers.append(f"{role.upper()}_SAMPLING_INVALID")
                if "min_p" in sampling and (
                    not isinstance(sampling["min_p"], (int, float))
                    or isinstance(sampling["min_p"], bool)
                    or not 0 <= sampling["min_p"] < 1
                ):
                    blockers.append(f"{role.upper()}_SAMPLING_INVALID")
            elif set(sampling) != {"do_sample"}:
                blockers.append(f"{role.upper()}_GREEDY_PROFILE_CONFLICT")

    for flag in ("profile_freeze_authorized", "inference_authorized", "gpu_authorized"):
        if document.get(flag) is not False:
            blockers.append(f"{flag.upper()}_MUST_REMAIN_FALSE")
    if document.get("training_authorized") is not False:
        blockers.append("TRAINING_AUTHORIZATION_MUST_REMAIN_FALSE")
    if document.get("development_only_tuning") is not True:
        blockers.append("DEVELOPMENT_ONLY_TUNING_REQUIRED")
    if document.get("locked_reference_accessed") is not False:
        blockers.append("LOCKED_REFERENCE_ACCESS_FORBIDDEN")

    blockers = list(dict.fromkeys(blockers))
    return SamplingAssessment(
        status="SAMPLING_DECISION_VALID__PROFILE_FREEZE_PENDING" if not blockers
        else "SAMPLING_DECISION_HOLD",
        ready_for_profile_freeze=False,
        blockers=tuple(blockers),
    )

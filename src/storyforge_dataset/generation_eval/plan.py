"""CPU-only, plan-only Hugging Face generation Job planning.

No network client, subprocess, model library, or Job submission is imported here.
The returned argv is an internal plan; SAFE serialization excludes mount paths.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Sequence

from .profiles import ProfileAssessment, assess_profile

BUCKET_PREFIX = "hf://buckets/adradar/storyforge-training/"
GPU_FLAVORS = frozenset({"a100-large", "h200", "rtx-pro-6000"})
IMAGE_DIGEST = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ROLES = frozenset({"A", "B", "challenger"})


class PlanError(ValueError):
    """A proposed generation Job violates the P4 plan-only contract."""


@dataclass(frozen=True)
class GenerationJobPlan:
    status: str
    plan_id: str | None
    role: str
    flavor: str
    timeout_minutes: int
    dataset_count: int
    dataset_sha256: str
    profile_status: str
    blockers: tuple[str, ...]
    argv: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "schema": "storyforge_r60_generation_job_plan_safe_v1",
            "status": self.status,
            "plan_id": self.plan_id,
            "model_role": self.role,
            "flavor": self.flavor,
            "timeout_minutes": self.timeout_minutes,
            "dataset_count": self.dataset_count,
            "dataset_sha256": self.dataset_sha256,
            "profile_status": self.profile_status,
            "blockers": list(self.blockers),
            "job_submitted": False,
            "inference_started": False,
            "gpu_started": False,
            "training_started": False,
            "private_values_emitted": False,
        }


def _volume(value: str, *, mode: str, destination: str) -> str:
    if not isinstance(value, str):
        raise PlanError("VOLUME_INVALID")
    try:
        source, mount, actual_mode = value.rsplit(":", 2)
    except ValueError as exc:
        raise PlanError("VOLUME_INVALID") from exc
    if not source.startswith(BUCKET_PREFIX):
        raise PlanError("VOLUME_OUTSIDE_PROJECT_BUCKET")
    relative = source[len(BUCKET_PREFIX):]
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise PlanError("VOLUME_SOURCE_PATH_INVALID")
    if mount != destination or actual_mode != mode:
        raise PlanError("VOLUME_MODE_OR_DESTINATION_INVALID")
    return source


def build_generation_plan(
    *,
    profile: dict[str, Any],
    model_role: str,
    dataset_manifest: dict[str, Any],
    namespace: str,
    flavor: str,
    timeout_minutes: int,
    image: str,
    input_volume: str,
    output_volume: str,
    output_subdir: str,
    code_revision: str,
) -> GenerationJobPlan:
    """Build a deterministic, non-submitting single-model Job plan."""
    assessment: ProfileAssessment = assess_profile(profile)
    blockers = list(assessment.blockers)

    if model_role not in ROLES or model_role not in profile.get("model_profiles", {}):
        raise PlanError("MODEL_ROLE_INVALID")
    if namespace != "adradar":
        raise PlanError("NAMESPACE_MUST_BE_ADRADAR")
    if flavor not in GPU_FLAVORS:
        raise PlanError("GPU_FLAVOR_NOT_IN_ALLOWLIST")
    if not isinstance(timeout_minutes, int) or isinstance(timeout_minutes, bool) or not 1 <= timeout_minutes <= 60:
        raise PlanError("GPU_TIMEOUT_OUT_OF_RANGE")
    if not isinstance(image, str) or not IMAGE_DIGEST.fullmatch(image):
        raise PlanError("IMAGE_MUST_BE_PINNED_BY_SHA256")
    if not isinstance(code_revision, str) or not SHA256.fullmatch(code_revision):
        raise PlanError("CODE_REVISION_MUST_BE_COMMIT_SHA")
    if not isinstance(output_subdir, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", output_subdir):
        raise PlanError("OUTPUT_SUBDIR_INVALID")

    if not isinstance(dataset_manifest, dict):
        raise PlanError("DATASET_MANIFEST_INVALID")
    if dataset_manifest.get("schema") != "storyforge_r60_generation_input_manifest_v1":
        raise PlanError("DATASET_MANIFEST_SCHEMA_INVALID")
    count = dataset_manifest.get("record_count")
    digest = dataset_manifest.get("sha256")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise PlanError("DATASET_RECORD_COUNT_INVALID")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise PlanError("DATASET_SHA256_INVALID")

    input_source = _volume(input_volume, mode="ro", destination="/input")
    output_source = _volume(output_volume, mode="rw", destination="/output")
    if input_source == output_source or input_source.startswith(output_source + "/") or output_source.startswith(input_source + "/"):
        raise PlanError("INPUT_OUTPUT_SOURCE_COLLISION")

    if not assessment.ready:
        return GenerationJobPlan(
            status="P4_JOB_PLAN_HOLD",
            plan_id=None,
            role=model_role,
            flavor=flavor,
            timeout_minutes=timeout_minutes,
            dataset_count=count,
            dataset_sha256=digest,
            profile_status=assessment.status,
            blockers=tuple(blockers),
        )

    model = profile["model_profiles"][model_role]
    plan_identity = {
        "schema": "storyforge_r60_generation_job_plan_v1",
        "role": model_role,
        "model_revision": model["revision"],
        "dataset_sha256": digest,
        "count": count,
        "flavor": flavor,
        "timeout_minutes": timeout_minutes,
        "image": image,
        "code_revision": code_revision,
        "output_subdir": output_subdir,
    }
    plan_id = hashlib.sha256(
        json.dumps(plan_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    command: Sequence[str] = (
        "python", "-m", "storyforge_dataset.generation_eval.worker",
        "--model-role", model_role,
        "--profile", "/input/generation-profile.json",
        "--manifest", "/input/manifest.json",
        "--output-dir", f"/output/{output_subdir}",
    )
    argv = (
        "hf", "jobs", "run",
        "--namespace", namespace,
        "--name", f"r60-p4-{model_role.lower()}-{plan_id[:10]}",
        "--flavor", flavor,
        "--timeout", f"{timeout_minutes}m",
        "--attempts", "1",
        "--detach",
        "-v", input_volume,
        "-v", output_volume,
        image, "--", *command,
    )
    return GenerationJobPlan(
        status="P4_JOB_PLAN_READY_NOT_SUBMITTED",
        plan_id=plan_id,
        role=model_role,
        flavor=flavor,
        timeout_minutes=timeout_minutes,
        dataset_count=count,
        dataset_sha256=digest,
        profile_status=assessment.status,
        blockers=(),
        argv=tuple(argv),
    )

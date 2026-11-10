from storyforge_dataset.generation_eval.plan import (
    PlanError,
    build_generation_plan,
)
from storyforge_dataset.generation_eval.profiles import EXPECTED_MODELS

from test_generation_eval_profiles import candidate_profile


def ready_profile():
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
    return profile


def plan_args(profile):
    return {
        "profile": profile,
        "model_role": "A",
        "dataset_manifest": {
            "schema": "storyforge_r60_generation_input_manifest_v1",
            "record_count": 90,
            "sha256": "d" * 64,
        },
        "namespace": "adradar",
        "flavor": "a100-large",
        "timeout_minutes": 30,
        "image": "python:3.11@sha256:" + "e" * 64,
        "input_volume": "hf://buckets/adradar/storyforge-training/p4/input:/input:ro",
        "output_volume": "hf://buckets/adradar/storyforge-training/p4/output:/output:rw",
        "output_subdir": "smoke-001",
        "code_revision": "f" * 40,
    }


def test_incomplete_p3_profile_holds_plan_and_never_submits():
    profile = candidate_profile()
    plan = build_generation_plan(**plan_args(profile))
    safe = plan.to_safe_dict()
    assert plan.status == "P4_JOB_PLAN_HOLD"
    assert plan.argv == ()
    assert safe["job_submitted"] is False
    assert safe["gpu_started"] is False
    assert "GPU_NOT_AUTHORIZED" in safe["blockers"]


def test_frozen_profile_builds_deterministic_plan_only():
    first = build_generation_plan(**plan_args(ready_profile()))
    second = build_generation_plan(**plan_args(ready_profile()))
    assert first.status == "P4_JOB_PLAN_READY_NOT_SUBMITTED"
    assert first.plan_id == second.plan_id
    assert first.argv[0:3] == ("hf", "jobs", "run")
    assert "--attempts" in first.argv
    assert first.argv[first.argv.index("--attempts") + 1] == "1"
    assert first.to_safe_dict()["job_submitted"] is False


def test_plan_rejects_personal_namespace_and_nonallowlisted_gpu():
    args = plan_args(ready_profile())
    args["namespace"] = "personal-user"
    try:
        build_generation_plan(**args)
    except PlanError as exc:
        assert str(exc) == "NAMESPACE_MUST_BE_ADRADAR"
    else:
        raise AssertionError("personal namespace must be rejected")


def test_plan_rejects_mutable_image_and_overlapping_mounts():
    args = plan_args(ready_profile())
    args["image"] = "python:3.11"
    try:
        build_generation_plan(**args)
    except PlanError as exc:
        assert str(exc) == "IMAGE_MUST_BE_PINNED_BY_SHA256"
    else:
        raise AssertionError("mutable image must be rejected")

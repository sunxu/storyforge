import base64

from storyforge_dataset.generation_eval.plan import (
    PlanError,
    build_generation_plan,
)
from storyforge_dataset.generation_eval.profiles import EXPECTED_MODELS


def ready_profile():
    models = {}
    for role, (model, revision) in EXPECTED_MODELS.items():
        models[role] = {
            "model": model,
            "revision": revision,
            "enable_thinking": True if role == "A" else None,
            "thinking_mode": "api_flag" if role == "A" else ("template_default" if role == "B" else "explicit_generation_prefix"),
            "generation_prefix": "<think>" if role == "challenger" else None,
            "sampling": {"do_sample": True, "temperature": 0.7, "top_p": 0.9},
            "chat_template_sha256": "a" * 64,
        }
    return {
        "schema": "storyforge_r60_p3_model_profiles_v1",
        "model_profiles": models,
        "context_ceiling_tokens": 32768,
        "input_budget_tokens": 28672,
        "generation_budget_tokens": 4096,
        "seed": 20261110,
        "runtime_digest": "sha256:" + "e" * 64,
        "dependency_lock_sha256": "d" * 64,
        "evaluation_prompt_sha256": "e" * 64,
        "output_schema_sha256": "f" * 64,
        "p3_download_safe_sha256": "a" * 64,
        "tokenizer_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "tokenizer_file_hashes": {"A":{"config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","generation_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","merges.txt":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","vocab.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"B":{"chat_template.jinja":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","generation_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","special_tokens_map.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"challenger":{"chat_template.jinja":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","generation_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","special_tokens_map.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}},
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
        "profile_freeze_authorized": True,
        "inference_authorized": True,
        "gpu_authorized": True,
        "training_authorized": False,
    }


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
    profile = ready_profile()
    profile["profile_freeze_authorized"] = False
    plan = build_generation_plan(**plan_args(profile))
    safe = plan.to_safe_dict()
    assert plan.status == "P4_JOB_PLAN_HOLD"
    assert plan.argv == ()
    assert safe["job_submitted"] is False
    assert safe["gpu_started"] is False
    assert "PROFILE_FREEZE_NOT_AUTHORIZED" in safe["blockers"]


def test_frozen_profile_builds_deterministic_plan_only():
    first = build_generation_plan(**plan_args(ready_profile()))
    second = build_generation_plan(**plan_args(ready_profile()))
    assert first.status == "P4_JOB_PLAN_READY_NOT_SUBMITTED"
    assert first.plan_id == second.plan_id
    assert first.argv[0:3] == ("hf", "jobs", "run")
    assert first.argv[-3] == "bash"
    shell = first.argv[first.argv.index("bash") + 2]
    encoded_script = shell.split("base64.b64decode('", 1)[1].split("')", 1)[0]
    archive_script = base64.b64decode(encoded_script).decode("utf-8")
    assert "codeload.github.com/sunxu/storyforge/tar.gz/" + ("f" * 40) in archive_script
    assert "SOURCE_ARCHIVE_PATH_INVALID" in archive_script
    assert "--input /input/inputs.jsonl" in shell
    assert "storyforge_dataset.generation_eval.worker_cli" in shell
    assert "pip install --disable-pip-version-check --require-hashes" in shell
    assert "hf-generation-eval.lock" in shell
    assert "--repo-root /workspace/storyforge" in shell
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

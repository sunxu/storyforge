"""Fail-closed, CPU-only gate for the three Owner-calibrated synthetic 32K inputs.

This gate executes before GPU imports and model-weight downloads.
It only accepts exact, pinned synthetic input bytes and an unchanged Frozen Profile.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager
from .profiles import assess_profile, load_profile
from .worker import WorkerError
from .synthetic_32k import FROZEN_SHA256, SYNTHETIC_SENTENCE

CALIBRATED_SHA256 = {
    "A": "a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398",
    "B": "8cb8ddf2fc511cf957ed03510853dad94b5169334fde8d6ff153afda6640285e",
    "challenger": "2676b44c9e0e6ea1c8ccc1824e246d20c08fd8b7cf789a669e3bd06a1f91c28c",
}
EXPECTED_INPUT_TOKENS = {"A": 28568, "B": 28593, "challenger": 28597}
AUTH_SCHEMA = "storyforge_r60_p4_staged_execution_authorization_v1"


def _is_exact_synthetic_text(content: str) -> bool:
    prefix = ("请确认你正在处理一次人工生成的长上下文运行时测试，"
              "请简洁概括下文重复结构，不要猜测真实人物或故事。\n")
    suffix = "\n结束。请输出一句简短中文确认。"
    if not content.startswith(prefix) or not content.endswith(suffix):
        return False
    middle = content[len(prefix):-len(suffix)]
    return bool(middle) and len(middle) % len(SYNTHETIC_SENTENCE) == 0 and (
        middle == SYNTHETIC_SENTENCE * (len(middle) // len(SYNTHETIC_SENTENCE))
    )


def authorize_synthetic_profile(
    *,
    frozen_path: Path,
    authorization_path: Path,
    manifest_path: Path,
    input_path: Path,
    model_role: str,
) -> dict[str, Any]:
    """Return an in-memory scoped profile; never modify the immutable Frozen JSON."""
    if model_role not in CALIBRATED_SHA256:
        raise WorkerError("SYNTHETIC_MODEL_ROLE_NOT_ALLOWED")
    try:
        InputManager.open_verified(
            frozen_path, max_bytes=2 * 1024 * 1024, expected_sha256=FROZEN_SHA256
        ).read_bytes()
        frozen = load_profile(frozen_path)
        auth_data = InputManager.open_verified(
            authorization_path, max_bytes=1024 * 1024
        ).read_bytes()
        auth = json.loads(auth_data)
        manifest = json.loads(InputManager.open_verified(
            manifest_path, max_bytes=1024 * 1024
        ).read_bytes())
        data = InputManager.open_verified(
            input_path, max_bytes=16 * 1024 * 1024,
            expected_sha256=CALIBRATED_SHA256[model_role],
        ).read_bytes()
        records = InputManager.validate_jsonl(data, max_records=1)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise WorkerError("SYNTHETIC_INPUT_VERIFICATION_FAILED") from exc

    scope = auth.get("stages", {}).get("synthetic_32k", {})
    denied = auth.get("denied", {})
    if not (
        auth.get("schema") == AUTH_SCHEMA
        and auth.get("frozen_profile_sha256") == FROZEN_SHA256
        and scope.get("owner_authorized") is True
        and scope.get("input_type") == "synthetic_only"
        and scope.get("roles") == ["A", "B", "challenger"]
        and scope.get("batch_size") == 1
        and scope.get("input_budget_tokens") == 28672
        and scope.get("output_budget_tokens") == 4096
        and scope.get("context_ceiling_tokens") == 32768
        and scope.get("max_attempts_per_job") == 1
        and scope.get("max_job_minutes") == 60
        and scope.get("flavor") == "h200"
        and scope.get("require_owner_mac_cli") is True
        and denied.get("training_authorized") is False
        and denied.get("chatgpt_hf_job_submission_authorized") is False
        and denied.get("auto_retry_authorized") is False
        and frozen.get("profile_freeze_authorized") is True
        and frozen.get("gpu_authorized") is False
        and frozen.get("inference_authorized") is False
        and frozen.get("training_authorized") is False
        and frozen.get("runtime_smoke_authorized") is False
    ):
        raise WorkerError("SYNTHETIC_AUTHORIZATION_SCOPE_INVALID")
    if not (
        isinstance(manifest, dict)
        and set(manifest) == {
            "schema", "record_count", "sha256", "max_input_tokens",
            "max_new_tokens", "seed",
        }
        and manifest["schema"] == "storyforge_r60_generation_input_manifest_v1"
        and manifest["record_count"] == 1
        and manifest["sha256"] == CALIBRATED_SHA256[model_role]
        and manifest["max_input_tokens"] == 28672
        and manifest["max_new_tokens"] == 4096
        and manifest["seed"] == frozen["seed"]
        and isinstance(records, list) and len(records) == 1
        and isinstance(records[0], dict)
        and set(records[0]) == {"sample_id", "messages"}
        and records[0]["sample_id"] == f"r60-synthetic-32k-{model_role.lower()}"
        and isinstance(records[0]["messages"], list)
        and len(records[0]["messages"]) == 1
        and records[0]["messages"][0].get("role") == "user"
        and set(records[0]["messages"][0]) == {"role", "content"}
        and isinstance(records[0]["messages"][0]["content"], str)
        and _is_exact_synthetic_text(records[0]["messages"][0]["content"])
    ):
        raise WorkerError("SYNTHETIC_INPUT_SCOPE_INVALID")

    # No execution authorization can be transferred back to the stored Frozen file.
    derived = dict(frozen)
    derived["inference_authorized"] = True
    derived["gpu_authorized"] = True
    derived["training_authorized"] = False
    derived["synthetic_only_runtime_scope"] = {
        "role": model_role,
        "sha256": CALIBRATED_SHA256[model_role],
        "input_tokens_cpu_calibrated": EXPECTED_INPUT_TOKENS[model_role],
    }
    if not assess_profile(derived).ready:
        raise WorkerError("SYNTHETIC_DERIVED_PROFILE_NOT_READY")
    return derived

"""Gold48-specific CPU contract bridge to the unchanged generation loop.

No GPU libraries, adapter weights, historical original answers, or R50 sealed
sources are read. The frozen four-arm profile is NEVER recast as the legacy P4
schema. Owner approval is a separate, explicitly scoped private runtime input.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager

from .gold48_qwen35_loader import ADAPTER_SIZE, EOS_IDS, MODEL, PAD_ID, REVISION
from .worker import (
    GenerationBackend,
    WorkerError,
    WorkerReceipt,
    _run_validated_generation_batch,
    _validate_records,
)

PROFILE_SCHEMA = "storyforge_r60_gold48_four_arm_generation_profile_frozen_v1"
OWNER_SCHEMA = "storyforge_r60_gold48_owner_scoped_freeze_private_v1"
BINDINGS_SCHEMA = "storyforge_r60_gold48_adapter_bindings_private_v1"
INPUT_SCHEMA = "storyforge_r60_gold48_generation_input_manifest_private_v1"
APPROVAL_SCHEMA = "storyforge_r60_gold48_generation_owner_authorization_private_v1"
ROLES = ("base", "r46_v02", "r54_v03a", "r60_base336")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
CASE_COUNT = 48
SAMPLING = {
    "do_sample": True, "temperature": 0.7,
    "top_p": 0.8, "top_k": 20, "min_p": 0,
}
# This mapping contains NO private SHA values or local paths.
PROVENANCE = {
    "r46_v02": "HISTORICAL_SHA_PROVENANCE_PASS",
    "r54_v03a": "HISTORICAL_SHA_PROVENANCE_PASS",
    "r60_base336": "CPU_BYTE_SHA_COMPUTED_PASS__PROVIDER_MOUNT_UNVERIFIED",
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise WorkerError(code)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def read_private_contract(path: Path, *, max_bytes: int = 2 * 1024 * 1024) -> dict[str, Any]:
    """Use the existing no-follow bounded input reader, require owner-only mode."""
    import stat
    try:
        st = path.lstat()
        _require(stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600,
                 "GOLD48_PRIVATE_CONTRACT_MODE_HOLD")
        obj = json.loads(InputManager.open_verified(path, max_bytes=max_bytes).read_bytes())
        _require(isinstance(obj, dict), "GOLD48_PRIVATE_CONTRACT_SCHEMA_HOLD")
        return obj
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_PRIVATE_CONTRACT_READ_HOLD") from exc


def _validate_frozen(frozen: dict[str, Any], owner: dict[str, Any]) -> list[dict[str, Any]]:
    _require(isinstance(frozen, dict) and frozen.get("schema") == PROFILE_SCHEMA
             and frozen.get("owner_generation_profile_freeze") is True
             and frozen.get("status") == "GOLD48_FOUR_ARM_PROFILE_FROZEN__RUNTIME_VALIDATION_PENDING"
             and frozen.get("inference_authorized") is False
             and frozen.get("gpu_authorized_by_this_document") is False
             and frozen.get("training_authorized") is False
             and frozen.get("model_generation_started") is False,
             "GOLD48_FROZEN_PROFILE_INVALID")
    base = frozen.get("base_model")
    generation = frozen.get("generation")
    arms = frozen.get("arms")
    _require(isinstance(base, dict) and base.get("model") == MODEL
             and base.get("revision") == REVISION
             and base.get("model_type") == "qwen3_5"
             and base.get("architecture") == "Qwen3_5ForConditionalGeneration"
             and base.get("eos_token_ids") == list(EOS_IDS)
             and base.get("pad_token_id") == PAD_ID
             and base.get("tokenizer_revision") == REVISION
             and base.get("generation_config_revision") == REVISION,
             "GOLD48_BASE_PIN_HOLD")
    _require(isinstance(generation, dict)
             and generation.get("enable_thinking") is False
             and generation.get("thinking_mode") == "disabled"
             and generation.get("chat_template_args") == {
                 "enable_thinking": False, "add_generation_prompt": True}
             and generation.get("context_ceiling_tokens") == 32768
             and generation.get("max_input_tokens") == 30720
             and generation.get("max_new_tokens") == 2048
             and generation.get("prompt_truncation") == "FORBIDDEN"
             and generation.get("overflow_action") == "HOLD_NO_OUTPUT"
             and generation.get("sampling") == SAMPLING
             and generation.get("seed_base") == 42
             and generation.get("per_case_seed") ==
                 "seed_base + fixed_frozen_case_index_zero_based"
             and generation.get("custom_stop_sequences") == []
             and generation.get("stop_rule") ==
                 "EOS_TOKEN_IDS_FROM_PINNED_BASE_GENERATION_CONFIG"
             and generation.get("same_generation_config_all_four_arms") is True,
             "GOLD48_GENERATION_PIN_HOLD")
    _require(isinstance(arms, dict) and set(arms) == set(ROLES),
             "GOLD48_FOUR_ARM_SET_HOLD")
    for role in ROLES:
        arm = arms[role]
        _require(isinstance(arm, dict) and arm.get("role") == role
                 and arm.get("model") == MODEL
                 and arm.get("base_revision") == REVISION
                 and arm.get("enable_thinking") is False
                 and arm.get("sampling") == SAMPLING
                 and arm.get("adapter_kind") ==
                     ("NONE" if role == "base" else "PEFT_LORA")
                 and arm.get("adapter_checkpoint_dir_immutable") is True
                 and (arm.get("adapter_checkpoint") is None if role == "base"
                      else isinstance(arm.get("adapter_checkpoint"), str)
                      and arm["adapter_checkpoint"].startswith("hf://buckets/adradar/storyforge-training/"))
                 and arm.get("adapter_sha256_from_existing_private_release_receipt_required")
                     is (role != "base"),
                 "GOLD48_ARM_IDENTITY_HOLD")
    _require(isinstance(owner, dict) and owner.get("schema") == OWNER_SCHEMA
             and owner.get("status") == "GOLD48_FROZEN_SCOPED__GENERATION_PROFILE_PENDING"
             and owner.get("owner_gold48_freeze") is True
             and owner.get("input_contract") == "RECONSTRUCTED_EVALUATION_INPUT"
             and owner.get("model_generation_authorized") is False
             and owner.get("gpu_authorized_by_this_freeze") is False
             and owner.get("training_authorized_by_this_freeze") is False
             and owner.get("run_key") == frozen.get("dataset", {}).get("run_key"),
             "GOLD48_OWNER_FREEZE_HOLD")
    cases = owner.get("cases_PRIVATE")
    _require(isinstance(cases, list) and len(cases) == CASE_COUNT
             and all(
                 isinstance(case, dict)
                 and case.get("candidate_case_id_PRIVATE") == f"G48-C{i:02d}"
                 and _sha(case.get("reconstructed_messages_sha256_PRIVATE"))
                 for i, case in enumerate(cases, 1)
             ), "GOLD48_OWNER_CASES_HOLD")
    return cases


def _validate_bindings(frozen: dict[str, Any], bindings: dict[str, Any]) -> None:
    _require(isinstance(bindings, dict)
             and bindings.get("schema") == BINDINGS_SCHEMA
             and bindings.get("run_key") == frozen["dataset"]["run_key"]
             and set(bindings.get("arms", {})) == set(ROLES),
             "GOLD48_ADAPTER_BINDING_SCHEMA_HOLD")
    for role in ROLES:
        entry = bindings["arms"][role]
        arm = frozen["arms"][role]
        _require(isinstance(entry, dict)
                 and entry.get("checkpoint_uri") == arm["adapter_checkpoint"]
                 and entry.get("weight_file_name") ==
                     (None if role == "base" else "adapter_model.safetensors"),
                 "GOLD48_ADAPTER_BINDING_IDENTITY_HOLD")
        if role == "base":
            _require(entry.get("expected_sha256") is None
                     and entry.get("local_dir") is None
                     and entry.get("provenance") == "BASE_NO_ADAPTER",
                     "GOLD48_BASE_BINDING_HOLD")
        else:
            _require(_sha(entry.get("expected_sha256"))
                     and entry.get("provenance") == PROVENANCE[role]
                     and _sha(entry.get("source_evidence_sha256"))
                     and isinstance(entry.get("local_dir"), str)
                     and Path(entry["local_dir"]).is_absolute()
                     and not any(p in (".", "..") for p in Path(entry["local_dir"]).parts)
                     and entry.get("expected_weight_size_bytes") == ADAPTER_SIZE,
                     "GOLD48_ADAPTER_BINDING_UNTRUSTED_HOLD")


def prepare_gold48_generation_contract(
    *,
    frozen: dict[str, Any],
    owner_freeze: dict[str, Any],
    adapter_bindings: dict[str, Any],
    input_manifest: dict[str, Any],
    input_path: Path,
    model_role: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """CPU-only: exact Owner case hashes, order, base/arm/budget/seed/stop pins."""
    _require(model_role in ROLES, "GOLD48_MODEL_ROLE_HOLD")
    cases = _validate_frozen(frozen, owner_freeze)
    _validate_bindings(frozen, adapter_bindings)
    g = frozen["generation"]
    _require(isinstance(input_manifest, dict)
             and input_manifest.get("schema") == INPUT_SCHEMA
             and input_manifest.get("run_key") == frozen["dataset"]["run_key"]
             and input_manifest.get("record_count") == CASE_COUNT
             and input_manifest.get("max_input_tokens") == g["max_input_tokens"]
             and input_manifest.get("max_new_tokens") == g["max_new_tokens"]
             and input_manifest.get("seed") == g["seed_base"]
             and _sha(input_manifest.get("sha256")),
             "GOLD48_INPUT_MANIFEST_HOLD")
    descriptors = input_manifest.get("cases")
    _require(isinstance(descriptors, list) and len(descriptors) == CASE_COUNT
             and all(
                 isinstance(x, dict)
                 and set(x) == {"sample_id", "messages_sha256"}
                 and x["sample_id"] == case["candidate_case_id_PRIVATE"]
                 and x["messages_sha256"] == case["reconstructed_messages_sha256_PRIVATE"]
                 for x, case in zip(descriptors, cases)
             ), "GOLD48_FROZEN_CASE_SHA_BINDING_HOLD")
    try:
        verified = InputManager.open_verified(
            input_path, max_bytes=16 * 1024 * 1024,
            expected_sha256=input_manifest["sha256"],
        )
        records = InputManager.validate_jsonl(verified.read_bytes(), max_records=CASE_COUNT)
    except (OSError, TypeError, ValueError) as exc:
        raise WorkerError("GOLD48_INPUT_FILE_SHA_HOLD") from exc
    _validate_records(records, CASE_COUNT)
    for record, descriptor in zip(records, descriptors):
        _require(record["sample_id"] == descriptor["sample_id"]
                 and _digest(record["messages"]) == descriptor["messages_sha256"],
                 "GOLD48_PER_CASE_INPUT_SHA_HOLD")
    normalized = {
        # Not a P4 profile: the bridge never invokes assess_profile().
        "schema": "storyforge_r60_gold48_worker_contract_v1",
        "input_budget_tokens": 30720,
        "generation_budget_tokens": 2048,
        "seed": 42,
        "model_profiles": {
            role: {
                "model": frozen["arms"][role]["model"],
                "revision": frozen["arms"][role]["base_revision"],
                "sampling": dict(frozen["arms"][role]["sampling"]),
                "enable_thinking": False,
                "generation_prefix": None,
            }
            for role in ROLES
        },
        "eos_token_ids": {role: list(EOS_IDS) for role in ROLES},
        "pad_token_ids": {role: PAD_ID for role in ROLES},
    }
    worker_manifest = {
        "schema": "storyforge_r60_generation_input_manifest_v1",
        "record_count": CASE_COUNT,
        "sha256": input_manifest["sha256"],
        "max_input_tokens": 30720,
        "max_new_tokens": 2048,
        "seed": 42,
    }
    return normalized, worker_manifest


def _approve_generation(
    *,
    approval: dict[str, Any] | None,
    frozen: dict[str, Any],
    bindings: dict[str, Any],
    manifest: dict[str, Any],
    model_role: str,
) -> None:
    _require(isinstance(approval, dict)
             and approval.get("schema") == APPROVAL_SCHEMA
             and approval.get("status") == "OWNER_APPROVED_GOLD48_GENERATION"
             and approval.get("scope") == "GOLD48_FOUR_ARM_192_GENERATIONS"
             and approval.get("run_key") == frozen["dataset"]["run_key"]
             and approval.get("model_role") == model_role
             and approval.get("frozen_profile_canonical_sha256") == _digest(frozen)
             and approval.get("adapter_bindings_canonical_sha256") == _digest(bindings)
             and approval.get("input_sha256") == manifest["sha256"]
             and approval.get("inference_authorized") is True
             and approval.get("gpu_authorized") is True
             and approval.get("training_authorized") is False,
             "GOLD48_SEPARATE_OWNER_INFERENCE_AUTHORIZATION_REQUIRED")


def run_gold48_generation_batch(
    *,
    frozen: dict[str, Any],
    owner_freeze: dict[str, Any],
    adapter_bindings: dict[str, Any],
    input_manifest: dict[str, Any],
    input_path: Path,
    output_path: Path,
    model_role: str,
    backend: GenerationBackend,
    separate_owner_authorization: dict[str, Any] | None = None,
) -> WorkerReceipt:
    """No CLI/Job submitter: only a separately Owner-authorized runtime may call."""
    profile, worker_manifest = prepare_gold48_generation_contract(
        frozen=frozen, owner_freeze=owner_freeze,
        adapter_bindings=adapter_bindings, input_manifest=input_manifest,
        input_path=input_path, model_role=model_role,
    )
    _approve_generation(
        approval=separate_owner_authorization, frozen=frozen,
        bindings=adapter_bindings, manifest=input_manifest, model_role=model_role,
    )
    entry = adapter_bindings["arms"][model_role]
    _require(backend.gpu_started is True
             and getattr(backend, "model_id", None) == MODEL
             and getattr(backend, "revision", None) == REVISION
             and getattr(backend, "gold48_adapter_sha256", "UNVERIFIED") ==
                 entry["expected_sha256"]
             and (
                 getattr(backend, "gold48_adapter_dir", "UNVERIFIED") is None
                 if model_role == "base"
                 else str(getattr(backend, "gold48_adapter_dir", "UNVERIFIED")) ==
                 str(Path(entry["local_dir"]))
             ), "GOLD48_LOADED_BACKEND_IDENTITY_HOLD")
    return _run_validated_generation_batch(
        profile=profile, model_role=model_role, manifest=worker_manifest,
        input_path=input_path, output_path=output_path, backend=backend,
    )

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
from storyforge_dataset.hf_runtime.outputs import OutputManager

from .gold48_owner_receipt import (
    make_owner_scope,
    verify_owner_authorization,
)
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

EVIDENCE_URIS = {
    "r46_v02": (
        "hf://buckets/adradar/storyforge-training/experiments/v02-r46/"
        "r46-20261014T070529Z-248172/r46_training_report.json"
    ),
    "r54_v03a": (
        "hf://buckets/adradar/storyforge-training/experiments/v03-r54/"
        "r54-v2-20261021T161818Z-507469/R54_ADAPTER_RELOAD_VERIFIED_PRIVATE.json"
    ),
    "r60_base336": (
        "https://huggingface.co/jobs/adradar/6b00a44aefaf5e14f4b3c6b5"
    ),
}

SOURCE_FIELDS = {
    "r46_v02": "training_evidence.adapter_sha256",
    "r54_v03a": "adapter_sha256",
    "r60_base336": "job_log_line.adapter_sha256",
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
                     and entry.get("source_evidence_uri") == EVIDENCE_URIS[role]
                     and entry.get("source_field") == SOURCE_FIELDS[role]
                     and isinstance(entry.get("local_dir"), str)
                     and Path(entry["local_dir"]).is_absolute()
                     and not any(p in (".", "..") for p in Path(entry["local_dir"]).parts)
                     and entry.get("expected_weight_size_bytes") == ADAPTER_SIZE,
                     "GOLD48_ADAPTER_BINDING_UNTRUSTED_HOLD")


def build_gold48_frozen_input_payload(
    *,
    frozen: dict[str, Any],
    owner_freeze: dict[str, Any],
    reconstructed_draft: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """CPU-only format conversion; never regenerate or alter frozen messages.

    The draft's message bytes are rehashed using the exact historic canonical
    rule, then checked against the Owner-frozen 48 per-case digests. Historical
    assistant original references are neither imported nor put in outputs.
    """
    cases = _validate_frozen(frozen, owner_freeze)
    _require(isinstance(reconstructed_draft, dict)
             and reconstructed_draft.get("schema") ==
                 "storyforge_r60_gold48_reconstructed_inputs_draft_private_v1"
             and reconstructed_draft.get("status") ==
                 "RECONSTRUCTED_48_INPUT_DRAFT__OWNER_FREEZE_PENDING"
             and reconstructed_draft.get("input_contract") ==
                 "RECONSTRUCTED_EVALUATION_INPUT",
             "GOLD48_RECONSTRUCTED_DRAFT_SCHEMA_HOLD")
    draft_cases = reconstructed_draft.get("cases_PRIVATE")
    _require(isinstance(draft_cases, list) and len(draft_cases) == CASE_COUNT,
             "GOLD48_RECONSTRUCTED_DRAFT_COUNT_HOLD")
    records = []
    for i, (frozen_case, draft_case) in enumerate(zip(cases, draft_cases), 1):
        _require(isinstance(draft_case, dict)
                 and draft_case.get("candidate_case_id_PRIVATE") == f"G48-C{i:02d}"
                 and draft_case.get("candidate_case_id_PRIVATE") ==
                     frozen_case["candidate_case_id_PRIVATE"],
                 "GOLD48_RECONSTRUCTED_DRAFT_CASE_ORDER_HOLD")
        messages = draft_case.get("reconstructed_messages_PRIVATE")
        _require(isinstance(messages, list)
                 and _digest(messages) ==
                     frozen_case["reconstructed_messages_sha256_PRIVATE"]
                 and draft_case.get("reconstructed_messages_sha256_PRIVATE") ==
                     frozen_case["reconstructed_messages_sha256_PRIVATE"],
                 "GOLD48_RECONSTRUCTED_DRAFT_CASE_SHA_HOLD")
        records.append({
            "sample_id": frozen_case["candidate_case_id_PRIVATE"],
            "messages": messages,
        })
    _validate_records(records, CASE_COUNT)
    payload = b"".join(_canonical(record) + b"\n" for record in records)
    _require(len(payload) <= 16 * 1024 * 1024,
             "GOLD48_INPUT_WORKER_FILE_SIZE_HOLD")
    manifest = {
        "schema": INPUT_SCHEMA,
        "run_key": frozen["dataset"]["run_key"],
        "record_count": CASE_COUNT,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "max_input_tokens": 30720,
        "max_new_tokens": 2048,
        "seed": 42,
        "cases": [
            {
                "sample_id": c["candidate_case_id_PRIVATE"],
                "messages_sha256": c["reconstructed_messages_sha256_PRIVATE"],
            }
            for c in cases
        ],
    }
    return payload, manifest


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


def verify_gold48_binding_source_evidence(
    bindings: dict[str, Any],
    evidence_paths: dict[str, Path] | None,
) -> None:
    """CPU-only: bind each private source receipt's exact bytes to its SHA.

    R46/R54 prove *historical report provenance*, not current remote weights.
    R60 verifies only the existing CPU Job's JSON log line, not provider volumes.
    """
    _require(isinstance(evidence_paths, dict)
             and set(evidence_paths) == set(PROVENANCE),
             "GOLD48_SOURCE_EVIDENCE_FILES_REQUIRED")
    import stat
    for role in PROVENANCE:
        entry = bindings["arms"][role]
        path = evidence_paths[role]
        _require(isinstance(path, Path), "GOLD48_SOURCE_EVIDENCE_PATH_HOLD")
        try:
            st = path.lstat()
            _require(stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600,
                     "GOLD48_SOURCE_EVIDENCE_MODE_HOLD")
            raw = InputManager.open_verified(
                path, max_bytes=65536,
                expected_sha256=entry["source_evidence_sha256"],
            ).read_bytes()
            receipt = json.loads(raw)
        except (OSError, TypeError, ValueError) as exc:
            if isinstance(exc, WorkerError):
                raise
            raise WorkerError("GOLD48_SOURCE_EVIDENCE_BYTE_SHA_HOLD") from exc
        _require(isinstance(receipt, dict),
                 "GOLD48_SOURCE_EVIDENCE_SCHEMA_HOLD")
        if role == "r46_v02":
            training = receipt.get("training_evidence")
            value = training.get("adapter_sha256") if isinstance(training, dict) else None
        else:
            value = receipt.get("adapter_sha256")
        _require(value == entry["expected_sha256"],
                 "GOLD48_SOURCE_EVIDENCE_ADAPTER_SHA_HOLD")
        if role == "r60_base336":
            _require(receipt.get("schema") == "storyforge_gold48_adapter_sha_cpu_only_safe_v1"
                     and receipt.get("status") == "R60_ADAPTER_BYTE_SHA_PASS"
                     and receipt.get("file_size") == ADAPTER_SIZE
                     and receipt.get("gpu_started") is False
                     and receipt.get("model_calls") == 0,
                     "GOLD48_R60_JOB_RECEIPT_HOLD")


def _verify_authorized_run(
    *,
    owner_authorization_receipt_path: Path | None,
    trusted_owner_public_key_pem_path: Path | None,
    runtime_lock_path: Path | None,
    runtime_image_digest: str | None,
    frozen: dict[str, Any],
    owner_freeze: dict[str, Any],
    bindings: dict[str, Any],
    manifest: dict[str, Any],
    role: str,
    output_path: Path,
):
    """No caller-supplied approval dictionary; independently verify Owner signature."""
    _require(all(isinstance(p, Path) for p in (
        owner_authorization_receipt_path,
        trusted_owner_public_key_pem_path,
        runtime_lock_path,
    )) and isinstance(runtime_image_digest, str),
             "GOLD48_SEPARATE_OWNER_INFERENCE_AUTHORIZATION_REQUIRED")
    try:
        lock = InputManager.open_verified(
            runtime_lock_path, max_bytes=8 * 1024 * 1024,
        )
    except (OSError, ValueError) as exc:
        raise WorkerError("GOLD48_RUNTIME_LOCK_READ_HOLD") from exc

    # Read-only, mode-0600; cannot infer authorization from a provided dict.
    receipt = read_private_contract(owner_authorization_receipt_path, max_bytes=65536)
    payload = receipt.get("payload")
    _require(isinstance(payload, dict),
             "GOLD48_OWNER_SIGNED_RECEIPT_REQUIRED")
    expected = make_owner_scope(
        frozen=frozen, owner_freeze=owner_freeze,
        adapter_bindings=bindings, input_manifest=manifest,
        model_role=role, output_filename=output_path.name,
        output_directory=str(output_path.parent),
        run_id=payload.get("run_id"),
        dependency_lock_sha256=lock.sha256,
        runtime_image_digest=runtime_image_digest,
        issued_at_utc=payload.get("issued_at_utc"),
        expires_at_utc=payload.get("expires_at_utc"),
    )
    try:
        verified = verify_owner_authorization(
            receipt_path=owner_authorization_receipt_path,
            trusted_public_key_pem_path=trusted_owner_public_key_pem_path,
            expected_scope=expected,
        )
    except WorkerError:
        raise
    return verified, lock.sha256


def _gold48_sidecar(
    *,
    frozen: dict[str, Any],
    bindings: dict[str, Any],
    input_manifest: dict[str, Any],
    role: str,
    auth,
    lock_sha256: str,
    runtime_image_digest: str,
    receipt: WorkerReceipt,
) -> dict[str, Any]:
    """Private identity only, never raw answers or historical original references."""
    return {
        "schema": "storyforge_r60_gold48_generation_identity_private_v1",
        "status": "GENERATION_IDENTITY_RECORDED__OWNER_REVIEW_REQUIRED",
        "run_key": frozen["dataset"]["run_key"],
        "run_id": auth.payload["run_id"],
        "selected_model_role": role,
        "arms": {
            key: {
                "model": frozen["arms"][key]["model"],
                "revision": frozen["arms"][key]["base_revision"],
                "adapter_checkpoint": frozen["arms"][key]["adapter_checkpoint"],
                "adapter_sha256": bindings["arms"][key]["expected_sha256"],
            }
            for key in ROLES
        },
        "model_revision": REVISION,
        "input_sha256": input_manifest["sha256"],
        "input_manifest_canonical_sha256": _digest(input_manifest),
        "frozen_profile_canonical_sha256": _digest(frozen),
        "adapter_bindings_canonical_sha256": _digest(bindings),
        "dependency_lock_sha256": lock_sha256,
        "runtime_image_digest": runtime_image_digest,
        "owner_authorization_receipt_sha256": auth.receipt_sha256,
        "output_sha256": receipt.output_sha256,
        "output_bytes": receipt.output_size_bytes,
        "record_count": receipt.record_count,
        "finish_reason_counts": dict(receipt.finish_reason_counts),
        "training_started": False,
    }


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
    owner_authorization_receipt_path: Path | None = None,
    trusted_owner_public_key_pem_path: Path | None = None,
    runtime_lock_path: Path | None = None,
    runtime_image_digest: str | None = None,
    source_evidence_paths: dict[str, Path] | None = None,
) -> WorkerReceipt:
    """No CLI/Job submitter: only a separately Owner-authorized runtime may call."""
    profile, worker_manifest = prepare_gold48_generation_contract(
        frozen=frozen, owner_freeze=owner_freeze,
        adapter_bindings=adapter_bindings, input_manifest=input_manifest,
        input_path=input_path, model_role=model_role,
    )
    auth, lock_sha256 = _verify_authorized_run(
        owner_authorization_receipt_path=owner_authorization_receipt_path,
        trusted_owner_public_key_pem_path=trusted_owner_public_key_pem_path,
        runtime_lock_path=runtime_lock_path,
        runtime_image_digest=runtime_image_digest,
        frozen=frozen, owner_freeze=owner_freeze,
        bindings=adapter_bindings, manifest=input_manifest, role=model_role,
        output_path=output_path,
    )
    verify_gold48_binding_source_evidence(
        adapter_bindings, source_evidence_paths,
    )
    sidecar_path = output_path.with_name(output_path.name + ".identity.private.json")
    _require(not output_path.exists() and not output_path.is_symlink()
             and not sidecar_path.exists() and not sidecar_path.is_symlink(),
             "GOLD48_OUTPUT_ALREADY_EXISTS_HOLD")
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
    receipt = _run_validated_generation_batch(
        profile=profile, model_role=model_role, manifest=worker_manifest,
        input_path=input_path, output_path=output_path, backend=backend,
    )
    sidecar = _gold48_sidecar(
        frozen=frozen, bindings=adapter_bindings, input_manifest=input_manifest,
        role=model_role, auth=auth, lock_sha256=lock_sha256,
        runtime_image_digest=runtime_image_digest, receipt=receipt,
    )
    try:
        OutputManager.write_safe(sidecar_path, sidecar, mode=0o600)
    except (ValueError, OSError) as exc:
        # The private generation file remains create-only: never delete or
        # overwrite it to hide a failed identity publication.
        raise WorkerError("GOLD48_IDENTITY_SIDECAR_PUBLICATION_HOLD") from exc
    return receipt

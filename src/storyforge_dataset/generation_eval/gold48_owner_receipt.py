"""Gold48 Owner-only Ed25519 create-only authorization and runtime verifier.

The runtime NEVER signs, takes an ordinary authorization dict, or trusts a
caller-chosen key. The Owner public-key PEM SHA must first be registered by a
reviewed code change; the default value is intentionally unprovisioned.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager
from storyforge_dataset.hf_runtime.outputs import OutputManager

from .worker import WorkerError

OWNER_TRUSTED_PUBLIC_PEM_SHA256 = ""  # fail closed until Owner pins a public key
RECEIPT_SCHEMA = "storyforge_r60_gold48_owner_generation_ed25519_private_v1"
PAYLOAD_SCHEMA = "storyforge_r60_gold48_owner_generation_scope_v1"
SIGNATURE_TYPE = "ed25519"
PRODUCTION_SCOPE = "PRODUCTION_GPU_48_GENERATIONS"
SYNTHETIC_SCOPE = "SYNTHETIC_CPU_ONLY_CONTRACT_TEST"
ROLES = ("base", "r46_v02", "r54_v03a", "r60_base336")
SHA = re.compile(r"[0-9a-f]{64}\Z")
HEX_SIGNATURE = re.compile(r"[0-9a-f]{128}\Z")
RUN_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{7,63}\Z")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise WorkerError(code)


def _private_bytes(path: Path, *, max_bytes: int = 65536) -> bytes:
    try:
        info = path.lstat()
        _require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600,
                 "GOLD48_OWNER_RECEIPT_MODE_HOLD")
        return InputManager.open_verified(path, max_bytes=max_bytes).read_bytes()
    except (OSError, ValueError, TypeError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_OWNER_RECEIPT_READ_HOLD") from exc


def _ed25519():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as exc:
        raise WorkerError("GOLD48_ED25519_DEPENDENCY_MISSING_HOLD") from exc
    return serialization, Ed25519PrivateKey, Ed25519PublicKey


@dataclass(frozen=True)
class VerifiedOwnerAuthorization:
    payload: dict[str, Any]
    receipt_sha256: str
    signer_public_pem_sha256: str


def make_owner_scope(
    *,
    frozen: dict[str, Any],
    owner_freeze: dict[str, Any],
    adapter_bindings: dict[str, Any],
    input_manifest: dict[str, Any],
    model_role: str,
    output_filename: str,
    output_directory: str,
    run_id: str,
    dependency_lock_sha256: str,
    runtime_image_digest: str,
    issued_at_utc: str,
    expires_at_utc: str,
    synthetic_test_only: bool = False,
) -> dict[str, Any]:
    """One role/run: production GPU and synthetic CPU are disjoint capabilities."""
    if type(synthetic_test_only) is not bool:
        raise WorkerError("GOLD48_OWNER_EXECUTION_MODE_HOLD")
    arm = frozen["arms"][model_role]
    return {
        "schema": PAYLOAD_SCHEMA,
        "scope": "GOLD48_FOUR_ARM_192_GENERATIONS",
        "execution_environment": (
            SYNTHETIC_SCOPE if synthetic_test_only else PRODUCTION_SCOPE
        ),
        "run_key": frozen["dataset"]["run_key"],
        "run_id": run_id,
        "model_role": model_role,
        "output_filename": output_filename,
        "output_directory": output_directory,
        "record_count": 48,
        "max_model_calls": 48,
        "model_revision": arm["base_revision"],
        "checkpoint_uri": arm["adapter_checkpoint"],
        "adapter_sha256": adapter_bindings["arms"][model_role]["expected_sha256"],
        "frozen_profile_canonical_sha256": sha(frozen),
        "owner_freeze_canonical_sha256": sha(owner_freeze),
        "adapter_bindings_canonical_sha256": sha(adapter_bindings),
        "input_manifest_canonical_sha256": sha(input_manifest),
        "input_sha256": input_manifest["sha256"],
        "dependency_lock_sha256": dependency_lock_sha256,
        "runtime_image_digest": runtime_image_digest,
        "issued_at_utc": issued_at_utc,
        "expires_at_utc": expires_at_utc,
        "inference_authorized": not synthetic_test_only,
        "gpu_authorized": not synthetic_test_only,
        "training_authorized": False,
    }


def _check_scope(
    scope: dict[str, Any], *,
    expected: dict[str, Any],
) -> None:
    _require(isinstance(scope, dict) and set(scope) == set(expected)
             and scope == expected, "GOLD48_OWNER_SIGNED_SCOPE_MISMATCH_HOLD")
    synthetic = scope.get("execution_environment") == SYNTHETIC_SCOPE
    _require(scope["schema"] == PAYLOAD_SCHEMA
             and scope.get("execution_environment") in (PRODUCTION_SCOPE, SYNTHETIC_SCOPE)
             and scope["inference_authorized"] is (not synthetic)
             and scope["gpu_authorized"] is (not synthetic)
             and scope["training_authorized"] is False
             and scope["model_role"] in ROLES
             and RUN_ID.fullmatch(scope["run_id"]) is not None
             and isinstance(scope["output_filename"], str)
             and scope["output_filename"] not in {"", ".", ".."}
             and Path(scope["output_filename"]).name == scope["output_filename"]
             and scope["output_filename"].endswith(".private.json")
             and isinstance(scope["output_directory"], str)
             and Path(scope["output_directory"]).is_absolute()
             and Path(scope["output_directory"]).name == scope["run_id"]
             and isinstance(scope["dependency_lock_sha256"], str)
             and SHA.fullmatch(scope["dependency_lock_sha256"]) is not None
             and isinstance(scope["runtime_image_digest"], str)
             and re.fullmatch(r"sha256:[0-9a-f]{64}", scope["runtime_image_digest"])
                 is not None,
             "GOLD48_OWNER_SIGNED_SCOPE_INVALID_HOLD")
    try:
        start = datetime.fromisoformat(scope["issued_at_utc"])
        end = datetime.fromisoformat(scope["expires_at_utc"])
    except (TypeError, ValueError) as exc:
        raise WorkerError("GOLD48_OWNER_RECEIPT_TIME_INVALID_HOLD") from exc
    now = datetime.now(UTC)
    _require(start.tzinfo is not None and end.tzinfo is not None
             and start <= now <= end
             and timedelta(0) < end - start <= timedelta(hours=48),
             "GOLD48_OWNER_RECEIPT_EXPIRED_OR_TOO_BROAD_HOLD")


def owner_sign_create_only(
    *,
    scope: dict[str, Any],
    private_key_path: Path,
    receipt_path: Path,
) -> str:
    """Trusted Owner-local operation; the GPU runtime has no signing key."""
    _require(isinstance(scope, dict) and scope.get("schema") == PAYLOAD_SCHEMA,
             "GOLD48_OWNER_SCOPE_INVALID_HOLD")
    serialization, Ed25519PrivateKey, _ = _ed25519()
    raw_key = _private_bytes(private_key_path, max_bytes=32768)
    try:
        key = serialization.load_pem_private_key(raw_key, password=None)
        _require(isinstance(key, Ed25519PrivateKey), "GOLD48_OWNER_KEY_TYPE_HOLD")
        signature = key.sign(canonical(scope)).hex()
    except (TypeError, ValueError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_OWNER_KEY_PARSE_HOLD") from exc
    public_key_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "signature_algorithm": SIGNATURE_TYPE,
        "signer_public_pem_sha256": hashlib.sha256(public_key_pem).hexdigest(),
        "payload": scope,
        "signature_hex": signature,
    }
    try:
        result = OutputManager.write_safe(receipt_path, receipt, mode=0o600)
    except (OSError, ValueError) as exc:
        raise WorkerError("GOLD48_OWNER_RECEIPT_CREATE_ONLY_HOLD") from exc
    return result.sha256


def verify_owner_authorization(
    *,
    receipt_path: Path,
    trusted_public_key_pem_path: Path,
    expected_scope: dict[str, Any],
) -> VerifiedOwnerAuthorization:
    """Only a pre-pinned Owner public key can authorize generation."""
    trusted_pin = OWNER_TRUSTED_PUBLIC_PEM_SHA256
    _require(isinstance(trusted_pin, str) and SHA.fullmatch(trusted_pin) is not None,
             "GOLD48_OWNER_TRUST_ANCHOR_NOT_PINNED_HOLD")
    key_bytes = _private_bytes(trusted_public_key_pem_path, max_bytes=8192)
    actual_key_pin = hashlib.sha256(key_bytes).hexdigest()
    _require(actual_key_pin == trusted_pin, "GOLD48_OWNER_TRUST_ANCHOR_MISMATCH_HOLD")
    raw = _private_bytes(receipt_path, max_bytes=65536)
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise WorkerError("GOLD48_OWNER_RECEIPT_JSON_INVALID_HOLD") from exc
    _require(isinstance(obj, dict)
             and set(obj) == {
                 "schema", "signature_algorithm", "signer_public_pem_sha256",
                 "payload", "signature_hex"
             }
             and obj["schema"] == RECEIPT_SCHEMA
             and obj["signature_algorithm"] == SIGNATURE_TYPE
             and obj["signer_public_pem_sha256"] == trusted_pin
             and isinstance(obj["signature_hex"], str)
             and HEX_SIGNATURE.fullmatch(obj["signature_hex"]) is not None,
             "GOLD48_OWNER_RECEIPT_FORMAT_HOLD")
    serialization, _, Ed25519PublicKey = _ed25519()
    try:
        public_key = serialization.load_pem_public_key(key_bytes)
        _require(isinstance(public_key, Ed25519PublicKey),
                 "GOLD48_OWNER_PUBLIC_KEY_TYPE_HOLD")
        public_key.verify(bytes.fromhex(obj["signature_hex"]), canonical(obj["payload"]))
    except Exception as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_OWNER_RECEIPT_SIGNATURE_INVALID_HOLD") from exc
    _check_scope(obj["payload"], expected=expected_scope)
    return VerifiedOwnerAuthorization(
        payload=obj["payload"],
        receipt_sha256=hashlib.sha256(raw).hexdigest(),
        signer_public_pem_sha256=trusted_pin,
    )

"""Gold48 production pre-GPU gate: Owner signature, measured runtime, one-shot.

No model/GPU import. Public booleans cannot mint a load permit. A trusted
provider must attest the *observed* image digest with its own pinned Ed25519
public key; a caller-supplied image string is not evidence.

The authorization consumption ledger MUST be a durable shared mount that
survives worker restarts. A crash consumes the grant; only a new Owner-signed
Run ID may retry. Synthetic tests may monkeypatch the two trust anchors.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import secrets
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager
from storyforge_dataset.hf_runtime.outputs import OutputManager

from .gold48_owner_receipt import (
    canonical,
    verify_owner_authorization,
)
from .worker import WorkerError

# Both of these must be separately approved before any production GPU startup.
PROVIDER_TRUSTED_PUBLIC_PEM_SHA256 = ""
DURABLE_CONSUMPTION_ROOT = Path("/mnt/storyforge-private/gold48-authorizations-spent")
MEASUREMENT_SCHEMA = "storyforge_r60_gold48_provider_image_measurement_v1"
SIGNED_MEASUREMENT_SCHEMA = "storyforge_r60_gold48_provider_ed25519_attestation_v1"
CONSUMPTION_SCHEMA = "storyforge_r60_gold48_authorization_consumed_private_v1"
# Process-local issuance registry: a file or dataclass alone cannot re-mint a grant.
_ISSUED_ONE_SHOT_PERMITS: dict[str, str] = {}
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _check(ok: bool, code: str) -> None:
    if not ok:
        raise WorkerError(code)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_0600(path: Path, max_bytes: int = 65536) -> bytes:
    try:
        stat_result = path.lstat()
        _check(stat.S_ISREG(stat_result.st_mode)
               and stat.S_IMODE(stat_result.st_mode) == 0o600,
               "GOLD48_RUNTIME_EVIDENCE_FILE_MODE_HOLD")
        return InputManager.open_verified(path, max_bytes=max_bytes).read_bytes()
    except (OSError, ValueError, TypeError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_RUNTIME_EVIDENCE_READ_HOLD") from exc


def verify_provider_image_measurement(
    *,
    attestation_path: Path,
    trusted_provider_public_key_path: Path,
    owner_scope: dict[str, Any],
) -> str:
    """Require separately pinned provider-signed exact runtime image identity."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    _check(bool(HEX_SHA.fullmatch(PROVIDER_TRUSTED_PUBLIC_PEM_SHA256)),
           "GOLD48_PROVIDER_TRUST_ANCHOR_NOT_PINNED_HOLD")
    key_bytes = _read_0600(trusted_provider_public_key_path, max_bytes=8192)
    _check(_sha_bytes(key_bytes) == PROVIDER_TRUSTED_PUBLIC_PEM_SHA256,
           "GOLD48_PROVIDER_TRUST_ANCHOR_MISMATCH_HOLD")
    raw = _read_0600(attestation_path)
    try:
        attestation = json.loads(raw)
        _check(isinstance(attestation, dict)
               and set(attestation) == {"schema", "measurement", "signature_hex"}
               and attestation["schema"] == SIGNED_MEASUREMENT_SCHEMA,
               "GOLD48_PROVIDER_ATTESTATION_SCHEMA_HOLD")
        measurement = attestation["measurement"]
        _check(isinstance(measurement, dict)
               and set(measurement) == {
                   "schema", "provider_job_id", "run_id", "model_role",
                   "image_digest", "measurement_source", "inspect_receipt_sha256",
               }
               and measurement["schema"] == MEASUREMENT_SCHEMA
               and isinstance(measurement["provider_job_id"], str)
               and bool(measurement["provider_job_id"])
               and measurement["run_id"] == owner_scope["run_id"]
               and measurement["model_role"] == owner_scope["model_role"]
               and measurement["image_digest"] == owner_scope["runtime_image_digest"]
               and measurement["measurement_source"] == "PROVIDER_JOB_INSPECT_IMAGE_DIGEST"
               and bool(HEX_SHA.fullmatch(measurement["inspect_receipt_sha256"]))
               and isinstance(attestation["signature_hex"], str)
               and re.fullmatch(r"[0-9a-f]{128}", attestation["signature_hex"]),
               "GOLD48_PROVIDER_MEASUREMENT_SCOPE_HOLD")
        public = serialization.load_pem_public_key(key_bytes)
        _check(isinstance(public, Ed25519PublicKey),
               "GOLD48_PROVIDER_PUBLIC_KEY_TYPE_HOLD")
        public.verify(
            bytes.fromhex(attestation["signature_hex"]), canonical(measurement)
        )
    except (ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_PROVIDER_ATTESTATION_INVALID_HOLD") from exc
    except Exception as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_PROVIDER_SIGNATURE_INVALID_HOLD") from exc
    return _sha_bytes(raw)


def verify_current_dependency_install(
    *, runtime_lock_path: Path, runtime_contract_path: Path,
    owner_scope: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    """Measure the running Python environment, not just a signed declaration."""
    try:
        contract = json.loads(
            InputManager.open_verified(runtime_contract_path, max_bytes=65536).read_bytes()
        )
        lock_sha = InputManager.open_verified(
            runtime_lock_path, max_bytes=8 * 1024 * 1024,
        ).sha256
    except (OSError, TypeError, ValueError) as exc:
        raise WorkerError("GOLD48_RUNTIME_DEPENDENCY_EVIDENCE_HOLD") from exc
    _check(contract.get("schema") ==
               "storyforge_r60_gold48_inference_cpu_dependency_contract_v1"
           and contract.get("lock_sha256") == lock_sha
           and owner_scope["dependency_lock_sha256"] == lock_sha
           and contract.get("base_image", "").endswith(
               "@" + owner_scope["runtime_image_digest"]
           )
           and contract.get("require_hashes_install_on_inference_image_verified") is True
           and sys.version_info[:2] == (3, 11)
           and sys.platform.startswith("linux")
           and platform.machine() in ("x86_64", "AMD64"),
           "GOLD48_RUNTIME_DEPENDENCY_PIN_HOLD")
    expected = dict(contract["pins"])
    measured = {}
    try:
        for name, version in expected.items():
            observed = importlib.metadata.version(name)
            if name == "torch":
                _check(observed == contract["observed_torch"]
                       and observed.startswith(version + "+"),
                       "GOLD48_TORCH_RUNTIME_VERSION_HOLD")
            else:
                _check(observed == version,
                       "GOLD48_RUNTIME_DEPENDENCY_VERSION_HOLD")
            measured[name] = observed
        checked = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True, timeout=60, check=False,
        )
        _check(checked.returncode == 0, "GOLD48_RUNTIME_PIP_CHECK_HOLD")
    except (OSError, subprocess.TimeoutExpired, importlib.metadata.PackageNotFoundError) as exc:
        raise WorkerError("GOLD48_RUNTIME_PACKAGE_MEASUREMENT_HOLD") from exc
    return lock_sha, measured


@dataclass(frozen=True)
class SignedGold48LoadPermit:
    """Pure-Python launch handle; loader rechecks signed and spent evidence."""
    owner_receipt_path: Path
    owner_public_key_path: Path
    signed_scope: dict[str, Any]
    spent_receipt_path: Path
    provider_attestation_path: Path
    provider_public_key_path: Path
    runtime_lock_path: Path
    runtime_contract_path: Path
    selected_adapter_dir: Path | None
    one_shot_nonce: str


def _validate_durable_ledger_root() -> None:
    root = DURABLE_CONSUMPTION_ROOT
    try:
        st = root.lstat()
        _check(stat.S_ISDIR(st.st_mode)
               and stat.S_IMODE(st.st_mode) == 0o700
               and root.is_mount(),
               "GOLD48_DURABLE_SHARED_LEDGER_MOUNT_REQUIRED")
    except OSError as exc:
        raise WorkerError("GOLD48_DURABLE_SHARED_LEDGER_MOUNT_REQUIRED") from exc


def authorize_and_consume_before_gpu(
    *,
    frozen: dict[str, Any],
    owner_freeze: dict[str, Any],
    adapter_bindings: dict[str, Any],
    input_manifest: dict[str, Any],
    input_path: Path,
    output_path: Path,
    model_role: str,
    owner_authorization_receipt_path: Path,
    trusted_owner_public_key_pem_path: Path,
    source_evidence_paths: dict[str, Path],
    runtime_lock_path: Path,
    runtime_contract_path: Path,
    provider_attestation_path: Path,
    trusted_provider_public_key_path: Path,
) -> SignedGold48LoadPermit:
    """Only trusted production coordinator calls this BEFORE any GPU loader."""
    from .gold48_contract_bridge import (
        _verify_authorized_run,
        prepare_gold48_generation_contract,
        verify_gold48_binding_source_evidence,
    )

    prepare_gold48_generation_contract(
        frozen=frozen, owner_freeze=owner_freeze,
        adapter_bindings=adapter_bindings, input_manifest=input_manifest,
        input_path=input_path, model_role=model_role,
    )
    _check(not output_path.exists() and not output_path.is_symlink(),
           "GOLD48_OUTPUT_ALREADY_EXISTS_HOLD")
    signed_receipt = json.loads(_read_0600(owner_authorization_receipt_path))
    _check(isinstance(signed_receipt, dict)
           and isinstance(signed_receipt.get("payload"), dict),
           "GOLD48_SIGNED_OWNER_RECEIPT_REQUIRED")
    image_digest = signed_receipt["payload"].get("runtime_image_digest")
    auth, lock_sha = _verify_authorized_run(
        owner_authorization_receipt_path=owner_authorization_receipt_path,
        trusted_owner_public_key_pem_path=trusted_owner_public_key_pem_path,
        runtime_lock_path=runtime_lock_path,
        runtime_image_digest=image_digest,
        frozen=frozen, owner_freeze=owner_freeze,
        bindings=adapter_bindings, manifest=input_manifest,
        role=model_role, output_path=output_path,
    )
    verify_gold48_binding_source_evidence(adapter_bindings, source_evidence_paths)
    measured_sha, versions = verify_current_dependency_install(
        runtime_lock_path=runtime_lock_path,
        runtime_contract_path=runtime_contract_path,
        owner_scope=auth.payload,
    )
    _check(measured_sha == lock_sha, "GOLD48_LOCK_SHA_DISAGREEMENT_HOLD")
    provider_sha = verify_provider_image_measurement(
        attestation_path=provider_attestation_path,
        trusted_provider_public_key_path=trusted_provider_public_key_path,
        owner_scope=auth.payload,
    )
    _validate_durable_ledger_root()
    spent = DURABLE_CONSUMPTION_ROOT / (
        auth.receipt_sha256 + ".spent.private.json"
    )
    payload = {
        "schema": CONSUMPTION_SCHEMA,
        "policy": "ONE_SHOT_CONSUME_BEFORE_GPU__NO_AUTOMATIC_RETRY",
        "run_key": auth.payload["run_key"],
        "run_id": auth.payload["run_id"],
        "model_role": model_role,
        "owner_authorization_receipt_sha256": auth.receipt_sha256,
        "output_path": str(output_path),
        "adapter_sha256": adapter_bindings["arms"][model_role]["expected_sha256"],
        "runtime_lock_sha256": lock_sha,
        "runtime_packages_measured": versions,
        "provider_image_measurement_receipt_sha256": provider_sha,
        "runtime_image_digest_measured": image_digest,
        "max_model_calls": 48,
    }
    try:
        OutputManager.write_safe(spent, payload, mode=0o600)
    except (OSError, ValueError) as exc:
        raise WorkerError("GOLD48_AUTHORIZATION_ALREADY_SPENT_OR_LEDGER_HOLD") from exc
    nonce = secrets.token_hex(32)
    _check(auth.receipt_sha256 not in _ISSUED_ONE_SHOT_PERMITS,
           "GOLD48_AUTHORIZATION_ALREADY_SPENT_OR_LEDGER_HOLD")
    _ISSUED_ONE_SHOT_PERMITS[auth.receipt_sha256] = nonce
    return SignedGold48LoadPermit(
        owner_receipt_path=owner_authorization_receipt_path,
        owner_public_key_path=trusted_owner_public_key_pem_path,
        signed_scope=auth.payload,
        spent_receipt_path=spent,
        provider_attestation_path=provider_attestation_path,
        provider_public_key_path=trusted_provider_public_key_path,
        runtime_lock_path=runtime_lock_path,
        runtime_contract_path=runtime_contract_path,
        selected_adapter_dir=(
            None if model_role == "base"
            else Path(adapter_bindings["arms"][model_role]["local_dir"])
        ),
        one_shot_nonce=nonce,
    )


def verify_and_consume_gold48_load_permit(
    *,
    permit: SignedGold48LoadPermit | None,
    adapter_dir: Path | None,
    adapter_sha256: str | None,
) -> None:
    """Final loader gate: NO model import before independently checking evidence.

    The durable spend was already create-only. A permit alone is not enough:
    re-verify pinned Owner signature, measured provider image and local versions.
    """
    _check(isinstance(permit, SignedGold48LoadPermit),
           "GOLD48_SIGNED_LAUNCH_PERMIT_REQUIRED")
    _check(permit.selected_adapter_dir == adapter_dir,
           "GOLD48_SIGNED_LAUNCH_ADAPTER_DIR_HOLD")
    _check(permit.signed_scope["adapter_sha256"] == adapter_sha256,
           "GOLD48_SIGNED_LAUNCH_ADAPTER_SHA_HOLD")
    auth = verify_owner_authorization(
        receipt_path=permit.owner_receipt_path,
        trusted_public_key_pem_path=permit.owner_public_key_path,
        expected_scope=permit.signed_scope,
    )
    _validate_durable_ledger_root()
    expected_path = DURABLE_CONSUMPTION_ROOT / (
        auth.receipt_sha256 + ".spent.private.json"
    )
    _check(permit.spent_receipt_path == expected_path,
           "GOLD48_AUTHORIZATION_SPEND_PATH_HOLD")
    spent = json.loads(_read_0600(expected_path))
    _check(isinstance(spent, dict)
           and spent.get("schema") == CONSUMPTION_SCHEMA
           and spent.get("owner_authorization_receipt_sha256") == auth.receipt_sha256
           and spent.get("run_id") == auth.payload["run_id"]
           and spent.get("model_role") == auth.payload["model_role"]
           and spent.get("adapter_sha256") == adapter_sha256
           and spent.get("output_path") == (
               str(Path(auth.payload["output_directory"]) /
                   auth.payload["output_filename"])
           )
           and spent.get("max_model_calls") == 48,
           "GOLD48_SPENT_GRANT_MISMATCH_HOLD")
    lock_sha, versions = verify_current_dependency_install(
        runtime_lock_path=permit.runtime_lock_path,
        runtime_contract_path=permit.runtime_contract_path,
        owner_scope=auth.payload,
    )
    image_sha = verify_provider_image_measurement(
        attestation_path=permit.provider_attestation_path,
        trusted_provider_public_key_path=permit.provider_public_key_path,
        owner_scope=auth.payload,
    )
    _check(spent["runtime_lock_sha256"] == lock_sha
           and spent["runtime_packages_measured"] == versions
           and spent["provider_image_measurement_receipt_sha256"] == image_sha
           and spent["runtime_image_digest_measured"] ==
               auth.payload["runtime_image_digest"],
           "GOLD48_RUNTIME_MEASUREMENT_CHANGED_HOLD")
    _check(_ISSUED_ONE_SHOT_PERMITS.pop(auth.receipt_sha256, None) ==
           permit.one_shot_nonce, "GOLD48_LOADER_ONE_SHOT_PERMIT_REUSED_HOLD")

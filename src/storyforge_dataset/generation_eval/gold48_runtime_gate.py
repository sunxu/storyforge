"""Gold48 production pre-GPU gate: Owner signature, measured runtime, one-shot.

No model/GPU import. Public booleans cannot mint a load permit. The trusted
Owner signs the image digest; Mac HF Job Inspect is required for admission.
public key; a caller-supplied image string is not evidence.

The trusted Owner Mac exclusively submits one Job per signed Run ID, backed
by its durable local submit marker and exhaustive HF history. The Job keeps a
PROCESS-LOCAL spend record for its own loader/worker, NOT a global cross-Job
lock. Synthetic tests may monkeypatch the two trust anchors.
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
    PRODUCTION_SCOPE,
    canonical,
    verify_owner_authorization,
)
from .worker import WorkerError

# Historical Provider proof verifier only; NOT a Gold48 production gate.
PROVIDER_TRUSTED_PUBLIC_PEM_SHA256 = ""
# Job-local ONLY, not a shared Bucket or distributed lock.
JOB_LOCAL_CONSUMPTION_ROOT = Path("/tmp/storyforge-gold48-private/spent")
# HF Job native :rw Bucket mount. Used only for result object transfer.
BUCKET_RESULT_MOUNT = Path("/output")
# A successful earlier CPU mount probe is not a production-process observation.
ADAPTER_MOUNT_ROOT = Path("/ro_adapters")
ADAPTER_MOUNTINFO_PATH = Path("/proc/self/mountinfo")
ADAPTER_WEIGHT_BYTES = 1_867_797_544
ADAPTER_CONFIG_BYTES = {"r46_v02": 1282, "r54_v03a": 1282, "r60_base336": 1288}
MEASUREMENT_SCHEMA = "storyforge_r60_gold48_provider_image_measurement_v1"
SIGNED_MEASUREMENT_SCHEMA = "storyforge_r60_gold48_provider_ed25519_attestation_v1"
CONSUMPTION_SCHEMA = "storyforge_r60_gold48_authorization_consumed_private_v1"
# Reviewed immutable hashes and versions; the runtime contract is not trusted
# merely because a caller supplied it. Changes require a reviewed code commit.
FROZEN_RUNTIME_IMAGE = (
    "pytorch/pytorch@sha256:"
    "77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"
)
FROZEN_RUNTIME_LOCK_SHA256 = (
    "dc3425f4895e091c4f5981a4933a6ba2e8fdd8426d8e074069c8cfa2ff4f8d5e"
)
FROZEN_RUNTIME_TORCH_BUILD = "2.6.0+cu124"
FROZEN_RUNTIME_PACKAGES = {
    "torch": "2.6.0",
    "transformers": "5.16.1",
    "peft": "0.21.2",
    "accelerate": "1.12.0",
    "huggingface_hub": "1.33.0",
    "cryptography": "46.0.4",
}
FROZEN_PINNED_INSTALL_JOB = "6b00b0894fdc5ab3c55be7f0"
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
    # JOB_ID is injected by HF Jobs after submission. Never accept a
    # signature for a different job, even if run/role/image match.
    current_job_id = os.environ.get("JOB_ID", "")
    _check(re.fullmatch(r"[0-9a-f]{24}", current_job_id) is not None,
           "GOLD48_PROVIDER_CURRENT_JOB_ID_REQUIRED_HOLD")
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
               and measurement["provider_job_id"] == current_job_id
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
           and contract.get("lock_sha256") == FROZEN_RUNTIME_LOCK_SHA256
           and lock_sha == FROZEN_RUNTIME_LOCK_SHA256
           and owner_scope["dependency_lock_sha256"] == FROZEN_RUNTIME_LOCK_SHA256
           and contract.get("base_image") == FROZEN_RUNTIME_IMAGE
           and contract["base_image"].endswith(
               "@" + owner_scope["runtime_image_digest"]
           )
           and contract.get("observed_torch") == FROZEN_RUNTIME_TORCH_BUILD
           and contract.get("pins") == FROZEN_RUNTIME_PACKAGES
           and contract.get("hash_pinned_install_verified_job") ==
               FROZEN_PINNED_INSTALL_JOB
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
    runtime_lock_path: Path
    runtime_contract_path: Path
    selected_adapter_dir: Path | None
    one_shot_nonce: str


def _validate_job_local_private_root(root: Path) -> None:
    """Reject remote/FUSE-backed private output: only local POSIX scratch."""
    try:
        st = root.lstat()
        _check(stat.S_ISDIR(st.st_mode)
               and stat.S_IMODE(st.st_mode) == 0o700
               and root.is_absolute()
               and root.resolve(strict=True) == root,
               "GOLD48_JOB_LOCAL_PRIVATE_ROOT_0700_HOLD")
        mount_types = []
        for line in Path("/proc/self/mountinfo").read_text(
            encoding="utf-8"
        ).splitlines():
            parts = line.split()
            if "-" not in parts:
                continue
            sep = parts.index("-")
            if len(parts) <= sep + 1 or len(parts) < 6:
                continue
            point = parts[4].replace(r"\040", " ")
            value = str(root)
            if value == point or value.startswith(point.rstrip("/") + "/"):
                mount_types.append((len(point), parts[sep + 1]))
        _check(bool(mount_types), "GOLD48_JOB_LOCAL_MOUNTINFO_HOLD")
        _check(max(mount_types)[1] in {
            "overlay", "ext4", "xfs", "btrfs", "tmpfs", "zfs",
        }, "GOLD48_JOB_LOCAL_ONLY_NO_FUSE_HOLD")
    except (OSError, UnicodeError) as exc:
        raise WorkerError("GOLD48_JOB_LOCAL_MOUNTINFO_HOLD") from exc


def _validate_job_local_ledger_root() -> None:
    _validate_job_local_private_root(JOB_LOCAL_CONSUMPTION_ROOT)


def verify_current_readonly_adapter_mount(
    *, role: str, adapter_dir: Path | None,
) -> dict[str, Any] | None:
    """CPU-only kernel mountinfo + lstat proof, BEFORE spending a GPU grant.

    This is per-launch evidence, not a claim that yesterday's CPU Job mount
    remains present. File contents and the 1.87 GB SHA are checked later by
    the existing Loader, without loading weights before authorization.
    """
    if role == "base":
        _check(adapter_dir is None, "GOLD48_BASE_ADAPTER_MOUNT_UNEXPECTED_HOLD")
        return None
    _check(role in ADAPTER_CONFIG_BYTES
           and adapter_dir == ADAPTER_MOUNT_ROOT / role,
           "GOLD48_RUNTIME_ADAPTER_MOUNT_TARGET_HOLD")
    try:
        parent = ADAPTER_MOUNT_ROOT.lstat()
        root = adapter_dir.lstat()
        weight = (adapter_dir / "adapter_model.safetensors").lstat()
        config = (adapter_dir / "adapter_config.json").lstat()
        _check(
            stat.S_ISDIR(parent.st_mode)
            and stat.S_ISDIR(root.st_mode)
            and stat.S_ISREG(weight.st_mode)
            and stat.S_ISREG(config.st_mode)
            and weight.st_size == ADAPTER_WEIGHT_BYTES
            and config.st_size == ADAPTER_CONFIG_BYTES[role],
            "GOLD48_RUNTIME_ADAPTER_MOUNT_METADATA_HOLD",
        )
        # Read only kernel mount metadata, never adapter weight bytes.
        mountinfo = ADAPTER_MOUNTINFO_PATH.read_text(encoding="utf-8")
        matching = []
        for line in mountinfo.splitlines():
            before, sep, _ = line.partition(" - ")
            if not sep:
                continue
            fields = before.split()
            if len(fields) >= 6 and fields[4] == str(adapter_dir):
                matching.append(fields[5].split(","))
        _check(len(matching) == 1 and "ro" in matching[0],
               "GOLD48_RUNTIME_ADAPTER_RO_MOUNT_REQUIRED_HOLD")
    except (OSError, UnicodeError) as exc:
        raise WorkerError("GOLD48_RUNTIME_ADAPTER_MOUNT_INSPECT_HOLD") from exc
    return {
        "mount_point": str(adapter_dir),
        "read_only": True,
        "weight_size_bytes": weight.st_size,
        "config_size_bytes": config.st_size,
        "weight_sha256_verified_by_mount_probe": False,
    }


def verify_atomic_private_publication_before_spend(root: Path) -> None:
    """Test the EXISTING OutputManager on the actual mounted filesystem.

    It must support mode-0600 durable, create-only publication and refusal to
    overwrite before a one-time Owner grant is spent. Test data is constant and
    synthetic; no model, source text, private IDs, or Owner receipt is touched.
    """
    _validate_job_local_private_root(root)
    path = root / (".gold48-atomic-probe-" + secrets.token_hex(20))
    written = False
    try:
        first = OutputManager.write_safe(
            path,
            {"schema": "storyforge_gold48_atomic_publication_probe_v1",
             "not_a_generation_or_owner_receipt": True},
            mode=0o600,
        )
        written = True
        _check(first.mode == 0o600,
               "GOLD48_ATOMIC_PUBLICATION_MODE_HOLD")
        # A duplicate publication MUST be rejected without changing the file.
        try:
            OutputManager.write_safe(
                path, {"schema": "duplicate_must_be_rejected"}, mode=0o600,
            )
        except ValueError as exc:
            _check(str(exc) == "OUTPUT_ALREADY_EXISTS",
                   "GOLD48_ATOMIC_PUBLICATION_NO_REPLACE_HOLD")
        else:
            raise WorkerError("GOLD48_ATOMIC_PUBLICATION_NO_REPLACE_HOLD")
    except (ValueError, OSError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_ATOMIC_PUBLICATION_UNSUPPORTED_HOLD") from exc
    finally:
        if written:
            try:
                path.unlink()
                _check(not path.exists() and not path.is_symlink(),
                       "GOLD48_ATOMIC_PUBLICATION_CLEANUP_HOLD")
            except OSError as exc:
                raise WorkerError("GOLD48_ATOMIC_PUBLICATION_CLEANUP_HOLD") from exc


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
    # This attests only that Owner accepted the EXISTING limited provenance.
    # The provider RO mount and current remote adapter bytes remain unverified
    # until exact runtime adapter bytes are checked in the Loader.
    _check(
        adapter_bindings.get("status") ==
            "OWNER_GOLD48_ADAPTER_BINDINGS_ACCEPTED__MOUNT_PENDING"
        and adapter_bindings.get("owner_receipt_verified") is True
        and adapter_bindings.get("provider_volume_attestation_verified") is False
        and adapter_bindings.get("current_remote_weight_bytes_verified_all_three") is False,
        "GOLD48_OWNER_BINDING_LIMITED_ACCEPTANCE_REQUIRED_HOLD",
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
    _check(
        auth.payload["execution_environment"] == PRODUCTION_SCOPE
        and auth.payload["gpu_authorized"] is True
        and auth.payload["inference_authorized"] is True,
        "GOLD48_PRODUCTION_GPU_SCOPE_REQUIRED_HOLD",
    )
    verify_gold48_binding_source_evidence(adapter_bindings, source_evidence_paths)
    measured_sha, versions = verify_current_dependency_install(
        runtime_lock_path=runtime_lock_path,
        runtime_contract_path=runtime_contract_path,
        owner_scope=auth.payload,
    )
    _check(measured_sha == lock_sha, "GOLD48_LOCK_SHA_DISAGREEMENT_HOLD")
    # Provider dynamic attestation is not required under the reviewed
    # single-Owner Mac dispatch policy. The Owner-signed image digest and
    # live package pins are checked here. Actual HF Inspect is checked by
    # Mac independently prior to quality-evaluation admission.
    mount_observation = verify_current_readonly_adapter_mount(
        role=model_role,
        adapter_dir=(
            None if model_role == "base"
            else Path(adapter_bindings["arms"][model_role]["local_dir"])
        ),
    )
    _validate_job_local_ledger_root()
    # Both LOCAL publication destinations must prove the real atomic IO contract
    # before consuming a single-use signed Owner authorization.
    verify_atomic_private_publication_before_spend(JOB_LOCAL_CONSUMPTION_ROOT)
    verify_atomic_private_publication_before_spend(output_path.parent)
    spent = JOB_LOCAL_CONSUMPTION_ROOT / (
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
        "current_job_adapter_ro_mount_observation": mount_observation,
        "runtime_lock_sha256": lock_sha,
        "runtime_packages_measured": versions,
        "provider_image_measurement_receipt_sha256": None,
        "runtime_image_digest_owner_signed": image_digest,
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

    The job-local spend is create-only. The Owner Mac guarantees no retry
    across Jobs. A permit alone is not enough:
    re-verify pinned Owner signature and measured local package versions.
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
    _validate_job_local_ledger_root()
    expected_path = JOB_LOCAL_CONSUMPTION_ROOT / (
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
           and spent.get("current_job_adapter_ro_mount_observation") ==
               verify_current_readonly_adapter_mount(
                   role=auth.payload["model_role"],
                   adapter_dir=adapter_dir,
               )
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
    _check(spent["runtime_lock_sha256"] == lock_sha
           and spent["runtime_packages_measured"] == versions
           and spent["provider_image_measurement_receipt_sha256"] is None
           and spent["runtime_image_digest_owner_signed"] ==
               auth.payload["runtime_image_digest"],
           "GOLD48_RUNTIME_MEASUREMENT_CHANGED_HOLD")
    _check(_ISSUED_ONE_SHOT_PERMITS.get(auth.receipt_sha256) ==
           permit.one_shot_nonce, "GOLD48_LOADER_ONE_SHOT_PERMIT_REUSED_HOLD")
    del _ISSUED_ONE_SHOT_PERMITS[auth.receipt_sha256]


def verify_consumed_gold48_output_grant(
    *,
    spent_receipt_path: Path,
    owner_receipt_sha256: str,
    owner_scope: dict[str, Any],
    model_role: str,
    output_path: Path,
    adapter_sha256: str | None,
    runtime_lock_sha256: str,
) -> None:
    """Read-only job-local binding for a real loaded backend before generation.

    The bridge cannot accept a caller-constructed Transformers Backend with a
    signed Owner receipt while omitting the job-local pre-GPU spend.
    """
    _validate_job_local_ledger_root()
    expected = JOB_LOCAL_CONSUMPTION_ROOT / (
        owner_receipt_sha256 + ".spent.private.json"
    )
    _check(spent_receipt_path == expected, "GOLD48_SPENT_LEDGER_PATH_HOLD")
    try:
        record = json.loads(_read_0600(expected))
    except (TypeError, ValueError) as exc:
        raise WorkerError("GOLD48_SPENT_LEDGER_READ_HOLD") from exc
    _check(
        isinstance(record, dict)
        and record.get("schema") == CONSUMPTION_SCHEMA
        and record.get("policy") == "ONE_SHOT_CONSUME_BEFORE_GPU__NO_AUTOMATIC_RETRY"
        and record.get("run_key") == owner_scope["run_key"]
        and record.get("run_id") == owner_scope["run_id"]
        and record.get("model_role") == model_role
        and record.get("owner_authorization_receipt_sha256") ==
            owner_receipt_sha256
        and record.get("output_path") == str(output_path)
        and record.get("adapter_sha256") == adapter_sha256
        and record.get("current_job_adapter_ro_mount_observation") ==
            verify_current_readonly_adapter_mount(
                role=model_role,
                adapter_dir=(
                    None if model_role == "base"
                    else ADAPTER_MOUNT_ROOT / model_role
                ),
            )
        and record.get("runtime_lock_sha256") == runtime_lock_sha256
        and record.get("provider_image_measurement_receipt_sha256") is None
        and record.get("runtime_image_digest_owner_signed") ==
            owner_scope["runtime_image_digest"]
        and record.get("max_model_calls") == 48
        and isinstance(record.get("runtime_packages_measured"), dict),
        "GOLD48_SPENT_LEDGER_SCOPE_MISMATCH_HOLD",
    )



def materialize_gold48_ro_input(
    *, source: Path, target: Path, expected_sha256: str,
    max_bytes: int = 16 * 1024 * 1024,
) -> None:
    """Copy an authenticated RO Bucket object to private JOB-LOCAL scratch.

    The RO FUSE layer need not preserve POSIX 0600. No synthetic approval is
    created: these bytes are later rechecked by the existing signed preflight.
    """
    _check(
        isinstance(expected_sha256, str)
        and HEX_SHA.fullmatch(expected_sha256) is not None
        and source.is_absolute() and target.is_absolute()
        and ".." not in source.parts and ".." not in target.parts
        and not source.is_symlink() and source.resolve(strict=True) == source,
        "GOLD48_RO_LOCALIZE_PATH_OR_SHA_HOLD",
    )
    _validate_job_local_private_root(target.parent)
    _check(not target.exists() and not target.is_symlink(),
           "GOLD48_RO_LOCALIZE_ALREADY_EXISTS_HOLD")
    try:
        verified = InputManager.open_verified(
            source, max_bytes=max_bytes, expected_sha256=expected_sha256,
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(target, flags, 0o600)
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(verified.read_bytes())
            out.flush()
            os.fsync(out.fileno())
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        check = InputManager.open_verified(
            target, max_bytes=max_bytes, expected_sha256=expected_sha256,
        )
        st = target.lstat()
        _check(stat.S_ISREG(st.st_mode)
               and stat.S_IMODE(st.st_mode) == 0o600
               and check.size_bytes == verified.size_bytes,
               "GOLD48_RO_LOCALIZE_READBACK_HOLD")
    except (OSError, ValueError) as exc:
        raise WorkerError("GOLD48_RO_LOCALIZE_IO_HOLD") from exc


def _validate_native_rw_result_mount(root: Path) -> None:
    """Prove the result destination is a distinct, kernel-visible RW FUSE mount.

    The Bucket is used only for transfer, NOT for POSIX atomic authorization.
    Requiring a direct mount avoids false success on ephemeral container files.
    """
    try:
        st = root.lstat()
        _check(
            root.is_absolute() and root != Path("/")
            and stat.S_ISDIR(st.st_mode)
            and not root.is_symlink()
            and root.is_mount(),
            "GOLD48_DELIVERY_RW_MOUNT_REQUIRED_HOLD",
        )
        records = []
        for line in Path("/proc/self/mountinfo").read_text(
            encoding="utf-8"
        ).splitlines():
            fields = line.split()
            if "-" not in fields:
                continue
            dash = fields.index("-")
            if len(fields) <= dash + 1 or len(fields) < 6:
                continue
            mountpoint = fields[4].replace(r"\040", " ")
            if mountpoint == str(root):
                records.append((fields[5].split(","), fields[dash + 1]))
        _check(len(records) == 1, "GOLD48_DELIVERY_RW_MOUNT_REQUIRED_HOLD")
        options, fstype = records[0]
        _check("rw" in options and fstype.startswith("fuse"),
               "GOLD48_DELIVERY_RW_BUCKET_FUSE_REQUIRED_HOLD")
    except (OSError, UnicodeError) as exc:
        raise WorkerError("GOLD48_DELIVERY_RW_MOUNT_INSPECT_HOLD") from exc


def deliver_gold48_private_result(
    *, output_path: Path, run_id: str, model_role: str,
    worker_receipt: Any,
) -> None:
    """Deliver four private objects through the native HF Job :rw volume.

    No HF_TOKEN, Job-side CLI or global lock is needed. Manifest is transferred
    last, after each object is read back from the mount and SHA-verified.
    The independent Owner Mac audit is still mandatory before evaluation.
    A partial remote output is never repaired by re-generating the same run.
    """
    from .gold48_contract_bridge import ROLES

    _check(model_role in ROLES
           and isinstance(run_id, str)
           and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", run_id)
           and output_path.name == model_role + ".private.json",
           "GOLD48_DELIVERY_SCOPE_HOLD")
    _validate_job_local_private_root(output_path.parent)
    _check(
        getattr(worker_receipt, "record_count", None) == 48
        and isinstance(getattr(worker_receipt, "output_sha256", None), str)
        and HEX_SHA.fullmatch(worker_receipt.output_sha256) is not None,
        "GOLD48_DELIVERY_WORKER_RECEIPT_HOLD",
    )
    files = (
        output_path,
        output_path.with_name(output_path.name + ".launch.private.json"),
        output_path.with_name(output_path.name + ".identity.private.json"),
    )
    entries = []
    for path in files:
        try:
            st = path.lstat()
            _check(stat.S_ISREG(st.st_mode)
                   and stat.S_IMODE(st.st_mode) == 0o600
                   and not path.is_symlink(),
                   "GOLD48_DELIVERY_PRIVATE_MODE_HOLD")
            item = InputManager.open_verified(path, max_bytes=16 * 1024 * 1024)
        except (OSError, ValueError) as exc:
            raise WorkerError("GOLD48_DELIVERY_SOURCE_READ_HOLD") from exc
        entries.append({
            "name": path.name, "sha256": item.sha256, "size_bytes": item.size_bytes,
        })
    _check(entries[0]["sha256"] == worker_receipt.output_sha256,
           "GOLD48_DELIVERY_GENERATION_SHA_HOLD")

    manifest_path = output_path.with_name(
        output_path.name + ".result-sha256-manifest.private.json"
    )
    manifest = {
        "schema": "storyforge_r60_gold48_private_result_delivery_v1",
        "run_id": run_id,
        "model_role": model_role,
        "record_count": 48,
        "files": entries,
        "owner_mac_independent_download_and_sha_audit_required": True,
    }
    try:
        OutputManager.write_safe(manifest_path, manifest, mode=0o600)
        confirmed = InputManager.open_verified(manifest_path, max_bytes=8192)
    except (OSError, ValueError) as exc:
        raise WorkerError("GOLD48_DELIVERY_MANIFEST_CREATE_HOLD") from exc
    entries.append({
        "name": manifest_path.name,
        "sha256": confirmed.sha256, "size_bytes": confirmed.size_bytes,
    })

    mount = BUCKET_RESULT_MOUNT
    _validate_native_rw_result_mount(mount)
    for source, entry in zip((*files, manifest_path), entries):
        remote = mount / entry["name"]
        _check(not remote.exists() and not remote.is_symlink(),
               "GOLD48_DELIVERY_REMOTE_ALREADY_EXISTS_HOLD")
        try:
            verified = InputManager.open_verified(
                source, max_bytes=16 * 1024 * 1024,
                expected_sha256=entry["sha256"],
            )
            # No POSIX mode or dir fsync requirement on the Bucket FUSE.
            # The local source already passed those requirements.
            fd = os.open(remote, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(verified.read_bytes())
                output.flush()
            observed = InputManager.open_verified(
                remote, max_bytes=16 * 1024 * 1024,
                expected_sha256=entry["sha256"],
            )
            _check(observed.size_bytes == entry["size_bytes"],
                   "GOLD48_DELIVERY_REMOTE_READBACK_HOLD")
        except (OSError, ValueError) as exc:
            raise WorkerError("GOLD48_DELIVERY_UNCONFIRMED_NO_RETRY_HOLD") from exc


def run_authorized_gold48_production(
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
    expected_template_sha256: str,
):
    """ONLY production dispatcher: verify+spend -> GPU loader -> existing Worker.

    All P1 gates run synchronously BEFORE torch import/CUDA allocation.
    There is no background job launch and no implicit GPU authorization.
    """
    from .gold48_contract_bridge import run_gold48_generation_batch
    from .gold48_qwen35_loader import load_pinned_gold48_backend

    permit = authorize_and_consume_before_gpu(
        frozen=frozen, owner_freeze=owner_freeze,
        adapter_bindings=adapter_bindings, input_manifest=input_manifest,
        input_path=input_path, output_path=output_path, model_role=model_role,
        owner_authorization_receipt_path=owner_authorization_receipt_path,
        trusted_owner_public_key_pem_path=trusted_owner_public_key_pem_path,
        source_evidence_paths=source_evidence_paths,
        runtime_lock_path=runtime_lock_path,
        runtime_contract_path=runtime_contract_path,
    )
    entry = adapter_bindings["arms"][model_role]
    backend = load_pinned_gold48_backend(
        adapter_dir=permit.selected_adapter_dir,
        expected_adapter_sha256=entry["expected_sha256"],
        expected_template_sha256=expected_template_sha256,
        launch_permit=permit,
    )
    receipt = run_gold48_generation_batch(
        frozen=frozen, owner_freeze=owner_freeze,
        adapter_bindings=adapter_bindings, input_manifest=input_manifest,
        input_path=input_path, output_path=output_path, model_role=model_role,
        backend=backend,
        owner_authorization_receipt_path=owner_authorization_receipt_path,
        trusted_owner_public_key_pem_path=trusted_owner_public_key_pem_path,
        runtime_lock_path=runtime_lock_path,
        runtime_image_digest=permit.signed_scope["runtime_image_digest"],
        source_evidence_paths=source_evidence_paths,
    )
    # No SUCCESS return while private output remains only in ephemeral scratch.
    deliver_gold48_private_result(
        output_path=output_path, run_id=permit.signed_scope["run_id"],
        model_role=model_role, worker_receipt=receipt,
    )
    return receipt

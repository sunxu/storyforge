"""Owner Mac, CPU-only readback of ONE Gold48 arm; no generation or submit.

Reuses existing HF remote_set, bounded InputManager, and Gold48 Worker receipt
parser. The remotely transferred Bucket objects are not a POSIX ledger.
Downloaded bytes remain private; stdout reports SAFE status only.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import r60_common2_wrapped_hf_cli as shared

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    MODEL,
    REVISION,
    ROLES,
    _read_existing_gold48_output,
    read_private_contract,
)
from storyforge_dataset.hf_runtime.inputs import InputManager

BUCKET = "adradar/storyforge-training"
PREFIX = "experiments/r60-gold48/outputs"
SCHEMA = "storyforge_r60_gold48_owner_download_audit_safe_v1"
MANIFEST_SCHEMA = "storyforge_r60_gold48_private_result_delivery_v1"
SHA = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}\Z")


class AuditHold(ValueError):
    pass


def _check(condition: bool, code: str) -> None:
    if not condition:
        raise AuditHold(code)


def _names(role: str) -> tuple[str, ...]:
    stem = role + ".private.json"
    return (
        stem,
        stem + ".launch.private.json",
        stem + ".identity.private.json",
        stem + ".result-sha256-manifest.private.json",
    )


def _read_json(path: Path, max_bytes: int = 16 * 1024 * 1024) -> dict:
    data = InputManager.open_verified(path, max_bytes=max_bytes).read_bytes()
    obj = InputManager.validate_json(data)
    _check(type(obj) is dict, "OWNER_REMOTE_JSON_SCHEMA_HOLD")
    return obj


def audit(run_id: str, model_role: str, root: Path, input_manifest: Path, *, api=None) -> dict:
    """Read-only remote check then create-only local download and SHA audit."""
    _check(bool(RUN_ID.fullmatch(run_id)) and model_role in ROLES,
           "OWNER_RESULT_SCOPE_HOLD")
    _check(root.is_absolute() and root.is_dir()
           and not root.is_symlink() and stat.S_IMODE(root.stat().st_mode) == 0o700,
           "OWNER_PRIVATE_ROOT_0700_HOLD")
    _check(not (root / run_id).exists() and not (root / run_id).is_symlink(),
           "OWNER_RESULT_ALREADY_DOWNLOADED_HOLD")

    expected_input = read_private_contract(input_manifest)
    _check(expected_input.get("record_count") == 48
           and isinstance(expected_input.get("sha256"), str)
           and SHA.fullmatch(expected_input["sha256"]) is not None,
           "OWNER_FROZEN_INPUT_MANIFEST_HOLD")
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    _check(shared.BUCKET == BUCKET, "OWNER_SHARED_BUCKET_HOLD")
    prefix = f"{PREFIX}/{run_id}/"
    names = _names(model_role)
    _check(shared.remote_set(api, prefix) == set(names),
           "OWNER_REMOTE_RESULT_FILESET_HOLD")
    dest = root / run_id
    dest.mkdir(mode=0o700, exist_ok=False)
    paths = {}
    for name in names:
        uri = f"hf://buckets/{BUCKET}/{prefix}{name}"
        target = dest / name
        result = subprocess.run(
            ["hf", "buckets", "cp", uri, str(target)],
            capture_output=True, text=True, timeout=300, check=False,
        )
        _check(result.returncode == 0 and not target.is_symlink()
               and target.is_file(), "OWNER_REMOTE_DOWNLOAD_HOLD")
        target.chmod(0o600)
        paths[name] = target

    manifest = _read_json(paths[names[-1]], max_bytes=8192)
    _check(set(manifest) == {
        "schema", "run_id", "model_role", "record_count", "files",
        "owner_mac_independent_download_and_sha_audit_required",
    } and manifest["schema"] == MANIFEST_SCHEMA
        and manifest["run_id"] == run_id
        and manifest["model_role"] == model_role
        and manifest["record_count"] == 48
        and manifest["owner_mac_independent_download_and_sha_audit_required"] is True
        and isinstance(manifest["files"], list)
        and len(manifest["files"]) == 3, "OWNER_REMOTE_MANIFEST_SCHEMA_HOLD")
    for row, name in zip(manifest["files"], names[:3]):
        _check(isinstance(row, dict) and set(row) == {
            "name", "size_bytes", "sha256",
        } and row["name"] == name
            and type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= 16 * 1024 * 1024
            and isinstance(row["sha256"], str)
            and SHA.fullmatch(row["sha256"]) is not None,
            "OWNER_REMOTE_MANIFEST_FILES_HOLD")
        verified = InputManager.open_verified(
            paths[name], max_bytes=16 * 1024 * 1024,
            expected_sha256=row["sha256"],
        )
        _check(verified.size_bytes == row["size_bytes"],
               "OWNER_REMOTE_RESULT_BYTES_HOLD")

    output = paths[names[0]]
    identity = _read_json(paths[names[2]], max_bytes=65536)
    launch = _read_json(paths[names[1]], max_bytes=65536)
    output_sha = manifest["files"][0]["sha256"]
    _check(
        identity.get("schema") == "storyforge_r60_gold48_generation_identity_private_v1"
        and identity.get("run_id") == run_id
        and identity.get("selected_model_role") == model_role
        and identity.get("output_sha256") == output_sha
        and identity.get("input_sha256") == expected_input["sha256"]
        and identity.get("record_count") == 48
        and identity.get("runtime_image_measured") is False
        and identity.get("provider_image_attestation_sha256") is None
        and identity.get("runtime_image_identity_source") ==
            "OWNER_SIGNED_CONFIGURATION_ONLY__NOT_MEASURED"
        and identity.get("owner_mac_independent_job_image_inspect_required") is True
        and launch.get("schema") == "storyforge_r60_gold48_generation_launch_private_v1"
        and launch.get("run_id") == run_id
        and launch.get("model_role") == model_role
        and launch.get("input_sha256") == expected_input["sha256"]
        and launch.get("runtime_image_measured") is False
        and launch.get("provider_image_attestation_sha256") is None
        and launch.get("gpu_backend_executed") is True
        and launch.get("runtime_image_digest_approved") ==
            identity.get("runtime_image_digest")
        and launch.get("owner_authorization_receipt_sha256") ==
            identity.get("owner_authorization_receipt_sha256"),
        "OWNER_REMOTE_OUTPUT_SCOPE_MISMATCH_HOLD",
    )
    receipt = _read_existing_gold48_output(
        output_path=output,
        profile={"model_profiles": {
            model_role: {"model": MODEL, "revision": REVISION},
        }},
        worker_manifest={"max_input_tokens": 30720, "max_new_tokens": 2048},
        model_role=model_role,
        gpu_started=True,
    )
    _check(receipt.output_sha256 == output_sha,
           "OWNER_REMOTE_GENERATED_OUTPUT_SHA_HOLD")
    return {
        "schema": SCHEMA,
        "status": "OWNER_GOLD48_RESULT_BYTES_AUDITED__IMAGE_INSPECT_PENDING",
        "run_id": run_id,
        "model_role": model_role,
        "file_count": 4,
        "record_count": receipt.record_count,
        "generation_status": receipt.status,
        "finish_reason_counts": receipt.finish_reason_counts,
        "owner_signature_independently_reverified": False,
        "owner_mac_job_image_inspect_verified": False,
        "provider_signature_independently_reverified": False,
        "quality_v1_admitted": 0,
        "gpu_started": False,
        "model_calls": 0,
        "private_values_emitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-role", required=True, choices=ROLES)
    parser.add_argument("--owner-download-root", type=Path, required=True)
    parser.add_argument("--frozen-input-manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(
            args.run_id, args.model_role,
            args.owner_download_root, args.frozen_input_manifest,
        )
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
        report = {
            "schema": SCHEMA, "status": "HOLD",
            "reason_code": "OWNER_GOLD48_REMOTE_RESULT_AUDIT_HOLD",
            "quality_v1_admitted": 0, "gpu_started": False,
            "model_calls": 0, "private_values_emitted": False,
        }
        rc = 2
    print(json.dumps(report, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

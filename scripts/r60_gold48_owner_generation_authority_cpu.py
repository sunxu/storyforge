"""Owner-local Gold48 authority: check sources, accept binding, sign ONE arm.

This script MUST run on the trusted Owner computer. It never submits inference,
runs a GPU, fetches a checkpoint, or reads the separate historical reference.
No keys, private hashes, or story text are printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    ROLES,
    WorkerError,
    _validate_frozen,
    _validate_bindings,
    prepare_gold48_generation_contract,
    read_private_contract,
    verify_gold48_binding_source_evidence,
)
from storyforge_dataset.generation_eval.gold48_owner_receipt import (
    make_owner_scope,
    owner_sign_create_only,
)
from storyforge_dataset.hf_runtime.inputs import InputManager
from storyforge_dataset.hf_runtime.outputs import OutputManager

from r60_gold48_generation_input_materialize_cpu import _read_frozen

ACCEPTED_STATUS = "OWNER_GOLD48_ADAPTER_BINDINGS_ACCEPTED__MOUNT_PENDING"
RUN_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{7,63}\Z")


def _read_manifest(path: Path) -> dict:
    return read_private_contract(path, max_bytes=2 * 1024 * 1024)


def _inputs(args):
    frozen = _read_frozen(args.frozen_profile)
    owner = read_private_contract(args.owner_freeze)
    bindings = read_private_contract(args.adapter_bindings)
    manifest = _read_manifest(args.input_manifest)
    evidence = {
        "r46_v02": args.r46_evidence,
        "r54_v03a": args.r54_evidence,
        "r60_base336": args.r60_evidence,
    }
    _validate_frozen(frozen, owner)
    _validate_bindings(frozen, bindings)
    verify_gold48_binding_source_evidence(bindings, evidence)
    prepare_gold48_generation_contract(
        frozen=frozen, owner_freeze=owner, adapter_bindings=bindings,
        input_manifest=manifest, input_path=args.input_jsonl,
        model_role="base",
    )
    return frozen, owner, bindings, manifest


def _accept(args):
    if args.explicit_owner_accept is not True:
        raise WorkerError("GOLD48_EXPLICIT_OWNER_ACCEPT_REQUIRED")
    frozen, owner, bindings, manifest = _inputs(args)
    if (bindings.get("status") != "CANDIDATE_PENDING_OWNER_SOURCE_ATTESTATION_AND_MOUNT"
            or bindings.get("owner_receipt_verified") is not False
            or bindings.get("provider_volume_attestation_verified") is not False
            or bindings.get("current_remote_weight_bytes_verified_all_three") is not False):
        raise WorkerError("GOLD48_CANDIDATE_STATUS_HOLD")
    accepted = dict(bindings)
    accepted["status"] = ACCEPTED_STATUS
    accepted["owner_receipt_verified"] = True
    accepted["provider_volume_attestation_verified"] = False
    accepted["current_remote_weight_bytes_verified_all_three"] = False
    accepted["owner_accepted_scope"] = "SCOPED_HISTORICAL_SHA_RECEIPTS_NOT_REMOTE_BYTES"
    accepted["owner_frozen_profile_canonical_sha256"] = hashlib.sha256(
        json.dumps(frozen, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    try:
        OutputManager.write_safe(args.accepted_output, accepted, mode=0o600)
    except (OSError, ValueError) as exc:
        raise WorkerError("GOLD48_BINDING_ACCEPT_CREATE_ONLY_HOLD") from exc
    return "OWNER_GOLD48_ADAPTER_BINDING_ACCEPTED__MOUNT_UNVERIFIED"


def _sign(args):
    if args.explicit_owner_generation_authorization is not True:
        raise WorkerError("GOLD48_EXPLICIT_OWNER_GENERATION_APPROVAL_REQUIRED")
    frozen, owner, bindings, manifest = _inputs(args)
    if bindings.get("status") != ACCEPTED_STATUS or bindings.get("owner_receipt_verified") is not True:
        raise WorkerError("GOLD48_BINDINGS_NOT_OWNER_ACCEPTED_HOLD")
    if args.model_role not in ROLES or not isinstance(args.run_id, str) or not RUN_ID.fullmatch(args.run_id):
        raise WorkerError("GOLD48_OWNER_RUN_SCOPE_HOLD")
    if args.output_directory.name != args.run_id or not args.output_directory.is_absolute():
        raise WorkerError("GOLD48_OWNER_OUTPUT_SCOPE_HOLD")
    if args.output_filename != args.model_role + ".private.json":
        raise WorkerError("GOLD48_OWNER_OUTPUT_FILENAME_HOLD")
    # The lock hash and image digest are taken from a pinned, reviewed candidate.
    contract = json.loads(InputManager.open_verified(
        args.dependency_contract, max_bytes=65536,
    ).read_bytes())
    lock_sha = InputManager.open_verified(
        args.dependency_lock, max_bytes=8 * 1024 * 1024,
    ).sha256
    if (contract.get("schema") !=
            "storyforge_r60_gold48_inference_cpu_dependency_contract_v1"
            or contract.get("lock_sha256") != lock_sha
            or contract.get("base_image") != args.runtime_image
            or contract.get("formal_inference_authorized") is not False):
        raise WorkerError("GOLD48_RUNTIME_LOCK_PIN_HOLD")
    start = datetime.now(UTC)
    scope = make_owner_scope(
        frozen=frozen, owner_freeze=owner, adapter_bindings=bindings,
        input_manifest=manifest, model_role=args.model_role,
        run_id=args.run_id, output_filename=args.output_filename,
        output_directory=str(args.output_directory),
        dependency_lock_sha256=lock_sha, runtime_image_digest=args.runtime_image.removeprefix(
            "pytorch/pytorch@"
        ),
        issued_at_utc=start.isoformat(),
        expires_at_utc=(start + timedelta(hours=args.expiry_hours)).isoformat(),
    )
    if not 0 < args.expiry_hours <= 48:
        raise WorkerError("GOLD48_APPROVAL_EXPIRY_HOLD")
    owner_sign_create_only(
        scope=scope, private_key_path=args.owner_private_ed25519_key,
        receipt_path=args.signed_receipt_output,
    )
    return "OWNER_GOLD48_ONE_ROLE_SIGNED_RECEIPT_CREATE_ONLY"


def _arguments(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", required=True, choices=("accept-bindings", "sign-one-arm"))
    p.add_argument("--frozen-profile", required=True, type=Path)
    p.add_argument("--owner-freeze", required=True, type=Path)
    p.add_argument("--adapter-bindings", required=True, type=Path)
    p.add_argument("--input-manifest", required=True, type=Path)
    p.add_argument("--input-jsonl", required=True, type=Path)
    p.add_argument("--r46-evidence", required=True, type=Path)
    p.add_argument("--r54-evidence", required=True, type=Path)
    p.add_argument("--r60-evidence", required=True, type=Path)
    p.add_argument("--explicit-owner-accept", action="store_true")
    p.add_argument("--accepted-output", type=Path)
    p.add_argument("--explicit-owner-generation-authorization", action="store_true")
    p.add_argument("--model-role", choices=ROLES)
    p.add_argument("--run-id")
    p.add_argument("--output-directory", type=Path)
    p.add_argument("--output-filename")
    p.add_argument("--dependency-lock", type=Path)
    p.add_argument("--dependency-contract", type=Path)
    p.add_argument("--runtime-image")
    p.add_argument("--expiry-hours", type=int, default=1)
    p.add_argument("--owner-private-ed25519-key", type=Path)
    p.add_argument("--signed-receipt-output", type=Path)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _arguments(argv)
    try:
        if args.mode == "accept-bindings":
            if args.accepted_output is None:
                raise WorkerError("GOLD48_OWNER_ACCEPT_OUTPUT_REQUIRED")
            status = _accept(args)
        else:
            required = (
                args.model_role, args.run_id, args.output_directory,
                args.output_filename, args.dependency_lock,
                args.dependency_contract, args.runtime_image,
                args.owner_private_ed25519_key, args.signed_receipt_output,
            )
            if any(value is None for value in required):
                raise WorkerError("GOLD48_OWNER_SIGNATURE_SCOPE_FIELDS_REQUIRED")
            status = _sign(args)
        print(json.dumps({
            "schema": "storyforge_gold48_owner_generation_authority_cpu_safe_v1",
            "status": status,
            "gpu_started": False, "model_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 0
    except (OSError, TypeError, ValueError, KeyError):
        print(json.dumps({
            "schema": "storyforge_gold48_owner_generation_authority_cpu_safe_v1",
            "status": "HOLD", "reason_code": "OWNER_GENERATION_AUTHORITY_HOLD",
            "gpu_started": False, "model_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

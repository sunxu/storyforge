"""Thin Gold48 HF Job entry: RO private staging -> existing authorized dispatcher.

No new model backend, sampling loop, HF API submitter, or retry manager.
The trusted Owner Mac prepares/stages these fixed files. Historical original
replies MUST NOT be staged. This entry only reads the signed generation inputs.
The "check" action never imports torch, starts GPU, or creates private scratch.
No dynamic Provider signature or extra RO handoff is required.
The Owner Mac must independently inspect the launched HF Job before admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from storyforge_dataset.generation_eval import gold48_runtime_gate as gate
from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    ROLES,
    read_private_contract,
)
from storyforge_dataset.generation_eval.gold48_owner_receipt import (
    APPROVAL_MODE,
    APPROVAL_SCHEMA,
    RUN_ID,
)
from storyforge_dataset.generation_eval.worker import WorkerError
from storyforge_dataset.hf_runtime.inputs import InputManager

SCHEMA = "storyforge_r60_gold48_hf_gpu_worker_entry_safe_v1"
RO_STAGE = Path("/input/gold48")
SCRATCH = Path("/tmp/storyforge-gold48-private")
FROZEN_GIT_BLOB_SHA = "45e068d8ee7745f026455e887ca914aa82ab7fe1"
STAGED = {
    "frozen_profile.json": 65536,
    "owner_freeze.private.json": 2 * 1024 * 1024,
    "adapter_bindings.private.json": 2 * 1024 * 1024,
    "input_manifest.private.json": 65536,
    "input.private.jsonl": 16 * 1024 * 1024,
    "r46_evidence.private.json": 65536,
    "r54_evidence.private.json": 65536,
    "r60_evidence.private.json": 65536,
    "owner_authorization.private.json": 65536,
    "runtime_lock.hashes": 8 * 1024 * 1024,
    "runtime_contract.json": 65536,
    "token_preflight.private.json": 65536,
}
ROLES_FROM_FILES = {
    "r46_v02": "r46_evidence.private.json",
    "r54_v03a": "r54_evidence.private.json",
    "r60_base336": "r60_evidence.private.json",
}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _hold(ok: bool, code: str) -> None:
    if not ok:
        raise WorkerError(code)


def _json(path: Path, max_bytes: int) -> dict:
    value = InputManager.validate_json(
        InputManager.open_verified(path, max_bytes=max_bytes).read_bytes()
    )
    _hold(type(value) is dict, "GOLD48_STAGE_JSON_HOLD")
    return value


def _require_direct_ro_fuse_mount(root: Path) -> None:
    """Verify the frozen Gold48 Stage is a direct, kernel-visible RO mount."""
    try:
        info = root.lstat()
        _hold(stat.S_ISDIR(info.st_mode) and not root.is_symlink()
              and root.is_mount(), "GOLD48_ENTRY_RO_MOUNT_REQUIRED_HOLD")
        matches = []
        for line in Path("/proc/self/mountinfo").read_text(
            encoding="utf-8"
        ).splitlines():
            fields = line.split()
            if "-" not in fields:
                continue
            dash = fields.index("-")
            if (len(fields) > dash + 1 and len(fields) >= 6
                    and fields[4].replace(r"\040", " ") == str(root)):
                matches.append((fields[5].split(","), fields[dash + 1]))
        _hold(len(matches) == 1 and "ro" in matches[0][0]
              and matches[0][1].startswith("fuse"),
              "GOLD48_ENTRY_RO_MOUNT_REQUIRED_HOLD")
    except (OSError, UnicodeError) as exc:
        raise WorkerError("GOLD48_ENTRY_RO_MOUNT_INSPECT_HOLD") from exc


def validate_ro_bundle(stage: Path, run_id: str, role: str) -> dict:
    """Check the ONE fixed RO mount and manifest contract, before any GPU."""
    _hold(bool(RUN_ID.fullmatch(run_id)) and role in ROLES,
          "GOLD48_ENTRY_RUN_SCOPE_HOLD")
    _hold(stage == RO_STAGE, "GOLD48_ENTRY_EXACT_STAGE_HOLD")
    _require_direct_ro_fuse_mount(stage)
    try:
        observed = {p.name for p in stage.iterdir()}
        _hold(observed == set(STAGED),
              "GOLD48_ENTRY_EXACT_INPUT_FILESET_HOLD")
        for name, bound in STAGED.items():
            path = stage / name
            info = path.lstat()
            _hold(stat.S_ISREG(info.st_mode) and not path.is_symlink()
                  and 0 < info.st_size <= bound,
                  "GOLD48_ENTRY_STAGED_FILE_TYPE_OR_SIZE_HOLD")
        frozen_bytes = InputManager.open_verified(
            stage / "frozen_profile.json", max_bytes=65536
        ).read_bytes()
        git_sha = hashlib.sha1(
            b"blob " + str(len(frozen_bytes)).encode() + b"\0" + frozen_bytes
        ).hexdigest()
        _hold(git_sha == FROZEN_GIT_BLOB_SHA,
              "GOLD48_ENTRY_FROZEN_PROFILE_BLOB_HOLD")
        input_manifest = _json(stage / "input_manifest.private.json", 65536)
        _hold(input_manifest.get("schema") ==
              "storyforge_r60_gold48_generation_input_manifest_private_v1"
              and input_manifest.get("record_count") == 48
              and isinstance(input_manifest.get("sha256"), str)
              and SHA.fullmatch(input_manifest["sha256"]) is not None,
              "GOLD48_ENTRY_INPUT_MANIFEST_HOLD")
        InputManager.open_verified(
            stage / "input.private.jsonl", max_bytes=16 * 1024 * 1024,
            expected_sha256=input_manifest["sha256"],
        )
        owner = _json(stage / "owner_authorization.private.json", 65536)
        scope = owner.get("payload")
        _hold(set(owner) == {"schema", "approval_mode", "payload"}
              and owner.get("schema") == APPROVAL_SCHEMA
              and owner.get("approval_mode") == APPROVAL_MODE
              and isinstance(scope, dict)
              and scope.get("run_id") == run_id
              and scope.get("model_role") == role
              and scope.get("output_directory") ==
                  str(SCRATCH / "outputs" / run_id)
              and scope.get("output_filename") == role + ".private.json",
              "GOLD48_ENTRY_OWNER_SCOPE_PRECHECK_HOLD")
        details = _json(stage / "token_preflight.private.json", 65536)
        template_sha = details.get("chat_template_sha256_PRIVATE")
        _hold(details.get("schema") ==
              "storyforge_r60_p2_gold48_token_preflight_private_v1"
              and details.get("tokenizer_revision") ==
                  "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
              and isinstance(template_sha, str)
              and SHA.fullmatch(template_sha) is not None,
              "GOLD48_ENTRY_TEMPLATE_RECEIPT_HOLD")
        lock = InputManager.open_verified(
            stage / "runtime_lock.hashes", max_bytes=8 * 1024 * 1024,
            expected_sha256=gate.FROZEN_RUNTIME_LOCK_SHA256,
        )
        _hold(lock.size_bytes > 0, "GOLD48_ENTRY_RUNTIME_LOCK_HOLD")
        return {
            "manifest_sha": input_manifest["sha256"],
            "template_sha": template_sha,
            "owner_scope": scope,
        }
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_ENTRY_RO_INPUT_READ_HOLD") from exc


def run(stage: Path, run_id: str, role: str, *, execute: bool) -> dict:
    validated = validate_ro_bundle(stage, run_id, role)
    if not execute:
        return {"status": "GOLD48_FIXED_RO_STAGE_VERIFIED__NO_GPU",
                "gpu_started": False, "model_calls": 0, "record_count": 0}
    _hold(not SCRATCH.exists() and not SCRATCH.is_symlink(),
          "GOLD48_ENTRY_SCRATCH_ALREADY_EXISTS_HOLD")
    SCRATCH.mkdir(mode=0o700)
    input_dir = SCRATCH / "inputs"
    output_base = SCRATCH / "outputs"
    output_dir = output_base / run_id
    for path in (input_dir, output_base, output_dir, gate.JOB_LOCAL_CONSUMPTION_ROOT):
        path.mkdir(mode=0o700)
        gate._validate_job_local_private_root(path)
    materialized = {}
    for name, maximum in STAGED.items():
        source = stage / name
        verified = InputManager.open_verified(source, max_bytes=maximum)
        target = input_dir / name
        gate.materialize_gold48_ro_input(
            source=source, target=target, expected_sha256=verified.sha256,
            max_bytes=maximum,
        )
        materialized[name] = target
    # Input SHA is anchored by the Owner-frozen manifest.
    _hold(InputManager.open_verified(
        materialized["input.private.jsonl"], max_bytes=16 * 1024 * 1024,
        expected_sha256=validated["manifest_sha"]
    ).size_bytes > 0, "GOLD48_ENTRY_INPUT_LOCAL_SHA_HOLD")
    frozen = read_private_contract(materialized["frozen_profile.json"])
    owner_freeze = read_private_contract(materialized["owner_freeze.private.json"])
    bindings = read_private_contract(materialized["adapter_bindings.private.json"])
    manifest = read_private_contract(materialized["input_manifest.private.json"])
    receipt = gate.run_authorized_gold48_production(
        frozen=frozen, owner_freeze=owner_freeze, adapter_bindings=bindings,
        input_manifest=manifest,
        input_path=materialized["input.private.jsonl"],
        output_path=output_dir / (role + ".private.json"),
        model_role=role,
        owner_authorization_receipt_path=materialized[
            "owner_authorization.private.json"
        ],
        trusted_owner_public_key_pem_path=None,
        source_evidence_paths={
            key: materialized[name] for key, name in ROLES_FROM_FILES.items()
        },
        runtime_lock_path=materialized["runtime_lock.hashes"],
        runtime_contract_path=materialized["runtime_contract.json"],
        expected_template_sha256=validated["template_sha"],
    )
    return {
        "status": "GOLD48_ONE_ARM_GENERATED_AND_TRANSFERRED__OWNER_AUDIT_PENDING",
        "gpu_started": receipt.gpu_started,
        "model_calls": receipt.record_count,
        "record_count": receipt.record_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "execute"))
    parser.add_argument("--stage", type=Path, default=RO_STAGE)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-role", choices=ROLES, required=True)
    parser.add_argument("--explicit-owner-gpu-execution", action="store_true")
    args = parser.parse_args(argv)
    try:
        _hold(args.action != "execute" or args.explicit_owner_gpu_execution,
              "GOLD48_ENTRY_OWNER_EXECUTION_FLAG_REQUIRED")
        result = run(args.stage, args.run_id, args.model_role,
                     execute=args.action == "execute")
        code = 0
    # The safe main must not surface private tracebacks.
    except Exception:  # noqa: BLE001
        result = {
            "status": "HOLD",
            "reason_code": "GOLD48_OWNER_STAGE_AUTHORIZATION_OR_RUNTIME_HOLD",
            # Execution may fail after CUDA or model calls: never claim false.
            "gpu_started": False if args.action == "check" else None,
            "model_calls": 0 if args.action == "check" else None,
            "record_count": 0,
        }
        code = 42
    result.update(
        schema=SCHEMA, private_values_emitted=False,
        training_started=False, quality_v1_admitted=0,
    )
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

"""Owner-local CPU-only materializer for the already-frozen Gold48 inputs.

Only copies reconstructed messages from the existing Owner-frozen draft; it
never generates a prompt, reads original historical answers, submits HF Jobs,
loads models, or modifies the frozen files. Outputs are create-only mode 0600.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    WorkerError,
    build_gold48_frozen_input_payload,
    read_private_contract,
)
from storyforge_dataset.hf_runtime.inputs import InputManager

GIT_BLOB_SHA = "45e068d8ee7745f026455e887ca914aa82ab7fe1"


def _read_frozen(path: Path) -> dict:
    try:
        raw = InputManager.open_verified(path, max_bytes=65536).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw)
        if blob.hexdigest() != GIT_BLOB_SHA:
            raise WorkerError("GOLD48_FROZEN_PROFILE_GIT_BLOB_HOLD")
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise WorkerError("GOLD48_FROZEN_PROFILE_SCHEMA_HOLD")
        return obj
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_FROZEN_PROFILE_READ_HOLD") from exc


def _read_owner_draft(path: Path, expected_sha: str) -> dict:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            raise WorkerError("GOLD48_PRIVATE_DRAFT_MODE_HOLD")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise WorkerError("GOLD48_OWNER_DRAFT_SHA_REQUIRED")
        raw = InputManager.open_verified(
            path, max_bytes=32 * 1024 * 1024, expected_sha256=expected_sha
        ).read_bytes()
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise WorkerError("GOLD48_PRIVATE_DRAFT_SCHEMA_HOLD")
        return result
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, WorkerError):
            raise
        raise WorkerError("GOLD48_OWNER_DRAFT_SHA_OR_READ_HOLD") from exc


def _create_only(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if not hasattr(os, "O_NOFOLLOW"):
        raise WorkerError("GOLD48_PRIVATE_CREATE_NOFOLLOW_REQUIRED")
    try:
        fd = os.open(path, flags | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise WorkerError("GOLD48_PRIVATE_CREATE_ONLY_HOLD") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen-profile", type=Path, required=True)
    p.add_argument("--owner-freeze", type=Path, required=True)
    p.add_argument("--reconstructed-draft", type=Path, required=True)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        root = args.private_root
        parent = args.output_dir.parent
        if (not root.is_absolute() or root.is_symlink()
                or args.output_dir.is_symlink() or args.output_dir.exists()
                or parent.is_symlink()
                or not parent.resolve(strict=True).is_relative_to(
                    root.resolve(strict=True)
                )):
            raise WorkerError("GOLD48_OUTPUT_PRIVATE_ROOT_OR_CREATE_ONLY_HOLD")
        root_stat = root.stat()
        if (not stat.S_ISDIR(root_stat.st_mode)
                or stat.S_IMODE(root_stat.st_mode) & 0o077):
            raise WorkerError("GOLD48_PRIVATE_ROOT_MODE_HOLD")
        frozen = _read_frozen(args.frozen_profile)
        owner = read_private_contract(args.owner_freeze, max_bytes=2 * 1024 * 1024)
        draft = _read_owner_draft(
            args.reconstructed_draft, owner.get("reconstructed_draft_sha256_PRIVATE")
        )
        payload, manifest = build_gold48_frozen_input_payload(
            frozen=frozen, owner_freeze=owner, reconstructed_draft=draft
        )
        os.mkdir(args.output_dir, mode=0o700)
        _create_only(args.output_dir / "GOLD48_GENERATION_INPUTS_PRIVATE.jsonl", payload)
        _create_only(
            args.output_dir / "GOLD48_GENERATION_INPUT_MANIFEST_PRIVATE.json",
            json.dumps(
                manifest, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8") + b"\n",
        )
        receipt = {
            "schema": "storyforge_r60_gold48_input_materialization_safe_v1",
            "status": "GOLD48_PRIVATE_WORKER_INPUTS_MATERIALIZED",
            "record_count": 48, "file_mode": "0600",
            "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
            "historical_original_reference_read": False,
            "private_values_emitted": False, "gpu_started": False,
            "model_calls": 0, "training_started": False,
        }
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (WorkerError, OSError, TypeError, ValueError):
        print(json.dumps({
            "schema": "storyforge_r60_gold48_input_materialization_safe_v1",
            "status": "HOLD", "reason_code": "PRIVATE_INPUT_MATERIALIZATION_HOLD",
            "private_values_emitted": False, "gpu_started": False,
            "model_calls": 0, "training_started": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

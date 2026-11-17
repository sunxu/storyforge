"""Create and verify immutable private R60 Base336 GPU stages; never submit HF Jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import r60_base336_gpu_contract as contract
import r60_common2_wrapped_hf_stage as shared_stage
from storyforge_dataset.hf_runtime import InputManager

SCHEMA = contract.STAGE_SCHEMA
REQUIREMENTS = "requirements/r60-base336-gpu.in"
TEMPLATE = "config/template.yaml"
CONFIG = contract.CONFIG_NAME
ENTRY = [
    "scripts/r60_base336_gpu_worker.sh",
    "scripts/r60_base336_gpu_worker.py",
]
EXTRA = [
    "scripts/r60_base336_gpu_contract.py",
    "scripts/hf_job_runner.py",
    "scripts/hf_smoke_guard.py",
]
RELEASE_FILES = (
    "train.jsonl",
    "validation.jsonl",
    contract.RELEASE_MANIFEST,
)
PROOF_RELATIVE = "private/proof/" + contract.PROOF_NAME
RUN_RE = contract.RUN_RE


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _copy_new(stage: Path, relative: str, raw: bytes) -> str:
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("STAGE_PATH_HOLD")
    target = stage / relative
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.parent.is_symlink() or target.exists() or target.is_symlink():
        raise ValueError("STAGE_CREATE_ONLY_HOLD")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("STAGE_NOFOLLOW_UNAVAILABLE")
    fd = os.open(target, flags | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise ValueError("STAGE_WRITE_HOLD")
            view = view[written:]
        os.fsync(fd)
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    return _sha(raw)


def _source_bytes(path: Path, maximum: int) -> bytes:
    return InputManager.open_verified(path, max_bytes=maximum).read_bytes()


def _git_commit() -> str:
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT,
        capture_output=True, text=True, timeout=10, check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True, timeout=10, check=False,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, timeout=10, check=False,
    )
    value = result.stdout.strip()
    if (
        branch.returncode or branch.stdout.strip() != "r60/common2-cpu2-owner"
        or status.returncode or status.stdout.strip()
        or result.returncode or re.fullmatch(r"[a-f0-9]{40}", value) is None
    ):
        raise ValueError("GIT_BRANCH_OR_WORKTREE_HOLD")
    return value


def verify(stage: Path, run_key: str) -> dict:
    return contract.verify_stage(stage, run_key)


def prepare(release_dir: Path, proof_receipt: Path, stage: Path, run_key: str) -> dict:
    if not RUN_RE.fullmatch(run_key) or stage.name != run_key:
        raise ValueError("RUN_KEY_HOLD")
    if stage.exists() or stage.is_symlink():
        raise ValueError("STAGE_ALREADY_EXISTS_HOLD")
    private_base = Path.home() / ".local/share/storyforge/r60/private"
    if (
        stage.parent.is_symlink() or not stage.parent.is_dir()
        or stage.parent.resolve() != private_base.resolve()
        or stat.S_IMODE(stage.parent.stat().st_mode) != 0o700
    ):
        raise ValueError("STAGE_PARENT_HOLD")
    contract.verify_release(release_dir)
    contract.verify_proof_receipt(proof_receipt)
    proof_stat = proof_receipt.lstat()
    if proof_stat.st_mode & 0o777 != 0o600:
        raise ValueError("PROOF_RECEIPT_MODE_HOLD")
    commit = _git_commit()
    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    files: dict[str, str] = {}
    try:
        dependencies = shared_stage.local_dependencies(entries=ENTRY, extras=EXTRA)
        for relative in dependencies:
            source = ROOT / relative
            if source.is_symlink() or not source.is_file():
                raise ValueError("LOCAL_CODE_MISSING_HOLD")
            files[relative] = _copy_new(
                stage, relative, _source_bytes(source, 8_000_000)
            )
        requirements = ROOT / REQUIREMENTS
        files[REQUIREMENTS] = _copy_new(
            stage, REQUIREMENTS, _source_bytes(requirements, 64_000)
        )
        template = ROOT / "configs/r60_base336_exploratory_293_43.yaml"
        template_raw = _source_bytes(template, 64_000)
        files[TEMPLATE] = _copy_new(stage, TEMPLATE, template_raw)
        files[CONFIG] = _copy_new(stage, CONFIG, contract.render_config(template_raw))

        for name in RELEASE_FILES:
            source = release_dir / name
            maximum = 4_000_000 if name.endswith(".jsonl") else contract.MAX_SAFE_BYTES
            files["private/release/" + name] = _copy_new(
                stage, "private/release/" + name, _source_bytes(source, maximum)
            )
        files[PROOF_RELATIVE] = _copy_new(
            stage, PROOF_RELATIVE, _source_bytes(proof_receipt, contract.MAX_SAFE_BYTES)
        )

        manifest = {
            "schema": SCHEMA,
            "status": "STAGED_NOT_SUBMITTED",
            "run_key": run_key,
            "git_commit": commit,
            "files": files,
            "model": contract.MODEL,
            "model_revision": contract.REVISION,
            "train_rows": contract.TRAIN_ROWS,
            "validation_rows": contract.VALIDATION_ROWS,
            "optimizer_steps": contract.optimizer_steps(),
            "input_contract": contract.INPUT_CONTRACT,
            "collator_transfer_status": contract.PROOF_STATUS,
            "collator_executed_in_this_run": False,
            "source_cpu_receipt_accepted": True,
            "private_data_contains_r50": False,
            "r50_semantic_isolation_verified": False,
            "semantic_world_isolation_verified": False,
            "reviewer_execution_independence_verified": False,
            "quality_v1_admitted": 0,
            "train_admitted": 0,
            "model_weights_in_stage": False,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
            "private_values_emitted": False,
        }
        manifest_raw = (
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        _copy_new(stage, "SHA256_MANIFEST_PRIVATE.json", manifest_raw)
        result = verify(stage, run_key)
        result["git_commit_bound"] = True
        result["stage_created"] = True
        return result
    except BaseException:
        shutil.rmtree(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("--release-dir", type=Path)
    parser.add_argument("--proof-receipt", type=Path)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--run-key", required=True)
    args = parser.parse_args()
    try:
        if args.action == "prepare" and args.release_dir and args.proof_receipt:
            result = prepare(args.release_dir, args.proof_receipt, args.stage, args.run_key)
        elif args.action == "verify":
            result = verify(args.stage, args.run_key)
        else:
            raise ValueError("ARGUMENTS_HOLD")
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - SAFE-only failure output
        print(json.dumps({
            "schema": "storyforge_r60_base336_gpu_stage_safe_v1",
            "status": "BASE336_GPU_STAGE_HOLD",
            "reason_code": "LOCAL_STAGE_OR_PROOF_HOLD",
            "train_admitted": 0,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

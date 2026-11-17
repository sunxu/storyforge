"""Read-only download and local SHA inventory for one completed R60 Base336 GPU run."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import r60_base336_gpu_cli as gpu_cli
import r60_base336_gpu_contract as contract
from hf_job_runner import check_inference_result, sha256

SCHEMA = "storyforge_r60_base336_gpu_result_audit_safe_v1"
WORKER_SCHEMA = "storyforge_r60_base336_gpu_worker_safe_v1"
WORKER_STATUS = "BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED"
AUDIT_STATUS = "BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION"
RESULT_FILES = (
    "R60_BASE336_GPU_RUNTIME_PRIVATE.log",
    "R60_BASE336_GPU_SAFE_RECEIPT_PRIVATE.json",
    "reload_prompt_PRIVATE.jsonl",
    "reload_response_PRIVATE.jsonl",
)
CHECKPOINT_FILES = (
    "README.md", "adapter_config.json", "adapter_model.safetensors",
    "additional_config.json", "args.json", "optimizer.pt", "rng_state.pth",
    "scheduler.pt", "trainer_state.json", "training_args.bin",
)
IMAGE_FILES = (
    "eval_loss.png", "eval_runtime.png", "eval_samples_per_second.png",
    "eval_steps_per_second.png", "eval_token_acc.png", "train_epoch.png",
    "train_grad_norm.png", "train_learning_rate.png", "train_loss.png",
    "train_token_acc.png", "train_total_flos.png", "train_train_loss.png",
    "train_train_runtime.png", "train_train_samples_per_second.png",
    "train_train_steps_per_second.png",
)
MIN_FREE_MARGIN = 1024 * 1024 * 1024
FALLBACK_REQUIRED_FREE = 8 * 1024 * 1024 * 1024


def safe(status: str, reason: str, **values: object) -> dict:
    return {
        "schema": SCHEMA, "status": status, "reason_code": reason,
        "run_key_validated": False, "remote_file_set_verified": False,
        "files_downloaded": 0, "files_hashed": 0, "total_bytes": 0,
        "sha256_manifest_created": False, "worker_receipt_verified": False,
        "checkpoint_verified": False, "adapter_reload_verified": False,
        "training_gpu_used": False, "audit_gpu_started": False,
        "hf_jobs_submitted": 0, "train_admitted": 0,
        "quality_v1_admitted": 0, "model_promoted": False,
        "private_values_emitted": False, **values,
    }


def expected_remote_files(found: set[str]) -> tuple[str, set[str]]:
    """Validate this run's frozen ms-swift output shape."""
    for item in found:
        path = PurePosixPath(item)
        if path.is_absolute() or not item or ".." in path.parts or "\\" in item:
            raise ValueError("RESULT_REMOTE_PATH_HOLD")
    training_dirs = {
        PurePosixPath(item).parts[1]
        for item in found
        if len(PurePosixPath(item).parts) >= 2
        and PurePosixPath(item).parts[0] == "training"
    }
    if len(training_dirs) != 1:
        raise ValueError("RESULT_TRAINING_RUN_DIR_HOLD")
    run_dir = next(iter(training_dirs))
    if re.fullmatch(r"v0-[0-9]{8}-[0-9]{6}", run_dir) is None:
        raise ValueError("RESULT_TRAINING_RUN_DIR_HOLD")
    event_files = {
        item for item in found
        if item.startswith(f"training/{run_dir}/runs/events.out.tfevents.")
        and len(PurePosixPath(item).parts) == 4
    }
    if len(event_files) != 1:
        raise ValueError("RESULT_TENSORBOARD_FILESET_HOLD")
    expected = set(RESULT_FILES)
    expected.update({
        f"training/{run_dir}/args.json",
        f"training/{run_dir}/r60_base336.yaml",
        f"training/{run_dir}/logging.jsonl",
    })
    expected.update(
        f"training/{run_dir}/checkpoint-37/{name}" for name in CHECKPOINT_FILES
    )
    expected.update(
        f"training/{run_dir}/images/{name}" for name in IMAGE_FILES
    )
    expected.update(event_files)
    if found != expected or len(expected) != 33:
        raise ValueError("RESULT_FILESET_HOLD")
    return run_dir, expected


def validate_worker_receipt(output_dir: Path, run_key: str) -> dict:
    receipt = contract.read_json(
        output_dir / "R60_BASE336_GPU_SAFE_RECEIPT_PRIVATE.json"
    )
    checkpoint, gpu, dependencies = (
        receipt.get("checkpoint"), receipt.get("gpu"), receipt.get("dependencies")
    )
    if (
        receipt.get("schema") != WORKER_SCHEMA
        or receipt.get("status") != WORKER_STATUS
        or receipt.get("run_key") != run_key
        or receipt.get("model") != contract.MODEL
        or receipt.get("model_revision") != contract.REVISION
        or receipt.get("input_contract") != contract.INPUT_CONTRACT
        or receipt.get("train_rows") != contract.TRAIN_ROWS
        or receipt.get("validation_rows") != contract.VALIDATION_ROWS
        or receipt.get("optimizer_steps") != 37
        or receipt.get("collator_transfer_verified") is not True
        or receipt.get("training_started") is not True
        or receipt.get("training_finished") is not True
        or receipt.get("gpu_started") is not True
        or receipt.get("gpu_used") is not True
        or receipt.get("terminal_checkpoint_verified") is not True
        or receipt.get("adapter_reload_verified") is not True
        or receipt.get("model_promoted") is not False
        or receipt.get("r50_read") is not False
        or receipt.get("train_admitted") != 0
        or receipt.get("quality_v1_admitted") != 0
        or receipt.get("private_values_emitted") is not False
        or not isinstance(checkpoint, dict)
        or checkpoint.get("global_step") != 37
        or checkpoint.get("one_epoch_complete") is not True
        or checkpoint.get("final_checkpoint_present") is not True
        or checkpoint.get("final_adapter_present") is not True
        or checkpoint.get("terminal_eval_present") is not True
        or checkpoint.get("adapter_rank") != 64
        or checkpoint.get("adapter_alpha") != 128
        or not isinstance(gpu, dict)
        or gpu.get("name") != "NVIDIA A100-SXM4-80GB"
        or float(gpu.get("total_memory_gib", 0)) < 75
        or not isinstance(dependencies, dict)
        or dependencies.get("ms-swift") != "4.5.3"
        or dependencies.get("transformers") != "5.16.1"
        or dependencies.get("bitsandbytes") != "0.50.2"
        or dependencies.get("qwen-vl-utils") != "0.0.14"
        or dependencies.get("huggingface_hub") != "1.33.0"
    ):
        raise ValueError("WORKER_RECEIPT_HOLD")
    return receipt


def validate_checkpoint(output_dir: Path, run_dir: str) -> dict:
    checkpoint_dir = output_dir / "training" / run_dir / "checkpoint-37"
    adapter = contract.read_json(checkpoint_dir / "adapter_config.json")
    trainer = contract.read_json(
        checkpoint_dir / "trainer_state.json", maximum=200_000
    )
    if (
        adapter.get("r") != 64
        or adapter.get("lora_alpha") != 128
        or trainer.get("global_step") != 37
        or float(trainer.get("epoch", 0)) < 0.999
        or not str(trainer.get("best_model_checkpoint", "")).endswith("checkpoint-37")
    ):
        raise ValueError("TERMINAL_CHECKPOINT_HOLD")
    if not (checkpoint_dir / "adapter_model.safetensors").is_file():
        raise ValueError("FINAL_ADAPTER_MISSING_HOLD")
    if not (checkpoint_dir / "optimizer.pt").is_file():
        raise ValueError("FINAL_OPTIMIZER_MISSING_HOLD")
    logging_path = output_dir / "training" / run_dir / "logging.jsonl"
    from storyforge_dataset.hf_runtime import InputManager

    verified_logging = InputManager.open_verified(
        logging_path, max_bytes=2_000_000
    )
    records = [
        json.loads(line)
        for line in verified_logging.read_bytes().decode("utf-8").splitlines()
        if line.strip()
    ]
    terminal_eval = next(
        (
            row for row in records
            if row.get("global_step/max_steps") == "37/37"
            and isinstance(row.get("eval_loss"), (int, float))
        ),
        None,
    )
    if terminal_eval is None:
        raise ValueError("TERMINAL_EVAL_LOG_HOLD")
    check_inference_result(output_dir / "reload_response_PRIVATE.jsonl")
    return {
        "global_step": 37, "one_epoch_complete": True,
        "terminal_eval_present": True, "adapter_reload_result_present": True,
    }


def _private_output_dir(path: Path) -> Path:
    private_root = Path.home() / ".local/share/storyforge/r60/private"
    if (
        private_root.is_symlink() or not private_root.is_dir()
        or stat.S_IMODE(private_root.stat().st_mode) != 0o700
        or path.parent != private_root or path.exists() or path.is_symlink()
    ):
        raise ValueError("PRIVATE_AUDIT_DIRECTORY_HOLD")
    return private_root


def _write_manifest(path: Path, value: dict) -> None:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("AUDIT_NOFOLLOW_UNAVAILABLE")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise ValueError("AUDIT_MANIFEST_WRITE_HOLD")
            view = view[count:]
        os.fsync(fd)
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)


def audit(
    run_key: str, output_dir: Path, *, api=None,
    run_command: Callable = subprocess.run,
) -> dict:
    if not contract.RUN_RE.fullmatch(run_key):
        return safe("BASE336_GPU_RESULT_AUDIT_HOLD", "RUN_KEY_HOLD")
    try:
        private_root = _private_output_dir(output_dir)
        if api is None:
            from huggingface_hub import HfApi

            api = HfApi()
        prefix = f"{contract.HF_RESULT_PREFIX}/{run_key}/"
        remote_files = gpu_cli._remote_set(api, prefix)
        run_dir, expected = expected_remote_files(remote_files)
        entries = list(api.list_bucket_tree(contract.HF_BUCKET, prefix=prefix, recursive=True))
        size_by_path = {
            entry.path[len(prefix):]: int(getattr(entry, "size", 0) or 0)
            for entry in entries
            if getattr(entry, "type", "") != "directory"
            and isinstance(getattr(entry, "path", None), str)
            and entry.path.startswith(prefix)
        }
        remote_total = sum(size_by_path.get(item, 0) for item in expected)
        required_free = (
            remote_total + MIN_FREE_MARGIN if remote_total > 0
            else FALLBACK_REQUIRED_FREE
        )
        if shutil.disk_usage(private_root).free < required_free:
            return safe(
                "BASE336_GPU_RESULT_AUDIT_HOLD", "LOCAL_DISK_SPACE_HOLD",
                run_key_validated=True, remote_file_set_verified=True,
                files_downloaded=0, total_bytes=remote_total,
            )
        output_dir.mkdir(mode=0o700, exist_ok=False)
        records = []
        total_bytes = 0
        for index, relative in enumerate(sorted(expected), start=1):
            target = output_dir / relative
            current = target.parent
            parents = []
            while current != output_dir:
                parents.append(current)
                current = current.parent
            for parent in reversed(parents):
                if parent.is_symlink():
                    raise ValueError("AUDIT_DIRECTORY_SYMLINK_HOLD")
                parent.mkdir(mode=0o700, exist_ok=True)
                os.chmod(parent, 0o700)
            if target.exists() or target.is_symlink():
                raise ValueError("AUDIT_CREATE_ONLY_HOLD")
            uri = gpu_cli._remote_uri(prefix, relative)
            result = run_command(
                ["hf", "buckets", "cp", uri, str(target)],
                capture_output=True, text=True, timeout=7200, check=False,
            )
            if result.returncode != 0 or not target.is_file() or target.is_symlink():
                raise ValueError("REMOTE_DOWNLOAD_HOLD")
            os.chmod(target, 0o600)
            size = target.stat().st_size
            expected_size = size_by_path.get(relative, 0)
            if expected_size and size != expected_size:
                raise ValueError("DOWNLOADED_SIZE_MISMATCH_HOLD")
            digest = sha256(target)
            total_bytes += size
            records.append({"path": relative, "bytes": size, "sha256": digest})
            print(f"RESULT_ARTIFACT_DOWNLOAD {index}/{len(expected)}", flush=True)
        validate_worker_receipt(output_dir, run_key)
        validate_checkpoint(output_dir, run_dir)
        _write_manifest(output_dir / "RESULT_SHA256_MANIFEST_PRIVATE.json", {
            "schema": "storyforge_r60_base336_gpu_result_sha256_manifest_private_v1",
            "run_key": run_key, "remote_prefix": prefix, "files": records,
            "files_verified": len(records), "total_bytes": total_bytes,
            "note": "Local SHA256 inventory of downloaded HF objects; no original worker-side per-file digest was published.",
        })
        gpu_cli.stage_tool._verify_local_modes(output_dir)
        return safe(
            AUDIT_STATUS, "DOWNLOADED_OBJECTS_HASHED_AND_WORKER_EVIDENCE_VALID",
            run_key_validated=True, remote_file_set_verified=True,
            files_downloaded=len(records), files_hashed=len(records),
            total_bytes=total_bytes, sha256_manifest_created=True,
            worker_receipt_verified=True, checkpoint_verified=True,
            adapter_reload_verified=True, training_gpu_used=True,
        )
    except ValueError as exc:
        reason = str(exc)
        allowed = {
            "RESULT_REMOTE_PATH_HOLD", "RESULT_TRAINING_RUN_DIR_HOLD",
            "RESULT_TENSORBOARD_FILESET_HOLD", "RESULT_FILESET_HOLD",
            "PRIVATE_AUDIT_DIRECTORY_HOLD", "AUDIT_NOFOLLOW_UNAVAILABLE",
            "AUDIT_MANIFEST_WRITE_HOLD", "AUDIT_DIRECTORY_SYMLINK_HOLD",
            "AUDIT_CREATE_ONLY_HOLD", "REMOTE_DOWNLOAD_HOLD",
            "DOWNLOADED_SIZE_MISMATCH_HOLD", "WORKER_RECEIPT_HOLD",
            "TERMINAL_CHECKPOINT_HOLD", "FINAL_ADAPTER_MISSING_HOLD",
            "FINAL_OPTIMIZER_MISSING_HOLD", "TERMINAL_EVAL_LOG_HOLD",
            "REMOTE_LIST_HOLD", "REMOTE_PATH_HOLD", "SHARED_BUCKET_CONTRACT_HOLD",
        }
        return safe(
            "BASE336_GPU_RESULT_AUDIT_HOLD",
            reason if reason in allowed else "RESULT_AUDIT_VALIDATION_HOLD",
            run_key_validated=True,
        )
    except (OSError, subprocess.SubprocessError):
        return safe(
            "BASE336_GPU_RESULT_AUDIT_HOLD", "LOCAL_OR_REMOTE_IO_HOLD",
            run_key_validated=True,
        )
    except (TypeError, KeyError):
        return safe(
            "BASE336_GPU_RESULT_AUDIT_HOLD", "RESULT_AUDIT_VALIDATION_HOLD",
            run_key_validated=True,
        )
    except Exception:
        return safe(
            "BASE336_GPU_RESULT_AUDIT_HOLD", "REMOTE_OR_LOCAL_RUNTIME_HOLD",
            run_key_validated=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run_key, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == AUDIT_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())

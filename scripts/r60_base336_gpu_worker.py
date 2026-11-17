"""R60 Base336 one-epoch QLoRA worker; invoked only inside an authorized HF GPU Job."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "src"),
    str(ROOT / "scripts"),
    str(ROOT / "experiments" / "r58_quality"),
]

import r60_base336_gpu_contract as contract
from hf_job_runner import (
    GpuMonitor,
    check_inference_result,
    make_inference_input,
    training_evidence,
)
from storyforge_dataset.hf_runtime import InputManager, OutputManager

GPU_SCOPE = "R60_BASE336_293_43_ONE_EPOCH_A10080GB"
RECEIPT_NAME = "R60_BASE336_GPU_SAFE_RECEIPT_PRIVATE.json"
STAGE_DEFAULT = Path("/input/r60-base336")
OUTPUT_DEFAULT = Path("/output")
CACHE = Path("/tmp/r60-base336-cache")
EXPECTED_PACKAGES = {
    "ms-swift": "4.5.3",
    "transformers": "5.16.1",
    "bitsandbytes": "0.50.2",
    "qwen-vl-utils": "0.0.14",
    "huggingface_hub": "1.33.0",
}


def safe_report(run_key: str) -> dict:
    return {
        "schema": "storyforge_r60_base336_gpu_worker_safe_v1",
        "status": "BASE336_GPU_RUN_HOLD__NOT_PROMOTED",
        "reason_code": "NOT_STARTED",
        "run_key": run_key,
        "model": contract.MODEL,
        "model_revision": contract.REVISION,
        "input_contract": contract.INPUT_CONTRACT,
        "train_rows": contract.TRAIN_ROWS,
        "validation_rows": contract.VALIDATION_ROWS,
        "optimizer_steps": 37,
        "collator_transfer_verified": False,
        "model_downloaded": False,
        "training_started": False,
        "training_finished": False,
        "terminal_checkpoint_verified": False,
        "adapter_reload_verified": False,
        "gpu_started": False,
        "gpu_used": False,
        "r50_read": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_promoted": False,
        "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }


def _gpu_gate() -> dict:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("GPU_DEVICE_COUNT_HOLD")
    props = torch.cuda.get_device_properties(0)
    free_bytes, _ = torch.cuda.mem_get_info(0)
    name = str(props.name)
    if "A100" not in name.upper():
        raise ValueError("GPU_MODEL_HOLD")
    if props.total_memory < 75 * 1024**3 or free_bytes < 70 * 1024**3:
        raise ValueError("GPU_MEMORY_HOLD")
    if shutil.disk_usage("/tmp").free < 80 * 1024**3:
        raise ValueError("GPU_DISK_CAPACITY_HOLD")
    return {
        "name": name,
        "total_memory_gib": round(props.total_memory / 1024**3, 1),
        "free_memory_gib_at_start": round(free_bytes / 1024**3, 1),
    }


def _dependency_gate() -> dict:
    from importlib.metadata import version
    import torch

    if sys.version_info[:2] != (3, 11):
        raise ValueError("PYTHON_VERSION_HOLD")
    if torch.__version__.split("+", maxsplit=1)[0] != "2.6.0":
        raise ValueError("TORCH_VERSION_HOLD")
    installed = {name: version(name) for name in EXPECTED_PACKAGES}
    if installed != EXPECTED_PACKAGES:
        raise ValueError("DEPENDENCY_VERSION_HOLD")
    check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if check.returncode or check.stdout.strip() or check.stderr.strip():
        raise ValueError("DEPENDENCY_INTEGRITY_HOLD")
    return installed


def _run_quiet(command: list[str], log_path: Path, *, timeout: int) -> None:
    with log_path.open("ab") as log:
        result = subprocess.run(
            command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
            timeout=timeout, check=False,
        )
    if result.returncode:
        raise ValueError("TRAINING_COMMAND_FAILED")


def _terminal_checkpoint(output: Path, expected_steps: int) -> tuple[dict, Path]:
    evidence = training_evidence(output)
    if evidence.get("global_step") != expected_steps:
        raise ValueError("TERMINAL_OPTIMIZER_STEP_HOLD")
    state_path = Path(str(evidence["checkpoint"]))
    if state_path.name != "trainer_state.json" or state_path.parent.name != f"checkpoint-{expected_steps}":
        raise ValueError("TERMINAL_CHECKPOINT_PATH_HOLD")
    state = json.loads(InputManager.open_verified(
        state_path, max_bytes=8_000_000
    ).read_bytes())
    history = state.get("log_history")
    if not isinstance(history, list) or not any(
        isinstance(item, dict)
        and item.get("step") == expected_steps
        and isinstance(item.get("eval_loss"), (int, float))
        for item in history
    ):
        raise ValueError("TERMINAL_EVAL_NOT_RECORDED_HOLD")
    if not isinstance(state.get("epoch"), (int, float)) or float(state["epoch"]) < 0.99:
        raise ValueError("ONE_EPOCH_COMPLETION_HOLD")
    adapter = Path(str(evidence["adapter_weights"]))
    if not adapter.is_file() or adapter.is_symlink():
        raise ValueError("FINAL_ADAPTER_MISSING_HOLD")
    adapter_config_path = adapter.parent / "adapter_config.json"
    adapter_config = json.loads(InputManager.open_verified(
        adapter_config_path, max_bytes=64_000
    ).read_bytes())
    if (
        str(adapter_config.get("peft_type", "")).upper() != "LORA"
        or adapter_config.get("r") != 64
        or adapter_config.get("lora_alpha") != 128
    ):
        raise ValueError("FINAL_ADAPTER_CONFIG_HOLD")
    return {
        "global_step": expected_steps,
        "final_checkpoint_present": True,
        "final_adapter_present": True,
        "terminal_eval_present": True,
        "one_epoch_complete": True,
        "adapter_rank": 64,
        "adapter_alpha": 128,
    }, state_path.parent

def run(stage: Path, output: Path, run_key: str, action: str) -> dict:
    report = safe_report(run_key)
    phase = "STAGE_VERIFY"
    started = time.monotonic()
    try:
        if not contract.RUN_RE.fullmatch(run_key):
            raise ValueError("RUN_KEY_HOLD")
        if stage != STAGE_DEFAULT and stage.is_symlink():
            raise ValueError("STAGE_PATH_HOLD")
        contract.verify_stage(stage, run_key)
        report["collator_transfer_verified"] = True
        if action == "preflight":
            report.update(
                status="BASE336_GPU_STAGE_VERIFIED__NO_GPU",
                reason_code="STAGE_AND_SOURCE_PROOFS_PASS",
            )
            return report
        if action != "train":
            raise ValueError("ACTION_HOLD")
        if os.environ.get("STORYFORGE_R60_BASE336_GPU_RUN_KEY") != run_key:
            raise ValueError("JOB_RUN_KEY_HOLD")
        if os.environ.get("STORYFORGE_R60_BASE336_GPU_SCOPE") != GPU_SCOPE:
            raise ValueError("GPU_SCOPE_HOLD")
        job_id = os.environ.get("JOB_ID", "")
        if not job_id or "/" in job_id or job_id in {".", ".."}:
            raise ValueError("HF_JOB_ID_HOLD")
        if output.is_symlink() or not output.is_dir():
            raise ValueError("OUTPUT_MOUNT_HOLD")
        OutputManager.probe(output)
        receipt_path = output / RECEIPT_NAME
        if receipt_path.exists() or receipt_path.is_symlink():
            raise ValueError("OUTPUT_RECEIPT_EXISTS_HOLD")
        train_output = output / "training"
        if train_output.exists() or train_output.is_symlink():
            raise ValueError("TRAINING_OUTPUT_EXISTS_HOLD")
        train_output.mkdir(mode=0o700, exist_ok=False)

        phase = "GPU_DEVICE_GATE"
        gpu = _gpu_gate()
        report["gpu"] = gpu
        report["gpu_used"] = True

        phase = "DEPENDENCY_GATE"
        dependencies = _dependency_gate()
        report["dependencies"] = dependencies

        phase = "MODEL_DOWNLOAD"
        CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.environ.update({
            "HF_HOME": str(CACHE / "huggingface"),
            "PIP_CACHE_DIR": str(CACHE / "pip"),
            "TOKENIZERS_PARALLELISM": "false",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "PYTHONUNBUFFERED": "1",
            "CUDA_VISIBLE_DEVICES": "0",
        })
        from huggingface_hub import snapshot_download

        snapshot = Path(snapshot_download(
            repo_id=contract.MODEL, revision=contract.REVISION, max_workers=4,
        ))
        if contract.REVISION not in str(snapshot.resolve()) or not (snapshot / "config.json").is_file():
            raise ValueError("PINNED_MODEL_SNAPSHOT_HOLD")
        report["model_downloaded"] = True

        phase = "TRAINING"
        config = stage / contract.CONFIG_NAME
        train = stage / "private/release/train.jsonl"
        validation = stage / "private/release/validation.jsonl"
        guard = stage / "scripts/hf_smoke_guard.py"
        log_path = output / "R60_BASE336_GPU_RUNTIME_PRIVATE.log"
        command = [
            "swift", "sft", str(config),
            "--model", str(snapshot),
            "--dataset", str(train),
            "--val_dataset", str(validation),
            "--output_dir", str(train_output),
            "--save_only_model", "false",
            "--loss_scale", "last_round",
            "--custom_register_path", str(guard),
        ]
        report["training_started"] = True
        report["gpu_started"] = True
        with GpuMonitor() as monitor:
            _run_quiet(command, log_path, timeout=6900)
        report["gpu_peak_memory_mib"] = monitor.peak_mib
        report["training_finished"] = True

        phase = "TERMINAL_CHECKPOINT"
        checkpoint, checkpoint_path = _terminal_checkpoint(
            train_output, contract.optimizer_steps()
        )
        report["checkpoint"] = checkpoint
        report["terminal_checkpoint_verified"] = True

        phase = "ADAPTER_RELOAD"
        inference_input = output / "reload_prompt_PRIVATE.jsonl"
        inference_output = output / "reload_response_PRIVATE.jsonl"
        make_inference_input(validation, inference_input)
        inference_input.chmod(0o600)
        _run_quiet([
            "swift", "infer",
            "--model", str(snapshot),
            "--use_hf", "true",
            "--adapters", str(checkpoint_path),
            "--val_dataset", str(inference_input),
            "--val_dataset_sample", "1",
            "--infer_backend", "transformers",
            "--torch_dtype", "bfloat16",
            "--quant_method", "bnb",
            "--quant_bits", "4",
            "--bnb_4bit_compute_dtype", "bfloat16",
            "--max_new_tokens", "128",
            "--result_path", str(inference_output),
        ], log_path, timeout=1800)
        check_inference_result(inference_output)
        report["adapter_reload_verified"] = True
        report.update(
            status="BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED",
            reason_code="TERMINAL_CHECKPOINT_AND_ADAPTER_RELOAD_PASS",
            training_finished=True,
            model_promoted=False,
        )
    except Exception:  # noqa: BLE001 - do not expose paths, data, logs or exception text
        report["status"] = "BASE336_GPU_RUN_HOLD__NOT_PROMOTED"
        report["reason_code"] = phase + "_HOLD"
    report["elapsed_seconds"] = round(time.monotonic() - started, 1)
    try:
        OutputManager.write_safe(output / RECEIPT_NAME, report)
    except Exception:  # noqa: BLE001 - SAFE-only output failure
        report = safe_report(run_key)
        report["status"] = "BASE336_GPU_RECEIPT_PUBLICATION_HOLD"
        report["reason_code"] = "OUTPUT_WRITE_HOLD"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("preflight", "train"), required=True)
    parser.add_argument("--stage", type=Path, default=STAGE_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--run-key", required=True)
    args = parser.parse_args()
    result = run(args.stage, args.output, args.run_key, args.action)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {
        "BASE336_GPU_STAGE_VERIFIED__NO_GPU",
        "BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED",
    } else 42


if __name__ == "__main__":
    raise SystemExit(main())

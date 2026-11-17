"""Shared R60 Base336 GPU contract; no network, model, GPU or HF Job actions."""
from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_RE = re.compile(r"r60-base336-gpu-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}\Z")
STAGE_SCHEMA = "storyforge_r60_base336_gpu_stage_private_v1"
PROOF_SCHEMA = "storyforge_r60_base336_exploratory_collator_transfer_safe_v1"
PROOF_STATUS = "BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD"
MODEL = "Qwen/Qwen3.8-27B"
REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
TRAIN_ROWS = 293
VALIDATION_ROWS = 43
INPUT_CONTRACT = "THREE_PERSISTED_MESSAGES_NO_SYSTEM"
CONFIG_TEMPLATE = ROOT / "configs/r60_base336_exploratory_293_43.yaml"
CONFIG_NAME = "config/r60_base336.yaml"
RELEASE_MANIFEST = "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json"
PROOF_NAME = "BASE336_COLLATOR_TRANSFER_SAFE_PRIVATE.json"
MAX_DATA_BYTES = 4_000_000
MAX_SAFE_BYTES = 32_768


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_verified(path: Path, maximum: int) -> bytes:
    from storyforge_dataset.hf_runtime import InputManager

    return InputManager.open_verified(path, max_bytes=maximum).read_bytes()


def read_json(path: Path, maximum: int = MAX_SAFE_BYTES) -> dict:
    from storyforge_dataset.hf_runtime import InputManager

    value = InputManager.validate_json(read_verified(path, maximum))
    if type(value) is not dict:
        raise ValueError("SAFE_JSON_SCHEMA_HOLD")
    return value


def verify_proof_receipt(path: Path) -> dict:
    value = read_json(path)
    required = {
        "schema": PROOF_SCHEMA,
        "status": PROOF_STATUS,
        "train_rows": TRAIN_ROWS,
        "validation_rows": VALIDATION_ROWS,
        "source_cpu_audited_rows": 336,
        "source_cpu_receipt_accepted": True,
        "all_final_rows_byte_identical_to_audited_rows": True,
        "actual_final_collator_verified": True,
        "collator_executed_in_this_run": False,
        "input_contract": INPUT_CONTRACT,
        "formal_source_admission_verified": False,
        "train_admitted": 0,
        "gpu_stage_prepared": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }
    if any(value.get(key) != expected for key, expected in required.items()):
        raise ValueError("COLLATOR_TRANSFER_PROOF_HOLD")
    return value


def verify_release(release_dir: Path) -> dict:
    import sys

    experiments = ROOT / "experiments/r58_quality"
    if str(experiments) not in sys.path:
        sys.path.insert(0, str(experiments))
    import r60_base336_exploratory_release_verify as release_verify

    result = release_verify.verify(release_dir)
    if (
        result.get("status") != "BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD"
        or result.get("train_rows") != TRAIN_ROWS
        or result.get("validation_rows") != VALIDATION_ROWS
        or result.get("sha256_verified") is not True
        or result.get("train_admitted") != 0
        or result.get("gpu_started") is not False
    ):
        raise ValueError("RELEASE_VERIFY_HOLD")
    manifest = read_json(release_dir / RELEASE_MANIFEST)
    stats = manifest.get("statistics")
    if (
        type(stats) is not dict
        or stats.get("rows") != {"train": TRAIN_ROWS, "validation": VALIDATION_ROWS}
        or stats.get("input_contract") != INPUT_CONTRACT
        or stats.get("semantic_world_isolation_verified") is not False
        or stats.get("r50_semantic_isolation_verified") is not False
        or stats.get("reviewer_execution_independence_verified") is not False
    ):
        raise ValueError("RELEASE_MANIFEST_SCOPE_HOLD")
    return result


def optimizer_steps(
    train_rows: int = TRAIN_ROWS,
    *,
    per_device_batch_size: int = 1,
    gradient_accumulation_steps: int = 8,
    world_size: int = 1,
    epochs: int = 1,
) -> int:
    values = (train_rows, per_device_batch_size, gradient_accumulation_steps, world_size, epochs)
    if any(type(value) is not int or value < 1 for value in values):
        raise ValueError("TRAINING_SHAPE_HOLD")
    batches = math.ceil(train_rows / (per_device_batch_size * world_size))
    return math.ceil(batches / gradient_accumulation_steps) * epochs


def render_config(template: bytes) -> bytes:
    text = template.decode("utf-8")
    replacements = {
        "/workspace/preflight/r60/base336-gpu/runs/REPLACE_RUN_KEY": "/input/r60-base336",
        "/workspace/experiments/r60-base336-exploratory/REPLACE_RUN_KEY/output": "/output/training",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    required_lines = {
        "model: Qwen/Qwen3.8-27B",
        "use_hf: true",
        "tuner_type: lora",
        "target_modules: all-linear",
        "lora_rank: 64",
        "lora_alpha: 128",
        "lora_dropout: 0.05",
        "torch_dtype: bfloat16",
        "quant_method: bnb",
        "quant_bits: 4",
        "bnb_4bit_compute_dtype: bfloat16",
        "bnb_4bit_quant_type: nf4",
        "bnb_4bit_use_double_quant: true",
        "max_length: 16384",
        "loss_scale: last_round",
        "per_device_train_batch_size: 1",
        "per_device_eval_batch_size: 1",
        "gradient_accumulation_steps: 8",
        "num_train_epochs: 1",
        "eval_strategy: steps",
        "save_strategy: steps",
        "eval_steps: 37",
        "save_steps: 37",
    }
    if not required_lines.issubset(set(text.splitlines())):
        raise ValueError("TRAINING_CONFIG_CONTRACT_HOLD")
    if "REPLACE_RUN_KEY" in text or "/workspace/preflight/" in text:
        raise ValueError("TRAINING_CONFIG_PATH_HOLD")
    if optimizer_steps() != 37:
        raise ValueError("OPTIMIZER_STEP_CONTRACT_HOLD")
    return text.encode("utf-8")


def verify_stage(stage: Path, run_key: str) -> dict:
    from storyforge_dataset.hf_runtime import InputManager

    if not RUN_RE.fullmatch(run_key):
        raise ValueError("RUN_KEY_HOLD")
    if stage.is_symlink() or not stage.is_dir():
        raise ValueError("STAGE_DIRECTORY_HOLD")
    manifest_path = stage / "SHA256_MANIFEST_PRIVATE.json"
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != STAGE_SCHEMA
        or manifest.get("status") != "STAGED_NOT_SUBMITTED"
        or manifest.get("run_key") != run_key
        or manifest.get("model") != MODEL
        or manifest.get("model_revision") != REVISION
        or manifest.get("train_rows") != TRAIN_ROWS
        or manifest.get("validation_rows") != VALIDATION_ROWS
        or manifest.get("optimizer_steps") != 37
        or manifest.get("input_contract") != INPUT_CONTRACT
        or manifest.get("train_admitted") != 0
        or manifest.get("quality_v1_admitted") != 0
        or manifest.get("gpu_started") is not False
        or manifest.get("hf_jobs_submitted") != 0
        or manifest.get("private_values_emitted") is not False
        or type(manifest.get("files")) is not dict
    ):
        raise ValueError("STAGE_MANIFEST_CONTRACT_HOLD")
    files = manifest["files"]
    if not files or any(
        type(name) is not str
        or not name
        or name.startswith("/")
        or ".." in Path(name).parts
        or type(digest) is not str
        or re.fullmatch(r"[a-f0-9]{64}", digest) is None
        for name, digest in files.items()
    ):
        raise ValueError("STAGE_FILE_MANIFEST_HOLD")
    expected = set(files) | {"SHA256_MANIFEST_PRIVATE.json"}
    actual = {
        item.relative_to(stage).as_posix()
        for item in stage.rglob("*")
        if item.is_file() or item.is_symlink()
    }
    if actual != expected:
        raise ValueError("STAGE_FILESET_HOLD")
    for name, digest in files.items():
        InputManager.open_verified(
            stage / name, max_bytes=8_000_000, expected_sha256=digest
        )
    release_dir = stage / "private/release"
    release = verify_release(release_dir)
    proof = verify_proof_receipt(stage / "private/proof" / PROOF_NAME)
    config = read_verified(stage / CONFIG_NAME, 64_000)
    if render_config((ROOT / "configs/r60_base336_exploratory_293_43.yaml").read_bytes()) != config:
        raise ValueError("TRAINING_CONFIG_DRIFT_HOLD")
    if (
        proof.get("actual_final_collator_verified") is not True
        or release.get("sha256_verified") is not True
    ):
        raise ValueError("SOURCE_TECHNICAL_PROOF_HOLD")
    return {
        "schema": "storyforge_r60_base336_gpu_stage_safe_v1",
        "status": "BASE336_GPU_STAGE_VERIFIED__NO_JOB",
        "run_key": run_key,
        "files_verified": len(files),
        "train_rows": TRAIN_ROWS,
        "validation_rows": VALIDATION_ROWS,
        "optimizer_steps": 37,
        "collator_transfer_verified": True,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }

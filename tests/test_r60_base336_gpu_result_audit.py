"""Synthetic-only tests for the R60 Base336 read-only result audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import r60_base336_gpu_result_audit as audit
import r60_base336_gpu_contract as contract

KEY = "r60-base336-gpu-20261117T055622Z-b609cb78661d"
RUN_DIR = "v0-20261117-071048"


def remote_files() -> set[str]:
    files = set(audit.RESULT_FILES)
    files.update({
        f"training/{RUN_DIR}/args.json",
        f"training/{RUN_DIR}/r60_base336.yaml",
        f"training/{RUN_DIR}/logging.jsonl",
    })
    files.update(
        f"training/{RUN_DIR}/checkpoint-37/{name}"
        for name in audit.CHECKPOINT_FILES
    )
    files.update(
        f"training/{RUN_DIR}/images/{name}"
        for name in audit.IMAGE_FILES
    )
    files.add(
        f"training/{RUN_DIR}/runs/events.out.tfevents.1794899489.job.550.0"
    )
    return files


def receipt() -> dict:
    return {
        "schema": audit.WORKER_SCHEMA, "status": audit.WORKER_STATUS,
        "run_key": KEY, "model": contract.MODEL,
        "model_revision": contract.REVISION,
        "input_contract": contract.INPUT_CONTRACT,
        "train_rows": 293, "validation_rows": 43, "optimizer_steps": 37,
        "collator_transfer_verified": True, "training_started": True,
        "training_finished": True, "gpu_started": True, "gpu_used": True,
        "terminal_checkpoint_verified": True, "adapter_reload_verified": True,
        "model_promoted": False, "r50_read": False,
        "train_admitted": 0, "quality_v1_admitted": 0,
        "private_values_emitted": False,
        "checkpoint": {
            "global_step": 37, "one_epoch_complete": True,
            "final_checkpoint_present": True, "final_adapter_present": True,
            "terminal_eval_present": True, "adapter_rank": 64,
            "adapter_alpha": 128,
        },
        "gpu": {"name": "NVIDIA A100-SXM4-80GB", "total_memory_gib": 79.2},
        "dependencies": {
            "ms-swift": "4.5.3", "transformers": "5.16.1",
            "bitsandbytes": "0.50.2", "qwen-vl-utils": "0.0.14",
            "huggingface_hub": "1.33.0",
        },
    }


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def test_expected_remote_file_set_is_exactly_33():
    run_dir, expected = audit.expected_remote_files(remote_files())
    assert run_dir == RUN_DIR
    assert len(expected) == 33


def test_expected_remote_file_set_rejects_missing_and_extra():
    missing = remote_files()
    missing.remove("reload_response_PRIVATE.jsonl")
    with pytest.raises(ValueError, match="RESULT_FILESET_HOLD"):
        audit.expected_remote_files(missing)
    with pytest.raises(ValueError, match="RESULT_FILESET_HOLD"):
        audit.expected_remote_files(remote_files() | {"unexpected/private.txt"})


def test_expected_remote_file_set_rejects_path_traversal():
    with pytest.raises(ValueError, match="RESULT_REMOTE_PATH_HOLD"):
        audit.expected_remote_files(remote_files() | {"training/../escape"})


def test_worker_receipt_requires_completed_not_promoted(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    write(out / "R60_BASE336_GPU_SAFE_RECEIPT_PRIVATE.json", receipt())
    result = audit.validate_worker_receipt(out, KEY)
    assert result["checkpoint"]["global_step"] == 37
    bad = receipt()
    bad["model_promoted"] = True
    write(out / "R60_BASE336_GPU_SAFE_RECEIPT_PRIVATE.json", bad)
    with pytest.raises(ValueError, match="WORKER_RECEIPT_HOLD"):
        audit.validate_worker_receipt(out, KEY)


def test_worker_receipt_rejects_wrong_revision(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    bad = receipt()
    bad["model_revision"] = "0" * 40
    write(out / "R60_BASE336_GPU_SAFE_RECEIPT_PRIVATE.json", bad)
    with pytest.raises(ValueError, match="WORKER_RECEIPT_HOLD"):
        audit.validate_worker_receipt(out, KEY)


def test_audit_safe_never_emits_private_values():
    result = audit.safe(
        audit.AUDIT_STATUS,
        "DOWNLOADED_OBJECTS_HASHED_AND_WORKER_EVIDENCE_VALID",
        files_downloaded=33, files_hashed=33,
    )
    assert result["private_values_emitted"] is False
    assert result["train_admitted"] == 0
    assert result["quality_v1_admitted"] == 0
    assert result["model_promoted"] is False
    assert "sha256" not in json.dumps(result).lower()

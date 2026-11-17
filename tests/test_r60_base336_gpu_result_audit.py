"""Synthetic-only tests for the R60 Base336 read-only result audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import r60_base336_gpu_contract as contract
import r60_base336_gpu_result_audit as audit

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
    assert "files" not in result
    assert "path" not in result
    assert "hashes" not in result


def test_checkpoint_and_reload_evidence_are_validated(tmp_path):
    out = tmp_path / "out"
    run = out / "training" / RUN_DIR
    checkpoint = run / "checkpoint-37"
    checkpoint.mkdir(parents=True)
    write(checkpoint / "adapter_config.json", {"r": 64, "lora_alpha": 128})
    write(checkpoint / "trainer_state.json", {
        "global_step": 37,
        "epoch": 1.0,
        "best_model_checkpoint": str(checkpoint),
    })
    (checkpoint / "adapter_model.safetensors").write_bytes(b"adapter")
    (checkpoint / "optimizer.pt").write_bytes(b"optimizer")
    (run / "logging.jsonl").write_text(
        json.dumps({
            "global_step/max_steps": "37/37",
            "eval_loss": 1.932103,
            "eval_token_acc": 0.550921,
        }) + "\n",
        encoding="utf-8",
    )
    (out / "reload_response_PRIVATE.jsonl").write_text(
        json.dumps({"response": "synthetic nonempty reload"}) + "\n",
        encoding="utf-8",
    )
    result = audit.validate_checkpoint(out, RUN_DIR)
    assert result["global_step"] == 37
    assert result["adapter_reload_result_present"] is True


def test_checkpoint_validation_rejects_step_drift(tmp_path):
    out = tmp_path / "out"
    run = out / "training" / RUN_DIR
    checkpoint = run / "checkpoint-37"
    checkpoint.mkdir(parents=True)
    write(checkpoint / "adapter_config.json", {"r": 64, "lora_alpha": 128})
    write(checkpoint / "trainer_state.json", {
        "global_step": 36,
        "epoch": 1.0,
        "best_model_checkpoint": str(checkpoint),
    })
    (checkpoint / "adapter_model.safetensors").write_bytes(b"adapter")
    (checkpoint / "optimizer.pt").write_bytes(b"optimizer")
    (run / "logging.jsonl").write_text("", encoding="utf-8")
    (out / "reload_response_PRIVATE.jsonl").write_text(
        json.dumps({"response": "synthetic"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="TERMINAL_CHECKPOINT_HOLD"):
        audit.validate_checkpoint(out, RUN_DIR)


def test_required_free_bytes_uses_exact_remote_total_when_complete():
    expected = {"a", "b", "c"}
    required, complete = audit.required_free_bytes(
        expected, {"a": 10, "b": 20, "c": 30}
    )
    assert complete is True
    assert required == 60 + audit.MIN_FREE_MARGIN


def test_required_free_bytes_uses_safe_fallback_for_partial_metadata():
    expected = {"a", "b", "c"}
    required, complete = audit.required_free_bytes(
        expected, {"a": 10, "b": 20}
    )
    assert complete is False
    assert required == audit.FALLBACK_REQUIRED_FREE

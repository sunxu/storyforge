"""CPU-only integrity gate for Gold48 hash-pinned dependency candidate."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def test_gold48_hash_lock_candidate_matches_cpu_job_receipt():
    root = Path(__file__).resolve().parents[1]
    report = json.loads(
        (root / "requirements/r60-gold48-inference-cpu-contract.json").read_text()
    )
    lock = (root / report["lock_path"]).read_bytes()
    assert report["schema"] == "storyforge_r60_gold48_inference_cpu_dependency_contract_v1"
    assert hashlib.sha256(lock).hexdigest() == report["lock_sha256"]
    assert len(lock) == report["lock_bytes"]
    assert report["base_image"].startswith("pytorch/pytorch@sha256:")
    assert report["formal_inference_authorized"] is False
    assert report["gpu_compatibility_verified"] is False
    assert report["require_hashes_install_on_inference_image_verified"] is True
    assert report["hash_pinned_install_verified_job"] == "6b00b0894fdc5ab3c55be7f0"
    assert report["hash_pinned_install_scope"] == (
        "SELECTED_IMMUTABLE_CPU_BASE_IMAGE__PREINSTALLED_TORCH_PRESERVED"
    )
    assert report["hash_pinned_install_gpu_started"] is False
    assert report["hash_pinned_install_model_calls"] == 0
    text = lock.decode("utf-8")
    required = (
        "torch==2.6.0", "transformers==5.16.1", "peft==0.21.2",
        "accelerate==1.12.0", "huggingface-hub==1.33.0",
        "cryptography==46.0.4",
    )
    for pin in required:
        assert pin in text
    assert len(re.findall(r"--hash=sha256:[0-9a-f]{64}", text)) >= 30
    assert "--hash=sha256:" in text
    assert "git+" not in text
    assert "http://" not in text


def test_signed_gpu_runtime_hard_pins_match_existing_cpu_job_contract():
    """Protect the reviewed launch gate against lock/image/version drift."""
    from storyforge_dataset.generation_eval import gold48_runtime_gate as runtime

    root = Path(__file__).resolve().parents[1]
    report = json.loads(
        (root / "requirements/r60-gold48-inference-cpu-contract.json").read_text()
    )
    assert runtime.FROZEN_RUNTIME_IMAGE == report["base_image"]
    assert runtime.FROZEN_RUNTIME_LOCK_SHA256 == report["lock_sha256"]
    assert runtime.FROZEN_RUNTIME_PACKAGES == report["pins"]
    assert runtime.FROZEN_RUNTIME_TORCH_BUILD == report["observed_torch"]
    assert runtime.FROZEN_PINNED_INSTALL_JOB == report["hash_pinned_install_verified_job"]
    assert report["gpu_generate_verified"] is False

"""One-prompt-per-model, sequential, GPU-only runtime smoke.

This is deliberately separate from the production generation worker. It uses
one built-in synthetic prompt, never writes generated text, and emits only a
0600 SAFE receipt containing hashes, token counts, finish reasons and runtime
fingerprints. It cannot train or process evaluation datasets.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.outputs import OutputManager

from .backend import (
    TransformersGenerationBackend,
    WorkerError,
    download_pinned_tokenizer_snapshot,
)
from .profiles import EXPECTED_MODELS, assess_profile, load_profile

SMOKE_MESSAGES = [
    {"role": "user", "content": "请用一句简短中文介绍你能帮助完成的事情。"}
]
SMOKE_MAX_INPUT_TOKENS = 256
SMOKE_MAX_NEW_TOKENS = 32
SMOKE_SEED = 42
ROLE_ORDER = ("A", "B", "challenger")
IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _write_receipt(output_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt = OutputManager.write_safe(output_path, report, mode=0o600)
    return {
        "path": str(output_path),
        "size_bytes": receipt.size_bytes,
        "sha256": receipt.sha256,
        "mode": f"{receipt.mode:04o}",
    }


def run_runtime_smoke(*, profile_path: Path, output_path: Path) -> dict[str, Any]:
    profile = load_profile(profile_path)
    assessment = assess_profile(profile, purpose="runtime_smoke")
    if not assessment.ready:
        raise WorkerError("RUNTIME_SMOKE_PROFILE_NOT_READY")
    if profile.get("status") != "P4_PROFILE_CANDIDATE__NOT_FROZEN":
        raise WorkerError("RUNTIME_SMOKE_REQUIRES_UNFROZEN_CANDIDATE")
    production_flags = (
        "profile_freeze_authorized",
        "inference_authorized",
        "gpu_authorized",
        "training_authorized",
    )
    if any(profile.get(flag) is True for flag in production_flags):
        raise WorkerError("RUNTIME_SMOKE_PRODUCTION_AUTH_FLAGS_MUST_REMAIN_DISABLED")

    lock_path = profile_path.parents[2] / profile["dependency_lock_path"]
    lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    if lock_sha != profile.get("dependency_lock_sha256"):
        raise WorkerError("DEPENDENCY_LOCK_SHA256_MISMATCH")
    runtime_digest = profile.get("runtime_digest")
    if not isinstance(runtime_digest, str) or not IMAGE_DIGEST_RE.fullmatch(runtime_digest):
        raise WorkerError("RUNTIME_IMAGE_DIGEST_INVALID")
    if os.environ.get("STORYFORGE_RUNTIME_IMAGE_DIGEST") != runtime_digest:
        raise WorkerError("RUNTIME_IMAGE_DIGEST_ENV_MISMATCH")

    hf_home = Path(os.environ.get("HF_HOME", "/tmp/storyforge-r60-p4-hf-cache"))
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["HF_HUB_CACHE"] = str(hf_home / "hub")

    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    accelerate = importlib.import_module("accelerate")
    hub = importlib.import_module("huggingface_hub")
    if not torch.__version__.startswith("2.6.0") or torch.version.cuda != "12.4":
        raise WorkerError("PYTORCH_CUDA_RUNTIME_MISMATCH")
    if sys.version_info[:2] != (3, 11):
        raise WorkerError("PYTHON_RUNTIME_MISMATCH")
    if not torch.cuda.is_available():
        raise WorkerError("CUDA_NOT_AVAILABLE")
    if not torch.cuda.is_bf16_supported():
        raise WorkerError("CUDA_BFLOAT16_UNSUPPORTED")

    report: dict[str, Any] = {
        "schema": "storyforge_r60_p4_runtime_smoke_safe_v1",
        "status": "RUNTIME_SMOKE_RUNNING",
        "purpose": "ONE_SYNTHETIC_PROMPT_PER_MODEL__SEQUENTIAL_GPU_RUNTIME_CHECK",
        "code_revision": os.environ.get("STORYFORGE_CODE_REVISION"),
        "runtime_digest": runtime_digest,
        "dependency_lock_sha256": lock_sha,
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "torch_version": torch.__version__,
        "cuda_build": torch.version.cuda,
        "transformers_version": transformers.__version__,
        "accelerate_version": accelerate.__version__,
        "huggingface_hub_version": hub.__version__,
        "cuda_device_name": torch.cuda.get_device_name(0),
        "bf16_supported": True,
        "model_count_expected": 3,
        "synthetic_record_count": 1,
        "max_input_tokens": SMOKE_MAX_INPUT_TOKENS,
        "max_new_tokens": SMOKE_MAX_NEW_TOKENS,
        "training_started": False,
        "production_profile_frozen": False,
        "production_inference_authorized": False,
        "private_values_emitted": False,
        "model_results": [],
    }

    for role in ROLE_ORDER:
        selected = profile["model_profiles"][role]
        model_id, revision = EXPECTED_MODELS[role]
        if (selected["model"], selected["revision"]) != (model_id, revision):
            raise WorkerError("MODEL_PIN_MISMATCH")
        record: dict[str, Any] = {
            "model_role": role,
            "model_revision": revision,
            "chat_template_sha256": selected["chat_template_sha256"],
            "tokenizer_file_hashes": dict(profile["tokenizer_file_hashes"][role]),
            "status": "RUNNING",
        }
        started = time.monotonic()
        backend = None
        try:
            with tempfile.TemporaryDirectory(prefix=f"r60-p4-{role}-") as tmp:
                snapshot = download_pinned_tokenizer_snapshot(
                    model_id=model_id,
                    revision=revision,
                    destination=Path(tmp) / "tokenizer",
                    expected_file_hashes=profile["tokenizer_file_hashes"][role],
                )
                torch.cuda.reset_peak_memory_stats(0)
                load_started = time.monotonic()
                backend = TransformersGenerationBackend.from_pretrained(
                    model_id=model_id,
                    revision=revision,
                    template_source=selected["chat_template_source"],
                    expected_template_sha256=selected["chat_template_sha256"],
                    tokenizer_snapshot=snapshot,
                    expected_tokenizer_file_hashes=profile["tokenizer_file_hashes"][role],
                    torch_module=torch,
                    transformers_module=transformers,
                )
                torch.cuda.synchronize(0)
                record["model_load_seconds"] = round(time.monotonic() - load_started, 3)
                generation_started = time.monotonic()
                generated = backend.generate(
                    model=model_id,
                    revision=revision,
                    messages=SMOKE_MESSAGES,
                    sampling=selected["sampling"],
                    enable_thinking=selected.get("enable_thinking"),
                    seed=SMOKE_SEED,
                    max_input_tokens=SMOKE_MAX_INPUT_TOKENS,
                    max_new_tokens=SMOKE_MAX_NEW_TOKENS,
                    eos_token_ids=profile["eos_token_ids"][role],
                    pad_token_id=profile["pad_token_ids"][role],
                )
                torch.cuda.synchronize(0)
                record.update({
                    "generation_seconds": round(time.monotonic() - generation_started, 3),
                    "input_tokens": generated.input_tokens,
                    "output_tokens": generated.output_tokens,
                    "finish_reason": generated.finish_reason,
                    "output_sha256": hashlib.sha256(
                        generated.text.encode("utf-8")
                    ).hexdigest(),
                    "peak_cuda_memory_allocated_bytes": int(
                        torch.cuda.max_memory_allocated(0)
                    ),
                    "model_resident_on_cuda": backend.gpu_started is True,
                    "dtype": "bfloat16",
                })
                if not backend.gpu_started or generated.output_tokens < 1:
                    raise WorkerError("RUNTIME_SMOKE_GENERATION_INVALID")
                if generated.finish_reason == "unrecognized_stop":
                    raise WorkerError("RUNTIME_SMOKE_UNRECOGNIZED_STOP")
                record["status"] = "PASS"
        except WorkerError as exc:
            record.update({"status": "HOLD", "error_code": str(exc)})
        except (OSError, RuntimeError, ValueError, ImportError):
            record.update({
                "status": "HOLD",
                "error_code": "RUNTIME_SMOKE_UNEXPECTED_FAILURE",
            })
        finally:
            backend = None
            gc.collect()
            torch.cuda.empty_cache()
            cache_path = (
                hf_home / "hub" / f"models--{model_id.replace('/', '--')}"
            )
            if cache_path.exists():
                shutil.rmtree(cache_path, ignore_errors=True)
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["model_results"].append(record)

    passed = sum(item["status"] == "PASS" for item in report["model_results"])
    report["model_count_passed"] = passed
    report["status"] = "RUNTIME_SMOKE_PASS" if passed == 3 else "RUNTIME_SMOKE_HOLD"
    receipt = _write_receipt(output_path, report)
    return {
        "status": report["status"],
        "model_count_passed": passed,
        "model_count_expected": 3,
        "receipt": receipt,
        "training_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_runtime_smoke(profile_path=args.profile, output_path=args.output)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "RUNTIME_SMOKE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

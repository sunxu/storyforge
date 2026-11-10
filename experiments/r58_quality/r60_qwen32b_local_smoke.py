"""One real Qwen3-32B H200 engine and generation smoke from verified local weights.

No StoryForge private examples, quality decisions, checkpoints or training.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

SCHEMA = "storyforge_r60_qwen32b_local_smoke_safe_v1"


def emit(event: str, **data: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **data},
                     sort_keys=True), flush=True)


def run(local_path: Path) -> int:
    from r60_qwen32b_weight_stage import frozen_manifest

    frozen_manifest(local_path)
    os.environ["VLLM_LOGGING_LEVEL"] = "INFO"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    emit("REAL_ENGINE_INIT_START")
    started = time.monotonic()
    try:
        from vllm import LLM, SamplingParams

        engine = LLM(model=str(local_path), tokenizer=str(local_path),
                     trust_remote_code=False, dtype="bfloat16",
                     max_model_len=32768, max_num_seqs=1,
                     enforce_eager=True, gpu_memory_utilization=0.80,
                     disable_log_stats=True)
        emit("REAL_ENGINE_READY", elapsed_sec=round(time.monotonic() - started, 1))
        result = engine.generate(["你好"], SamplingParams(
            temperature=0, max_tokens=32), use_tqdm=False)
        generated = bool(result and result[0].outputs and
                         len(result[0].outputs[0].token_ids) > 0)
        if not generated:
            emit("REAL_GENERATE_HOLD", reason_code="EMPTY_GENERATION")
            return 42
        emit("REAL_GENERATE_DONE", elapsed_sec=round(time.monotonic() - started, 1),
             generated_tokens=len(result[0].outputs[0].token_ids))
        return 0
    except Exception:  # noqa: BLE001 - redact paths and raw generated text
        emit("REAL_SMOKE_HOLD", reason_code="RUNTIME_ERROR_REDACTED",
             elapsed_sec=round(time.monotonic() - started, 1))
        return 42


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-dir", type=Path, required=True)
    parser.add_argument("--confirm-paid-gpu", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_gpu:
        emit("REAL_SMOKE_HOLD", reason_code="PAID_GPU_NOT_AUTHORIZED")
        return 42
    try:
        return run(args.local_dir)
    except Exception:  # noqa: BLE001 - redact all private filesystem details
        emit("REAL_SMOKE_HOLD", reason_code="PRELOAD_VALIDATION_HOLD")
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

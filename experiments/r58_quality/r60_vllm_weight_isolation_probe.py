"""R60 safe model-weight isolation probe; no private review inputs.

Modes:
  cache: CPU-only inspection of pinned model's *local* HF cache.
  dummy: paid GPU engine initialization with load_format='dummy' and no inference.
The dummy result proves engine construction only, NOT real weight or review readiness.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"
SCHEMA = "storyforge_r60_weight_isolation_safe_v1"


def emit(event: str, **values: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **values},
                     sort_keys=True), flush=True)


def cache_dir() -> Path:
    root = os.environ.get("HF_HUB_CACHE")
    if not root:
        home = os.environ.get("HF_HOME")
        root = str(Path(home).expanduser() / "hub") if home else str(
            Path.home() / ".cache" / "huggingface" / "hub")
    return Path(root).expanduser() / "models--Qwen--Qwen3-32B" / "snapshots" / REV


def cache_probe(root: Path | None = None) -> dict:
    directory = root or cache_dir()
    if not directory.is_dir():
        return {"status": "PINNED_SNAPSHOT_NOT_LOCAL",
                "shards_expected": None, "shards_present": 0}
    index = directory / "model.safetensors.index.json"
    if not index.is_file():
        return {"status": "PINNED_INDEX_MISSING",
                "shards_expected": None, "shards_present": 0}
    try:
        index_data = json.loads(index.read_text())
        mapping = index_data["weight_map"]
        shards = {name for name in mapping.values()
                  if isinstance(name, str) and name.endswith(".safetensors")
                  and "/" not in name and "\\" not in name}
        if not shards or len(shards) > 512:
            return {"status": "PINNED_INDEX_INVALID"}
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "PINNED_INDEX_INVALID"}
    found = 0
    total = 0
    probe_ms = 0.0
    for name in sorted(shards):
        path = directory / name
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size <= 0:
            continue
        # Tiny read at both ends checks accessibility without scanning ~65GB.
        start = time.monotonic()
        try:
            with path.open("rb") as fp:
                if len(fp.read(4096)) == 0:
                    continue
                fp.seek(max(0, size - 4096))
                if len(fp.read(4096)) == 0:
                    continue
        except OSError:
            continue
        probe_ms += (time.monotonic() - start) * 1000
        found += 1
        total += size
    return {
        "status": ("LOCAL_SHARDS_ACCESSIBLE" if found == len(shards)
                   else "LOCAL_SHARDS_INCOMPLETE"),
        "shards_expected": len(shards), "shards_present": found,
        "weight_gib": round(total / 1073741824, 2),
        "sample_read_ms": round(probe_ms, 1),
    }


def dummy_probe() -> int:
    os.environ["VLLM_LOGGING_LEVEL"] = "INFO"
    emit("DUMMY_ENGINE_START", model_pinned=True, revision_pinned=True)
    start = time.monotonic()
    try:
        from vllm import LLM
        model = LLM(
            model=MODEL, revision=REV, tokenizer_revision=REV,
            trust_remote_code=False, dtype="bfloat16",
            load_format="dummy", max_model_len=32768, max_num_seqs=1,
            enforce_eager=True, gpu_memory_utilization=0.80,
            disable_log_stats=True)
    except Exception:  # noqa: BLE001 - no paths or stack dumps from private runtime
        emit("DUMMY_ENGINE_HOLD", reason_code="DUMMY_INIT_FAILED_REDACTED",
             elapsed_sec=round(time.monotonic() - start, 1))
        return 42
    emit("DUMMY_ENGINE_READY", elapsed_sec=round(time.monotonic() - start, 1))
    del model
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("cache", "dummy"))
    parser.add_argument("--confirm-paid-gpu", action="store_true")
    args = parser.parse_args()
    if args.mode == "cache":
        result = cache_probe()
        emit("CACHE_PROBE", **result)
        return 0 if result["status"] == "LOCAL_SHARDS_ACCESSIBLE" else 42
    if not args.confirm_paid_gpu:
        emit("DUMMY_ENGINE_HOLD", reason_code="PAID_GPU_NOT_AUTHORIZED")
        return 42
    return dummy_probe()


if __name__ == "__main__":
    raise SystemExit(main())

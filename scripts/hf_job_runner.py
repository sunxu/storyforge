#!/usr/bin/env python3
"""HF Job entrypoint. Mount the private training bucket at /workspace."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/workspace")
DATA = ROOT / "datasets/v0.3"
RUN = ROOT / "runs" / os.environ.get("JOB_ID", "local-smoke")
ENV = ROOT / "env"
CACHE = ROOT / "cache"

def run(cmd: list[str], **kwargs: object) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)

def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(CACHE / "huggingface")
    os.environ["PIP_CACHE_DIR"] = str(CACHE / "pip")
    os.environ["PYTHONUNBUFFERED"] = "1"
    # Reuse package wheels/cache, but use the container's compatible PyTorch.
    run([sys.executable, "-m", "pip", "install", "-U",
         "ms-swift", "transformers>=5.2.0", "bitsandbytes",
         "qwen_vl_utils", "decord"])
    from importlib.metadata import version
    (RUN / "environment.json").write_text(json.dumps({
        "python": sys.version,
        "ms_swift": version("ms-swift"),
        "transformers": version("transformers"),
        "job_id": os.environ.get("JOB_ID"),
    }, indent=2))
    script = ROOT / "scripts/prepare_sft.py"
    for split in ("train", "validation"):
        source = DATA / f"{split}.jsonl"
        if not source.is_file():
            raise FileNotFoundError(f"missing {source}")
        run([sys.executable, str(script),
             "--source", str(source),
             "--output", str(RUN / f"{split}.jsonl")])
    config = ROOT / "configs/qwen38-27b-qlora-smoke.yaml"
    cmd = ["swift", "sft", str(config),
           "--dataset", str(RUN / "train.jsonl"),
           "--val_dataset", str(RUN / "validation.jsonl"),
           "--output_dir", str(RUN / "output"),
           "--max_steps", "3",
           "--max_length", "16384",
           "--save_only_model", "false"]
    try:
        with (RUN / "train.log").open("w") as log:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            code = process.wait()
        if code:
            raise RuntimeError(f"swift exited {code}")
        (RUN / "SUCCESS").write_text("Smoke training exited successfully; adapter reload unverified\n")
    finally:
        print("Artifacts at", RUN, flush=True)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""R58 CPU-only HF Job bootstrap. Direct python argv; no shell -c/-lc.

Code-only entrypoint, staged with original SHA256 manifest. No model weights,
GPU or inference. Operates solely on the exact R58 run-key directory.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess
import sys

RUN_RE = re.compile(r"r58-hfcpu132-\d{8}T\d{6}Z-\d{6}\Z")
BASE = Path("/workspace/preflight/r58/hf-cpu132")


def main():
    if len(sys.argv) != 2 or not RUN_RE.fullmatch(sys.argv[1]):
        print("R58_CPU132_INVALID_RUN_KEY__HOLD", file=sys.stderr)
        return 42
    key = sys.argv[1]
    source = BASE / "runs" / key
    result = BASE / "results" / key
    worker = source / "code/gold195_hf_review_cpu_worker.py"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    check = [sys.executable, str(worker), "--stage", str(source),
             "--result-dir", str(result), "--run-key", key]
    # The frozen manifest and 132 input contract are checked before pip.
    subprocess.run(check, check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                    "transformers==5.16.1", "huggingface_hub>=1.7,<3",
                    "jinja2>=3.1,<4"], check=True)
    result.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    subprocess.run(check + ["--run"], check=True)
    print("R58_HF_CPU132_BOOTSTRAP_COMPLETE__NO_GPU_NO_TRAIN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

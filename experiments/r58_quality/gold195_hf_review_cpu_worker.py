#!/usr/bin/env python3
"""R58 private HF CPU tokenizer worker. Requires pinned stage and no GPU.

This file is bundled with the original GPU prompt-rendering module for exact
prompt parity. No model weights, inference, training, R50, or private stdout.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from gold195_hf_review_gpu_runner import make_prompt, canon

MODEL = "Qwen/Qwen3-32B"
MODEL_REVISION = "9216db5781bf21249d130ec9da846c4624c16137"
SCHEMA = "r58_hf_semantic_review_input_private_v1"
RUN_RE = re.compile(r"r58-hfcpu132-\d{8}T\d{6}Z-\d{6}\Z")
FILES = (
    "code/gold195_hf_review_cpu_worker.py",
    "code/gold195_hf_review_gpu_runner.py",
    "private/input132.private.jsonl",
)


def verify_stage(stage):
    manifest = stage / "SHA256SUMS.txt"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("stage manifest missing")
    entries = {}
    for line in manifest.read_text().splitlines():
        if not re.fullmatch(r"[a-f0-9]{64}  (?:code|private)/[a-zA-Z0-9_.-]+", line):
            raise ValueError("invalid manifest format")
        digest, name = line.split("  ", 1)
        if name in entries:
            raise ValueError("duplicate manifest entry")
        entries[name] = digest
    if set(entries) != set(FILES):
        raise ValueError("wrong staged file set")
    for name, digest in entries.items():
        path = stage / name
        if (not path.is_file() or path.is_symlink()
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError("source bytes mismatch")
    return entries


def load_rows(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < 120 * 1024 * 1024:
        raise ValueError("invalid private input")
    rows = [json.loads(x) for x in path.read_bytes().splitlines() if x.strip()]
    if len(rows) != 132:
        raise ValueError("expected exactly 132 cases")
    for i, row in enumerate(rows, 1):
        if (not isinstance(row, dict) or row.get("schema") != SCHEMA
                or row.get("review_label") != "full%03d" % i
                or row.get("training_authorized") is not False
                or not isinstance(row.get("original_history"), list)
                or not row["original_history"]):
            raise ValueError("source contract invalid")
    return rows


def preflight(rows, tokenizer, context=8192, reserve=1200):
    sizes = []
    for row in rows:
        prompt = make_prompt(row)
        try:
            ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True, add_generation_prompt=True)
        sizes.append(len(ids))
    sizes.sort()
    within = sum(x + reserve <= context for x in sizes)
    return {
        "cases_total": len(sizes), "fits_context": within,
        "token_hold": len(sizes) - within,
        "prompt_tokens_min": sizes[0],
        "prompt_tokens_median": sizes[(len(sizes)-1)//2],
        "prompt_tokens_p95": sizes[(len(sizes)*95+99)//100-1],
        "prompt_tokens_max": sizes[-1],
        "max_model_len": context, "max_output_tokens": reserve,
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--result-dir", type=Path, required=True)
    p.add_argument("--run-key", required=True)
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    try:
        if not RUN_RE.fullmatch(args.run_key) or not args.stage.is_absolute():
            raise ValueError("invalid run identity")
        verify_stage(args.stage)
        if not args.run:
            print("R58_HF_CPU132_STAGE_SHA256_PASS__NO_INFERENCE")
            return 0
        if (os.environ.get("CUDA_VISIBLE_DEVICES") != ""
                or args.result_dir.exists()
                or not args.result_dir.is_absolute()):
            raise ValueError("CPU only or output already exists")
        rows = load_rows(args.stage / "private/input132.private.jsonl")
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL, revision=MODEL_REVISION, trust_remote_code=False)
        counts = preflight(rows, tokenizer)
        report = {
            "schema": "r58_hf_cpu132_tokenizer_safe_v1",
            "status": "R58_HF_CPU132_TOKEN_LENGTHS_CHECKED__NO_INFERENCE",
            "source_rows_verified": 132, "model": MODEL,
            "model_revision": MODEL_REVISION,
            "counts": counts, "gpu_used": False, "training_performed": False,
            "quality_v1_admitted": 0, "r50_accessed": False,
            "private_text_or_case_ids_emitted": False,
        }
        args.result_dir.mkdir(mode=0o700, parents=False)
        target = args.result_dir / "R58_HF_CPU132_SAFE.json"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(canon(report))
        print("R58_HF_CPU132_SAFE_REPORT_WRITTEN__NO_TRAIN")
        return 0
    except Exception:
        print("R58_HF_CPU132_SOURCE_OR_RUNTIME_INVALID__HOLD", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

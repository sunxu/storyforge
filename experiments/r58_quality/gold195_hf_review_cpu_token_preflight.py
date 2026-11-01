#!/usr/bin/env python3
"""CPU-only Qwen3 pinned tokenizer preflight for R58 HF 132 review.

No training, GPU, HF Job, bucket upload, or story content emitted to stdout.
Downloads only public tokenizer assets from Hugging Face when not cached.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import re

from gold195_hf_review_batch import locked_read, SCHEMA
from gold195_hf_review_gpu_runner import make_prompt

DEFAULT_MODEL = "Qwen/Qwen3-32B"
DEFAULT_REVISION = "9216db5781bf21249d130ec9da846c4624c16137"


def validate_input(rows):
    if len(rows) != 132:
        raise ValueError("expected 132 private rows")
    seen = set()
    for i, row in enumerate(rows, 1):
        if (not isinstance(row, dict) or row.get("schema") != SCHEMA
                or row.get("review_label") != "full%03d" % i
                or row.get("review_label") in seen
                or row.get("training_authorized") is not False
                or not isinstance(row.get("original_history"), list)
                or not row["original_history"]
                or not isinstance(row.get("frozen_target_text"), str)
                or not isinstance(row.get("source_card_snapshot"), dict)):
            raise ValueError("input contract mismatch")
        seen.add(row["review_label"])
    return rows


def count_lengths(rows, tokenizer, max_model_len, max_output_tokens):
    lengths, exceeding = [], 0
    labels = set()
    for row in rows:
        prompt = make_prompt(row)
        try:
            ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True, add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True, add_generation_prompt=True,
            )
        size = len(ids)
        lengths.append(size)
        if size + max_output_tokens > max_model_len:
            exceeding += 1
            labels.add(row["review_label"])
    lengths.sort()
    return {
        "cases_total": len(rows),
        "fits_context": len(rows) - exceeding,
        "token_hold": exceeding,
        "prompt_tokens_min": lengths[0],
        "prompt_tokens_median": lengths[(len(lengths)-1)//2],
        "prompt_tokens_p95": lengths[min(len(lengths)-1, (len(lengths)*95+99)//100-1)],
        "prompt_tokens_max": lengths[-1],
        "max_model_len": max_model_len,
        "max_output_tokens": max_output_tokens,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-input", type=Path, required=True)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--model-revision", default=DEFAULT_REVISION)
    p.add_argument("--max-model-len", type=int, default=8192)
    p.add_argument("--max-output-tokens", type=int, default=1200)
    a = p.parse_args()
    try:
        if (not re.fullmatch("[0-9a-f]{40}", a.model_revision)
                or a.model != DEFAULT_MODEL
                or a.model_revision != DEFAULT_REVISION
                or not 1024 <= a.max_model_len <= 32768
                or not 128 <= a.max_output_tokens <= 4096):
            raise ValueError("unexpected model revision/context")
        rows = validate_input([json.loads(x) for x in locked_read(
            a.private_input).splitlines() if x.strip()])
        # Import after validating all private input so malformed data needs no
        # network access. HF tokenizer download may use normal public network.
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            a.model, revision=a.model_revision, trust_remote_code=False)
        counts = count_lengths(rows, tokenizer,
                               a.max_model_len, a.max_output_tokens)
        report = {
            "schema": "r58_hf_semantic_cpu_token_preflight_safe_v1",
            "status": "CPU_ONLY_PINNED_TOKENIZER_PREFLIGHT__NO_GPU",
            "model": a.model, "model_revision": a.model_revision,
            "counts": counts,
            "hf_job_started": False, "gpu_authorized": False,
            "model_inference_performed": False, "private_bucket_uploaded": False,
            "r50_accessed": False, "quality_v1_admitted": 0,
            "private_text_or_ids_emitted": False,
        }
        exit_code = 0
    except Exception:
        report = {
            "schema": "r58_hf_semantic_cpu_token_preflight_safe_v1",
            "status": "TOKENIZER_OR_PRIVATE_INPUT_INVALID__HOLD",
            "hf_job_started": False, "gpu_authorized": False,
            "r50_accessed": False, "quality_v1_admitted": 0,
        }
        exit_code = 42
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

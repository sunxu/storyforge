#!/usr/bin/env python3
"""HF CPU-only, 13/13 private Gold195 A/B reviewer prompt token preflight.

Imports the exact reviewer prompt serializer and tokenization code. Never runs
vLLM or loads model weights; never prints source, prompts, IDs or token arrays.
Run *on Hugging Face CPU*, not on the Mac. Does not launch a Job itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

try:
    # Repository test / development import.
    from r58_hf_gpu_literary_reviewer import (
        MODELS, read_source, encode_one, prompt_messages, JUDGE_SYSTEM, JUDGE_USER,
    )
except ModuleNotFoundError:
    # Private staged HF mount contains runner.py, never another reviewer's input.
    from runner import MODELS, read_source, encode_one, prompt_messages, JUDGE_SYSTEM, JUDGE_USER

try:
    from token_core import describe_token_lengths, digest_serialized_items
except ModuleNotFoundError:
    # Repository execution: reviewer.py resolves src/ without requiring Mac pip.
    from storyforge_dataset.token_preflight import (
        describe_token_lengths, digest_serialized_items,
    )

SCHEMA = "r58_hf_cpu_literary_token_preflight_all13_safe_v1"
MODE = "R58_HF_CPU_GOLD195_TOKEN_PREFLIGHT_ALL13_PASS__NO_GPU"
HOLD = "R58_HF_CPU_GOLD195_TOKEN_PREFLIGHT_ALL13_HOLD"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def check_all(args, tokenizer_factory=None, package_version=None):
    if (args.slot not in MODELS or args.model != MODELS[args.slot]
            or HEX40.fullmatch(args.revision) is None
            or args.max_model_len < 4096 or args.max_model_len > 40960
            or args.max_output_tokens < 1200 or args.max_output_tokens > 4096
            or not re.fullmatch(r"\d+\.\d+\.\d+", args.transformers_version)):
        raise ValueError("CONFIG_INVALID")
    if not args.input.is_absolute() or not args.input.is_file() or args.input.is_symlink():
        raise ValueError("PRIVATE_INPUT_INVALID")
    if (not args.output_dir.is_absolute() or not args.output_dir.is_dir()
            or args.output_dir.is_symlink()):
        raise ValueError("PRIVATE_OUTPUT_DIR_INVALID")
    if (args.output_dir / "r58_cpu_preflight_all13_safe.json").exists():
        raise ValueError("SAFE_RECEIPT_ALREADY_EXISTS")
    rows = read_source(args.input)  # exactly 13 unreviewed blind cases
    if tokenizer_factory is None:
        from transformers import AutoTokenizer, __version__ as transformers_version
        tokenizer_factory = AutoTokenizer.from_pretrained
    else:
        transformers_version = package_version
    if transformers_version != args.transformers_version:
        raise ValueError("TRANSFORMERS_VERSION_MISMATCH")
    tokenizer = tokenizer_factory(args.model, revision=args.revision,
                                  trust_remote_code=False)
    template = getattr(tokenizer, "chat_template", None)
    if not isinstance(template, str) or not template:
        raise ValueError("CHAT_TEMPLATE_MISSING")
    lengths = [len(encode_one(tokenizer, r, args.model)) for r in rows]
    if len(lengths) != 13:
        raise ValueError("EXPECTED_13")
    stats = describe_token_lengths(
        lengths, max_model_len=args.max_model_len,
        reserved_output_tokens=args.max_output_tokens, pilot_count=2,
    )
    # Reuse identity covers the actual bytes AND serialized judge prompts.
    # Hashes are kept in the private receipt, not in stdout/log SAFE summary.
    source_digest = hashlib.sha256(args.input.read_bytes()).hexdigest()
    prompt_digest = digest_serialized_items([prompt_messages(row) for row in rows])
    payload = {
        "schema": SCHEMA,
        "status": MODE if stats["over_budget_count"] == 0 else HOLD,
        "slot": args.slot,
        "model": args.model,
        "model_revision": args.revision,
        "transformers_version": transformers_version,
        "tokenizer_class": type(tokenizer).__name__,
        "chat_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
        "reviewer_prompt_template_sha256": hashlib.sha256(
            (JUDGE_SYSTEM + JUDGE_USER).encode("utf-8")).hexdigest(),
        **stats,
        "private_input_sha256": source_digest,
        "serialized_prompt_batch_sha256": prompt_digest,
        "inference_performed": False,
        "model_weights_loaded": False,
        "paid_gpu_submitted": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "private_text_emitted": False,
    }
    return payload


def save_receipt(output_dir: Path, payload: dict):
    target = output_dir / "r58_cpu_preflight_all13_safe.json"
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        f.write(b"\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=("A", "B"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--transformers-version", required=True)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--max-output-tokens", type=int, default=2400)
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    try:
        receipt = check_all(args)
        save_receipt(args.output_dir, receipt)
        code = 0 if receipt["status"] == MODE else 42
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError and str(exc) in {
            "CONFIG_INVALID", "PRIVATE_INPUT_INVALID", "PRIVATE_OUTPUT_DIR_INVALID",
            "SAFE_RECEIPT_ALREADY_EXISTS", "TRANSFORMERS_VERSION_MISMATCH",
            "CHAT_TEMPLATE_MISSING", "EXPECTED_13",
        } else "TOKENIZER_OR_PRIVATE_INPUT_ERROR"
        receipt = {
            "schema": SCHEMA, "status": HOLD, "reason_code": reason,
            "quality_v1_admitted": 0, "training_authorized": False,
            "paid_gpu_submitted": False, "private_text_emitted": False,
        }
        code = 42
    # Only SAFE aggregate leaves the private output; never print source hashes.
    public = {k: v for k, v in receipt.items()
              if k not in ("private_input_sha256", "serialized_prompt_batch_sha256")}
    print(json.dumps(public, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())

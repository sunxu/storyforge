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
import stat
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

SCHEMA = "r58_hf_cpu_literary_token_preflight_all13_safe_v2"
MODE = "R58_HF_CPU_GOLD195_TOKEN_PREFLIGHT_ALL13_PASS__NO_GPU"
HOLD = "R58_HF_CPU_GOLD195_TOKEN_PREFLIGHT_ALL13_HOLD"
def _code_digests():
    """Runtime source identity: code-only; never includes story bytes."""
    try:
        import runner as reviewer
        import token_core as core
    except ModuleNotFoundError:
        import r58_hf_gpu_literary_reviewer as reviewer
        from storyforge_dataset import token_preflight as core
    return {
        "reviewer_code_sha256": hashlib.sha256(Path(reviewer.__file__).read_bytes()).hexdigest(),
        "token_core_sha256": hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
    }


def _private_fingerprints(rows, input_path):
    return {
        "private_input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "serialized_prompt_batch_sha256":
            digest_serialized_items([prompt_messages(row) for row in rows]),
        **_code_digests(),
    }


def verify_reuse(args):
    """Mac-safe receipt integrity check. No Transformers/tokenizer or Job invoked."""
    path = args.output_dir / "r58_cpu_preflight_all13_safe.json"
    if (path.is_symlink() or not path.is_file()
            or stat.S_IMODE(path.stat().st_mode) != 0o600
            or path.stat().st_size > 32 * 1024):
        raise ValueError("CACHE_RECEIPT_MISSING_OR_UNSAFE")
    record = json.loads(path.read_bytes())
    rows = read_source(args.input)
    expected = {
        "schema": SCHEMA,
        "status": MODE,
        "slot": args.slot,
        "model": args.model,
        "model_revision": args.revision,
        "transformers_version": args.transformers_version,
        "max_model_len": args.max_model_len,
        "reserved_output_tokens": args.max_output_tokens,
        "cases_checked": 13,
        "over_budget_count": 0,
        "pilot_cases_checked": 2,
        "remaining_cases_checked": 11,
        "private_text_emitted": False,
        "training_authorized": False,
        **_private_fingerprints(rows, args.input),
    }
    if not isinstance(record, dict) or any(record.get(k) != v for k, v in expected.items()):
        raise ValueError("CACHE_IDENTITY_MISMATCH")
    if (type(record.get("max_total_tokens")) is not int
            or record["max_total_tokens"] > args.max_model_len
            or type(record.get("prompt_tokens_max")) is not int
            or not 32 <= record["prompt_tokens_max"] <= record["max_total_tokens"]):
        raise ValueError("CACHE_BUDGET_INVALID")
    return {
        "schema": SCHEMA,
        "status": "R58_HF_CPU_TOKEN_PREFLIGHT_CACHED_PASS__NO_JOB",
        "cases_checked": 13, "slot": args.slot,
        "paid_gpu_submitted": False, "private_text_emitted": False,
        "training_authorized": False,
    }


HEX40 = re.compile(r"^[0-9a-f]{40}$")

SAFE_FAILURE_REASONS = {
    "PRIVATE_INPUT_READ_FAILED",
    "PRIVATE_INPUT_JSON_INVALID",
    "PRIVATE_INPUT_VALIDATION_FAILED",
    "PRIVATE_INPUT_SOURCE_PATH_INVALID",
    "PRIVATE_INPUT_SOURCE_EXPECTED_13",
    "PRIVATE_INPUT_SOURCE_UNREVIEWED_CONTRACT_INVALID",
    "PRIVATE_INPUT_SOURCE_CHAT_INVALID",
    "TOKENIZER_IMPORT_FAILED",
    "TOKENIZER_LOAD_FAILED",
    "TOKENIZATION_FAILED",
    "CHAT_TEMPLATE_RENDER_FAILED_TYPE_ERROR",
    "CHAT_TEMPLATE_RENDER_FAILED_RUNTIME_ERROR",
    "CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR",
    "CHAT_TEMPLATE_RENDER_FAILED_OTHER",
    "TOKEN_IDS_INVALID",
    "CHAT_MESSAGES_INVALID",
    "TOKEN_BUDGET_SUMMARY_FAILED",
    "PREFLIGHT_FINGERPRINT_FAILED",
}


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
    try:
        rows = read_source(args.input)  # exactly 13 unreviewed blind cases
    except OSError:
        raise ValueError("PRIVATE_INPUT_READ_FAILED") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("PRIVATE_INPUT_JSON_INVALID") from None
    except Exception as exc:
        source_codes = {
            "SOURCE_PATH_INVALID", "SOURCE_EXPECTED_13",
            "SOURCE_UNREVIEWED_CONTRACT_INVALID", "SOURCE_CHAT_INVALID",
        }
        code = str(exc) if type(exc) is ValueError and str(exc) in source_codes else None
        raise ValueError(
            f"PRIVATE_INPUT_{code}" if code else "PRIVATE_INPUT_VALIDATION_FAILED"
        ) from None
    if tokenizer_factory is None:
        try:
            from transformers import AutoTokenizer, __version__ as transformers_version
            tokenizer_factory = AutoTokenizer.from_pretrained
        except Exception:
            raise ValueError("TOKENIZER_IMPORT_FAILED") from None
    else:
        transformers_version = package_version
    if transformers_version != args.transformers_version:
        raise ValueError("TRANSFORMERS_VERSION_MISMATCH")
    try:
        tokenizer = tokenizer_factory(args.model, revision=args.revision,
                                      trust_remote_code=False)
    except Exception:
        raise ValueError("TOKENIZER_LOAD_FAILED") from None
    template = getattr(tokenizer, "chat_template", None)
    if not isinstance(template, str) or not template:
        raise ValueError("CHAT_TEMPLATE_MISSING")
    try:
        lengths = [len(encode_one(tokenizer, r, args.model)) for r in rows]
    except Exception as exc:
        known = {
            "CHAT_TEMPLATE_RENDER_FAILED_TYPE_ERROR",
            "CHAT_TEMPLATE_RENDER_FAILED_RUNTIME_ERROR",
            "CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR",
            "CHAT_TEMPLATE_RENDER_FAILED_OTHER",
            "TOKEN_IDS_INVALID", "CHAT_MESSAGES_INVALID",
        }
        code = str(exc) if type(exc) is ValueError and str(exc) in known else "TOKENIZATION_FAILED"
        raise ValueError(code) from None
    if len(lengths) != 13:
        raise ValueError("EXPECTED_13")
    try:
        stats = describe_token_lengths(
            lengths, max_model_len=args.max_model_len,
            reserved_output_tokens=args.max_output_tokens, pilot_count=2,
        )
    except Exception:
        raise ValueError("TOKEN_BUDGET_SUMMARY_FAILED") from None
    # Reuse identity covers the actual bytes AND serialized judge prompts.
    # Hashes are kept in the private receipt, not in stdout/log SAFE summary.
    try:
        fingerprints = _private_fingerprints(rows, args.input)
    except Exception:
        raise ValueError("PREFLIGHT_FINGERPRINT_FAILED") from None
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
        **fingerprints,
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
    parser.add_argument("--verify-cache-only", action="store_true",
                        help="Mac-safe integrity of previously synced private SAFE receipt")
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    try:
        if args.verify_cache_only:
            receipt = verify_reuse(args)
            code = 0
        else:
            receipt = check_all(args)
            save_receipt(args.output_dir, receipt)
            code = 0 if receipt["status"] == MODE else 42
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError and str(exc) in {
            "CONFIG_INVALID", "PRIVATE_INPUT_INVALID", "PRIVATE_OUTPUT_DIR_INVALID",
            "SAFE_RECEIPT_ALREADY_EXISTS", "TRANSFORMERS_VERSION_MISMATCH",
            "CHAT_TEMPLATE_MISSING", "EXPECTED_13",
            "CACHE_RECEIPT_MISSING_OR_UNSAFE", "CACHE_IDENTITY_MISMATCH",
            "CACHE_BUDGET_INVALID",
            *SAFE_FAILURE_REASONS,
        } else "TOKENIZER_OR_PRIVATE_INPUT_ERROR"
        receipt = {
            "schema": SCHEMA, "status": HOLD, "reason_code": reason,
            "quality_v1_admitted": 0, "training_authorized": False,
            "paid_gpu_submitted": False, "private_text_emitted": False,
        }
        code = 42
    # Only SAFE aggregate leaves the private output; never print source hashes.
    public = {k: v for k, v in receipt.items()
              if k not in ("private_input_sha256", "serialized_prompt_batch_sha256",
                           "reviewer_code_sha256", "token_core_sha256")}
    print(json.dumps(public, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())

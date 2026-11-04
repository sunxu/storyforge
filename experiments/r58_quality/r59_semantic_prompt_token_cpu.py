"""R59 Pilot8 HF CPU-only tokenizer audit. No inference, GPU or admission.

Run only on Hugging Face CPU against an immutable model revision. Uses the
shared StoryForge token_preflight core, never a new token length algorithm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

# HF Jobs uploads the entry script separately under /data, while the
# read-only local input volume is mounted at /job. Resolve the shared core
# from that mount before trying repository-local development imports.
_JOB_VOLUME = Path("/job")
if _JOB_VOLUME.is_dir():
    sys.path.insert(0, str(_JOB_VOLUME))

try:
    from token_core import describe_token_lengths, digest_serialized_items, encode_chat
except ModuleNotFoundError:
    # Local development fallback: find the repository's src directory without
    # assuming a fixed depth (HF's /data/runner.py has no such ancestor).
    _SOURCE_ROOT = next(
        (parent / "src" for parent in Path(__file__).resolve().parents
         if (parent / "src" / "storyforge_dataset" / "token_preflight.py").is_file()),
        None,
    )
    if _SOURCE_ROOT is None:
        raise
    sys.path.insert(0, str(_SOURCE_ROOT))
    from storyforge_dataset.token_preflight import (
        describe_token_lengths,
        digest_serialized_items,
        encode_chat,
    )

SCHEMA = "storyforge-r59-pilot8-hf-cpu-review-token-safe-v1"
PROMPT_SCHEMA = "storyforge-r59-semantic-review-prompt-private-v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_INPUT_BYTES = 160 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_private(path: Path) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("INPUT_INVALID")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1 or not 0 < info.st_size <= MAX_INPUT_BYTES):
        raise ValueError("INPUT_INVALID")
    return path.read_bytes()


def load_prompts(raw: bytes, expected_sha: str, expected_fingerprint: str) -> list[dict]:
    if (HEX64.fullmatch(expected_sha) is None or sha(raw) != expected_sha
            or HEX64.fullmatch(expected_fingerprint) is None):
        raise ValueError("SOURCE_PIN_MISMATCH")
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise ValueError("INPUT_JSON_INVALID") from None
    if len(rows) != 8:
        raise ValueError("INPUT_COUNT_INVALID")
    for i, row in enumerate(rows):
        if (not isinstance(row, dict) or row.get("schema") != PROMPT_SCHEMA
                or row.get("pilot_index") != i
                or row.get("prompt_fingerprint") != expected_fingerprint
                or row.get("review_decision") is not None
                or row.get("gpu_started") is not False
                or row.get("quality_v1_admitted") is not False
                or not isinstance(row.get("messages"), list)
                or len(row["messages"]) != 2
                or any(not isinstance(m, dict) for m in row["messages"])
                or [m["role"] for m in row["messages"]] != ["system", "user"]
                or any(not isinstance(m.get("content"), str) or not m["content"].strip()
                       for m in row["messages"])
                or not isinstance(row.get("history_coverage"), dict)
                or row["history_coverage"].get("scope") != "FULL_STAGED_SUFFIX_ONLY"):
            raise ValueError("PROMPT_CONTRACT_INVALID")
    return rows


def audit(raw: bytes, *, expected_sha: str, expected_fingerprint: str,
          model: str, revision: str, max_model_len: int,
          reserved_output_tokens: int, tokenizer, transformers_version: str,
          disable_thinking: bool = True) -> dict:
    if (not isinstance(model, str) or not model.strip() or HEX40.fullmatch(revision) is None
            or type(max_model_len) is not int or not 4096 <= max_model_len <= 131072
            or type(reserved_output_tokens) is not int
            or not 1200 <= reserved_output_tokens <= 4096):
        raise ValueError("CONFIG_INVALID")
    rows = load_prompts(raw, expected_sha, expected_fingerprint)
    prompts = [r["messages"] for r in rows]
    lengths = [len(encode_chat(tokenizer, messages, disable_thinking=disable_thinking))
               for messages in prompts]
    summary = describe_token_lengths(
        lengths, max_model_len=max_model_len,
        reserved_output_tokens=reserved_output_tokens, pilot_count=8,
    )
    return {
        "schema": SCHEMA,
        "status": ("R59_PILOT8_HF_CPU_TOKEN_PASS__NO_GPU" if summary["over_budget_count"] == 0
                   else "R59_PILOT8_HF_CPU_TOKEN_OVER_BUDGET__HOLD"),
        "model": model,
        "revision": revision,
        "model_revision_pinned": True,
        "transformers_version": transformers_version,
        "tokenizer_class": type(tokenizer).__name__,
        "thinking_disabled": disable_thinking,
        "private_input_sha256": expected_sha,
        "prompt_fingerprint": expected_fingerprint,
        "serialized_prompts_sha256": digest_serialized_items(prompts),
        **summary,
        "tokenizer_checked": True,
        "gpu_started": False,
        "training_authorized": False,
        "quality_v1_admitted": 0,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def write_safe(path: Path, report: dict) -> None:
    # HF Jobs RW volume mountpoints may be provisioned with platform-managed
    # directory modes (not 0700). The SAFE file itself is always create-only,
    # O_NOFOLLOW, and 0600; the output volume is unique to this Job.
    if (not path.is_absolute() or path.is_symlink() or not path.parent.is_dir()
            or path.parent.is_symlink()):
        raise ValueError("OUTPUT_PATH_INVALID")
    parent_info = path.parent.stat()
    if not stat.S_ISDIR(parent_info.st_mode) or not parent_info.st_mode & stat.S_IWUSR:
        raise ValueError("OUTPUT_DIRECTORY_NOT_OWNER_WRITABLE")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(json.dumps(report, sort_keys=True, ensure_ascii=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--input-sha256", required=True)
    p.add_argument("--prompt-fingerprint", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--revision", required=True)
    p.add_argument("--max-model-len", type=int, default=32768)
    p.add_argument("--reserved-output-tokens", type=int, default=2400)
    p.add_argument("--output-safe", required=True, type=Path)
    args = p.parse_args()
    report = {"schema": SCHEMA, "status": "R59_PILOT8_HF_CPU_TOKEN_HOLD",
              "tokenizer_checked": False, "gpu_started": False,
              "training_authorized": False, "quality_v1_admitted": 0,
              "r50_accessed": False, "private_values_emitted": False}
    code = 42
    phase = "CONFIG_VALIDATION"
    try:
        # No model weights or torch/vllm imports.
        if HEX40.fullmatch(args.revision) is None:
            raise ValueError("CONFIG_INVALID")
        phase = "INPUT_READ"
        raw = read_private(args.input)
        phase = "PROMPT_VALIDATION"
        load_prompts(raw, args.input_sha256, args.prompt_fingerprint)
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        phase = "TOKENIZER_IMPORT"
        from transformers import AutoTokenizer
        from transformers import __version__ as version
        phase = "TOKENIZER_LOAD"
        tokenizer = AutoTokenizer.from_pretrained(
            args.model, revision=args.revision, trust_remote_code=False,
        )
        phase = "TOKENIZATION"
        report = audit(
            raw, expected_sha=args.input_sha256,
            expected_fingerprint=args.prompt_fingerprint,
            model=args.model, revision=args.revision,
            max_model_len=args.max_model_len,
            reserved_output_tokens=args.reserved_output_tokens,
            tokenizer=tokenizer, transformers_version=version,
        )
        code = 0 if report["status"] == "R59_PILOT8_HF_CPU_TOKEN_PASS__NO_GPU" else 42
    except Exception as exc:  # noqa: BLE001 - never log exception messages or private values
        report.update({
            "status": "R59_PILOT8_HF_CPU_TOKEN_HOLD",
            "tokenizer_checked": False,
            "failure_phase": phase,
            "reason_code": {
                "INPUT_READ": "INPUT_READ_OR_MODE_INVALID",
                "PROMPT_VALIDATION": "PROMPT_CONTRACT_INVALID",
                "TOKENIZER_IMPORT": "TOKENIZER_DEPENDENCY_IMPORT_FAILED",
                "TOKENIZER_LOAD": "TOKENIZER_LOAD_FAILED",
                "TOKENIZATION": "CHAT_TEMPLATE_OR_ENCODING_FAILED",
            }.get(phase, "PREFLIGHT_VALIDATION_FAILED"),
            "exception_type": type(exc).__name__,
        })
        code = 42
    try:
        write_safe(args.output_safe, report)
    except (OSError, ValueError):
        code = 43
        report = {"schema": SCHEMA, "status": "R59_PILOT8_HF_CPU_SAFE_WRITE_HOLD",
                  "gpu_started": False, "training_authorized": False,
                  "quality_v1_admitted": 0, "private_values_emitted": False}
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
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
import sys
from pathlib import Path

from storyforge_dataset.hf_runtime import (
    DiagnosticReporter, InputManager, OutputManager, PathResolver, ReceiptValidator,
    ResourceGuard, RuntimeContext,
)
from storyforge_dataset.hf_runtime.diagnostics import ERROR_CODES

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


def read_private(path: Path, *, path_kind: str = "host") -> bytes:
    resolved = PathResolver.resolve(path, kind=path_kind)
    path = Path(str(resolved.value))
    PathResolver.validate_input_root(path.parent)
    verified = InputManager.open_verified(path, max_bytes=MAX_INPUT_BYTES)
    if verified.size_bytes <= 0:
        raise ValueError("INPUT_SIZE_LIMIT_EXCEEDED")
    return verified.read_bytes()


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


def write_safe(path: Path, report: dict, *, path_kind: str = "host") -> None:
    resolved = PathResolver.resolve(path, kind=path_kind)
    path = Path(str(resolved.value))
    PathResolver.validate_output_root(path.parent)
    try:
        OutputManager.write_safe(path, report, mode=0o600)
    except ValueError as exc:
        if str(exc) == "OUTPUT_ALREADY_EXISTS":
            raise FileExistsError("OUTPUT_ALREADY_EXISTS") from None
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--input-sha256", default=os.environ.get("R59_INPUT_SHA256"))
    p.add_argument("--prompt-fingerprint", default=os.environ.get("R59_PROMPT_FINGERPRINT"))
    p.add_argument("--model", required=True)
    p.add_argument("--revision", required=True)
    p.add_argument("--max-model-len", type=int, default=32768)
    p.add_argument("--reserved-output-tokens", type=int, default=2400)
    p.add_argument("--output-safe", required=True, type=Path)
    p.add_argument("--runtime-diagnostic-safe", required=True, type=Path)
    args = p.parse_args()
    if not args.input_sha256 or not args.prompt_fingerprint:
        p.error("input identity must be supplied through protected HF secrets or explicit private arguments")

    reporter = DiagnosticReporter(profile="cpu")
    report = {"schema": SCHEMA, "status": "R59_PILOT8_HF_CPU_TOKEN_HOLD",
              "tokenizer_checked": False, "gpu_started": False,
              "training_authorized": False, "quality_v1_admitted": 0,
              "r50_accessed": False, "private_values_emitted": False}
    code = 42
    phase = "CONFIG_VALIDATION"
    try:
        phase = "ENVIRONMENT"
        reporter.start_phase("ENVIRONMENT")
        runtime = RuntimeContext.detect(profile="cpu")
        reporter.environment = runtime.to_safe_dict()
        reporter.record_check("runtime_context", "PASS")
        if runtime.runtime != "HF_JOB":
            raise ValueError("RUNTIME_ENVIRONMENT_UNKNOWN")

        phase = "PREFLIGHT"
        reporter.start_phase("PREFLIGHT")
        resource = ResourceGuard.check_cpu_only()
        for name, status in resource.checks.items():
            reporter.record_check(name, status)
        if resource.status != "PASS":
            raise ValueError(resource.error_code or "CPU_PROFILE_RESOURCE_UNKNOWN")
        if HEX40.fullmatch(args.revision) is None:
            raise ValueError("CLI_ARGUMENT_INVALID")

        phase = "INPUT_READ"
        reporter.start_phase("INPUT_READ")
        raw = read_private(args.input, path_kind="container")
        reporter.record_check("input_open_verified", "PASS")

        phase = "PROMPT_VALIDATION"
        reporter.start_phase("INPUT_VALIDATION")
        load_prompts(raw, args.input_sha256, args.prompt_fingerprint)
        reporter.record_check("prompt_contract", "PASS")

        # Tokenizer-only path: no model weights, inference, torch or vLLM imports.
        phase = "TOKENIZER_IMPORT"
        reporter.start_phase("DEPENDENCY_IMPORT")
        from transformers import AutoTokenizer
        from transformers import __version__ as version
        reporter.record_check("tokenizer_dependency_import", "PASS")

        phase = "TOKENIZER_LOAD"
        reporter.start_phase("TOKENIZER_LOAD")
        tokenizer = AutoTokenizer.from_pretrained(
            args.model, revision=args.revision, trust_remote_code=False,
        )
        reporter.record_check("tokenizer_loaded", "PASS")

        phase = "TOKENIZATION"
        reporter.start_phase("TOKENIZATION")
        report = audit(
            raw, expected_sha=args.input_sha256,
            expected_fingerprint=args.prompt_fingerprint,
            model=args.model, revision=args.revision,
            max_model_len=args.max_model_len,
            reserved_output_tokens=args.reserved_output_tokens,
            tokenizer=tokenizer, transformers_version=version,
        )
        post_resource = ResourceGuard.check_cpu_only()
        for name, status in post_resource.checks.items():
            reporter.record_check(name, status)
        if post_resource.status != "PASS":
            raise ValueError(post_resource.error_code or "CPU_PROFILE_RESOURCE_UNKNOWN")
        reporter.record_check("tokenization_completed", "PASS")
        code = 0 if report["status"] == "R59_PILOT8_HF_CPU_TOKEN_PASS__NO_GPU" else 42

    except Exception as exc:  # noqa: BLE001 - never log exception messages or private values
        failed_phase = phase
        business_reason = {
            "ENVIRONMENT": "RUNTIME_ENVIRONMENT_UNKNOWN",
            "PREFLIGHT": "CPU_PROFILE_RESOURCE_UNKNOWN",
            "INPUT_READ": "INPUT_READ_OR_MODE_INVALID",
            "PROMPT_VALIDATION": "PROMPT_CONTRACT_INVALID",
            "TOKENIZER_IMPORT": "TOKENIZER_DEPENDENCY_IMPORT_FAILED",
            "TOKENIZER_LOAD": "TOKENIZER_LOAD_FAILED",
            "TOKENIZATION": "CHAT_TEMPLATE_OR_ENCODING_FAILED",
        }.get(failed_phase, "PREFLIGHT_VALIDATION_FAILED")
        report.update({
            "status": "R59_PILOT8_HF_CPU_TOKEN_HOLD",
            "tokenizer_checked": False,
            "failure_phase": failed_phase,
            "reason_code": business_reason,
            "exception_type": type(exc).__name__,
        })
        raw_code = str(exc) if isinstance(exc, ValueError) else ""
        if raw_code not in ERROR_CODES:
            raw_code = {
                "PROMPT_CONTRACT_INVALID": "INPUT_JSONL_INVALID",
                "RUNTIME_ENVIRONMENT_UNKNOWN": "RUNTIME_ENVIRONMENT_UNKNOWN",
                "TOKENIZER_DEPENDENCY_IMPORT_FAILED": "RUNTIME_INTERNAL_ERROR",
                "TOKENIZER_LOAD_FAILED": "RUNTIME_INTERNAL_ERROR",
                "CHAT_TEMPLATE_OR_ENCODING_FAILED": "RUNTIME_INTERNAL_ERROR",
                "PREFLIGHT_VALIDATION_FAILED": "RUNTIME_INTERNAL_ERROR",
            }.get(business_reason, "RUNTIME_INTERNAL_ERROR")
        runtime_phase = {
            "ENVIRONMENT": "ENVIRONMENT",
            "PREFLIGHT": "PREFLIGHT",
            "INPUT_READ": "INPUT_READ",
            "PROMPT_VALIDATION": "INPUT_VALIDATION",
            "TOKENIZER_IMPORT": "DEPENDENCY_IMPORT",
            "TOKENIZER_LOAD": "TOKENIZER_LOAD",
            "TOKENIZATION": "TOKENIZATION",
        }.get(failed_phase, "BUSINESS_LOGIC")
        reporter.fail(raw_code, phase=runtime_phase)
        code = 42

    try:
        reporter.start_phase("OUTPUT_WRITE")
        if args.output_safe == args.runtime_diagnostic_safe:
            raise ValueError("PATH_KIND_AMBIGUOUS")
        if args.output_safe.parent != args.runtime_diagnostic_safe.parent:
            raise ValueError("PATH_KIND_AMBIGUOUS")
        PathResolver.resolve(args.output_safe, kind="container")
        PathResolver.resolve(args.runtime_diagnostic_safe, kind="container")
        PathResolver.validate_output_root(args.output_safe.parent)
        OutputManager.probe(args.output_safe.parent)
        write_safe(args.output_safe, report, path_kind="container")
        reporter.record_check("business_safe_written", "PASS")
        if report.get("tokenizer_checked") is True:
            reporter.start_phase("COMPLETION")
            reporter.record_check("tokenizer_checked", "PASS")
        reporter.write_safe(args.runtime_diagnostic_safe)
        ReceiptValidator.verify_file(
            args.runtime_diagnostic_safe,
            expected_schema="storyforge-hf-runtime-diagnostic-v1",
        )
    except (OSError, ValueError):
        code = 43
        if reporter.status == "PASS":
            reporter.fail("OUTPUT_CREATE_FAILED", phase="OUTPUT_WRITE")
        report = {"schema": SCHEMA, "status": "R59_PILOT8_HF_CPU_SAFE_WRITE_HOLD",
                  "gpu_started": False, "training_authorized": False,
                  "quality_v1_admitted": 0, "private_values_emitted": False}

    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
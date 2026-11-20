"""CPU-only source-bound Gold48 draft token preflight; not a freeze or inference.

Only a thin private-draft adapter. Reuses storyforge_dataset.token_preflight
for actual Qwen Chat Template encoding and budget statistics. No GPU, weights,
HF Jobs, original historical replies, DB, truncation, or candidate rewriting.
Tokenizer may retrieve ONLY its needed public configuration/tokenizer assets
from the pinned model revision if not already cached.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from itertools import pairwise
from pathlib import Path

from storyforge_dataset.token_preflight import describe_token_lengths, encode_chat

MODEL = "Qwen/Qwen3.8-27B"
REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
SCHEMA = "storyforge_r60_p2_gold48_token_preflight_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_p2_gold48_token_preflight_private_v1"
DRAFT_SCHEMA = "storyforge_r60_gold48_reconstructed_inputs_draft_private_v1"
EXPECTED_STATUS = "RECONSTRUCTED_48_INPUT_DRAFT__OWNER_FREEZE_PENDING"
BUDGETS = ((16384, 1536), (32768, 2048))
MAX_BYTES = 32 * 1024 * 1024


class Hold(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Hold(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def load_draft(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and stat.S_IMODE(info.st_mode) == 0o600
            and 0 < info.st_size <= MAX_BYTES,
            "DRAFT_PRIVATE_FILE_MODE_OR_SIZE_HOLD")
    raw = path.read_bytes()
    doc = json.loads(raw)
    require(isinstance(doc, dict)
            and doc.get("schema") == DRAFT_SCHEMA
            and doc.get("status") == EXPECTED_STATUS
            and doc.get("input_contract") == "RECONSTRUCTED_EVALUATION_INPUT"
            and doc.get("historical_actual_sent_verified") is False
            and doc.get("original_reference_not_read_or_included") is True
            and doc.get("prompt_owner_freeze") is False,
            "DRAFT_INPUT_CONTRACT_HOLD")
    cases = doc.get("cases_PRIVATE")
    require(isinstance(cases, list) and len(cases) == 48,
            "DRAFT_ROW_COUNT_HOLD")
    lengths = []
    sources = Counter()
    memories = Counter()
    for i, row in enumerate(cases):
        require(isinstance(row, dict)
                and row.get("candidate_case_id_PRIVATE") == f"G48-C{i + 1:02d}"
                and row.get("historical_actual_sent_verified") is False
                and row.get("source_components_provenance") == "EVALUATION_TIME_SNAPSHOT"
                and row.get("system_provenance") == "EVALUATION_CONSTRUCTED_GENERIC_SYSTEM"
                and row.get("rules_provenance") == "ONLY_AS_EXPRESSED_IN_PUBLIC_CARD_WORLD"
                and isinstance(row.get("story_id_PRIVATE"), str)
                and isinstance(row.get("source_revision_PRIVATE"), int),
                "DRAFT_CASE_SOURCE_BINDING_HOLD")
        messages = row.get("reconstructed_messages_PRIVATE")
        require(isinstance(messages, list) and 4 <= len(messages) <= 41
                and isinstance(messages[0], dict)
                and messages[0].get("role") == "system"
                and messages[-1].get("role") == "user"
                and all(isinstance(m, dict) and set(m) == {"role", "content"}
                        and m["role"] in ("system", "user", "assistant")
                        and isinstance(m["content"], str) and bool(m["content"].strip())
                        for m in messages)
                and all(m["role"] != "system" for m in messages[1:])
                and all(x["role"] != y["role"] for x, y in pairwise(messages[1:])),
                "DRAFT_MESSAGES_STRUCTURE_HOLD")
        require(sha(canonical(messages)) == row.get(
            "reconstructed_messages_sha256_PRIVATE")
            and sha(canonical(messages[1:])) ==
            row.get("history_prefix_sha256_PRIVATE"),
            "DRAFT_MESSAGES_SHA_OR_HISTORY_MISMATCH_HOLD")
        memory = row.get("memory_provenance")
        require(memory in {"VERIFIED_PRETARGET_SESSION_SUMMARY",
                           "NO_VERIFIED_PRETARGET_MEMORY"},
                "DRAFT_MEMORY_PROVENANCE_HOLD")
        memories[memory] += 1
        sources[row["story_id_PRIVATE"]] += 1
        lengths.append(messages)
    require(len(sources) == 8 and set(sources.values()) == {6},
            "DRAFT_EIGHT_BY_SIX_SCOPE_HOLD")
    return raw, lengths, dict(memories)


def assess(draft_path, tokenizer, tokenizer_version):
    raw, prompts, memories = load_draft(draft_path)
    require(isinstance(getattr(tokenizer, "chat_template", None), str)
            and bool(tokenizer.chat_template.strip()),
            "TOKENIZER_CHAT_TEMPLATE_ABSENT_HOLD")
    modes = {}
    for thinking_mode, disabled in (("default", False), ("disabled", True)):
        try:
            tokens = [len(encode_chat(tokenizer, prompt, disable_thinking=disabled))
                      for prompt in prompts]
            summary = {
                f"context_{cap}_reserve_{reserve}":
                describe_token_lengths(tokens, max_model_len=cap,
                                       reserved_output_tokens=reserve)
                for cap, reserve in BUDGETS
            }
        except ValueError:
            raise Hold("QWEN_CHAT_TEMPLATE_TOKENIZATION_HOLD") from None
        modes[thinking_mode] = {"summary": summary, "token_counts_PRIVATE": tokens}
    template_sha = sha(tokenizer.chat_template.encode("utf-8"))
    details = {
        "schema": PRIVATE_SCHEMA,
        "status": "GOLD48_TOKEN_PREFLIGHT_COMPLETE__NO_PROMPT_FREEZE",
        "input_draft_file_sha256_PRIVATE": sha(raw),
        "tokenizer_model": MODEL,
        "tokenizer_revision": REVISION,
        "tokenizer_version": tokenizer_version,
        "tokenizer_class": type(tokenizer).__name__,
        "chat_template_sha256_PRIVATE": template_sha,
        "mode_token_counts_PRIVATE": {
            mode: info["token_counts_PRIVATE"] for mode, info in modes.items()
        },
        "memory_provenance_counts": memories,
        "budgets_are_diagnostics_not_owner_authorized": True,
        "owner_gold48_freeze": False,
        "gpu_started": False,
        "model_calls": 0,
    }
    receipt = {
        "schema": SCHEMA,
        "status": "GOLD48_48_INPUT_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE",
        "case_count": 48,
        "source_count": 8,
        "memory_pretarget_verified_count":
            memories.get("VERIFIED_PRETARGET_SESSION_SUMMARY", 0),
        "memory_unverified_omitted_count":
            memories.get("NO_VERIFIED_PRETARGET_MEMORY", 0),
        "tokenizer_model_pinned": True,
        "tokenizer_revision_pinned": True,
        "chat_template_modes_checked": 2,
        "mode_stats": {
            mode: {
                name: {
                    "prompt_tokens_min": data["prompt_tokens_min"],
                    "prompt_tokens_median": data["prompt_tokens_median"],
                    "prompt_tokens_p95": data["prompt_tokens_p95"],
                    "prompt_tokens_max": data["prompt_tokens_max"],
                    "over_budget_count": data["over_budget_count"],
                    "max_total_tokens": data["max_total_tokens"],
                } for name, data in info["summary"].items()
            } for mode, info in modes.items()
        },
        "budgets_are_diagnostics_not_owner_authorized": True,
        "full_model_runtime_compatibility_verified": False,
        "history_original_reference_read": False,
        "owner_gold48_freeze": False,
        "database_accessed": False,
        "gpu_started": False,
        "model_calls": 0,
        "private_values_emitted": False,
    }
    return details, receipt


def private_write(path, document):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical(document) + b"\n")


def run(args):
    base = Path.home() / ".local/share/storyforge/r60/private"
    require(base.is_dir() and not base.is_symlink()
            and stat.S_IMODE(base.stat().st_mode) == 0o700,
            "PRIVATE_BASE_MODE_HOLD")
    require(args.draft_dir.parent == base
            and args.output_dir.parent == base
            and not args.output_dir.exists()
            and not args.output_dir.is_symlink(),
            "TOKEN_PREFLIGHT_PRIVATE_PATH_HOLD")
    path = args.draft_dir / "GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
    # Fail on private input shape before importing HF packages or downloading.
    load_draft(path)
    try:
        from transformers import AutoTokenizer
        from transformers import __version__ as transformers_version
    except (ImportError, OSError):
        raise Hold("TOKENIZER_DEPENDENCY_MISSING_HOLD") from None
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL, revision=REVISION, trust_remote_code=False,
            local_files_only=args.local_files_only,
        )
    except (OSError, ValueError, TypeError):
        raise Hold("PINNED_TOKENIZER_LOAD_HOLD") from None
    details, receipt = assess(path, tokenizer, transformers_version)
    os.mkdir(args.output_dir, mode=0o700)
    require(stat.S_IMODE(args.output_dir.stat().st_mode) == 0o700,
            "PRIVATE_OUTPUT_DIRECTORY_MODE_HOLD")
    private_write(args.output_dir / "GOLD48_TOKEN_PREFLIGHT_PRIVATE.json", details)
    private_write(args.output_dir / "GOLD48_TOKEN_PREFLIGHT_SAFE.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--local-files-only", action="store_true",
                        help="Do not download tokenizer/config files if absent from HF cache")
    args = parser.parse_args()
    try:
        result = run(args)
    except (Hold, ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        result = {
            "schema": SCHEMA, "status": "HOLD",
            "reason_code": str(exc) if type(exc) is Hold else "TOKEN_PREFLIGHT_RUNTIME_HOLD",
            "database_accessed": False, "gpu_started": False, "model_calls": 0,
            "private_values_emitted": False,
        }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

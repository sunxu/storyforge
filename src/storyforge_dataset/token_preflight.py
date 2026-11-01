"""Portable, dependency-free StoryForge tokenizer preflight primitives.

Shared by HF CPU count-only checks and HF GPU reviewer prompt encoding.
No HF/model imports, no I/O, no private text or token IDs are logged.

Stage this exact module as token_core.py beside a standalone HF worker.
The installed storyforge_dataset.token_preflight package is the source of truth.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math


def extract_input_ids(encoded, *, prompt_chars: int = 0) -> list[int]:
    """Extract true 1-D token IDs, rejecting BatchEncoding field-count bugs."""
    if isinstance(encoded, Mapping):
        if "input_ids" not in encoded:
            raise ValueError("TOKEN_IDS_INVALID")
        encoded = encoded["input_ids"]
    if hasattr(encoded, "tolist") and not isinstance(encoded, list):
        encoded = encoded.tolist()
    if isinstance(encoded, list) and len(encoded) == 1 and isinstance(encoded[0], list):
        encoded = encoded[0]
    if (not isinstance(encoded, list) or not encoded
            or any(type(token) is not int or token < 0 for token in encoded)
            or (prompt_chars >= 100 and len(encoded) < 32)):
        raise ValueError("TOKEN_IDS_INVALID")
    return encoded


def encode_chat(tokenizer, messages: list[dict], *, disable_thinking: bool = False) -> list[int]:
    """Use the model's own chat template; no artificial truncation."""
    if (not isinstance(messages, list) or not messages
            or any(not isinstance(m, dict)
                   or m.get("role") not in ("system", "user", "assistant", "tool")
                   or not isinstance(m.get("content"), str) for m in messages)):
        raise ValueError("CHAT_MESSAGES_INVALID")
    opts = {"tokenize": True, "add_generation_prompt": True}
    if disable_thinking:
        opts["enable_thinking"] = False
    try:
        encoded = tokenizer.apply_chat_template(messages, **opts)
    except TypeError as exc:
        # Preserve older Transformers compatibility without hiding unrelated errors.
        if not disable_thinking or "enable_thinking" not in str(exc):
            raise
        opts.pop("enable_thinking")
        encoded = tokenizer.apply_chat_template(messages, **opts)
    chars = sum(len(m["content"]) for m in messages)
    return extract_input_ids(encoded, prompt_chars=chars)


def describe_token_lengths(
    lengths: Sequence[int], *, max_model_len: int, reserved_output_tokens: int,
    pilot_count: int = 0,
) -> dict:
    """Summarize *actual input_ids* lengths with reserved-generation budget."""
    if (not lengths or type(max_model_len) is not int or max_model_len <= 0
            or type(reserved_output_tokens) is not int or reserved_output_tokens < 0
            or type(pilot_count) is not int or not 0 <= pilot_count <= len(lengths)
            or any(type(x) is not int or x <= 0 for x in lengths)):
        raise ValueError("TOKEN_BUDGET_INVALID")
    lengths = list(lengths)
    ordered = sorted(lengths)
    totals = [x + reserved_output_tokens for x in lengths]
    return {
        "cases_checked": len(lengths),
        "prompt_tokens_min": ordered[0],
        "prompt_tokens_median": ordered[(len(lengths) - 1) // 2],
        "prompt_tokens_p95": ordered[math.ceil(len(lengths) * 0.95) - 1],
        "prompt_tokens_max": ordered[-1],
        "max_total_tokens": max(totals),
        "over_budget_count": sum(x > max_model_len for x in totals),
        "max_model_len": max_model_len,
        "reserved_output_tokens": reserved_output_tokens,
        "pilot_cases_checked": pilot_count,
        "remaining_cases_checked": len(lengths) - pilot_count,
        "pilot_prompt_tokens_max": max(lengths[:pilot_count]) if pilot_count else None,
        "remaining_prompt_tokens_max": max(lengths[pilot_count:]) if pilot_count < len(lengths) else None,
    }


def digest_serialized_items(items: Sequence[object]) -> str:
    """Stable SHA256 for structured prompt identities; no original text returned."""
    digest = hashlib.sha256()
    for item in items:
        payload = json.dumps(item, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()

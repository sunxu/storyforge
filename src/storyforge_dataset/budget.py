from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .analyze import _encode_chat, _load_jsonl


def _load_tokenizer(model: str) -> Any:
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            'transformers is required for token budgeting; install with: pip install -e ".[analysis]"'
        ) from exc
    return AutoTokenizer.from_pretrained(
        model,
        trust_remote_code=True,
        use_fast=True,
    )


def _trim_sample(
    tokenizer: Any,
    sample: dict[str, Any],
    max_length: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    messages = [dict(message) for message in sample["messages"]]
    before = len(_encode_chat(tokenizer, messages))

    if not messages or messages[-1].get("role") != "assistant":
        raise ValueError(f'sample {sample.get("id")} does not end with assistant target')

    current_user_idx = None
    for idx in range(len(messages) - 2, -1, -1):
        if messages[idx].get("role") == "user":
            current_user_idx = idx
            break
    if current_user_idx is None:
        raise ValueError(f'sample {sample.get("id")} has no current user message')

    # Preserve all leading system messages, the current user message, and target.
    system_end = 0
    while system_end < len(messages) and messages[system_end].get("role") == "system":
        system_end += 1

    prefix = messages[:system_end]
    history = messages[system_end:current_user_idx]
    current_user = messages[current_user_idx]
    target = messages[-1]
    removed = 0

    candidate = prefix + history + [current_user, target]
    while len(_encode_chat(tokenizer, candidate)) > max_length and history:
        history.pop(0)
        removed += 1
        # Avoid starting the retained history with an assistant response detached
        # from its preceding user turn.
        while history and history[0].get("role") == "assistant":
            history.pop(0)
            removed += 1
        candidate = prefix + history + [current_user, target]

    after = len(_encode_chat(tokenizer, candidate))
    fits = after <= max_length

    result = dict(sample)
    result["messages"] = candidate
    metadata = dict(result.get("metadata") or {})
    metadata.update(
        {
            "token_budget_model": getattr(tokenizer, "name_or_path", None),
            "token_budget_max_length": max_length,
            "token_count_before_budget": before,
            "token_count_after_budget": after,
            "history_messages_removed_for_budget": removed,
            "fits_token_budget": fits,
        }
    )
    result["metadata"] = metadata

    report = {
        "id": sample.get("id"),
        "split": metadata.get("split"),
        "story_id": metadata.get("story_id"),
        "before_tokens": before,
        "after_tokens": after,
        "removed_history_messages": removed,
        "fits": fits,
    }
    return result, report


def budget_dataset(
    root: Path,
    output: Path,
    model: str,
    max_length: int,
) -> dict[str, Any]:
    if max_length < 1024:
        raise ValueError("max_length must be >= 1024")

    tokenizer = _load_tokenizer(model)
    output.mkdir(parents=True, exist_ok=True)

    sample_reports: list[dict[str, Any]] = []
    split_counts: dict[str, int] = {}

    for split in ("train", "validation", "test"):
        source = root / f"{split}.jsonl"
        rows = _load_jsonl(source)
        split_counts[split] = len(rows)
        with (output / f"{split}.jsonl").open("w", encoding="utf-8") as fh:
            for sample in rows:
                trimmed, report = _trim_sample(tokenizer, sample, max_length)
                sample_reports.append(report)
                fh.write(json.dumps(trimmed, ensure_ascii=False) + "\n")

    overflow = [report for report in sample_reports if not report["fits"]]
    changed = [report for report in sample_reports if report["removed_history_messages"] > 0]
    report = {
        "schema_version": "0.3",
        "source_dataset": str(root),
        "model": model,
        "max_length": max_length,
        "sample_count": len(sample_reports),
        "split_sample_counts": split_counts,
        "changed_sample_count": len(changed),
        "overflow_sample_count": len(overflow),
        "max_before_tokens": max((item["before_tokens"] for item in sample_reports), default=0),
        "max_after_tokens": max((item["after_tokens"] for item in sample_reports), default=0),
        "changed_samples": changed,
        "overflow_samples": overflow,
    }
    (output / "budget_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean
from typing import Any


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    weight = rank - lo
    return round(ordered[lo] * (1 - weight) + ordered[hi] * weight)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL: {path}:{line_no}: {exc}") from exc
    return rows


def load_compiled_dataset(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in ("train.jsonl", "validation.jsonl", "test.jsonl"):
        path = root / name
        if not path.exists():
            raise FileNotFoundError(path)
        rows.extend(_load_jsonl(path))
    return rows


def _encode_chat(tokenizer: Any, messages: list[dict[str, str]]) -> list[int]:
    # Render first, then tokenize explicitly. Some custom Qwen tokenizers may return
    # mapping-like objects from apply_chat_template(tokenize=True); list(mapping)
    # would count dictionary keys instead of token ids.
    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    encoded = tokenizer(rendered, add_special_tokens=False)["input_ids"]
    if hasattr(encoded, "tolist"):
        encoded = encoded.tolist()
    if encoded and isinstance(encoded[0], list):
        encoded = encoded[0]
    return list(encoded)


def _encode_text(tokenizer: Any, text: str) -> list[int]:
    encoded = tokenizer(text, add_special_tokens=False)["input_ids"]
    if hasattr(encoded, "tolist"):
        encoded = encoded.tolist()
    if encoded and isinstance(encoded[0], list):
        encoded = encoded[0]
    return list(encoded)


def analyze_dataset(root: Path, model: str) -> dict[str, Any]:
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            'transformers is required for token analysis; install with: pip install -e ".[analysis]"'
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(
        model,
        trust_remote_code=True,
        use_fast=True,
    )
    samples = load_compiled_dataset(root)

    totals: list[int] = []
    systems: list[int] = []
    histories: list[int] = []
    users: list[int] = []
    targets: list[int] = []

    per_sample: list[dict[str, Any]] = []

    for sample in samples:
        messages = sample["messages"]
        if not messages or messages[-1].get("role") != "assistant":
            raise ValueError(f'sample {sample.get("id")} does not end with assistant target')

        total_tokens = len(_encode_chat(tokenizer, messages))
        target_tokens = len(_encode_text(tokenizer, str(messages[-1].get("content") or "")))

        system_tokens = sum(
            len(_encode_text(tokenizer, str(m.get("content") or "")))
            for m in messages
            if m.get("role") == "system"
        )

        current_user_idx = None
        for i in range(len(messages) - 2, -1, -1):
            if messages[i].get("role") == "user":
                current_user_idx = i
                break
        if current_user_idx is None:
            raise ValueError(f'sample {sample.get("id")} has no current user message')

        user_tokens = len(
            _encode_text(tokenizer, str(messages[current_user_idx].get("content") or ""))
        )
        history_tokens = sum(
            len(_encode_text(tokenizer, str(m.get("content") or "")))
            for m in messages[1:current_user_idx]
        )

        totals.append(total_tokens)
        systems.append(system_tokens)
        histories.append(history_tokens)
        users.append(user_tokens)
        targets.append(target_tokens)

        per_sample.append(
            {
                "id": sample.get("id"),
                "split": (sample.get("metadata") or {}).get("split"),
                "story_id": (sample.get("metadata") or {}).get("story_id"),
                "total_tokens": total_tokens,
                "system_tokens": system_tokens,
                "history_tokens": history_tokens,
                "current_user_tokens": user_tokens,
                "target_tokens": target_tokens,
            }
        )

    def stats(values: list[int]) -> dict[str, float | int]:
        return {
            "min": min(values) if values else 0,
            "mean": round(mean(values), 2) if values else 0,
            "p50": _percentile(values, 0.50),
            "p75": _percentile(values, 0.75),
            "p90": _percentile(values, 0.90),
            "p95": _percentile(values, 0.95),
            "p99": _percentile(values, 0.99),
            "max": max(values) if values else 0,
        }

    thresholds = [4096, 8192, 16384]
    fit = {
        str(limit): {
            "count": sum(1 for value in totals if value <= limit),
            "percent": round(100 * sum(1 for value in totals if value <= limit) / len(totals), 2)
            if totals
            else 0,
            "over_count": sum(1 for value in totals if value > limit),
        }
        for limit in thresholds
    }

    if fit["4096"]["percent"] >= 95:
        recommended = 4096
    elif fit["8192"]["percent"] >= 95:
        recommended = 8192
    else:
        recommended = 16384

    return {
        "model": model,
        "sample_count": len(samples),
        "tokenizer_class": tokenizer.__class__.__name__,
        "stats": {
            "total_tokens": stats(totals),
            "system_tokens": stats(systems),
            "history_tokens": stats(histories),
            "current_user_tokens": stats(users),
            "target_tokens": stats(targets),
        },
        "fit_by_max_length": fit,
        "recommended_max_length": recommended,
        "recommendation_reason": (
            f"smallest tested max_length covering at least 95% of samples: {recommended}"
        ),
        "largest_samples": sorted(
            per_sample,
            key=lambda item: item["total_tokens"],
            reverse=True,
        )[:10],
    }


def write_token_report(report: dict[str, Any], output: Path) -> None:
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

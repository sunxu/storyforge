"""Measure final Gold-only response token lengths for StoryForge Dataset v0.3.

No 27B model weights or GPU required. Never prints story text.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def percentile(values: list[int], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty values")
    position = (len(ordered) - 1) * pct / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def gold_contents(path: Path) -> list[str]:
    answers = []
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row.get("messages")
            if not isinstance(messages, list) or len(messages) < 2:
                raise ValueError(f"{path}:{index}: invalid messages")
            if messages[-2].get("role") != "user" or messages[-1].get("role") != "assistant":
                raise ValueError(f"{path}:{index}: expected user/Gold assistant tail")
            content = messages[-1].get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"{path}:{index}: Gold content must be nonempty text")
            answers.append(content)
    return answers


def calculate(splits: dict[str, list[str]], tokenizer) -> dict:
    report = {"split_counts": {}, "by_split": {}}
    all_counts = []
    for name, answers in splits.items():
        counts = [len(tokenizer.encode(a, add_special_tokens=False)) for a in answers]
        report["split_counts"][name] = len(counts)
        report["by_split"][name] = summarize(counts)
        all_counts.extend(counts)
    report["all"] = summarize(all_counts)
    report["metric"] = "final Gold assistant content tokens, without prompt or special tokens"
    return report


def summarize(counts: list[int]) -> dict:
    if not counts:
        raise ValueError("empty split")
    result = {"count": len(counts), "mean": round(sum(counts) / len(counts), 2),
              "min": min(counts), "max": max(counts)}
    for pct in (50, 75, 90, 95, 99):
        result[f"p{pct}"] = round(percentile(counts, pct), 2)
    for limit in (128, 256, 512, 768, 1024, 1536, 2048):
        over = sum(n > limit for n in counts)
        result[f"over_{limit}"] = over
        result[f"over_{limit}_pct"] = round(100 * over / len(counts), 2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/compiled/v0.3"))
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B")
    parser.add_argument("--output", type=Path, default=Path("/tmp/storyforge-gold-token-stats.json"))
    args = parser.parse_args()
    from transformers import AutoTokenizer

    splits = {name: gold_contents(args.data / f"{name}.jsonl")
              for name in ("train", "validation", "test")}
    if [len(splits[name]) for name in ("train", "validation", "test")] != [65, 15, 20]:
        raise ValueError("unexpected Dataset v0.3 split sizes; expected 65/15/20")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    result = calculate(splits, tokenizer)
    result["model"] = args.model
    result["dataset"] = "v0.3"
    if args.output.exists():
        raise FileExistsError(f"refusing overwrite: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""CPU-only truncation audit on already generated ms-swift results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def audit(base: Path, adapter: Path, tokenizer, cap: int) -> dict:
    report = {"cap": cap, "arms": {}}
    for name, path in (("base", base), ("adapter", adapter)):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        counts = []
        for index, row in enumerate(rows):
            answer = row.get("response")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError(f"{name} row {index}: empty response")
            counts.append(len(tokenizer.encode(answer, add_special_tokens=False)))
        report["arms"][name] = {
            "samples": len(counts),
            "min_tokens": min(counts),
            "max_tokens": max(counts),
            "near_cap_ge_120": sum(n >= 120 for n in counts),
            "at_cap_ge_128": sum(n >= cap for n in counts),
            "token_counts": counts,
        }
    if report["arms"]["base"]["samples"] != report["arms"]["adapter"]["samples"]:
        raise ValueError("base and adapter sample counts differ")
    report["caveat"] = ("Retokenized response lengths are approximate: template handling, "
                        "special tokens and generated-token counting may differ.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B")
    parser.add_argument("--cap", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    report = audit(args.base, args.adapter, tokenizer, args.cap)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

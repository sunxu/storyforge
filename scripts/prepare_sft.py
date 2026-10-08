"""Validate and convert StoryForge dataset for last-assistant-only ms-swift SFT."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def convert(source: Path, dest: Path) -> int:
    count = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with source.open(encoding="utf-8") as inp, dest.open("w", encoding="utf-8") as out:
        for line_no, line in enumerate(inp, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row["messages"]
            if len(messages) < 3 or messages[-1]["role"] != "assistant" or messages[-2]["role"] != "user":
                raise ValueError(f"{source}:{line_no}: invalid user/assistant target suffix")
            clean = []
            for i, message in enumerate(messages):
                msg = {"role": message["role"], "content": message["content"]}
                if msg["role"] == "assistant":
                    msg["loss"] = i == len(messages) - 1
                clean.append(msg)
            out.write(json.dumps({"messages": clean}, ensure_ascii=False) + "\n")
            count += 1
    return count

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps({"samples": convert(args.source, args.output), "output": str(args.output)}))

if __name__ == "__main__":
    main()

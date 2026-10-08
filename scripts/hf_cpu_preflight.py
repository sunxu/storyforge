#!/usr/bin/env python3
"""Fail-fast CPU preflight for StoryForge HF Jobs (no GPU required)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

def check_data(path: Path) -> dict:
    count = 0
    historical = 0
    targets = 0
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row["messages"]
            if not messages or messages[-1]["role"] != "assistant" or messages[-1].get("loss") is not True:
                raise ValueError(f"{path}:{number}: missing final supervised assistant")
            if messages[-2]["role"] != "user":
                raise ValueError(f"{path}:{number}: target not preceded by user")
            for msg in messages[:-1]:
                if msg["role"] == "assistant":
                    historical += 1
                    if msg.get("loss") is not False:
                        raise ValueError(f"{path}:{number}: historical assistant is supervised")
            targets += 1
            count += 1
    if not count:
        raise ValueError(f"{path}: empty dataset")
    return {"rows": count, "historical_assistants_masked": historical, "targets": targets}

def check_config(path: Path) -> dict:
    import yaml
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key, expected in {
        "max_length": 16384, "max_steps": 3,
        "quant_bits": 4, "quant_method": "bnb"
    }.items():
        if config.get(key) != expected:
            raise ValueError(f"config {key}: expected {expected}, got {config.get(key)}")
    return {"config": str(path), "max_length": config["max_length"]}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--check-cli", action="store_true")
    args = p.parse_args()
    report = {
        "train": check_data(args.data / "train.jsonl"),
        "validation": check_data(args.data / "validation.jsonl"),
        "settings": check_config(args.config),
    }
    if args.check_cli:
        result = subprocess.run(
            ["swift", "sft", "--help"], capture_output=True, text=True, check=True
        )
        text = result.stdout + result.stderr
        for key in ("quant_method", "max_length", "lora_rank"):
            if key not in text:
                raise ValueError(f"swift CLI help missing {key}")
        report["swift_cli"] = "help available"
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

"""CPU-only evaluation CLI safety preflight; does not load the 27B model."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.hf_evaluation_runner import infer_command


def check_help(help_text: str) -> None:
    required = ("--model", "--use_hf", "--val_dataset", "--infer_backend",
                "--torch_dtype", "--quant_method", "--quant_bits",
                "--bnb_4bit_compute_dtype", "--max_new_tokens",
                "--seed", "--data_seed", "--val_dataset_shuffle",
                "--do_sample", "--adapters", "--result_path")
    missing = [flag for flag in required
               if not re.search(r"(?<![\w-])" + re.escape(flag) + r"(?![\w-])", help_text)]
    if missing:
        raise ValueError(f"EVAL_CLI_FLAGS_MISSING: {missing}")


def main() -> None:
    base = infer_command(Path("/tmp/base.jsonl"), adapter=False)
    tuned = infer_command(__import__("pathlib").Path("/tmp/adapter.jsonl"), adapter=True)
    for cmd in (base, tuned):
        if "--val_dataset_sample" in cmd:
            raise ValueError("val_dataset_sample override must be absent")
        if cmd[cmd.index("--do_sample") + 1] != "false":
            raise ValueError("do_sample must be false")
    result = subprocess.run(["swift", "infer", "--help"], check=True,
                            capture_output=True, text=True)
    check_help(result.stdout + result.stderr)
    print("STORYFORGE_EVAL_CLI_PREFLIGHT_PASS")
    print("NOTE: help validation does not prove runtime argument parsing or model inference")


if __name__ == "__main__":
    main()

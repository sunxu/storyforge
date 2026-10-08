"""CPU-only check for ms-swift inference CLI flags used by StoryForge."""
from __future__ import annotations

import argparse
import subprocess

REQUIRED = (
    "--model", "--adapters", "--val_dataset", "--val_dataset_sample",
    "--infer_backend", "--torch_dtype", "--quant_method", "--quant_bits",
    "--bnb_4bit_compute_dtype", "--result_path", "--max_new_tokens",
)


def check_help(text: str) -> list[str]:
    return [flag for flag in REQUIRED if flag not in text]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    result = subprocess.run(["swift", "infer", "--help"], capture_output=True, text=True, check=True)
    missing = check_help(result.stdout + result.stderr)
    if missing:
        raise RuntimeError(f"unsupported inference flags: {missing}")
    print("STORYFORGE_INFER_CLI_PREFLIGHT_PASS")


if __name__ == "__main__":
    main()

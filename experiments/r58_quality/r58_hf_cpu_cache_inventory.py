#!/usr/bin/env python3
"""Read-only inventory of existing R58 A/B private HF CPU token preflight receipts.

Checks local identity via the existing R58 verifier. Never tokenizes, submits
an HF Job, edits the private stage or declares HF provenance / runtime parity.
The public JSON contains counts and slot labels only; no private hashes/paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import SimpleNamespace

from r58_hf_cpu_literary_token_preflight import verify_reuse
from r58_hf_gpu_literary_reviewer import MODELS, JUDGE_SYSTEM, JUDGE_USER

RECEIPT_NAME = "r58_cpu_preflight_all13_safe.json"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
VERSION = re.compile(r"\d+\.\d+\.\d+\Z")
SCHEMA = "r58_hf_cpu_cache_inventory_safe_v1"


def private_directory(path: Path) -> bool:
    return (path.is_absolute() and not path.is_symlink() and path.is_dir()
            and stat.S_IMODE(path.stat().st_mode) == 0o700)


def private_file(path: Path, max_bytes: int) -> bool:
    return (not path.is_symlink() and path.is_file()
            and stat.S_IMODE(path.stat().st_mode) == 0o600
            and path.stat().st_nlink == 1
            and 0 < path.stat().st_size <= max_bytes)


def inspect_slot(stage: Path, slot: str) -> str:
    """MISSING / LOCAL_MATCH_ORIGIN_UNVERIFIED / HOLD. No private data returned."""
    incoming = stage / f"input_{slot}"
    outgoing = stage / f"output_{slot}"
    if not private_directory(incoming) or not private_directory(outgoing):
        return "HOLD"
    source = incoming / "source.private.jsonl"
    if not private_file(source, 20 * 1024 * 1024):
        return "HOLD"
    receipt = outgoing / RECEIPT_NAME
    if not receipt.exists() and not receipt.is_symlink():
        return "MISSING"
    if not private_file(receipt, 32 * 1024):
        return "HOLD"
    try:
        record = json.loads(receipt.read_bytes())
        if not isinstance(record, dict):
            return "HOLD"
        model = record.get("model")
        revision = record.get("model_revision")
        runtime_version = record.get("transformers_version")
        max_length = record.get("max_model_len")
        reserve = record.get("reserved_output_tokens")
        template_sha = record.get("chat_template_sha256")
        prompt_sha = hashlib.sha256(
            (JUDGE_SYSTEM + JUDGE_USER).encode("utf-8")
        ).hexdigest()
        if (model != MODELS[slot]
                or not isinstance(revision, str) or not SHA40.fullmatch(revision)
                or not isinstance(runtime_version, str)
                or not VERSION.fullmatch(runtime_version)
                or type(max_length) is not int or not 4096 <= max_length <= 40960
                or type(reserve) is not int or not 1200 <= reserve <= 4096
                or not isinstance(record.get("tokenizer_class"), str)
                or not record["tokenizer_class"]
                or not isinstance(template_sha, str)
                or not SHA64.fullmatch(template_sha)
                or record.get("reviewer_prompt_template_sha256") != prompt_sha
                or record.get("inference_performed") is not False
                or record.get("model_weights_loaded") is not False
                or record.get("paid_gpu_submitted") is not False
                or record.get("quality_v1_admitted") != 0):
            return "HOLD"
        args = SimpleNamespace(
            slot=slot, model=model, revision=revision,
            transformers_version=runtime_version,
            max_model_len=max_length, max_output_tokens=reserve,
            input=source, output_dir=outgoing,
        )
        verify_reuse(args)
        # The receipt can match local identities without proving it came
        # from a trusted HF CPU Job or matches the future GPU runtime.
        return "LOCAL_MATCH_ORIGIN_UNVERIFIED"
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return "HOLD"


def inspect(stage: Path) -> dict:
    if not private_directory(stage):
        states = {"A": "HOLD", "B": "HOLD"}
    else:
        states = {slot: inspect_slot(stage, slot) for slot in ("A", "B")}
    counts = {key: sum(v == key for v in states.values())
              for key in ("MISSING", "LOCAL_MATCH_ORIGIN_UNVERIFIED", "HOLD")}
    return {
        "schema": SCHEMA,
        "status": ("R58_CPU_CACHE_INVENTORY_HOLD" if counts["HOLD"]
                   else "R58_CPU_CACHE_INVENTORY_LOCAL_ONLY__NO_JOB"),
        "slots": states,
        "counts": counts,
        "hf_origin_proven": False,
        "gpu_runtime_equivalence_proven": False,
        "tokenizer_loaded": False,
        "hf_job_submitted": False,
        "private_text_emitted": False,
        "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", required=True, type=Path)
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    result = inspect(args.stage_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 42 if result["status"] == "R58_CPU_CACHE_INVENTORY_HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())

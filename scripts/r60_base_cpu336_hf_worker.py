"""HF CPU thin adapter for Base-start 336 HELD technical cases.

Uses shared Runtime, Common2 actual ms-swift/R18 label audit, no weights.
Writes only a SAFE aggregate receipt with create-only OutputManager.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"),
                str(ROOT / "experiments/r58_quality")]

import r60_base_cpu336_hf_stage as stage_tools
import r60_common2_sft_cpu_template_audit as common

from storyforge_dataset.hf_runtime import (
    InputManager,
    OutputManager,
    ResourceGuard,
    RuntimeContext,
)

SCHEMA = "storyforge_r60_base_cpu336_hf_receipt_safe_v1"
RECEIPT = "R60_BASE_CPU336_HF_SAFE_RECEIPT.json"
MODEL = "Qwen/Qwen3.8-27B"
ALLOW = [
    "config.json", "tokenizer.json", "tokenizer_config.json",
    "chat_template.jinja", "vocab.json", "merges.txt",
    "preprocessor_config.json", "video_preprocessor_config.json",
    "generation_config.json",
]


def summary(values: list[int]) -> dict:
    if len(values) != 336 or any(type(x) is not int or x <= 0 for x in values):
        raise ValueError("COUNTS_HOLD")
    ordered = sorted(values)
    return {
        "min": ordered[0], "median": ordered[168],
        "p95": ordered[int(335 * 0.95)], "max": ordered[-1],
    }


def base(key: str) -> dict:
    return {
        "schema": SCHEMA, "run_key": key,
        "status": "BASE_CPU336_HF_AUDIT_HOLD",
        "stage": "START", "model": MODEL,
        "revision": common.PIN,
        "source_cases": 336, "audited_cases": 0,
        "input_sha_verified": False,
        "tokenizer_verified": False,
        "actual_collator_verified": False,
        "last_assistant_label_mask_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "world_component_isolation_verified": False,
        "training_dataset_created": False, "train_admitted": 0,
        "model_weights_loaded": False, "model_inference_calls": 0,
        "gpu_started": False, "private_values_emitted": False,
    }


def inspect_technical_rows(raw: bytes) -> list[dict]:
    if len(raw) > 4_000_000 or not raw:
        raise ValueError("DATA_SIZE_HOLD")
    lines = raw.splitlines()
    if len(lines) != 336:
        raise ValueError("DATA_COUNT_HOLD")
    result = []
    for line in lines:
        row = json.loads(line)
        if type(row) is not dict or set(row) != {"messages"}:
            raise ValueError("ROW_SCHEMA_HOLD")
        msgs = row["messages"]
        if (type(msgs) is not list or len(msgs) != 4 or
                [m.get("role") for m in msgs] !=
                ["user", "assistant", "user", "assistant"] or
                any(type(m) is not dict or set(m) != {"role", "content"}
                    or type(m["content"]) is not str or not m["content"]
                    for m in msgs)):
            raise ValueError("MESSAGES_HOLD")
        result.append(row)
    return result


def run(stage: Path, key: str) -> dict:
    out = base(key)
    try:
        out["stage"] = "CPU_GUARD"
        ctx = RuntimeContext.detect(profile="cpu")
        if ctx.operating_system != "linux":
            raise ValueError("LINUX_CPU_REQUIRED")
        if ResourceGuard.check_cpu_only().status != "PASS":
            raise ValueError("ACCELERATOR_HOLD")
        out["stage"] = "STAGE_VERIFY"
        stage_tools.verify(stage, key)
        raw = InputManager.open_verified(
            stage / "private" / stage_tools.DATA,
            max_bytes=4_000_000).read_bytes()
        manifest = InputManager.validate_json(
            InputManager.open_verified(
                stage / "private" / stage_tools.MANIFEST,
                max_bytes=32768).read_bytes())
        if (manifest.get("data_sha256") != hashlib.sha256(raw).hexdigest()
                or manifest.get("examples") != 336
                or manifest.get("train_admitted") != 0):
            raise ValueError("SOURCE_SHA_HOLD")
        rows = inspect_technical_rows(raw)
        out["input_sha_verified"] = True
        out["stage"] = "DEPENDENCIES"
        from importlib.metadata import version
        for name, expected in {
            "ms-swift": "4.5.3",
            "transformers": "5.16.1",
            "tokenizers": "0.23.3",
            "huggingface_hub": "1.33.0",
            "jinja2": "3.1.6",
        }.items():
            if version(name) != expected:
                raise ValueError("PIN_HOLD")
        from huggingface_hub import snapshot_download
        from swift import get_processor, get_template
        from transformers import AutoTokenizer

        with tempfile.TemporaryDirectory(prefix="r60-cpu336-") as scratch:
            snapshot = Path(scratch) / common.PIN
            snapshot.mkdir(mode=0o700)
            out["stage"] = "TOKENIZER_ONLY_DOWNLOAD"
            snapshot_download(
                repo_id=MODEL, revision=common.PIN, local_dir=str(snapshot),
                allow_patterns=ALLOW, max_workers=4)
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            out["stage"] = "TEMPLATE_INIT"
            tok = AutoTokenizer.from_pretrained(
                str(snapshot), local_files_only=True,
                trust_remote_code=False, use_fast=True)
            processor = get_processor(str(snapshot), model_type="qwen3_5")
            template = get_template(
                processor, template_type="qwen3_8",
                loss_scale="last_round", max_length=common.CEILING,
                add_non_thinking_prefix=False)
            template.set_mode("train")
            common.bind_text_only_rope(template, snapshot)
            out["stage"] = "ACTUAL_336_COLLATOR"
            # Reuses Common2 and R18 strict label audit. Raw per-case arrays
            # never escape this process; only four aggregate statistics do.
            checked = common.inspect_rows(rows, tok, template)
            if checked["cases"] != 336 or not checked["collator_verified"]:
                raise ValueError("COLLATOR_RESULT_HOLD")
            out.update(
                status="BASE_CPU336_ACTUAL_COLLATOR_PASS__ALL_HELD",
                stage="AUDIT_COMPLETE", audited_cases=336,
                tokenizer_verified=True, actual_collator_verified=True,
                last_assistant_label_mask_verified=True,
                tokenizer_tokens=summary(checked["tokenizer_input_token_counts"]),
                collator_tokens=summary(checked["real_collator_token_counts"]),
                supervised_tokens=summary(checked["supervised_token_counts"]),
            )
    except Exception:  # noqa: BLE001 - no raw private content or exceptions
        out["reason_code"] = out["stage"] + "_HOLD"
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", type=Path, default=Path("/input/base336"))
    p.add_argument("--output", type=Path, default=Path("/output"))
    p.add_argument("--run-key", required=True)
    a = p.parse_args()
    result = run(a.stage, a.run_key)
    try:
        OutputManager.probe(a.output)
        OutputManager.write_safe(a.output / RECEIPT, result)
    except Exception:  # noqa: BLE001 - do not expose output path
        print("BASE_CPU336_OUTPUT_PUBLICATION_HOLD")
        return 42
    print(json.dumps(result, sort_keys=True))
    return 0 if result["actual_collator_verified"] else 42


if __name__ == "__main__":
    sys.exit(main())

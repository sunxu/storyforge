"""HF CPU-only audit of frozen 293/43 exploratory release, no model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"),
                str(ROOT / "experiments/r58_quality")]

import r60_base336_final_cpu_stage as stage_tool
import r60_common2_sft_cpu_template_audit as common

from storyforge_dataset.hf_runtime import (
    InputManager, OutputManager, ResourceGuard, RuntimeContext,
)

SCHEMA = "storyforge_r60_base336_final_cpu_receipt_safe_v1"
RECEIPT = "R60_BASE336_FINAL_CPU_SAFE_RECEIPT.json"
ALLOW = [
    "config.json", "tokenizer.json", "tokenizer_config.json",
    "chat_template.jinja", "vocab.json", "merges.txt",
    "preprocessor_config.json", "video_preprocessor_config.json",
    "generation_config.json",
]


def _summary(values: list[int], expected: int) -> dict:
    if len(values) != expected or any(type(v) is not int or v <= 0 for v in values):
        raise ValueError("TOKEN_COUNTS_HOLD")
    ordered = sorted(values)
    return {"min": ordered[0], "median": ordered[len(values) // 2],
            "p95": ordered[int((len(values) - 1) * 0.95)],
            "max": ordered[-1]}


def load_release(stage: Path) -> tuple[dict, dict]:
    metadata = InputManager.validate_json(InputManager.open_verified(
        stage / "private" / "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json",
        max_bytes=200_000).read_bytes())
    if (metadata.get("status") != "EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED"
            or metadata.get("case_pool") != 336 or metadata.get("train_admitted") != 0
            or metadata.get("statistics", {}).get("rows") !=
            {"train": 293, "validation": 43}):
        raise ValueError("RELEASE_MANIFEST_HOLD")
    all_rows = {}
    for part, expected in (("train", 293), ("validation", 43)):
        raw = InputManager.open_verified(
            stage / "private" / f"{part}.jsonl",
            max_bytes=4_000_000,
            expected_sha256=metadata["data_sha256"][part]).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines()]
        if len(rows) != expected:
            raise ValueError("RELEASE_ROW_COUNT_HOLD")
        for row in rows:
            if (type(row) is not dict or set(row) != {"messages"}
                    or type(row["messages"]) is not list
                    or len(row["messages"]) != 4
                    or [m.get("role") for m in row["messages"]]
                    != ["user", "assistant", "user", "assistant"]):
                raise ValueError("MESSAGE_SHAPE_HOLD")
        all_rows[part] = rows
    return all_rows, metadata


def run(stage: Path, key: str) -> dict:
    safe = {
        "schema": SCHEMA, "run_key": key,
        "status": "BASE336_FINAL_CPU_COLLATOR_HOLD",
        "phase": "CPU_GUARD", "model": "Qwen/Qwen3.8-27B",
        "revision": common.PIN, "train_rows": 293, "validation_rows": 43,
        "actual_collator_verified": False,
        "last_assistant_label_mask_verified": False,
        "train_admitted": 0, "model_weights_loaded": False,
        "gpu_started": False, "private_values_emitted": False,
    }
    try:
        ctx = RuntimeContext.detect(profile="cpu")
        if ctx.operating_system != "linux" or (
                ResourceGuard.check_cpu_only().status != "PASS"):
            raise ValueError("CPU_RESOURCE_HOLD")
        safe["phase"] = "STAGE_VERIFY"
        stage_tool.verify(stage, key)
        rows, manifest = load_release(stage)
        safe["data_sha256_verified"] = True
        safe["phase"] = "DEPENDENCIES"
        for name, expected in {
            "ms-swift": "4.5.3", "transformers": "5.16.1",
            "tokenizers": "0.23.3", "huggingface_hub": "1.33.0",
            "jinja2": "3.1.6",
        }.items():
            if version(name) != expected:
                raise ValueError("DEPENDENCY_PIN_HOLD")
        from huggingface_hub import snapshot_download
        from swift import get_processor, get_template
        from transformers import AutoTokenizer

        with tempfile.TemporaryDirectory(prefix="r60-finalcpu-") as tmp:
            snapshot = Path(tmp) / common.PIN
            snapshot.mkdir(mode=0o700)
            safe["phase"] = "TOKENIZER_ONLY_DOWNLOAD"
            snapshot_download(
                repo_id="Qwen/Qwen3.8-27B", revision=common.PIN,
                local_dir=str(snapshot), allow_patterns=ALLOW, max_workers=4)
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            safe["phase"] = "COLLATOR_INIT"
            tokenizer = AutoTokenizer.from_pretrained(
                str(snapshot), local_files_only=True,
                trust_remote_code=False, use_fast=True)
            processor = get_processor(str(snapshot), model_type="qwen3_5")
            template = get_template(
                processor, template_type="qwen3_8", loss_scale="last_round",
                max_length=common.CEILING, add_non_thinking_prefix=False)
            template.set_mode("train")
            common.bind_text_only_rope(template, snapshot)
            summaries = {}
            for part, expected in (("train", 293), ("validation", 43)):
                safe["phase"] = "COLLATOR_" + part.upper()
                checked = common.inspect_rows(rows[part], tokenizer, template)
                if checked.get("cases") != expected or (
                        checked.get("collator_verified") is not True):
                    raise ValueError("COLLATOR_RESULT_HOLD")
                summaries[part] = {
                    "collator_tokens": _summary(
                        checked["real_collator_token_counts"], expected),
                    "supervised_tokens": _summary(
                        checked["supervised_token_counts"], expected),
                }
            safe.update(
                status="BASE336_FINAL_CPU_ACTUAL_COLLATOR_PASS__GPU_HOLD",
                phase="AUDIT_COMPLETE", actual_collator_verified=True,
                last_assistant_label_mask_verified=True,
                data_sha256=manifest["data_sha256"], split_summaries=summaries)
    except Exception:  # noqa: BLE001 - never expose private content
        safe["reason_code"] = safe["phase"] + "_HOLD"
    return safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", type=Path, default=Path("/input/common2"))
    p.add_argument("--output", type=Path, default=Path("/output"))
    p.add_argument("--run-key", required=True)
    a = p.parse_args()
    result = run(a.stage, a.run_key)
    try:
        OutputManager.probe(a.output)
        OutputManager.write_safe(a.output / RECEIPT, result)
    except Exception:  # noqa: BLE001
        print("BASE336_FINAL_CPU_OUTPUT_HOLD")
        return 42
    print(json.dumps(result, sort_keys=True))
    return 0 if result["actual_collator_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())

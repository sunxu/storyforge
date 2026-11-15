"""HF CPU3 synthetic constructed System smoke: SAFE receipt only.

Reuse Common2 ms-swift/R18 actual collator and pinned model config/tokenizer.
Never read any private story, model weights, database, or GPU device.
"""
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

import r60_base_constructed_hf_cpu_stage as stage_tool
import r60_base_constructed_sft_cpu_smoke as smoke
import r60_common2_sft_cpu_template_audit as common

from storyforge_dataset.hf_runtime import OutputManager, ResourceGuard, RuntimeContext

SCHEMA = "storyforge_r60_base_constructed_hf_cpu_safe_v1"
RECEIPT = "R60_BASE_CONSTRUCTED_HF_CPU_SAFE_RECEIPT.json"
ALLOW = [
    "config.json", "tokenizer.json", "tokenizer_config.json",
    "chat_template.jinja", "vocab.json", "merges.txt",
    "preprocessor_config.json", "video_preprocessor_config.json",
    "generation_config.json",
]


def run(stage: Path, key: str) -> dict:
    result = {
        "schema": SCHEMA, "run_key": key,
        "status": "BASE_CONSTRUCTED_HF_CPU_HOLD",
        "phase": "CPU_GUARD", "synthetic_cases": 3,
        "model": "Qwen/Qwen3.8-27B", "revision": common.PIN,
        "actual_collator_verified": False,
        "train_admitted": 0, "model_weights_loaded": False,
        "gpu_started": False, "model_requests": 0,
        "database_accessed": False, "private_values_emitted": False,
    }
    try:
        ctx = RuntimeContext.detect(profile="cpu")
        if ctx.operating_system != "linux":
            raise ValueError("LINUX_REQUIRED")
        if ResourceGuard.check_cpu_only().status != "PASS":
            raise ValueError("ACCELERATOR_HOLD")
        result["phase"] = "STAGE_VERIFY"
        stage_tool.verify(stage, key)
        result["phase"] = "DEPENDENCIES"
        for name, required in {
            "ms-swift": "4.5.3",
            "transformers": "5.16.1",
            "tokenizers": "0.23.3",
            "huggingface_hub": "1.33.0",
            "jinja2": "3.1.6",
        }.items():
            if version(name) != required:
                raise ValueError("DEPENDENCY_PIN_HOLD")
        from huggingface_hub import snapshot_download

        with tempfile.TemporaryDirectory(prefix="r60-synthetic-") as temp:
            snapshot = Path(temp) / common.PIN
            snapshot.mkdir(mode=0o700)
            result["phase"] = "TOKENIZER_ONLY_DOWNLOAD"
            snapshot_download(
                repo_id="Qwen/Qwen3.8-27B", revision=common.PIN,
                local_dir=str(snapshot), allow_patterns=ALLOW, max_workers=4,
            )
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            result["phase"] = "ACTUAL_COLLATOR"
            checked = smoke.run(argparse.Namespace(
                snapshot=snapshot, stage="both", _safe_phase="SNAPSHOT_CHECK",
            ))
            if (checked["status"] !=
                    "BASE_CONSTRUCTED_V1_ACTUAL_COLLATOR_SYNTHETIC_PASS__TRAIN_HOLD"
                    or checked["synthetic_cases"] != 3
                    or checked["actual_collator_verified"] is not True
                    or checked["train_admitted"] != 0):
                raise ValueError("COLLATOR_CONTRACT_HOLD")
            result.update(checked)
            result.update(
                schema=SCHEMA, run_key=key,
                status="BASE_CONSTRUCTED_HF_CPU3_ACTUAL_COLLATOR_PASS__TRAIN_HOLD",
                phase="AUDIT_COMPLETE",
                model="Qwen/Qwen3.8-27B", revision=common.PIN,
                source_sha256=hashlib.sha256(
                    Path(stage / "SHA256_MANIFEST_PRIVATE.json").read_bytes()
                ).hexdigest(),
            )
    except Exception:  # noqa: BLE001 - no source/exception leaks
        result["reason_code"] = result["phase"] + "_HOLD"
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", type=Path, default=Path("/input/common2"))
    p.add_argument("--output", type=Path, default=Path("/output"))
    p.add_argument("--run-key", required=True)
    args = p.parse_args()
    out = run(args.stage, args.run_key)
    try:
        OutputManager.probe(args.output)
        OutputManager.write_safe(args.output / RECEIPT, out)
    except Exception:  # noqa: BLE001
        print("BASE_CONSTRUCTED_CPU3_OUTPUT_HOLD")
        return 42
    print(json.dumps(out, sort_keys=True))
    return 0 if out["actual_collator_verified"] else 42


if __name__ == "__main__":
    sys.exit(main())

"""HF CPU quality-pipeline adapter for Common2 proposed System wrapper.

Pure CPU + pinned tokenizer/processor, no model weights or training. The only
persistent output is a create-only SAFE receipt via shared OutputManager.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "src"), str(ROOT / "scripts"),
    str(ROOT / "experiments" / "r58_quality"),
]
from storyforge_dataset.hf_runtime import InputManager, OutputManager, ResourceGuard
import r60_common2_wrapped_hf_stage as stage_tools
import r60_common2_wrapped_system_cpu_audit as audit
import r60_common2_generic_system_wrapper_preview_cpu as wrapper
import r60_real1000_common2_sft_experimental_cpu as sft

SCHEMA = "storyforge_r60_common2_wrapped_hf_cpu_receipt_v1"
RECEIPT_NAME = "R60_COMMON2_WRAPPED_CPU_SAFE_RECEIPT.json"
MODEL_REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
MODEL = "Qwen/Qwen3.8-27B"
ALLOW_PATTERNS = [
    "config.json", "tokenizer.json", "tokenizer_config.json",
    "chat_template.jinja", "vocab.json", "merges.txt",
    "preprocessor_config.json", "video_preprocessor_config.json",
    "generation_config.json",
]


def base_report(key: str) -> dict:
    return {
        "schema": SCHEMA, "run_key": key,
        "status": "WRAPPED_CPU_AUDIT_HOLD", "reason_code": "UNVERIFIED",
        "stage": "START", "model": MODEL, "model_revision": MODEL_REVISION,
        "system_origin": "R27_R52_FROZEN_SYNTHETIC_NOT_HISTORICAL_SENT",
        "system_text_pin_verified": False, "stage_sha_verified": False,
        "original_input_sha_verified": False,
        "source_examples": 0, "wrapped_examples": 0,
        "tokenizer_verified": False, "actual_swift_collator_verified": False,
        "last_assistant_label_mask_verified": False,
        "deployment_template_compatibility_verified": False,
        "semantic_world_isolation_verified": False,
        "r60_input_design_approved": False, "train_admitted": 0,
        "quality_v1_admitted": 0, "model_weights_loaded": False,
        "model_inference_calls": 0, "gpu_started": False,
        "hf_jobs_submitted": 0, "private_values_emitted": False,
        "files_written": 0,
    }


def run(stage: Path, output: Path, key: str) -> dict:
    out = base_report(key)
    try:
        if not stage_tools.RUN_RE.fullmatch(key):
            raise ValueError("KEY_HOLD")
        out["stage"] = "CPU_RESOURCE_GUARD"
        resource = ResourceGuard.check_cpu_only()
        if resource.status != "PASS":
            raise ValueError("CPU_RESOURCE_HOLD")
        out["stage"] = "STAGE_VERIFY"
        verified = stage_tools.verify(stage, key)
        if verified["status"] != "WRAPPED_CPU_STAGE_VERIFIED__NO_JOB":
            raise ValueError("STAGE_VERIFY_HOLD")
        out["stage_sha_verified"] = True
        if hashlib.sha256(wrapper.PINNED_R27_R52_SYSTEM.encode()).hexdigest() != wrapper.SYSTEM_SHA256:
            raise ValueError("SYSTEM_SHA_HOLD")
        out["system_text_pin_verified"] = True
        out["stage"] = "MODEL_FILES_ONLY"
        # Hub may be accessed for small tokenizer/config/processor assets only.
        # No *.safetensors/*.bin/model weights are requested or loaded.
        from huggingface_hub import snapshot_download
        from importlib.metadata import version
        required = {
            "ms-swift": "4.5.3", "transformers": "5.16.1",
            "tokenizers": "0.23.3", "huggingface_hub": "1.33.0",
            "jinja2": "3.1.6",
        }
        if any(version(pkg) != v for pkg, v in required.items()):
            raise ValueError("DEPENDENCY_VERSION_HOLD")
        with tempfile.TemporaryDirectory(prefix="r60-wrapcpu-") as temp:
            scratch = Path(temp)
            private = scratch / "private"
            private.mkdir(mode=0o700)
            for name in (sft.DATA_NAME, sft.MANIFEST_NAME):
                raw = InputManager.open_verified(
                    stage / "private" / name, max_bytes=8_000_000
                ).read_bytes()
                p = private / name
                p.write_bytes(raw)
                p.chmod(0o600)
            snapshot = scratch / MODEL_REVISION
            snapshot.mkdir(mode=0o700)
            snapshot_download(
                repo_id=MODEL, revision=MODEL_REVISION,
                local_dir=str(snapshot), allow_patterns=ALLOW_PATTERNS,
                max_workers=4,
            )
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            out["stage"] = "WRAPPED_ACTUAL_COLLATOR"
            verified_input = audit.check(private, snapshot)
            if (verified_input["status"] !=
                    "COMMON2_WRAPPED_SYSTEM_ACTUAL_CPU_COLLATOR_PASS__TRAIN_HOLD"
                    or verified_input["train_admitted"] != 0
                    or verified_input["actual_swift_collator_verified"] is not True
                    or verified_input["last_assistant_label_mask_verified"] is not True):
                raise ValueError("BUSINESS_AUDIT_HOLD")
            out.update(
                status="R60_COMMON2_WRAPPED_HF_CPU_COLLATOR_PASS__TRAIN_HOLD",
                reason_code="WRAPPED_ACTUAL_SWIFT_ONLY",
                stage="AUDIT_COMPLETE",
                source_examples=2, wrapped_examples=2,
                original_input_sha_verified=True,
                tokenizer_verified=True, actual_swift_collator_verified=True,
                last_assistant_label_mask_verified=True,
                tokenizer_token_counts=verified_input["tokenizer_token_counts"],
                real_collator_token_counts=verified_input["real_collator_token_counts"],
                supervised_token_counts=verified_input["supervised_token_counts"],
            )
    except Exception:
        out["reason_code"] = out["stage"] + "_HOLD"
    # A dedicated RW output mounted outside the RO input is mandatory.
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=Path, default=Path("/input/common2"))
    p.add_argument("--output", type=Path, default=Path("/output"))
    p.add_argument("--run-key", required=True)
    a = p.parse_args()
    result = run(a.stage, a.output, a.run_key)
    try:
        OutputManager.probe(a.output)
        # Persist even failures as SAFE to prevent expensive opaque retries.
        OutputManager.write_safe(a.output / RECEIPT_NAME, result)
    except Exception:
        print("R60_WRAPPED_CPU_OUTPUT_PUBLICATION_HOLD")
        return 42
    # No output content other than bounded SAFE result status.
    print(json.dumps(result, sort_keys=True))
    return 0 if result["actual_swift_collator_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())

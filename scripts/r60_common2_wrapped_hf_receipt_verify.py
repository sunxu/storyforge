"""Read-only SAFE receipt acceptance for R60 Common2 wrapped System HF CPU.

Never accepts job COMPLETED alone, never publishes private hashes/text.
Reuses shared InputManager; optionally verifies expected byte SHA as a
private Owner-only argument (never printed).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from storyforge_dataset.hf_runtime import InputManager  # noqa: E402

SCHEMA = "storyforge_r60_common2_wrapped_hf_cpu_receipt_v1"
SUCCESS = "R60_COMMON2_WRAPPED_HF_CPU_COLLATOR_PASS__TRAIN_HOLD"
PIN = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
RUN_RE = re.compile(r"r60-common2-wrapcpu-\d{8}T\d{6}Z-[0-9a-f]{12}\Z")
EXPECTED_NAME = "R60_COMMON2_WRAPPED_CPU_SAFE_RECEIPT.json"
MAX_BYTES = 8192


def inspect(path: Path, run_key: str, expected_sha256: str | None = None) -> dict:
    out = {
        "schema": "storyforge_r60_common2_wrapped_hf_receipt_verify_safe_v1",
        "status": "WRAPPED_CPU_RECEIPT_HOLD",
        "reason_code": "UNVERIFIED",
        "cases_verified": 0,
        "real_swift_collator_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }
    try:
        if path.name != EXPECTED_NAME or not RUN_RE.fullmatch(run_key):
            raise ValueError("RECEIPT_IDENTITY_HOLD")
        data = InputManager.open_verified(
            path, max_bytes=MAX_BYTES, expected_sha256=expected_sha256,
        ).read_bytes()
        receipt = json.loads(data)
        fixed = {
            "schema": SCHEMA, "run_key": run_key,
            "status": SUCCESS, "reason_code": "WRAPPED_ACTUAL_SWIFT_ONLY",
            "stage": "AUDIT_COMPLETE", "model": "Qwen/Qwen3.8-27B",
            "model_revision": PIN, "stage_sha_verified": True,
            "system_text_pin_verified": True,
            "original_input_sha_verified": True,
            "source_examples": 2, "wrapped_examples": 2,
            "tokenizer_verified": True, "actual_swift_collator_verified": True,
            "last_assistant_label_mask_verified": True,
            "deployment_template_compatibility_verified": False,
            "semantic_world_isolation_verified": False,
            "r60_input_design_approved": False,
            "train_admitted": 0, "quality_v1_admitted": 0,
            "model_weights_loaded": False,
            "model_inference_calls": 0, "gpu_started": False,
            "hf_jobs_submitted": 0, "private_values_emitted": False,
            "training_dataset_files_written": 0,
            "safe_receipt_publication_expected": True,
            "system_origin": "R27_R52_FROZEN_SYNTHETIC_NOT_HISTORICAL_SENT",
        }
        if type(receipt) is not dict or any(
                key not in receipt or type(receipt[key]) is not type(value)
                or receipt[key] != value for key, value in fixed.items()):
            raise ValueError("RECEIPT_CONTRACT_HOLD")
        arrays = [receipt.get(n) for n in (
            "tokenizer_token_counts", "real_collator_token_counts",
            "supervised_token_counts",
        )]
        if any(type(arr) is not list or len(arr) != 2 for arr in arrays):
            raise ValueError("RECEIPT_ARRAY_SHAPE_HOLD")
        native, swift, supervised = arrays
        if (any(type(n) is not int or n < 1 or n > 16384 for n in native + swift)
                or any(type(n) is not int or n < 1 or n > count
                       for n, count in zip(supervised, swift))):
            raise ValueError("RECEIPT_COUNT_RANGE_HOLD")
        out.update(
            status="WRAPPED_CPU_RECEIPT_ACCEPTED__TRAIN_HOLD",
            reason_code="ACTUAL_SWIFT_R18_LABEL_MASK_TWO_OF_TWO",
            cases_verified=2, real_swift_collator_verified=True,
            tokenizer_token_counts=native,
            real_collator_token_counts=swift,
            supervised_token_counts=supervised,
        )
    except Exception as exc:
        allowed = {
            "RECEIPT_IDENTITY_HOLD", "RECEIPT_CONTRACT_HOLD",
            "RECEIPT_ARRAY_SHAPE_HOLD", "RECEIPT_COUNT_RANGE_HOLD",
        }
        out["reason_code"] = (
            str(exc) if type(exc) is ValueError and str(exc) in allowed
            else "RECEIPT_INPUT_OR_RUNTIME_HOLD"
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--expected-sha256", default=None)
    args = parser.parse_args()
    out = inspect(args.receipt, args.run_key, args.expected_sha256)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["real_swift_collator_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())

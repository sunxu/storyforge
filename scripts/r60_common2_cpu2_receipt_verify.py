"""Read-only validation of the existing CPU2 SAFE receipt; never emits private text/IDs.

This tool does not download, submit, run inference, or mutate any artifact.
Use an Owner-local 0600 copy of the already-written HF output receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

SCHEMA = "storyforge_r60_common2_sft_cpu_template_audit_safe_v1"
SUCCESS = "COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD"
EXPECTED_NAME = "R60_COMMON2_CPU2_SAFE_RECEIPT.json"
MAX_BYTES = 8192
TOKEN_LIMIT = 16384
SAFE_SCHEMA = "storyforge_r60_common2_cpu2_receipt_recheck_safe_v1"


def inspect(path: Path) -> dict:
    """Return only allowlisted scalar counts and fixed machine status."""
    result = {
        "schema": SAFE_SCHEMA,
        "status": "CPU2_SAFE_RECEIPT_HOLD",
        "reason_code": "RECEIPT_UNVERIFIED",
        "cases_verified": 0,
        "tokenizer_verified": False,
        "collator_verified": False,
        "r50_complete_exclusion_verified": False,
        "native_template_token_parity_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "model_inference_calls": 0,
        "private_values_emitted": False,
    }
    try:
        if path.name != EXPECTED_NAME or path.is_symlink():
            raise ValueError("RECEIPT_PATH_HOLD")
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size < 2
                or info.st_size > MAX_BYTES
                or info.st_mode & 0o077):
            raise ValueError("RECEIPT_MODE_OR_SIZE_HOLD")
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) != info.st_size:
            raise ValueError("RECEIPT_READ_HOLD")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("RECEIPT_SCHEMA_HOLD")
        required = {
            "schema": SCHEMA,
            "status": SUCCESS,
            "cases": 2,
            "tokenizer_verified": True,
            "collator_verified": True,
            "r50_complete_exclusion_verified": False,
            "train_admitted": 0,
            "model_inference_calls": 0,
            "model_weights_loaded": False,
            "native_template_token_parity_verified": False,
            "gpu_started": False,
            "private_values_emitted": False,
            "database_accessed": False,
        }
        if any(
            k not in payload or type(payload[k]) is not type(v)
            or payload[k] != v for k, v in required.items()
        ):
            raise ValueError("RECEIPT_CONTRACT_HOLD")
        token = payload.get("tokenizer_input_token_counts")
        real = payload.get("real_collator_token_counts")
        supervised = payload.get("supervised_token_counts")
        if not all(isinstance(x, list) and len(x) == 2 for x in (token, real, supervised)):
            raise ValueError("RECEIPT_COUNTS_SHAPE_HOLD")
        if any(type(x) is not int or x <= 0 or x > TOKEN_LIMIT for x in token + real):
            raise ValueError("RECEIPT_TOKEN_RANGE_HOLD")
        if any(type(x) is not int or x <= 0 or x > r for x, r in zip(supervised, real)):
            raise ValueError("RECEIPT_LABEL_RANGE_HOLD")
        result.update({
            "status": "CPU2_SAFE_RECEIPT_VERIFIED__R50_TRAIN_HOLD",
            "reason_code": "FROZEN_CPU_TWO_CASES_PASS",
            "cases_verified": 2,
            "tokenizer_verified": True,
            "collator_verified": True,
            "tokenizer_token_counts": token,
            "real_collator_token_counts": real,
            "supervised_token_counts": supervised,
        })
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        # Do not report exception details, contents, paths, timestamps or hashes.
        allowed = {
            "RECEIPT_PATH_HOLD", "RECEIPT_MODE_OR_SIZE_HOLD",
            "RECEIPT_READ_HOLD", "RECEIPT_SCHEMA_HOLD",
            "RECEIPT_CONTRACT_HOLD", "RECEIPT_COUNTS_SHAPE_HOLD",
            "RECEIPT_TOKEN_RANGE_HOLD", "RECEIPT_LABEL_RANGE_HOLD",
        }
        result["reason_code"] = (
            str(exc) if isinstance(exc, ValueError) and str(exc) in allowed
            else "RECEIPT_UNVERIFIED"
        )
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()
    report = inspect(args.receipt)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"].startswith("CPU2_SAFE_RECEIPT_VERIFIED") else 42


if __name__ == "__main__":
    raise SystemExit(main())

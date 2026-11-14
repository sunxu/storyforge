"""Owner read-only acceptance of Base CPU336 HF SAFE receipt.

A completed HF Job is not sufficient. Verify schema, run identity, aggregate
ranges and explicit held flags through shared InputManager; no private values.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from storyforge_dataset.hf_runtime import InputManager

from scripts import r60_base_cpu336_hf_stage as stage
from scripts import r60_base_cpu336_hf_worker as worker

SCHEMA = "storyforge_r60_base_cpu336_receipt_verify_safe_v1"


def accept(receipt_path: Path, key: str, sha256: str | None = None) -> dict:
    out = {
        "schema": SCHEMA,
        "status": "BASE_CPU336_RECEIPT_HOLD",
        "verified_cases": 0,
        "actual_collator_verified": False,
        "train_admitted": 0, "gpu_started": False,
        "private_values_emitted": False,
    }
    try:
        if not stage.RUN_RE.fullmatch(key) or receipt_path.name != worker.RECEIPT:
            raise ValueError("RECEIPT_IDENTITY_HOLD")
        raw = InputManager.open_verified(
            receipt_path, max_bytes=8192,
            expected_sha256=sha256).read_bytes()
        record = InputManager.validate_json(raw)
        fixed = {
            "schema": worker.SCHEMA, "run_key": key,
            "status": "BASE_CPU336_ACTUAL_COLLATOR_PASS__ALL_HELD",
            "stage": "AUDIT_COMPLETE", "model": worker.MODEL,
            "revision": worker.common.PIN,
            "source_cases": 336, "audited_cases": 336,
            "input_sha_verified": True,
            "tokenizer_verified": True,
            "actual_collator_verified": True,
            "last_assistant_label_mask_verified": True,
            "r50_complete_exclusion_verified": False,
            "reviewer_independence_verified": False,
            "world_component_isolation_verified": False,
            "training_dataset_created": False,
            "train_admitted": 0,
            "model_weights_loaded": False, "model_inference_calls": 0,
            "gpu_started": False, "private_values_emitted": False,
        }
        if type(record) is not dict or any(
                k not in record or type(record[k]) is not type(v)
                or record[k] != v for k, v in fixed.items()):
            raise ValueError("RECEIPT_CONTRACT_HOLD")
        for name in ("tokenizer_tokens", "collator_tokens",
                     "supervised_tokens"):
            stats = record.get(name)
            if (type(stats) is not dict
                    or set(stats) != {"min", "median", "p95", "max"}
                    or any(type(v) is not int or not 1 <= v <= 16384
                           for v in stats.values())
                    or not stats["min"] <= stats["median"] <=
                    stats["p95"] <= stats["max"]):
                raise ValueError("RECEIPT_STATS_HOLD")
        if (record["supervised_tokens"]["max"] >
                record["collator_tokens"]["max"]):
            raise ValueError("RECEIPT_LABEL_COUNT_HOLD")
        out.update(
            status="BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD",
            verified_cases=336, actual_collator_verified=True,
            tokenizer_tokens=record["tokenizer_tokens"],
            collator_tokens=record["collator_tokens"],
            supervised_tokens=record["supervised_tokens"])
    except Exception as exc:  # noqa: BLE001 - fixed public codes only
        code = str(exc) if type(exc) is ValueError else ""
        out["reason_code"] = (code if re.fullmatch(
            r"RECEIPT_[A-Z_]{3,48}_HOLD", code)
            else "RECEIPT_INPUT_OR_RUNTIME_HOLD")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--run-key", required=True)
    p.add_argument("--expected-sha256")
    a = p.parse_args()
    out = accept(a.receipt, a.run_key, a.expected_sha256)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["actual_collator_verified"] else 42


if __name__ == "__main__":
    sys.exit(main())

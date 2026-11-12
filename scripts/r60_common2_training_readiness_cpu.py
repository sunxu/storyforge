"""Offline Common2 two-case SFT evidence readout; NEVER grants training admission.

Uses existing private payload SHA/boundary check and existing HF CPU SAFE receipt
verifier. No raw content, IDs, paths, hashes, decoded tokens or secrets in output.
No model inference, external requests, DB, GPU or files written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "r58_quality"))
import r60_common2_sft_cpu_template_audit as audit  # noqa: E402
import r60_real1000_common2_sft_experimental_cpu as sft  # noqa: E402
import r60_common2_cpu2_receipt_verify as receipt  # noqa: E402

SCHEMA = "storyforge_r60_common2_training_readiness_safe_v1"


def private_bytes(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise ValueError("PRIVATE_INPUT_LINK_HOLD")
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077
            or not 0 < st.st_size <= limit):
        raise ValueError("PRIVATE_INPUT_MODE_SIZE_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        before = os.fstat(f.fileno())
        data = f.read(limit + 1)
        after = os.fstat(f.fileno())
    if (len(data) != st.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        raise ValueError("PRIVATE_INPUT_CHANGED_HOLD")
    return data


def inspect(input_dir: Path, receipt_path: Path) -> dict:
    out = {
        "schema": SCHEMA, "status": "COMMON2_READINESS_EVIDENCE_HOLD",
        "reason_code": "UNVERIFIED", "stage": "INPUTS",
        "payload_sha_verified": False, "derived_input_contract_verified": False,
        "cpu2_existing_receipt_verified": False,
        "cases_verified": 0, "train_template": "SWIFT_QWEN3_8_CANDIDATE_NOT_OWNER_APPROVED",
        "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
        "train_deploy_template_policy_approved": False,
        "semantic_world_alias_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "final_heldout_seal_verified": False,
        "train_admitted": 0, "quality_v1_admitted": 0,
        "gpu_started": False, "hf_jobs_submitted": 0,
        "database_accessed": False, "private_values_emitted": False,
    }
    try:
        if input_dir.is_symlink() or not input_dir.is_dir():
            raise ValueError("PRIVATE_INPUT_DIR_HOLD")
        if input_dir.stat().st_mode & 0o077:
            raise ValueError("PRIVATE_INPUT_DIR_MODE_HOLD")
        if receipt_path.resolve(strict=False) in {
            (input_dir / sft.DATA_NAME).resolve(strict=False),
            (input_dir / sft.MANIFEST_NAME).resolve(strict=False),
        }:
            raise ValueError("INPUT_PATH_COLLISION_HOLD")
        raw = private_bytes(input_dir / sft.DATA_NAME, audit.LIMIT)
        manifest = json.loads(private_bytes(input_dir / sft.MANIFEST_NAME, 65536))
        if type(manifest) is not dict:
            raise ValueError("MANIFEST_SCHEMA_HOLD")
        rows = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
        audit.validate_payload(rows, manifest, raw)
        out["payload_sha_verified"] = manifest["data_sha256"] == hashlib.sha256(raw).hexdigest()
        out["derived_input_contract_verified"] = True
        out["stage"] = "CPU2_RECEIPT"
        cpu = receipt.inspect(receipt_path)
        if (cpu.get("status") != "CPU2_SAFE_RECEIPT_VERIFIED__R50_TRAIN_HOLD"
                or cpu.get("cases_verified") != 2
                or cpu.get("tokenizer_verified") is not True
                or cpu.get("collator_verified") is not True):
            raise ValueError("CPU2_RECEIPT_CONTRACT_HOLD")
        # The historical SAFE receipt carries aggregate counts only; it cannot
        # prove its CPU execution used this exact payload. Do not claim that.
        out.update(cpu2_existing_receipt_verified=True, cases_verified=2,
                   tokenizer_token_counts=cpu["tokenizer_token_counts"],
                   real_collator_token_counts=cpu["real_collator_token_counts"],
                   supervised_token_counts=cpu["supervised_token_counts"],
                   status="COMMON2_INPUT_AND_CPU2_INDEPENDENT_CHECKS_PASS__ADMISSION_HOLD",
                   reason_code="INDEPENDENT_ARTIFACT_CHECKS_ONLY",
                   stage="READINESS_REPORTED")
    except Exception as exc:
        allowed = {
            "PRIVATE_INPUT_LINK_HOLD", "PRIVATE_INPUT_MODE_SIZE_HOLD",
            "PRIVATE_INPUT_CHANGED_HOLD", "PRIVATE_INPUT_DIR_HOLD",
            "PRIVATE_INPUT_DIR_MODE_HOLD", "INPUT_PATH_COLLISION_HOLD",
            "MANIFEST_SCHEMA_HOLD", "CPU2_RECEIPT_CONTRACT_HOLD",
            "PRIVATE_EXPERIMENT_CONTRACT_HOLD", "EXPERIMENT_MESSAGE_SEQUENCE_HOLD",
        }
        out["reason_code"] = (
            str(exc) if type(exc) is ValueError and str(exc) in allowed
            else "PRIVATE_INPUT_OR_RUNTIME_HOLD"
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--cpu2-receipt", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.input_dir, args.cpu2_receipt)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["cases_verified"] == 2 else 42


if __name__ == "__main__":
    raise SystemExit(main())

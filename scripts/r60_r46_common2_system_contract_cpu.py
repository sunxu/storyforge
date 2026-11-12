"""Read-only original R45/R46 vs Common2 dialogue System-role contract report.

No private story/system text, IDs, hashes, decoded tokens or paths in stdout.
Does not re-evaluate source overlaps, train anything, or claim runtime parity.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "r58_quality"))
sys.path.insert(0, str(ROOT / "scripts"))
import r60_common2_r45_source_story_cpu as r45
import r60_common2_training_readiness_cpu as readiness
import r60_common2_sft_cpu_template_audit as audit
import r60_real1000_common2_sft_experimental_cpu as sft

SCHEMA = "storyforge_r60_r46_common2_system_contract_safe_v1"

class Hold(ValueError):
    pass


def original_split(path: Path, kind: str) -> tuple[int, int]:
    raw = r45.private_bytes(path)
    pin_sha, expected = r45.PINS[kind]
    import hashlib
    if hashlib.sha256(raw).hexdigest() != pin_sha:
        raise Hold("R45_FROZEN_SHA_HOLD")
    lines = raw.splitlines()
    if len(lines) != expected:
        raise Hold("R45_COUNT_HOLD")
    with_system = 0
    for line in lines:
        row = json.loads(line)
        if type(row) is not dict or type(row.get("messages")) is not list:
            raise Hold("R45_SCHEMA_HOLD")
        messages = row["messages"]
        if (len(messages) < 3 or any(type(m) is not dict or
              m.get("role") not in {"system", "user", "assistant"} or
              type(m.get("content")) is not str for m in messages)
              or messages[0]["role"] != "system"
              or messages[-2]["role"] != "user"
              or messages[-1]["role"] != "assistant"
              or any(m.get("loss") is not False for m in messages[:-1])
              or messages[-1].get("loss") is not True):
            raise Hold("R46_DATA_ROLE_LOSS_HOLD")
        with_system += 1
    return expected, with_system


def common2_input(folder: Path) -> tuple[int, int]:
    if folder.is_symlink() or not folder.is_dir() or folder.stat().st_mode & 0o077:
        raise Hold("COMMON2_PRIVATE_DIR_HOLD")
    raw = readiness.private_bytes(folder / sft.DATA_NAME, audit.LIMIT)
    manifest = json.loads(readiness.private_bytes(folder / sft.MANIFEST_NAME, 65536))
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    audit.validate_payload(rows, manifest, raw)
    count = sum(any(m["role"] == "system" for m in r["messages"]) for r in rows)
    if count != 0:
        raise Hold("COMMON2_UNEXPECTED_SYSTEM_HOLD")
    return len(rows), count


def inspect(train: Path, validation: Path, input_dir: Path) -> dict:
    out = {
        "schema": SCHEMA,
        "status": "SYSTEM_INPUT_CONTRACT_HOLD",
        "reason_code": "UNVERIFIED", "stage": "R45_TRAIN",
        "r45_source_sha_verified": False,
        "r45_train_rows": 0, "r45_validation_rows": 0,
        "r45_rows_with_initial_system": 0,
        "common2_input_sha_verified": False,
        "common2_rows": 0, "common2_rows_with_system": 0,
        "historical_vs_current_system_contract_equal": False,
        "r46_runtime_template_equivalence_verified": False,
        "r46_actual_system_text_equal_to_current": False,
        "training_input_policy_approved": False,
        "train_admitted": 0, "gpu_started": False,
        "hf_jobs_submitted": 0, "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        if len({str(p.resolve(strict=False)) for p in (
            train, validation, input_dir / sft.DATA_NAME,
            input_dir / sft.MANIFEST_NAME)}) != 4:
            raise Hold("INPUT_COLLISION_HOLD")
        n, s = original_split(train, "train")
        out.update(r45_train_rows=n, r45_rows_with_initial_system=s)
        out["stage"] = "R45_VALIDATION"
        n, s = original_split(validation, "validation")
        out["r45_validation_rows"] = n
        out["r45_rows_with_initial_system"] += s
        out["r45_source_sha_verified"] = True
        out["stage"] = "COMMON2"
        n, s = common2_input(input_dir)
        out.update(common2_rows=n, common2_rows_with_system=s,
                   common2_input_sha_verified=True)
        out.update(
            stage="CONTRACT_COMPARISON",
            status="R46_R60_SYSTEM_ROLE_CONTRACT_DIFFERENCE_CONFIRMED__TRAIN_HOLD",
            reason_code="HISTORICAL_SYSTEM_PRESENT_CURRENT_SYSTEM_ABSENT",
        )
    except Exception as exc:
        allowed = {
            "R45_FROZEN_SHA_HOLD", "R45_COUNT_HOLD", "R45_SCHEMA_HOLD",
            "R46_DATA_ROLE_LOSS_HOLD", "COMMON2_PRIVATE_DIR_HOLD",
            "COMMON2_UNEXPECTED_SYSTEM_HOLD", "INPUT_COLLISION_HOLD",
            "PRIVATE_INPUT_LINK_HOLD", "PRIVATE_INPUT_MODE_SIZE_HOLD",
            "PRIVATE_INPUT_CHANGED_HOLD", "PRIVATE_EXPERIMENT_CONTRACT_HOLD",
            "EXPERIMENT_MESSAGE_SEQUENCE_HOLD",
        }
        out["reason_code"] = (
            str(exc) if isinstance(exc, ValueError) and str(exc) in allowed
            else "INPUT_OR_RUNTIME_HOLD"
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r45-original-train", required=True, type=Path)
    parser.add_argument("--r45-original-validation", required=True, type=Path)
    parser.add_argument("--common2-input-dir", required=True, type=Path)
    args = parser.parse_args()
    out = inspect(args.r45_original_train, args.r45_original_validation, args.common2_input_dir)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["stage"] == "CONTRACT_COMPARISON" else 42


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only Common2 synthetic System wrapper preview, never writes training data.

The public pinned R27/R52 generic System is an EXPLICIT_NEW_TRAINING_WRAPPER,
NOT historical original sent prompt. Private source data and target are untouched.
This tool only validates in memory. Its output contains allowlisted safe metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "r58_quality"))
sys.path.insert(0, str(ROOT / "scripts"))
import r60_common2_training_readiness_cpu as readiness
import r60_common2_sft_cpu_template_audit as audit
import r60_real1000_common2_sft_experimental_cpu as sft

SCHEMA = "storyforge_r60_common2_generic_system_wrapper_preview_safe_v1"
PINNED_R27_R52_SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)
SYSTEM_SHA256 = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
SYSTEM_SOURCE = "docs/evidence/V03_R52_NO_CARD_INPUT_DESIGN_APPROVAL_20261021.md"


class Hold(ValueError):
    pass


def preview(folder: Path) -> dict:
    report = {
        "schema": SCHEMA,
        "status": "COMMON2_GENERIC_SYSTEM_PREVIEW_HOLD",
        "reason_code": "UNVERIFIED",
        "stage": "SYSTEM_PIN",
        "system_text_pin_verified": False,
        "original_input_sha_verified": False,
        "source_examples": 0,
        "synthetic_system_messages_added": 0,
        "wrapped_examples": 0,
        "source_messages_preserved": False,
        "original_targets_unchanged": False,
        "supervision_only_final_assistant": False,
        "system_origin": "R27_R52_FROZEN_SYNTHETIC_NOT_HISTORICAL_SENT",
        "wrapper_kind": "EXPLICIT_NEW_TRAINING_WRAPPER_PREVIEW_ONLY",
        "historical_sent_prompt_verified": False,
        "new_swift_collator_verified": False,
        "deployment_template_compatibility_verified": False,
        "world_semantic_isolation_verified": False,
        "r60_input_design_approved": False,
        "train_admitted": 0, "gpu_started": False, "hf_jobs_submitted": 0,
        "database_accessed": False, "private_values_emitted": False,
        "files_written": 0,
    }
    try:
        if hashlib.sha256(PINNED_R27_R52_SYSTEM.encode("utf-8")).hexdigest() != SYSTEM_SHA256:
            raise Hold("SYSTEM_PIN_MISMATCH_HOLD")
        report["system_text_pin_verified"] = True
        report["stage"] = "SOURCE_CONTRACT"
        if folder.is_symlink() or not folder.is_dir() or folder.stat().st_mode & 0o077:
            raise Hold("PRIVATE_DIR_HOLD")
        raw = readiness.private_bytes(folder / sft.DATA_NAME, audit.LIMIT)
        manifest = json.loads(readiness.private_bytes(folder / sft.MANIFEST_NAME, 65536))
        rows = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
        audit.validate_payload(rows, manifest, raw)
        report["original_input_sha_verified"] = True
        report["source_examples"] = 2
        report["stage"] = "WRAPPER_PREVIEW"
        for row in rows:
            orig_messages = row["messages"]
            wrapped = [{"role": "system", "content": PINNED_R27_R52_SYSTEM, "loss": False}]
            wrapped += [{**m, "loss": i == len(orig_messages) - 1}
                        for i, m in enumerate(orig_messages)]
            if (len(wrapped) != len(orig_messages) + 1 or
                wrapped[0]["content"] != PINNED_R27_R52_SYSTEM or
                wrapped[0]["loss"] is not False or
                any(w["role"] != o["role"] or w["content"] != o["content"]
                    for w,o in zip(wrapped[1:],orig_messages))):
                raise Hold("ORIGINAL_MESSAGE_CHANGED_HOLD")
            if (any(msg["loss"] is not False for msg in wrapped[:-1])
                or wrapped[-1]["role"] != "assistant"
                or wrapped[-1]["loss"] is not True):
                raise Hold("FINAL_SUPERVISION_HOLD")
        report.update(
            status="COMMON2_GENERIC_SYSTEM_IN_MEMORY_WRAPPER_PREVIEW_PASS__TRAIN_HOLD",
            reason_code="FROZEN_R27_R52_SYNTHETIC_SYSTEM_ONLY",
            stage="WRAPPER_PREVIEW_COMPLETE",
            wrapped_examples=2,
            synthetic_system_messages_added=2,
            source_messages_preserved=True,
            original_targets_unchanged=True,
            supervision_only_final_assistant=True,
        )
    except Exception as exc:
        allowed = {
            "SYSTEM_PIN_MISMATCH_HOLD", "PRIVATE_DIR_HOLD",
            "ORIGINAL_MESSAGE_CHANGED_HOLD", "FINAL_SUPERVISION_HOLD",
            "PRIVATE_INPUT_LINK_HOLD", "PRIVATE_INPUT_MODE_SIZE_HOLD",
            "PRIVATE_INPUT_CHANGED_HOLD", "PRIVATE_EXPERIMENT_CONTRACT_HOLD",
            "EXPERIMENT_MESSAGE_SEQUENCE_HOLD",
        }
        report["reason_code"] = (
            str(exc) if isinstance(exc, ValueError) and str(exc) in allowed
            else "INPUT_OR_RUNTIME_HOLD"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    args = parser.parse_args()
    report = preview(args.input_dir)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["wrapped_examples"] == 2 else 42


if __name__ == "__main__":
    raise SystemExit(main())

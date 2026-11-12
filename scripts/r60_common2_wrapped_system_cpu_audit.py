"""Offline Qwen tokenizer + genuine ms-swift last-round audit on a temporary System wrapper.

No training data files are written. No model weights, GPU, HF jobs, network or
inference. Requires preexisting pinned local Qwen3.8 tokenizer/config files.
Never prints model source text, private story text, IDs, paths, token IDs or hashes.
This is a technical preflight of proposed wrapper, NOT training admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
sys.path.insert(0, str(ROOT / "scripts"))
import r60_common2_generic_system_wrapper_preview_cpu as wrapper
import r60_common2_sft_cpu_template_audit as audit
import r60_common2_training_readiness_cpu as readiness
import r60_real1000_common2_sft_experimental_cpu as sft

SCHEMA = "storyforge_r60_common2_wrapped_system_cpu_audit_safe_v1"
PHASES = frozenset({
    "SYSTEM_PIN", "SNAPSHOT", "SOURCE_INPUT", "WRAPPED_MESSAGES",
    "TOKENIZER_LOAD", "SWIFT_PROCESSOR_LOAD", "SWIFT_TEMPLATE_INIT",
    "TEXT_ONLY_ROPE_SETUP", "ACTUAL_SWIFT_COLLATOR",
})


class Hold(ValueError):
    pass


def prepare_rows(folder: Path) -> list[dict]:
    if folder.is_symlink() or not folder.is_dir() or folder.stat().st_mode & 0o077:
        raise Hold("PRIVATE_DIR_HOLD")
    raw = readiness.private_bytes(folder / sft.DATA_NAME, audit.LIMIT)
    manifest = json.loads(readiness.private_bytes(folder / sft.MANIFEST_NAME, 65536))
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    audit.validate_payload(rows, manifest, raw)
    if hashlib.sha256(wrapper.PINNED_R27_R52_SYSTEM.encode()).hexdigest() != wrapper.SYSTEM_SHA256:
        raise Hold("SYSTEM_PIN_MISMATCH_HOLD")
    result = []
    for row in rows:
        source_messages = row["messages"]
        # Keep source messages/targets verbatim; the injected System is explicitly
        # a synthetic training policy, never a historical actually-sent prompt.
        msgs = [{"role": "system", "content": wrapper.PINNED_R27_R52_SYSTEM}]
        msgs.extend({"role": m["role"], "content": m["content"]} for m in source_messages)
        if (len(msgs) != 13 or msgs[0]["role"] != "system"
                or any(m != o for m, o in zip(msgs[1:], source_messages))
                or msgs[-2]["role"] != "user" or msgs[-1]["role"] != "assistant"):
            raise Hold("WRAPPER_CONTRACT_HOLD")
        result.append({"messages": msgs})
    return result


def local_snapshot(snapshot: Path) -> None:
    if snapshot.is_symlink() or audit.PIN not in str(snapshot.resolve()):
        raise Hold("LOCAL_PINNED_SNAPSHOT_HOLD")
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        if not (snapshot / name).is_file():
            raise Hold("LOCAL_SNAPSHOT_FILES_HOLD")


def check(folder: Path, snapshot: Path) -> dict:
    report = {
        "schema": SCHEMA, "status": "COMMON2_WRAPPED_SYSTEM_CPU_AUDIT_HOLD",
        "reason_code": "UNVERIFIED", "stage": "SYSTEM_PIN",
        "source_examples": 0, "wrapped_examples": 0,
        "system_text_pin_verified": False,
        "original_input_sha_verified": False, "source_messages_preserved": False,
        "original_targets_unchanged": False,
        "tokenizer_verified": False, "actual_swift_collator_verified": False,
        "last_assistant_label_mask_verified": False,
        "r46_runtime_template_equivalence_verified": False,
        "deployment_template_compatibility_verified": False,
        "r60_input_design_approved": False,
        "semantic_world_isolation_verified": False,
        "train_admitted": 0, "gpu_started": False, "hf_jobs_submitted": 0,
        "model_weights_loaded": False, "model_inference_calls": 0,
        "database_accessed": False, "private_values_emitted": False,
        "files_written": 0,
    }
    try:
        if hashlib.sha256(wrapper.PINNED_R27_R52_SYSTEM.encode()).hexdigest() != wrapper.SYSTEM_SHA256:
            raise Hold("SYSTEM_PIN_MISMATCH_HOLD")
        report["system_text_pin_verified"] = True
        report["stage"] = "SNAPSHOT"
        local_snapshot(snapshot)
        report["stage"] = "SOURCE_INPUT"
        rows = prepare_rows(folder)
        report.update(source_examples=2, original_input_sha_verified=True)
        report["stage"] = "WRAPPED_MESSAGES"
        report.update(wrapped_examples=2, source_messages_preserved=True,
                      original_targets_unchanged=True)

        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        report["stage"] = "TOKENIZER_LOAD"
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True
        )
        report["stage"] = "SWIFT_PROCESSOR_LOAD"
        from swift import get_processor, get_template
        processor = get_processor(str(snapshot), model_type="qwen3_5")
        report["stage"] = "SWIFT_TEMPLATE_INIT"
        template = get_template(
            processor, template_type="qwen3_8", loss_scale="last_round",
            max_length=audit.CEILING, add_non_thinking_prefix=False,
        )
        template.set_mode("train")
        report["stage"] = "TEXT_ONLY_ROPE_SETUP"
        audit.bind_text_only_rope(template, snapshot)

        report["stage"] = "ACTUAL_SWIFT_COLLATOR"
        # Existing R18 label verifier captures and discards all internal decoded
        # debug in audit.inspect_rows; outer caller never prints source exceptions.
        observed = audit.inspect_rows(rows, tokenizer, template)
        if (observed["cases"] != 2
                or observed["collator_verified"] is not True
                or observed["tokenizer_verified"] is not True
                or any(n <= 0 or n > audit.CEILING for n in
                       observed["real_collator_token_counts"])
                or any(n <= 0 for n in observed["supervised_token_counts"])):
            raise Hold("WRAPPED_COLLATOR_CONTRACT_HOLD")
        report.update(
            status="COMMON2_WRAPPED_SYSTEM_ACTUAL_CPU_COLLATOR_PASS__TRAIN_HOLD",
            reason_code="WRAPPED_IN_MEMORY_CPU_VERIFIED_ONLY",
            stage="AUDIT_COMPLETE",
            tokenizer_verified=True, actual_swift_collator_verified=True,
            last_assistant_label_mask_verified=True,
            tokenizer_token_counts=observed["tokenizer_input_token_counts"],
            real_collator_token_counts=observed["real_collator_token_counts"],
            supervised_token_counts=observed["supervised_token_counts"],
        )
    except Exception:
        report["reason_code"] = (
            report["stage"] + "_HOLD" if report["stage"] in PHASES
            else "INPUT_OR_RUNTIME_HOLD"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    report = check(args.input_dir, args.snapshot)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["actual_swift_collator_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())

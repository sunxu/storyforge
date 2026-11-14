"""Local CPU Qwen tokenizer / actual ms-swift collation for 336 HELD R60 cases.

Reuses audited Common2 ms-swift label-mask checks, works entirely in memory.
No System/card fabrication, no model weights, no dataset write/admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import r60_base_start_sft_shape_cpu as shape
import r60_common2_sft_cpu_template_audit as common
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base_start_cpu336_template_safe_v1"
PHASES = common.SAFE_PHASES | frozenset({
    "FROZEN_SOURCE_CHECK", "STATIC_SHAPE_CHECK", "BUILD_IN_MEMORY",
})
EXPECTED = 336


class Hold(ValueError):
    pass


def prepare(cases: list[dict], manifest: dict) -> list[dict]:
    result = shape.inspect(cases, manifest)
    if (result["status"] != "BASE_SFT_STATIC_SHAPE_PASS__ALL_HELD"
            or result["validated_three_message_cases"] != EXPECTED):
        raise Hold("STATIC_SHAPE_REQUIRED_HOLD")
    rows = []
    for item in manifest["remaining_full_r50_hold"]:
        case = cases[item["position"] - 1]
        rows.append({"messages": [
            *[{"role": m["role"], "content": m["content"]}
              for m in case["history_messages"]],
            {"role": "assistant", "content": case["target_text"]},
        ]})
    if len(rows) != EXPECTED:
        raise Hold("PREPARED_CASE_COUNT_HOLD")
    return rows


def _stats(numbers: list[int]) -> dict:
    if len(numbers) != EXPECTED or any(type(n) is not int or n <= 0
                                       for n in numbers):
        raise Hold("RESULT_COUNT_OR_FORMAT_HOLD")
    ordered = sorted(numbers)
    return {
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "p95": ordered[int((len(ordered) - 1) * 0.95)],
        "max": ordered[-1],
    }


def run(args: argparse.Namespace) -> dict:
    def phase(code: str) -> None:
        if code not in PHASES:
            raise Hold("UNEXPECTED_PHASE_HOLD")
        args._phase = code

    phase("SNAPSHOT_CHECK")
    if (args.snapshot.is_symlink()
            or common.PIN not in str(args.snapshot.resolve())):
        raise Hold("PINNED_LOCAL_SNAPSHOT_HOLD")
    if any(not (args.snapshot / name).is_file()
           for name in ("tokenizer.json", "tokenizer_config.json")):
        raise Hold("TOKENIZER_FILES_HOLD")
    phase("FROZEN_SOURCE_CHECK")
    private.private_dir(args.quarantine_dir, create=False)
    cases, crosswalk_report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir,
        args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(
        cases, crosswalk_report, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if saved != expected:
        raise Hold("QUARANTINE_SNAPSHOT_DRIFT_HOLD")
    phase("STATIC_SHAPE_CHECK")
    rows = prepare(cases, saved)

    # No network lookup, model weight loading, or accelerator use.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    phase("TOKENIZER_LOAD")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True,
        trust_remote_code=False, use_fast=True)
    template = None
    if args.stage == "both":
        phase("SWIFT_PROCESSOR_LOAD")
        from swift import get_processor, get_template

        processor = get_processor(
            str(args.snapshot), model_type="qwen3_5")
        phase("SWIFT_TEMPLATE_INIT")
        template = get_template(
            processor, template_type="qwen3_8",
            loss_scale="last_round", max_length=common.CEILING,
            add_non_thinking_prefix=False)
        template.set_mode("train")
        phase("TEXT_ONLY_ROPE_SETUP")
        common.bind_text_only_rope(template, args.snapshot)
    phase("BUILD_IN_MEMORY")
    report = common.inspect_rows(rows, tok, template, phase=phase)
    if report.get("cases") != EXPECTED:
        raise Hold("REUSED_AUDITOR_CONTRACT_HOLD")
    token_stats = _stats(report["tokenizer_input_token_counts"])
    collator_stats = (_stats(report["real_collator_token_counts"])
                      if template is not None else None)
    supervised_stats = (_stats(report["supervised_token_counts"])
                        if template is not None else None)
    return {
        "schema": SCHEMA,
        "status": ("BASE_CPU336_TOKENIZER_COLLATOR_PASS__ALL_HELD"
                   if template is not None else
                   "BASE_CPU336_TOKENIZER_PASS__COLLATOR_HOLD"),
        "cases_checked": EXPECTED,
        "model": "Qwen/Qwen3.8-27B",
        "model_revision": common.PIN,
        "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
        "token_stats": token_stats,
        "collator_token_stats": collator_stats,
        "supervised_token_stats": supervised_stats,
        "tokenizer_verified": True,
        "collator_verified": template is not None,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "world_component_isolation_verified": False,
        "train_admitted": 0,
        "training_dataset_created": False,
        "model_weights_loaded": False,
        "model_requests": 0,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--stage", choices=("token", "both"), default="token")
    args = parser.parse_args()
    args._phase = "SNAPSHOT_CHECK"
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - suppress private values and stderr
        print(json.dumps({
            "schema": SCHEMA,
            "status": "BASE_CPU336_TEMPLATE_AUDIT_HOLD",
            "reason_code": args._phase + "_HOLD",
            "tokenizer_verified": False,
            "collator_verified": False,
            "train_admitted": 0,
            "model_weights_loaded": False,
            "model_requests": 0,
            "gpu_started": False,
            "database_modified": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

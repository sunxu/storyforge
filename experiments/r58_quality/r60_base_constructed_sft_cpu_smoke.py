"""CPU-only real tokenizer/ms-swift smoke for constructed-System V1.

Three fully synthetic stories; no private data, DB, weight loading, GPU or
network. Uses existing Common2/R18 last-assistant-only actual collator audit.
Requires already-pinned local Qwen snapshot. The result is technical evidence
only, NEVER training admission or world-source provenance certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import r60_base_constructed_system_contract_v1 as contract
import r60_common2_sft_cpu_template_audit as common

SCHEMA = "storyforge_r60_base_constructed_sft_cpu_smoke_safe_v1"
PHASES = common.SAFE_PHASES | frozenset({"SYNTHETIC_BUILD", "CONTRACT_CHECK"})
CASES = 3


class Hold(ValueError):
    pass


def synthetic_rows() -> list[dict]:
    rows = []
    for index in range(CASES):
        messages = [
            {"role": "user", "content": f"虚构人物在第{index}幕推开一扇门。"},
            {"role": "assistant", "content": "门后传来钟声，但人物尚未作出决定。"},
            {"role": "user", "content": "请描写守门人的反应，不替我作决定。"},
        ]
        world = (
            contract.SourceBoundFact(
                field_path="v2_data.world",
                content="【合成测试】这座虚构城市每天会鸣钟一次。",
                story_id=f"SYNTHETIC-{index}",
                revision_id="SYNTHETIC-REV-1",
                target_time_proof_ref="SYNTHETIC-ONLY-NOT-HISTORICAL-PROOF",
            ) if index > 0 else None
        )
        roles = (
            contract.SourceBoundFact(
                field_path="v2_data.characters",
                content="【合成测试】守门人只负责开门与回答问题。",
                story_id=f"SYNTHETIC-{index}",
                revision_id="SYNTHETIC-REV-1",
                target_time_proof_ref="SYNTHETIC-ONLY-NOT-HISTORICAL-PROOF",
            ) if index == 2 else None
        )
        assembled = contract.assemble_candidate(
            messages,
            "守门人侧过身让出一条路，轻声询问来者是否需要指引。",
            history_turns=(1, 2, 3), target_turn=4,
            world=world, roles=roles,
        )
        if assembled["train_admitted"] != 0:
            raise Hold("ADMISSION_GUARD_HOLD")
        rows.append({"messages": assembled["messages"]})
    return rows


def check_report(report: dict, *, stage: str) -> dict:
    if (type(report) is not dict or report.get("cases") != CASES
            or report.get("tokenizer_verified") is not True
            or report.get("collator_verified") is not (stage == "both")
            or type(report.get("tokenizer_input_token_counts")) is not list
            or len(report["tokenizer_input_token_counts"]) != CASES):
        raise Hold("TECHNICAL_AUDIT_CONTRACT_HOLD")
    counts = report["tokenizer_input_token_counts"]
    if any(type(n) is not int or not 0 < n <= common.CEILING for n in counts):
        raise Hold("TOKEN_COUNT_HOLD")
    if stage == "both":
        for name in ("real_collator_token_counts", "supervised_token_counts"):
            values = report.get(name)
            if (type(values) is not list or len(values) != CASES
                    or any(type(v) is not int or v <= 0 for v in values)):
                raise Hold("COLLATOR_LABELS_HOLD")
    return {
        "schema": SCHEMA,
        "status": (
            "BASE_CONSTRUCTED_V1_ACTUAL_COLLATOR_SYNTHETIC_PASS__TRAIN_HOLD"
            if stage == "both"
            else "BASE_CONSTRUCTED_V1_TOKENIZER_SYNTHETIC_PASS__COLLATOR_HOLD"
        ),
        "input_contract": contract.CONTRACT_ID,
        "provenance": contract.PROVENANCE,
        "generic_system_sha256": hashlib.sha256(
            contract.GENERIC_SYSTEM.encode("utf-8")).hexdigest(),
        "synthetic_cases": CASES,
        "tokenizer_verified": True,
        "actual_collator_verified": stage == "both",
        "last_assistant_only_mask_verified": stage == "both",
        "real_source_content_verified": False,
        "real_candidate_contract_verified": False,
        "reviewer_independence_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "model_weights_loaded": False,
        "gpu_started": False,
        "model_requests": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }


def run(args: argparse.Namespace) -> dict:
    def phase(value: str) -> None:
        if value not in PHASES:
            raise Hold("PHASE_HOLD")
        args._safe_phase = value

    phase("SNAPSHOT_CHECK")
    if (args.snapshot.is_symlink()
            or common.PIN not in str(args.snapshot.resolve())
            or any(not (args.snapshot / name).is_file()
                   for name in ("tokenizer.json", "tokenizer_config.json",
                                "config.json"))):
        raise Hold("PINNED_SNAPSHOT_HOLD")
    phase("SYNTHETIC_BUILD")
    rows = synthetic_rows()
    phase("CONTRACT_CHECK")
    if (len(rows) != CASES or any(
        len(r["messages"]) != 5
        or [m["role"] for m in r["messages"]]
        != ["system", "user", "assistant", "user", "assistant"]
        for r in rows
    )):
        raise Hold("MESSAGE_STRUCTURE_HOLD")
    # Offline, CPU-only; do not load model weights.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    phase("TOKENIZER_LOAD")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True,
        trust_remote_code=False, use_fast=True,
    )
    template = None
    if args.stage == "both":
        phase("SWIFT_PROCESSOR_LOAD")
        from swift import get_processor, get_template

        processor = get_processor(str(args.snapshot), model_type="qwen3_5")
        phase("SWIFT_TEMPLATE_INIT")
        template = get_template(
            processor, template_type="qwen3_8",
            loss_scale="last_round", max_length=common.CEILING,
            add_non_thinking_prefix=False,
        )
        template.set_mode("train")
        phase("TEXT_ONLY_ROPE_SETUP")
        common.bind_text_only_rope(template, args.snapshot)
    result = common.inspect_rows(rows, tokenizer, template, phase=phase)
    return check_report(result, stage=args.stage)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--stage", choices=("token", "both"), default="both")
    args = p.parse_args()
    args._safe_phase = "SNAPSHOT_CHECK"
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no exception texts, decoded labels or paths
        print(json.dumps({
            "schema": SCHEMA,
            "status": "BASE_CONSTRUCTED_V1_CPU_SMOKE_HOLD",
            "reason_code": args._safe_phase + "_HOLD",
            "tokenizer_verified": False,
            "actual_collator_verified": False,
            "train_admitted": 0,
            "model_weights_loaded": False,
            "gpu_started": False,
            "model_requests": 0,
            "database_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

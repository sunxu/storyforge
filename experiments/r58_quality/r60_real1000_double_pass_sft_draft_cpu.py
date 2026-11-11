"""Create-only SFT format draft for 3 frozen double-PASS source candidates.

The System is explicitly constructed for training: it is NOT claimed to be the
historical System prompt. No official admission or GPU/model calls.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import r60_real1000_double_pass_context_cpu as context
import r60_real1000_double_pass_candidates_cpu as double
import r60_real1000_pilot20_local_review as pilot
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_double_pass_sft_draft_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_real1000_double_pass_sft_draft_private_v1"
FILENAME = "R60_DOUBLE_PASS_SFT_DRAFT_PRIVATE.json"
CONSTRUCTED_SYSTEM = (
    "你正在续写中文互动小说。严格遵守用户当前可见的选择和事实，"
    "不得替玩家做关键决定、发言或行动；在缺少世界设定时不要编造"
    "硬性规则。保持角色连续性、自然叙事与NPC主动性。"
)


class Hold(ValueError):
    pass


def make(packets: list[dict], positions: list[int]) -> dict:
    if len(packets) != 20 or len(positions) != 3 or len(set(positions)) != 3:
        raise Hold("DRAFT_POSITION_HOLD")
    rows = []
    for pos in sorted(positions):
        if type(pos) is not int or not 1 <= pos <= 20:
            raise Hold("DRAFT_POSITION_HOLD")
        packet = packets[pos - 1]
        history = packet["history_messages"]
        target = packet["assistant_target"]
        if (len(history) != 3 or
                [x["role"] for x in history] != ["user", "assistant", "user"]
                or not all(isinstance(x["content"], str) and x["content"]
                           for x in history)
                or not isinstance(target, str) or not target):
            raise Hold("DRAFT_HISTORY_HOLD")
        rows.append({
            "pilot_position": pos,
            "messages": [{"role": "system", "content": CONSTRUCTED_SYSTEM},
                         *history, {"role": "assistant", "content": target}],
            "system_provenance": "TRAINING_CONSTRUCTED_CONTEXT__NOT_HISTORICAL",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
            "training_admitted": False,
        })
    return {
        "schema": PRIVATE_SCHEMA,
        "status": "SFT_FORMAT_DRAFT__NOT_ADMITTED",
        "candidate_count": 3,
        "samples": rows,
        "train_admitted": 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expand-dir", type=Path, required=True)
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--candidate-file", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        safe_context = context.check(args.expand_dir, args.sample_dir,
                                     args.review_dir, args.candidate_file)
        if safe_context["candidate_count"] != 3:
            raise Hold("CONTEXT_GATE_HOLD")
        manifest = json.loads(private.read_private(args.candidate_file, 65536))
        if manifest["schema"] != double.PRIVATE_SCHEMA:
            raise Hold("MANIFEST_SCHEMA_HOLD")
        _config, packets, _progress = pilot.get_state(args.review_dir)
        draft = make(packets["packets"], [
            x["pilot_position"] for x in manifest["candidates"]])
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise Hold("OUTPUT_EXISTS_HOLD")
        private.private_dir(args.output_dir, create=True)
        private.write_new(args.output_dir / FILENAME, pilot.canonical(draft))
        print(json.dumps({
            "schema": SCHEMA,
            "status": "SFT_CONSTRUCTED_CONTEXT_DRAFT_READY__TRAIN_ADMISSION_HOLD",
            "draft_cases": 3,
            "conversation_message_count_per_case": 5,
            "historical_system_recovered": False,
            "constructed_system_explicit": True,
            "world_components_verified": False,
            "r50_complete_exclusion_verified": False,
            "tokenizer_or_collator_run": False,
            "quality_v1_admitted": 0,
            "train_admitted": 0,
            "database_accessed": False,
            "gpu_job_started": False,
            "model_inference_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - redact private errors
        reason = str(exc) if isinstance(exc, Hold) else "DRAFT_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "SFT_DRAFT_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0, "train_admitted": 0,
            "model_inference_calls": 0, "gpu_job_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

"""R60: prepare private E0-E3 semantic review packets from verified previews.

This is a thin adapter, not a second reviewer, SFT compiler or admission gate.
Reuses R59 actual input-shape validation and existing R60 exact Packet linkage.
Source paragraphs/targets never leave private 0600 files; no model is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from quality_v1 import FLOORS, SEVERE, canonical, sha
from r59_sft_collator_cpu import validate_preview_row
from r60_experimental_shape_adapter import GATES, NOT_ACTUAL_SENT
from r60_p3_stage_pair_probe import ALLOWED_BASE, Hold, parse_lines, private_bytes

SCHEMA = "storyforge_r60_experimental_semantic_review_packets_safe_v1"
REVIEW_SCHEMA = "storyforge_r60_experimental_semantic_review_private_v1"
QUESTIONS = {
    "E0_SOURCE_AND_RIGHTS": (
        "原始 Gold 版本、使用权和隐私边界有无独立原件？明确已核对和未知部分；"
        "Packet 导出快照不等于目标时点原件。"
    ),
    "E1_RECONSTRUCTION": (
        "逐条核对历史消息、当前玩家输入与上下文范围。是否有缺失前缀、"
        "不一致角色设定、未来信息或时间点错误？不得声称原样发送 Provider。"
    ),
    "E2_TARGET_SEMANTICS": (
        "回复是否为完整、单次适用的 Assistant 监督目标？检查重试、拼接、"
        "续写、过滤和后处理；明确无法从材料推断的部分。"
    ),
    "E3_PRIVACY_WORLD_PROTECTED_EXPOSURE": (
        "按原 Quality-v1 六维与严重问题定义，逐项核对连贯性/玩家自主权/硬规则。"
        "世界归属、Train/Validation 隔离、历史曝光及 Protected Set 完整性须有"
        "独立可复核的元数据证据；不可访问 R50 正文。"
    ),
}


def prepare(locators: list[dict], previews: list[dict]):
    if len(locators) != 3 or len(previews) != 3:
        raise Hold("THREE_CASES_REQUIRED")
    review = []
    seen_ids = set()
    seen_targets = set()
    for linked, preview in zip(locators, previews, strict=True):
        cid = linked.get("case_id")
        digest = linked.get("source_target_sha256")
        if (not isinstance(cid, str) or not cid or cid in seen_ids
                or not isinstance(digest, str) or len(digest) != 64
                or digest in seen_targets
                or linked.get("context_provenance") != NOT_ACTUAL_SENT
                or linked.get("packet_target_exact_equal") is not True
                or linked.get("packet_current_user_exact_equal") is not True
                or linked.get("gates") != {g: "HOLD_UNREVIEWED" for g in GATES}):
            raise Hold("E03_LINKAGE_OR_GATE_DRIFT")
        seen_ids.add(cid)
        seen_targets.add(digest)
        validate_preview_row(preview)
        messages = preview["messages"]
        target = messages[-1]["content"]
        if (sha(target.encode("utf-8")) != digest
                or preview["metadata"]["source_target_sha256"] != digest):
            raise Hold("REVIEW_TARGET_HASH_MISMATCH")
        source_msgs = [
            {"role": m["role"], "content": m["content"]} for m in messages[:-1]
        ]
        input_sha = sha(canonical(source_msgs))
        if input_sha != preview["metadata"].get("input_messages_sha256"):
            raise Hold("REVIEW_INPUT_HASH_MISMATCH")
        review.append({
            "schema": REVIEW_SCHEMA,
            "case_id": cid,
            "source_target_sha256": digest,
            "input_messages_sha256": input_sha,
            "packet_source_sha256": linked["packet_source_sha256"],
            "packet_case_locator": linked["packet_case_locator"],
            "packet_snapshot_sha256": linked["packet_snapshot_sha256"],
            "stage_file_sha256": linked["stage_file_sha256"],
            "context_provenance": NOT_ACTUAL_SENT,
            "review_source_scope": "STAGED_VISIBLE_SUFFIX_ONLY",
            "review_input_messages": source_msgs,
            "review_target_assistant": target,
            "review_questions": QUESTIONS,
            "quality_floors": FLOORS,
            "severe_flag_names": list(SEVERE),
            "review_record": {
                "semantic_decision": None,
                "reviewer_type": None,
                "reviewer_evidence_ref": None,
                "dimension_scores": None,
                "severe_flags": None,
                "source_quotes": None,
                "target_quotes": None,
                "uncertainties": None,
                "notes": None,
            },
            "gate_decisions": {gate: {
                "decision": "HOLD_UNREVIEWED",
                "evidence_ref": None,
                "review_note": None,
            } for gate in QUESTIONS},
            "owner_signed_off": False,
            "experimental_training_admitted": False,
            "quality_v1_admitted": False,
            "training_authorized": False,
        })
    return review, {
        "schema": SCHEMA,
        "status": "E03_SEMANTIC_REVIEW_PACKETS_CREATED__OWNER_EVIDENCE_HOLD",
        "source_cases_checked": len(review),
        "review_packets": len(review),
        "input_messages_revalidated": len(review),
        "packet_target_and_user_exact": len(review),
        "review_decisions_created": 0,
        "owner_e0_e3_attestations_created": 0,
        "context_provenance": NOT_ACTUAL_SENT,
        "experimental_dataset_frozen": False,
        "actual_swift_collator_run": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "database_modified": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e03-locators", required=True, type=Path)
    parser.add_argument("--experimental-preview", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        locators_raw = private_bytes(args.e03_locators, 4_000_000)
        preview_raw = private_bytes(args.experimental_preview, 30_000_000)
        locators = parse_lines(locators_raw, 3)
        previews = parse_lines(preview_raw, 3)
        output = args.output_dir
        if (not output.is_absolute() or output.is_symlink() or output.exists()
                or not output.is_relative_to(ALLOWED_BASE / "r59/private")
                or output.parent.is_symlink()
                or not output.parent.is_dir()
                or stat.S_IMODE(output.parent.stat().st_mode) != 0o700):
            raise Hold("PRIVATE_OUTPUT_INVALID")
        review, safe = prepare(locators, previews)
        safe["source_e03_file_sha256"] = hashlib.sha256(locators_raw).hexdigest()
        safe["source_preview_file_sha256"] = hashlib.sha256(preview_raw).hexdigest()
        output.mkdir(mode=0o700)
        for filename, body in (
            ("R60_E03_SEMANTIC_REVIEW_PRIVATE.jsonl",
             b"".join(canonical(row) + b"\n" for row in review)),
            ("R60_E03_SEMANTIC_REVIEW_SAFE.json", canonical(safe) + b"\n"),
        ):
            fd = os.open(output / filename, os.O_WRONLY | os.O_CREAT
                         | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "E03_SEMANTIC_REVIEW_PREPARE_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "database_modified": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

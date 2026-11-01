#!/usr/bin/env python3
"""Prepare PRIVATE six-dimension literary review tasks for Gold195 B route.

Does not perform reviews, score examples, approve cards, produce training files
or send source text to an external service. Default stdout is SAFE counts only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat

from gold195_card_gold_review import private_read, PACKET_SCHEMA
from gold195_source_review_packet import canon

RUBRIC = {
    "chinese_prose": "中文文学表达自然，有具体场景与节奏；避免重复、模板化与空洞叙述",
    "character_consistency": "人物身份、关系、行为动机和口吻符合可见上下文与来源设定",
    "npc_initiative": "NPC 有自主目标与合理剧情推进，但不强行替玩家行动",
    "player_agency": "不替玩家角色决定意愿、关键选择、台词或行动",
    "rule_fidelity": "遵守故事硬设定、明确禁令和内容安全边界",
    "narrative_continuity": "情节、人物关系、地点和时间连续，不引入未来信息",
}
FLOORS = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 3,
    "player_agency": 4,
    "rule_fidelity": 4,
    "narrative_continuity": 4,
}
SEVERE = ("serious_player_agency", "hard_fact_or_ban", "safety_exclusion")
MAX_PRIVATE_BYTES = 60 * 1024 * 1024


def check_history(messages):
    if not isinstance(messages, list):
        return False
    for index, item in enumerate(messages):
        if (not isinstance(item, dict) or set(item) != {"role", "content"}
                or item.get("role") != ("user" if index % 2 == 0 else "assistant")
                or not isinstance(item.get("content"), str)
                or not item["content"].strip()):
            return False
    return True


def prepare_row(row):
    if not isinstance(row, dict) or row.get("schema") != PACKET_SCHEMA:
        raise ValueError("source review schema mismatch")
    if row.get("candidate_status") != "PRIVATE_REVIEW_ONLY_NOT_TRAIN_READY":
        raise ValueError("source unexpectedly admitted")
    if row.get("quality_v1_admitted") is not False:
        raise ValueError("source quality status invalid")
    if not isinstance(row.get("card_snapshot"), dict) or not row["card_snapshot"]:
        raise ValueError("no source card")
    if not isinstance(row.get("story_uuid"), str) or not row["story_uuid"]:
        raise ValueError("missing world identity")
    if not isinstance(row.get("card_snapshot_sha256"), str):
        raise ValueError("missing card hash")
    # Original card source uses pretty JSON, not the canonical message hash form.
    card_bytes = json.dumps(
        row["card_snapshot"], ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8")
    if hashlib.sha256(card_bytes).hexdigest() != row["card_snapshot_sha256"]:
        raise ValueError("snapshot hash mismatch")
    target = row.get("target_assistant_text")
    current = row.get("current_user_text")
    if not isinstance(target, str) or not target.strip() or not isinstance(current, str) or not current.strip():
        raise ValueError("target/user missing")
    if hashlib.sha256(target.encode("utf-8")).hexdigest() != row.get("source_target_sha256"):
        raise ValueError("target digest changed")
    old = row.get("original_history")
    leading = row.get("source_history_starts_with_assistant")
    if leading is True:
        return None, "LEADING_ASSISTANT_CONTEXT_HOLD"
    if leading is not False or not check_history(old):
        return None, "HISTORY_INPUT_SHAPE_HOLD"
    messages = [
        {"role": "system", "content": card_bytes.decode("utf-8")},
        *old,
        {"role": "user", "content": current},
    ]
    if messages[-1]["role"] != "user":
        raise ValueError("bad current turn")
    task = {
        "schema": "r58_gold195_six_dimension_review_task_private_v1",
        "case_id": row.get("case_id"),
        "story_uuid": row["story_uuid"],
        "card_snapshot_sha256": row["card_snapshot_sha256"],
        "card_source_kind": row.get("card_source_kind"),
        "input_design_status": "PROPOSED_OFFLINE_CARD_NOT_APPROVED",
        "messages": messages,
        "target_text": target,
        "input_messages_sha256": hashlib.sha256(canon(messages)).hexdigest(),
        "target_sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
        "review_instructions": {
            "source_world_card_is_unapproved": True,
            "check_card_gold_contradictions": True,
            "score_range": [1, 5],
            "dimension_floors": FLOORS,
            "dimensions": RUBRIC,
            "severe_flags": list(SEVERE),
            "two_independent_blinded_reviews_required": True,
            "do_not_infer_missing_world_facts": True,
        },
        "review_status": "UNREVIEWED",
        "review_results": [],
        "world_component_id": None,
        "split": None,
        "quality_v1_admitted": False,
        "training_authorized": False,
    }
    return task, None


def build(path: Path, collect=False):
    if path.stat().st_size > MAX_PRIVATE_BYTES:
        raise ValueError("private input oversized")
    data = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                data.append(json.loads(line))
                if len(data) > 195:
                    raise ValueError("too many review rows")
    if len(data) != 195:
        raise ValueError("expected frozen 195 rows")
    counts = Counter()
    tasks = []
    ids = set()
    for row in data:
        identity = row.get("case_id") if isinstance(row, dict) else None
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError("missing or duplicate case ID")
        ids.add(identity)
        task, hold = prepare_row(row)
        counts["source_rows_checked"] += 1
        if hold:
            counts[hold] += 1
        else:
            counts["user_first_review_tasks_prepared"] += 1
            if collect:
                tasks.append(task)
    return {
        "schema": "r58_gold195_six_dimension_review_task_safe_v1",
        "status": "PRIVATE_LITERARY_REVIEW_TASKS_READY__NO_REVIEW_COMPLETED",
        "counts": dict(sorted(counts.items())),
        "review_tasks_written": False,
        "reviewers_completed": 0,
        "quality_v1_admitted": 0,
        "no_card_approval_assumed": True,
        "protected_test_read": False,
        "hf_job_started": False,
    }, tasks


def write_private(target: Path, repo_root: Path, tasks):
    if not target.is_absolute() or target.is_symlink() or target.exists():
        raise ValueError("new absolute output required")
    parent = target.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or repo_root.resolve() == parent.resolve()
            or repo_root.resolve() in parent.resolve().parents):
        raise ValueError("private directory required")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as output:
        for row in tasks:
            output.write(canon(row) + b"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-card-gold-review", type=Path, required=True)
    p.add_argument("--private-task-output", type=Path)
    opts = p.parse_args()
    try:
        path = opts.private_card_gold_review
        if (not path.is_absolute() or path.is_symlink() or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode) != 0o600
                or path.stat().st_nlink != 1):
            raise ValueError("unsafe private input")
        receipt, tasks = build(path, collect=bool(opts.private_task_output))
        if opts.private_task_output:
            write_private(opts.private_task_output, opts.repo_root, tasks)
            receipt["review_tasks_written"] = True
    except Exception:
        receipt = {
            "schema": "r58_gold195_six_dimension_review_task_safe_v1",
            "status": "PRIVATE_REVIEW_INPUT_OR_OUTPUT_INVALID__HOLD",
            "quality_v1_admitted": 0, "protected_test_read": False,
        }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["status"] == "PRIVATE_LITERARY_REVIEW_TASKS_READY__NO_REVIEW_COMPLETED" else 42


if __name__ == "__main__":
    raise SystemExit(main())

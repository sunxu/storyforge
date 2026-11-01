#!/usr/bin/env python3
"""Prepare 10 PRIVATE cross-world review packets from 132 frozen comparisons.

Offline metadata + review templates only. No evaluation, truncation approval,
training admission, network call, or secret text printed to stdout.
"""
from __future__ import annotations
import argparse
from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import stat

from gold195_assistant_first_diagnostic import SCHEMA as SOURCE_SCHEMA
from gold195_source_review_packet import canon
from gold195_six_dimension_review_tasks import check_history

EXPECTED_ROWS = 132
PILOT_SIZE = 10
MAX_BYTES = 90 * 1024 * 1024
SCHEMA = "r58_gold195_assistant_first_semantic_pilot_private_v1"


def read_comparisons(path):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("private source path invalid")
    st = path.stat()
    if not (stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600
            and st.st_nlink == 1 and 0 < st.st_size <= MAX_BYTES):
        raise ValueError("private source permissions or size")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        opened = os.fstat(f.fileno())
        if (opened.st_ino, opened.st_dev) != (st.st_ino, st.st_dev):
            raise ValueError("source changed during read")
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("source too large")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows) != EXPECTED_ROWS:
        raise ValueError("expected 132 comparison records")
    ids = set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("schema") != SOURCE_SCHEMA
                or not isinstance(row.get("case_id"), str) or not row["case_id"]
                or row["case_id"] in ids
                or not isinstance(row.get("story_uuid"), str) or not row["story_uuid"]
                or row.get("approved_history_transform") is not False
                or row.get("quality_v1_admitted") is not False
                or row.get("training_authorized") is not False
                or row.get("training_candidate_messages") is not None):
            raise ValueError("comparison row contract")
        ids.add(row["case_id"])
        original = row.get("original_history")
        proposed = row.get("proposed_history_if_first_assistant_removed")
        if (not isinstance(original, list) or not original
                or not isinstance(proposed, list)
                or original[0].get("role") != "assistant"
                or proposed != original[1:]
                or not check_history(proposed)
                or hashlib.sha256(canon(original)).hexdigest()
                != row.get("original_history_sha256")
                or hashlib.sha256(canon(proposed)).hexdigest()
                != row.get("proposed_history_sha256")
                or hashlib.sha256(original[0]["content"].encode()).hexdigest()
                != row.get("leading_assistant_sha256")):
            raise ValueError("history, hash, or role mismatch")
        target = row.get("frozen_target_text")
        if (not isinstance(target, str) or not target.strip()
                or hashlib.sha256(target.encode()).hexdigest()
                != row.get("source_target_sha256")):
            raise ValueError("frozen target mismatch")
        if not isinstance(row.get("source_card_snapshot"), dict):
            raise ValueError("world card source missing")
    return rows


def select(rows):
    groups = OrderedDict()
    for item in rows:
        groups.setdefault(item["story_uuid"], []).append(item)
    selected = []
    # One per distinct world before a second from the same world.
    while len(selected) < PILOT_SIZE:
        progress = False
        for group in groups.values():
            if group and len(selected) < PILOT_SIZE:
                selected.append(group.pop(0))
                progress = True
        if not progress:
            raise ValueError("insufficient cases")
    return selected


def prepare(rows):
    chosen = select(rows)
    output = []
    for i, row in enumerate(chosen, 1):
        output.append({
            "schema": SCHEMA,
            "pilot_label": "pilot%02d" % i,
            "case_id": row["case_id"],
            "story_uuid": row["story_uuid"],
            "source_target_sha256": row["source_target_sha256"],
            "original_history_sha256": row["original_history_sha256"],
            "proposed_history_sha256": row["proposed_history_sha256"],
            "leading_assistant_sha256": row["leading_assistant_sha256"],
            "first_assistant_message": row["original_history"][0]["content"],
            "original_history": row["original_history"],
            "candidate_history_after_drop": row[
                "proposed_history_if_first_assistant_removed"],
            "source_card_snapshot": row["source_card_snapshot"],
            "current_user_text": row["current_user_text"],
            "frozen_target_text": row["frozen_target_text"],
            "review_instructions": {
                "role_shape_only_never_enough": True,
                "judge_loss_of_identity_relationships": "UNREVIEWED",
                "judge_loss_of_events_chronology": "UNREVIEWED",
                "judge_loss_of_hard_rules_bans": "UNREVIEWED",
                "judge_loss_of_implicit_player_decisions": "UNREVIEWED",
                "is_lost_information_restated_later": "UNREVIEWED",
                "is_source_card_sufficient_without_future_leakage": "UNREVIEWED",
                "allowed_recommendations": [
                    "PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS",
                    "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW",
                    "HOLD_CONTEXT_UNRECOVERABLE",
                ],
            },
            "review_status": "UNREVIEWED",
            "review_evidence": [],
            "recommended_policy": "HOLD_PENDING_SEMANTIC_REVIEW",
            "world_card_approved": False,
            "approved_history_transform": False,
            "training_candidate_messages": None,
            "quality_v1_admitted": False,
            "training_authorized": False,
        })
    return {
        "schema": "r58_gold195_assistant_first_semantic_pilot_safe_v1",
        "status": "TEN_CROSS_WORLD_CONTEXT_REVIEW_TASKS_PREPARED__NO_REVIEWS",
        "source_comparisons_verified": len(rows),
        "review_tasks": len(output),
        "distinct_worlds_in_pilot": len({row["story_uuid"] for row in chosen}),
        "semantic_reviews_completed": 0,
        "new_training_samples_created": 0,
        "history_truncation_approved": False,
        "world_cards_approved": False,
        "quality_v1_admitted": 0,
        "external_review_authorized": False,
        "r50_accessed": False, "network_called": False,
        "gpu_authorized": False,
        "private_data_emitted": False,
        "private_output_written": False,
    }, output


def write_private(path, root, rows):
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("new absolute destination required")
    parent = path.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or root.resolve() == parent.resolve()
            or root.resolve() in parent.resolve().parents):
        raise ValueError("destination must be private and outside repository")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        for row in rows:
            f.write(canon(row) + b"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument("--private-comparison-input", required=True, type=Path)
    p.add_argument("--private-task-output", type=Path)
    a = p.parse_args()
    try:
        rows = read_comparisons(a.private_comparison_input)
        receipt, tasks = prepare(rows)
        if a.private_task_output:
            write_private(a.private_task_output, a.repo_root, tasks)
            receipt["private_output_written"] = True
        status = 0
    except Exception:
        receipt = {
            "schema": "r58_gold195_assistant_first_semantic_pilot_safe_v1",
            "status": "PRIVATE_COMPARISON_OR_OUTPUT_INVALID__HOLD",
            "quality_v1_admitted": 0, "r50_accessed": False,
            "network_called": False,
        }
        status = 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())

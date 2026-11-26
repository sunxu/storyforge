#!/usr/bin/env python3
"""Offline SAFE full-132 Assistant-first semantic review task exporter.

Does not modify the frozen 10-case pilot or any underlying Gold source.
No external calls, semantic judgments, training rows or admission.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from gold195_assistant_first_semantic_pilot import (
    read_comparisons, write_private, EXPECTED_ROWS,
)
from gold195_source_review_packet import canon

SCHEMA = "r58_gold195_assistant_first_full132_review_private_v1"
SAFE_SCHEMA = "r58_gold195_assistant_first_full132_review_safe_v1"


def build(rows):
    if len(rows) != EXPECTED_ROWS:
        raise ValueError("expected frozen 132 cases")
    seen = set()
    tasks = []
    for index, row in enumerate(rows, 1):
        identity = row["case_id"]
        if identity in seen:
            raise ValueError("duplicated frozen case ID")
        seen.add(identity)
        history = row["original_history"]
        candidate = row["proposed_history_if_first_assistant_removed"]
        # read_comparisons already checked source digests and exact history.
        tasks.append({
            "schema": SCHEMA,
            "review_label": "full%03d" % index,
            "case_id": identity,
            "story_uuid": row["story_uuid"],
            "source_target_sha256": row["source_target_sha256"],
            "original_history_sha256": row["original_history_sha256"],
            "proposed_history_sha256": row["proposed_history_sha256"],
            "leading_assistant_sha256": row["leading_assistant_sha256"],
            "original_history": history,
            "candidate_history_after_drop": candidate,
            "first_assistant_message": history[0]["content"],
            "source_card_snapshot": row["source_card_snapshot"],
            "current_user_text": row["current_user_text"],
            "frozen_target_text": row["frozen_target_text"],
            "review_questions": {
                "lost_identity_or_relationship": "UNREVIEWED",
                "lost_events_or_chronology": "UNREVIEWED",
                "lost_hard_rules_or_bans": "UNREVIEWED",
                "lost_player_agency_context": "UNREVIEWED",
                "essential_facts_reestablished_later": "UNREVIEWED",
                "source_card_sufficient_without_future_leakage": "UNREVIEWED",
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
    if len(tasks) != 132:
        raise ValueError("incomplete task export")
    counts = Counter(x["story_uuid"] for x in tasks)
    return {
        "schema": SAFE_SCHEMA,
        "status": "FULL132_CONTEXT_REVIEW_TASKS_EXPORTED__UNREVIEWED",
        "source_comparisons_verified": 132,
        "review_tasks": len(tasks),
        "distinct_worlds": len(counts),
        "semantic_reviews_completed": 0,
        "history_truncation_approved": False,
        "quality_v1_admitted": 0,
        "new_training_samples_created": 0,
        "external_review_authorized": False,
        "network_called": False,
        "r50_accessed": False,
        "gpu_authorized": False,
        "private_data_emitted": False,
        "private_output_written": False,
        "existing_pilot10_modified": False,
    }, tasks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument("--private-comparison-input", required=True, type=Path)
    p.add_argument("--private-task-output", type=Path)
    args = p.parse_args()
    try:
        receipt, rows = build(read_comparisons(args.private_comparison_input))
        if args.private_task_output is not None:
            write_private(args.private_task_output, args.repo_root, rows)
            receipt["private_output_written"] = True
        status = 0
    except Exception:
        receipt = {
            "schema": SAFE_SCHEMA,
            "status": "FULL132_PRIVATE_SOURCE_OR_OUTPUT_INVALID__HOLD",
            "quality_v1_admitted": 0,
            "network_called": False, "r50_accessed": False,
        }
        status = 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())

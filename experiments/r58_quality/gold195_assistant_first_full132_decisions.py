#!/usr/bin/env python3
"""Offline 132-case semantic decision templates / guarded validation.

All checks are structural and evidence-substring only, not independent literary
fact checking. Original source comparisons and 10-case pilot remain unchanged.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

from gold195_assistant_first_semantic_pilot import read_comparisons
from gold195_assistant_first_full132 import build, SCHEMA as TASK_SCHEMA
from gold195_assistant_first_semantic_decisions import (
    read_jsonl, write_new, QUESTIONS, POLICIES, JUDGMENTS,
)
from gold195_source_review_packet import canon

SCHEMA = "r58_gold195_assistant_first_full132_decision_private_v1"
SAFE_SCHEMA = "r58_gold195_assistant_first_full132_decision_safe_v1"


def verify(tasks, comparisons):
    if len(tasks) != 132 or len(comparisons) != 132:
        raise ValueError("wrong source length")
    _, expected = build(comparisons)
    for index, (task, ref) in enumerate(zip(tasks, expected), 1):
        if (not isinstance(task, dict) or task.get("schema") != TASK_SCHEMA
                or task.get("review_label") != "full%03d" % index
                or canon(task) != canon(ref)):
            raise ValueError("unapproved modification of source task")


def blank(task):
    return {
        "schema": SCHEMA,
        "review_label": task["review_label"],
        "source_target_sha256": task["source_target_sha256"],
        "original_history_sha256": task["original_history_sha256"],
        "proposed_history_sha256": task["proposed_history_sha256"],
        "reviewer_label": "",
        "policy": "UNREVIEWED",
        "judgments": {q: "UNCERTAIN" for q in QUESTIONS},
        "gold_exact_quotes": [],
        "leading_assistant_exact_quotes": [],
        "reasoning": "",
        "uncertainty": "",
        "review_completed": False,
        "world_card_approved": False,
        "history_truncation_approved": False,
        "quality_v1_admitted": False,
        "training_authorized": False,
    }


def evaluate(tasks, decisions):
    if len(tasks) != 132 or len(decisions) != 132:
        raise ValueError("wrong decision count")
    counts = Counter()
    for index, (task, decision) in enumerate(zip(tasks, decisions), 1):
        expected = blank(task)
        if (not isinstance(decision, dict) or set(decision) != set(expected)
                or any(decision[k] != expected[k] for k in (
                    "schema", "review_label", "source_target_sha256",
                    "original_history_sha256", "proposed_history_sha256",
                    "world_card_approved", "history_truncation_approved",
                    "quality_v1_admitted", "training_authorized",
                ))):
            raise ValueError("source binding or immutable gate modified")
        if (decision["policy"] not in POLICIES
                or type(decision["review_completed"]) is not bool
                or not isinstance(decision["judgments"], dict)
                or set(decision["judgments"]) != set(QUESTIONS)
                or any(x not in JUDGMENTS for x in decision["judgments"].values())):
            raise ValueError("invalid review state")
        if decision["policy"] == "UNREVIEWED":
            if decision["review_completed"]:
                raise ValueError("unreviewed row cannot be completed")
            counts["UNREVIEWED"] += 1
            continue
        if (not decision["review_completed"]
                or not isinstance(decision["reviewer_label"], str)
                or not decision["reviewer_label"].strip()
                or not isinstance(decision["reasoning"], str)
                or len(decision["reasoning"].strip()) < 30
                or not isinstance(decision["uncertainty"], str)):
            raise ValueError("reviewer attribution and reasoning required")
        for field, source in (
            ("gold_exact_quotes", task["frozen_target_text"]),
            ("leading_assistant_exact_quotes", task["first_assistant_message"]),
        ):
            quotes = decision[field]
            if (not isinstance(quotes, list) or len(quotes) > 12
                    or any(not isinstance(x, str) or not x.strip()
                           or len(x) > 120 or x not in source for x in quotes)):
                raise ValueError("quote does not match frozen text")
        if not decision["leading_assistant_exact_quotes"]:
            raise ValueError("missing explicit opening Assistant evidence")
        if decision["policy"] == "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW":
            if (any(decision["judgments"][q] != "NO" for q in QUESTIONS[:4])
                    or decision["judgments"]["essential_facts_reestablished_later"] != "YES"
                    or decision["judgments"]["source_card_sufficient_without_future_leakage"] != "YES"):
                raise ValueError("drop proposed without affirmative fact review")
        counts[decision["policy"]] += 1
    return {
        "schema": SAFE_SCHEMA,
        "status": "FULL132_SEMANTIC_DECISIONS_STRUCTURALLY_VALID__NO_ADMISSION",
        "source_cases_verified": 132,
        "review_states": dict(sorted(counts.items())),
        "reviewed_cases": 132 - counts["UNREVIEWED"],
        "unreviewed_cases": counts["UNREVIEWED"],
        "history_truncation_approved": False,
        "world_cards_approved": False,
        "quality_v1_admitted": 0,
        "training_samples_created": 0,
        "network_called": False,
        "external_review_authorized": False,
        "r50_accessed": False, "gpu_authorized": False,
        "private_text_or_case_ids_emitted": False,
        "pilot10_originals_modified": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument("--private-comparison-input", required=True, type=Path)
    p.add_argument("--private-full-tasks", required=True, type=Path)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--private-blank-decisions-output", type=Path)
    group.add_argument("--private-filled-decisions-input", type=Path)
    args = p.parse_args()
    try:
        comparisons = read_comparisons(args.private_comparison_input)
        tasks = read_jsonl(args.private_full_tasks, 132)
        verify(tasks, comparisons)
        if args.private_blank_decisions_output:
            decisions = [blank(task) for task in tasks]
            write_new(args.private_blank_decisions_output, args.repo_root, decisions)
            report = evaluate(tasks, decisions)
            report["status"] = "FULL132_SEMANTIC_DECISION_TEMPLATES_READY__UNREVIEWED"
            report["private_decision_file_written"] = True
        else:
            decisions = read_jsonl(args.private_filled_decisions_input, 132)
            report = evaluate(tasks, decisions)
            report["private_decision_file_written"] = False
        code = 0
    except Exception:
        report = {
            "schema": SAFE_SCHEMA,
            "status": "FULL132_DECISION_SOURCE_OR_CONTENT_INVALID__HOLD",
            "quality_v1_admitted": 0,
            "network_called": False, "r50_accessed": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate and validate local 10-case Assistant-first semantic decisions.

No model calls. Never modifies frozen task packets or approves training.
Each result is bound to a source hash; semantic assertions require real review.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat

from gold195_assistant_first_semantic_pilot import SCHEMA as TASK_SCHEMA
from gold195_source_review_packet import canon

SCHEMA = "r58_gold195_assistant_first_semantic_decision_private_v1"
MAX_BYTES = 90 * 1024 * 1024
POLICIES = (
    "UNREVIEWED",
    "PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS",
    "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW",
    "HOLD_CONTEXT_UNRECOVERABLE",
)
QUESTIONS = (
    "lost_identity_or_relationship",
    "lost_events_or_chronology",
    "lost_hard_rules_or_bans",
    "lost_player_agency_context",
    "essential_facts_reestablished_later",
    "source_card_sufficient_without_future_leakage",
)
JUDGMENTS = ("YES", "NO", "UNCERTAIN")


def read_jsonl(path, expected):
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()):
        raise ValueError("invalid private path")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= MAX_BYTES):
        raise ValueError("unsafe private file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_ino, opened.st_dev) != (st.st_ino, st.st_dev):
            raise ValueError("file changed while reading")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("oversize data")
    rows = [json.loads(x) for x in raw.splitlines() if x.strip()]
    if len(rows) != expected or any(not isinstance(x, dict) for x in rows):
        raise ValueError("unexpected row count")
    return rows


def verified_tasks(rows):
    if len(rows) != 10:
        raise ValueError("expected ten cases")
    worlds, labels = set(), set()
    for index, row in enumerate(rows, 1):
        label = "pilot%02d" % index
        if (row.get("schema") != TASK_SCHEMA
                or row.get("pilot_label") != label
                or label in labels
                or not isinstance(row.get("story_uuid"), str)
                or not row["story_uuid"]
                or row.get("review_status") != "UNREVIEWED"
                or row.get("recommended_policy") != "HOLD_PENDING_SEMANTIC_REVIEW"
                or row.get("approved_history_transform") is not False
                or row.get("quality_v1_admitted") is not False
                or row.get("training_candidate_messages") is not None
                or row.get("training_authorized") is not False):
            raise ValueError("task contract changed")
        worlds.add(row["story_uuid"])
        labels.add(label)
        original = row.get("original_history")
        proposed = row.get("candidate_history_after_drop")
        if (not isinstance(original, list) or not original
                or not isinstance(proposed, list) or proposed != original[1:]
                or hashlib.sha256(canon(original)).hexdigest()
                != row.get("original_history_sha256")
                or hashlib.sha256(canon(proposed)).hexdigest()
                != row.get("proposed_history_sha256")
                or original[0]["content"] != row.get("first_assistant_message")
                or hashlib.sha256(original[0]["content"].encode()).hexdigest()
                != row.get("leading_assistant_sha256")
                or hashlib.sha256(row["frozen_target_text"].encode()).hexdigest()
                != row.get("source_target_sha256")):
            raise ValueError("task history or frozen target altered")
    if len(worlds) != 10:
        raise ValueError("pilot must cover ten distinct worlds")


def blank(task):
    return {
        "schema": SCHEMA,
        "pilot_label": task["pilot_label"],
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
    verified_tasks(tasks)
    counts = Counter()
    for task, row in zip(tasks, decisions):
        if not isinstance(row, dict):
            raise ValueError("decision object missing")
        template = blank(task)
        if (set(row) != set(template)
                or any(row.get(k) != template[k] for k in (
                    "schema", "pilot_label", "source_target_sha256",
                    "original_history_sha256", "proposed_history_sha256",
                    "world_card_approved", "history_truncation_approved",
                    "quality_v1_admitted", "training_authorized"
                ))):
            raise ValueError("decision source or safety fields altered")
        policy = row.get("policy")
        if policy not in POLICIES or row.get("review_completed") not in (True, False):
            raise ValueError("invalid status")
        if (not isinstance(row.get("judgments"), dict)
                or set(row["judgments"]) != set(QUESTIONS)
                or any(v not in JUDGMENTS for v in row["judgments"].values())):
            raise ValueError("invalid semantic judgments")
        if policy == "UNREVIEWED":
            if row["review_completed"] is not False:
                raise ValueError("unreviewed marked done")
            counts["unreviewed"] += 1
            continue
        if (row["review_completed"] is not True
                or not isinstance(row.get("reviewer_label"), str)
                or not row["reviewer_label"].strip()
                or not isinstance(row.get("reasoning"), str)
                or len(row["reasoning"].strip()) < 30
                or not isinstance(row.get("uncertainty"), str)):
            raise ValueError("review lacks attribution or explanation")
        for field, text in (
            ("gold_exact_quotes", task["frozen_target_text"]),
            ("leading_assistant_exact_quotes", task["first_assistant_message"]),
        ):
            quotes = row.get(field)
            if (not isinstance(quotes, list) or len(quotes) > 12
                    or any(not isinstance(q, str) or not q.strip()
                           or len(q) > 120 or q not in text for q in quotes)):
                raise ValueError("quote not verbatim in source")
        if not row["leading_assistant_exact_quotes"]:
            raise ValueError("review must reference leading Assistant")
        if policy == "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW":
            if (any(row["judgments"][q] != "NO" for q in QUESTIONS[:4])
                    or row["judgments"]["essential_facts_reestablished_later"] != "YES"
                    or row["judgments"]["source_card_sufficient_without_future_leakage"]
                    != "YES"):
                raise ValueError("cannot consider drop with unresolved loss risks")
        counts[policy] += 1
    return {
        "schema": "r58_gold195_assistant_first_semantic_decision_safe_v1",
        "status": "PILOT10_SEMANTIC_DECISIONS_VALIDATED__NO_ADMISSION",
        "source_cases_verified": len(tasks),
        "review_states": dict(sorted(counts.items())),
        "reviewed_cases": len(tasks) - counts["unreviewed"],
        "new_training_samples_created": 0,
        "history_truncation_approved": False,
        "world_card_approved": False,
        "quality_v1_admitted": 0,
        "external_model_called": False, "r50_accessed": False,
        "gpu_authorized": False,
        "private_text_or_case_ids_emitted": False,
    }


def write_new(path, root, rows):
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("new absolute output required")
    parent = path.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or root.resolve() == parent.resolve()
            or root.resolve() in parent.resolve().parents):
        raise ValueError("unsafe private destination")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        for row in rows:
            stream.write(canon(row) + b"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-pilot-tasks", type=Path, required=True)
    choices = p.add_mutually_exclusive_group(required=True)
    choices.add_argument("--private-blank-decisions-output", type=Path)
    choices.add_argument("--private-filled-decisions-input", type=Path)
    args = p.parse_args()
    try:
        tasks = read_jsonl(args.private_pilot_tasks, 10)
        verified_tasks(tasks)
        if args.private_blank_decisions_output:
            write_new(args.private_blank_decisions_output, args.repo_root,
                      [blank(t) for t in tasks])
            report = evaluate(tasks, [blank(t) for t in tasks])
            report["status"] = "TEN_SEMANTIC_DECISION_TEMPLATES_READY__UNREVIEWED"
            report["private_decision_file_written"] = True
        else:
            decisions = read_jsonl(args.private_filled_decisions_input, 10)
            report = evaluate(tasks, decisions)
            report["private_decision_file_written"] = False
        code = 0
    except Exception:
        report = {
            "schema": "r58_gold195_assistant_first_semantic_decision_safe_v1",
            "status": "PRIVATE_SEMANTIC_DECISIONS_INVALID__HOLD",
            "quality_v1_admitted": 0,
            "r50_accessed": False, "external_model_called": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

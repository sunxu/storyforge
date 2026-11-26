#!/usr/bin/env python3
"""R58 offline diagnostic for 132 Assistant-first Gold195 histories.

Produces optional PRIVATE comparison records only. A suggested drop of the
first assistant message is NEVER approved for training or review automatically.
No text, UUIDs, case IDs or hashes emitted to stdout.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat

from gold195_card_gold_review import PACKET_SCHEMA
from gold195_source_review_packet import canon
from gold195_six_dimension_review_tasks import check_history

ROW_COUNT = 195
EXPECTED_LEADING = 132
MAX_BYTES = 90 * 1024 * 1024
SCHEMA = "r58_gold195_assistant_first_context_diagnostic_private_v1"


def verified_rows(path: Path):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("private input required")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= MAX_BYTES):
        raise ValueError("input permission/size mismatch")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        opened = os.fstat(f.fileno())
        if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
            raise ValueError("source changed")
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("input exceeds bound")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows) != ROW_COUNT:
        raise ValueError("not frozen Gold195")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("schema") != PACKET_SCHEMA
                or row.get("quality_v1_admitted") is not False
                or row.get("candidate_status") != "PRIVATE_REVIEW_ONLY_NOT_TRAIN_READY"
                or not isinstance(row.get("case_id"), str)
                or not row["case_id"] or row["case_id"] in seen):
            raise ValueError("invalid case/source contract")
        seen.add(row["case_id"])
        t = row.get("target_assistant_text")
        if (not isinstance(t, str) or not t.strip()
                or hashlib.sha256(t.encode()).hexdigest()
                != row.get("source_target_sha256")):
            raise ValueError("frozen target mutation")
    return rows


def analyze(rows, collect=False):
    counts, private = Counter(), []
    for row in rows:
        counts["source_rows_checked"] += 1
        history = row.get("original_history")
        leading = row.get("source_history_starts_with_assistant")
        target = row["target_assistant_text"]
        current = row.get("current_user_text")
        if (not isinstance(history, list) or not isinstance(current, str)
                or not current.strip() or not isinstance(target, str)):
            raise ValueError("source context invalid")
        if leading is False:
            if not check_history(history):
                raise ValueError("non-leading history invalid")
            counts["user_first_unchanged"] += 1
            continue
        if leading is not True or not history or history[0].get("role") != "assistant":
            raise ValueError("leading marker mismatch")
        if any(
            not isinstance(m, dict) or set(m) != {"role", "content"}
            or m["role"] != ("assistant" if i % 2 == 0 else "user")
            or not isinstance(m["content"], str) or not m["content"].strip()
            for i, m in enumerate(history)
        ):
            raise ValueError("leading history role/content invalid")
        if len(history) % 2 != 1:
            raise ValueError("leading role parity mismatch")
        # This is a proposed review-only alternative, not an automatic fix.
        alternative = history[1:]
        if not check_history(alternative):
            raise ValueError("candidate view not user-first")
        counts["assistant_first_hold"] += 1
        counts["drop_first_assistant_shape_valid_only"] += 1
        if len(history) == 1:
            counts["would_leave_zero_earlier_history"] += 1
        else:
            counts["would_preserve_other_history"] += 1
        if collect:
            private.append({
                "schema": SCHEMA,
                "case_id": row["case_id"],
                "story_uuid": row.get("story_uuid"),
                "corpus": row.get("corpus"),
                "card_snapshot_sha256": row.get("card_snapshot_sha256"),
                "source_target_sha256": row["source_target_sha256"],
                "original_history_sha256": hashlib.sha256(canon(history)).hexdigest(),
                "proposed_history_sha256": hashlib.sha256(canon(alternative)).hexdigest(),
                "leading_assistant_sha256": hashlib.sha256(
                    history[0]["content"].encode("utf-8")).hexdigest(),
                "original_history": history,
                "proposed_history_if_first_assistant_removed": alternative,
                "current_user_text": current,
                "frozen_target_text": target,
                "source_card_snapshot": row.get("card_snapshot"),
                "review_questions": {
                    "does_leading_assistant_introduce_required_facts": "UNREVIEWED",
                    "does_later_history_explicitly_reestablish_those_facts": "UNREVIEWED",
                    "would_removal_break_character_or_plot_continuity": "UNREVIEWED",
                    "would_removal_change_rules_or_safety_context": "UNREVIEWED",
                    "is_a_new_offline_card_semantically_sufficient": "UNREVIEWED",
                },
                "proposal_status": "DROP_LEADING_ASSISTANT_FOR_HUMAN_OR_AI_REVIEW_ONLY",
                "training_candidate_messages": None,
                "approved_history_transform": False,
                "world_card_approved": False,
                "quality_v1_admitted": False,
                "training_authorized": False,
            })
    if (counts["source_rows_checked"] != ROW_COUNT
            or counts["assistant_first_hold"] != EXPECTED_LEADING
            or counts["user_first_unchanged"] != ROW_COUNT - EXPECTED_LEADING):
        raise ValueError("frozen leading role distribution mismatch")
    receipt = {
        "schema": "r58_gold195_assistant_first_context_diagnostic_safe_v1",
        "status": "ASSISTANT_FIRST_132_SHAPE_DIAGNOSED__SEMANTIC_HOLD",
        "counts": dict(sorted(counts.items())),
        "private_comparison_written": False,
        "historical_assistant_removed_from_frozen_source": False,
        "proposed_truncation_semantically_approved": False,
        "system_world_card_approved": False,
        "quality_v1_admitted": 0,
        "new_training_samples_created": 0,
        "new_user_turns_invented": 0,
        "protected_r50_accessed": False,
        "gpu_authorized": False, "hf_job_started": False,
        "network_called": False,
        "story_text_or_identifiers_emitted": False,
    }
    return receipt, private


def write_private(path: Path, root: Path, rows):
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("output must be a new absolute file")
    parent = path.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or root.resolve() == parent.resolve()
            or root.resolve() in parent.resolve().parents):
        raise ValueError("unsafe private destination")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        for row in rows:
            f.write(canon(row) + b"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-card-gold-review", type=Path, required=True)
    p.add_argument("--private-comparison-output", type=Path)
    a = p.parse_args()
    try:
        rows = verified_rows(a.private_card_gold_review)
        receipt, comparisons = analyze(rows, collect=bool(a.private_comparison_output))
        if a.private_comparison_output:
            write_private(a.private_comparison_output, a.repo_root, comparisons)
            receipt["private_comparison_written"] = True
        code = 0
    except Exception:
        receipt = {
            "schema": "r58_gold195_assistant_first_context_diagnostic_safe_v1",
            "status": "PRIVATE_GOLD195_INPUT_OR_OUTPUT_INVALID__HOLD",
            "quality_v1_admitted": 0, "protected_r50_accessed": False,
            "network_called": False,
        }
        code = 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

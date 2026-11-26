#!/usr/bin/env python3
"""R58 HF private batch review: local packaging, fail-closed auditing.

NO upload, HF job start, paid compute or model inference in this module.
The original 132 tasks are read-only; all output stays outside the Git checkout.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat

from gold195_assistant_first_semantic_pilot import read_comparisons
from gold195_assistant_first_full132_decisions import verify
from gold195_assistant_first_semantic_decisions import read_jsonl
from gold195_source_review_packet import canon

SCHEMA = "r58_hf_semantic_review_input_private_v1"
RESPONSE_SCHEMA = "r58_hf_semantic_review_response_private_v1"
SAFE_SCHEMA = "r58_hf_semantic_review_safe_v1"
QUESTIONS = (
    "lost_identity_or_relationship", "lost_events_or_chronology",
    "lost_hard_rules_or_bans", "lost_player_agency_context",
    "essential_facts_reestablished_later",
    "source_card_sufficient_without_future_leakage",
)
POLICIES = (
    "PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS",
    "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW",
    "HOLD_CONTEXT_UNRECOVERABLE",
)
MAX_BYTES = 120 * 1024 * 1024


def locked_read(path, maximum=MAX_BYTES):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("private absolute input required")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= maximum):
        raise ValueError("file mode or size invalid")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        opened = os.fstat(f.fileno())
        if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
            raise ValueError("input inode changed")
        raw = f.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("oversize source")
    return raw


def safe_folder(folder, repo, create=False):
    if not folder.is_absolute() or folder.is_symlink():
        raise ValueError("private absolute folder required")
    if repo.resolve() == folder.resolve() or repo.resolve() in folder.resolve().parents:
        raise ValueError("output inside repository")
    if create:
        if folder.exists():
            raise ValueError("output exists")
        parent = folder.parent
        if (not parent.is_dir() or parent.is_symlink()
                or stat.S_IMODE(parent.stat().st_mode) & 0o077):
            raise ValueError("unsafe parent")
        folder.mkdir(mode=0o700)
    if not folder.is_dir() or stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("unsafe output folder")


def write_new(path, payload):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(payload)


def input_record(row):
    return {
        "schema": SCHEMA,
        "review_label": row["review_label"],
        "source_target_sha256": row["source_target_sha256"],
        "original_history_sha256": row["original_history_sha256"],
        "proposed_history_sha256": row["proposed_history_sha256"],
        "leading_assistant_sha256": row["leading_assistant_sha256"],
        "original_history": row["original_history"],
        "candidate_history_after_drop": row["candidate_history_after_drop"],
        "current_user_text": row["current_user_text"],
        "frozen_target_text": row["frozen_target_text"],
        "source_card_snapshot": row["source_card_snapshot"],
        "training_authorized": False,
    }


def make_package(tasks, folder, repo):
    if len(tasks) != 132:
        raise ValueError("expected 132")
    safe_folder(folder, repo, create=True)
    payload = [input_record(t) for t in tasks]
    # Per-row content hashes allow fail-closed resume without exposing case IDs.
    digest = [hashlib.sha256(canon(r)).hexdigest() for r in payload]
    manifest = {
        "schema": "r58_hf_semantic_review_manifest_private_v1",
        "row_count": 132,
        "input_sha256": hashlib.sha256(
            b"".join(canon(r) + b"\n" for r in payload)).hexdigest(),
        "row_sha256": digest,
        "model_revision": "UNSET_REQUIRES_EXPLICIT_PIN",
        "approved_to_train": False,
    }
    write_new(folder / "input132.private.jsonl",
              b"".join(canon(r) + b"\n" for r in payload))
    write_new(folder / "manifest.private.json", canon(manifest))
    return {
        "schema": SAFE_SCHEMA, "status": "HF_PRIVATE_INPUT132_PREPARED__NOT_UPLOADED",
        "source_rows_verified": 132, "private_output_written": True,
        "hf_upload_performed": False, "hf_job_started": False,
        "gpu_authorized": False, "model_revision_pinned": False,
        "quality_v1_admitted": 0, "r50_accessed": False,
        "private_text_or_hashes_emitted": False,
    }


def check_output(obj, source):
    if not isinstance(obj, dict) or set(obj) != {
        "schema", "review_label", "source_row_sha256", "model_id",
        "model_revision", "policy", "judgments", "leading_assistant_exact_quotes",
        "later_history_exact_quotes", "gold_exact_quotes", "reasoning",
        "uncertainty", "inference_status",
    }:
        return "MALFORMED"
    if (obj["schema"] != RESPONSE_SCHEMA
            or obj["review_label"] != source["review_label"]
            or obj["source_row_sha256"] != hashlib.sha256(canon(source)).hexdigest()):
        return "SOURCE_BINDING_INVALID"
    if (not isinstance(obj["model_id"], str) or not obj["model_id"]
            or not isinstance(obj["model_revision"], str)
            or len(obj["model_revision"]) != 40
            or any(c not in "0123456789abcdef" for c in obj["model_revision"])):
        return "MODEL_NOT_PINNED"
    if obj["inference_status"] != "COMPLETE":
        return "INFERENCE_FAILED_HOLD"
    if obj["policy"] not in POLICIES:
        return "INVALID_POLICY"
    judgments = obj["judgments"]
    if (not isinstance(judgments, dict) or set(judgments) != set(QUESTIONS)
            or any(v not in ("YES", "NO", "UNCERTAIN") for v in judgments.values())):
        return "INVALID_JUDGMENTS"
    later = "\n".join(x["content"] for x in source["candidate_history_after_drop"])
    for key, text in (
        ("leading_assistant_exact_quotes", source["original_history"][0]["content"]),
        ("later_history_exact_quotes", later),
        ("gold_exact_quotes", source["frozen_target_text"]),
    ):
        quoted = obj[key]
        if (not isinstance(quoted, list) or len(quoted) > 12
                or any(not isinstance(q, str) or not q.strip()
                       or len(q) > 120 or q not in text for q in quoted)):
            return "EVIDENCE_QUOTE_INVALID"
    if (not obj["leading_assistant_exact_quotes"]
            or not isinstance(obj["reasoning"], str)
            or not 30 <= len(obj["reasoning"].strip()) <= 4000
            or not isinstance(obj["uncertainty"], str)):
        return "REASONING_OR_EVIDENCE_MISSING"
    if obj["policy"] == "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW":
        if (any(judgments[k] != "NO" for k in QUESTIONS[:4])
                or any(judgments[k] != "YES" for k in QUESTIONS[4:])
                or not obj["later_history_exact_quotes"]):
            return "UNSUPPORTED_DROP_HOLD"
        return "PROVISIONAL_DROP_NOT_APPROVED"
    if obj["policy"] == "PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS":
        return "PRESERVE_RECOMMENDATION"
    return "SEMANTIC_HOLD"


def audit(private_input, results_dir, calibration_only=False):
    rows = [json.loads(x) for x in locked_read(private_input).splitlines() if x.strip()]
    if len(rows) != 132 or any(x.get("schema") != SCHEMA for x in rows):
        raise ValueError("private batch input invalid")
    # No need to read or emit complete result content to stdout.
    if not results_dir.is_absolute() or results_dir.is_symlink():
        raise ValueError("private result directory invalid")
    counts = Counter()
    expected = rows[:10] if calibration_only else rows
    for source in expected:
        p = results_dir / (source["review_label"] + ".json")
        if not p.exists():
            counts["MISSING_RESPONSE"] += 1
            continue
        try:
            obj = json.loads(locked_read(p, 128 * 1024))
            state = check_output(obj, source)
        except Exception:
            state = "INVALID_RESPONSE"
        counts[state] += 1
    pass_states = {"PROVISIONAL_DROP_NOT_APPROVED", "PRESERVE_RECOMMENDATION"}
    complete_and_reviewable = set(counts).issubset(pass_states) and sum(counts.values()) == len(expected)
    return {
        "schema": SAFE_SCHEMA,
        "status": ("REVIEW_EVIDENCE_COMPLETE__OWNER_QUALITY_GATE" if complete_and_reviewable
                   else "REVIEW_RESULTS_INCOMPLETE_OR_UNCERTAIN__HOLD"),
        "cases_expected": len(expected), "review_state_counts": dict(sorted(counts.items())),
        "model_quality_independently_proven": False,
        "owner_review_required": True,
        "automatic_training_admission": False,
        "history_truncation_approved": False,
        "quality_v1_admitted": 0,
        "r50_accessed": False,
        "private_text_or_identifiers_emitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True, type=Path)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-dir", type=Path)
    mode.add_argument("--audit-results-dir", type=Path)
    p.add_argument("--private-comparison-input", type=Path)
    p.add_argument("--private-full-tasks", type=Path)
    p.add_argument("--private-input-jsonl", type=Path)
    p.add_argument("--calibration-only", action="store_true")
    a = p.parse_args()
    try:
        if a.prepare_dir:
            if not a.private_comparison_input or not a.private_full_tasks:
                raise ValueError("missing sources")
            source = read_comparisons(a.private_comparison_input)
            tasks = read_jsonl(a.private_full_tasks, 132)
            verify(tasks, source)
            report = make_package(tasks, a.prepare_dir, a.repo_root)
        else:
            if not a.private_input_jsonl:
                raise ValueError("missing input")
            report = audit(a.private_input_jsonl, a.audit_results_dir, a.calibration_only)
        code = 0
    except Exception:
        report = {
            "schema": SAFE_SCHEMA, "status": "HF_PRIVATE_SOURCE_OR_OUTPUT_INVALID__HOLD",
            "quality_v1_admitted": 0, "hf_job_started": False,
            "r50_accessed": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

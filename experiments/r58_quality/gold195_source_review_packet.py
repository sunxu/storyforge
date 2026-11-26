#!/usr/bin/env python3
"""Gold195: source-faithful review packet, never a train-ready dataset.

SAFE summary by default. Optional PRIVATE local review JSONL is never Git/CI output.
No invented System prompt, no silent deletion of leading Assistant context.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import stat

ROOTS = (
    ("gold87", "evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl", 87),
    ("gold108", "evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl", 108),
)
INDEX = "evaluations/v0.2/gold-quality-108/gold_108_index.csv"
SCHEMA = "r58_gold195_source_faithful_review_packet_v1"
FALLBACK108 = ("evaluations/v0.2/admission-audit-20261013/"
               "r02-point-in-time-cards/candidate_card_version_evidence_108.csv")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canon(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def index108(root: Path) -> dict:
    path = root / INDEX
    if path.is_symlink() or not path.is_file():
        raise ValueError("unavailable index")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"candidate_id", "target_sha256", "story_id"}.issubset(reader.fieldnames or ()):
            raise ValueError("index contract")
        rows = list(reader)
    lookup = {x["candidate_id"]: x for x in rows}
    if len(rows) != 108 or len(lookup) != 108 or "" in lookup:
        raise ValueError("index cardinality")
    # A distinct frozen R02 audit contains source_story_id fallback evidence.
    # Resolve an empty index story_id only when candidate ID and target SHA match.
    fallback = root / FALLBACK108
    if fallback.is_file() and not fallback.is_symlink():
        with fallback.open(encoding="utf-8-sig", newline="") as stream:
            evidence = list(csv.DictReader(stream))
        if len(evidence) != 108:
            raise ValueError("fallback coverage mismatch")
        verified = set()
        for item in evidence:
            key = item.get("candidate_id")
            if not key or key in verified or key not in lookup:
                raise ValueError("fallback identity mismatch")
            verified.add(key)
            original = lookup[key]
            if item.get("target_sha256") != original["target_sha256"]:
                raise ValueError("fallback target mismatch")
            alternate = item.get("story_id")
            primary = original.get("story_id")
            if primary and alternate and primary != alternate:
                raise ValueError("conflicting source story UUID")
            if not primary and alternate:
                original["story_id"] = alternate
                original["story_id_resolution"] = "R02_SOURCE_BOUND_FALLBACK"
    return lookup


def normalize_record(row: dict, cohort: str, index: dict) -> tuple[dict, tuple[str, ...]]:
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
        raise ValueError("bad source record")
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        raise ValueError("bad metadata")
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError("bad messages")
    if any(
        not isinstance(m, dict) or set(m) != {"role", "content"}
        or m["role"] not in {"system", "user", "assistant"}
        or not isinstance(m["content"], str) or not m["content"].strip()
        for m in messages
    ):
        raise ValueError("bad message object")
    roles = [m["role"] for m in messages]
    if roles[-2:] != ["user", "assistant"] or any(
        roles[i] == roles[i - 1] for i in range(1, len(roles))
    ):
        raise ValueError("history role contract")
    if any(role == "system" for role in roles[1:]):
        raise ValueError("system inside history")
    if cohort == "gold87":
        expected = meta.get("target_sha256_utf8")
        story = meta.get("story_id")
        review = "historic_gold87_owner_double_accept"
    else:
        entry = index.get(row["id"])
        if entry is None:
            raise ValueError("108 index missing")
        expected = entry["target_sha256"]
        story = entry.get("story_id")
        review = "historic_gold108_owner_double_accept"
    target = messages[-1]["content"]
    actual = sha(target.encode("utf-8"))
    if actual != expected:
        raise ValueError("frozen target digest mismatch")
    # Never remove the first historical Assistant without exposing the gap.
    leading = roles[0] == "assistant"
    holds = ["SYSTEM_CARD_NOT_SOURCE_BOUND", "WORLD_COMPONENT_NOT_REVIEWED",
             "NEW_SIX_DIMENSION_REVIEW_REQUIRED", "TOKEN_AND_MASK_UNVERIFIED",
             "PROTECTED_WORLD_ISOLATION_UNVERIFIED"]
    if leading:
        holds.append("LEADING_ASSISTANT_CONTEXT_UNRESOLVED")
    if not isinstance(story, str) or not story.strip():
        holds.append("STORY_UUID_MISSING")
    packet = {
        "schema": SCHEMA, "case_id": row["id"], "corpus": cohort,
        "legacy_review_source": review, "legacy_review_is_new_quality_v1": False,
        "source_record_sha256": sha(canon(row)),
        "target_sha256": actual,
        "story_uuid": story if isinstance(story, str) and story.strip() else None,
        "world_component_id": None, "split": None,
        # Source-faithful: keep all messages, including orphan Assistant and Gold target.
        "frozen_messages": messages,
        "current_user_text": messages[-2]["content"],
        "target_assistant_text": target,
        "historical_context": messages[:-2],
        "system_source": "UNRESOLVED",
        "quality_v1_status": "HOLD",
        "hold_reasons": holds,
        "training_admitted": False,
    }
    return packet, tuple(holds)


def assemble(root: Path, *, collect: bool = False) -> tuple[dict, list[dict]]:
    index = index108(root)
    totals, all_packets = Counter(), []
    seen = set()
    for name, relative, expected in ROOTS:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("frozen source missing")
        count = 0
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                count += 1
                row = json.loads(line)
                packet, holds = normalize_record(row, name, index)
                key = (name, packet["case_id"])
                if key in seen:
                    raise ValueError("duplicate record")
                seen.add(key)
                totals["source_rows_checked"] += 1
                totals["target_hash_verified"] += 1
                totals["current_user_target_adjacent"] += 1
                if "LEADING_ASSISTANT_CONTEXT_UNRESOLVED" in holds:
                    totals["leading_assistant_context_hold"] += 1
                if "STORY_UUID_MISSING" in holds:
                    totals["story_uuid_hold"] += 1
                if collect:
                    all_packets.append(packet)
        if count != expected:
            raise ValueError("frozen count mismatch")
        totals[name + "_rows"] = count
    if totals["source_rows_checked"] != 195:
        raise ValueError("total count mismatch")
    report = {
        "schema": "r58_gold195_source_faithful_safe_summary_v1",
        "status": "SOURCE_REVIEW_PACKET_PREFLIGHT_PASS__ALL_QUALITY_HOLD",
        "counts": dict(sorted(totals.items())),
        "quality_v1_pass": 0,
        "train_admitted": 0,
        "private_review_packet_written": False,
        "r50_body_accessed": False,
        "no_system_prompt_invented": True,
        "all_frozen_messages_preserved_in_optional_private_packet": True,
    }
    return report, all_packets


def write_private(path: Path, root: Path, packets: list[dict]) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("private output must be new absolute regular path")
    # Do not put review packets into a Git checkout or a symlinked directory.
    if root.resolve() == path.parent.resolve() or root.resolve() in path.parent.resolve().parents:
        raise ValueError("private output under repository")
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("unsafe private parent")
    mode = stat.S_IMODE(parent.stat().st_mode)
    if mode & 0o077:
        raise ValueError("private parent permissions are too broad")
    payload = b"".join(canon(row) + b"\n" for row in packets)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-review-output", type=Path)
    args = parser.parse_args()
    try:
        report, packets = assemble(
            args.repo_root, collect=args.private_review_output is not None,
        )
        if args.private_review_output is not None:
            write_private(args.private_review_output, args.repo_root, packets)
            report["private_review_packet_written"] = True
    except Exception:
        report = {
            "schema": "r58_gold195_source_faithful_safe_summary_v1",
            "status": "SOURCE_OR_PRIVATE_OUTPUT_UNAVAILABLE__HOLD",
            "train_admitted": 0, "r50_body_accessed": False,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "SOURCE_REVIEW_PACKET_PREFLIGHT_PASS__ALL_QUALITY_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())

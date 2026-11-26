#!/usr/bin/env python3
"""B-route: bind PRIVATE frozen card snapshots to Gold195 for semantic review.

No card is asserted trusted merely because it is hash-matched to source archives.
Outputs count-only SAFE receipt; private packet is optional and never train-ready.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat

from gold195_source_review_packet import assemble, canon
from gold195_card_snapshot_candidates import card_utf8

PRIVATE_SCHEMA = "r58_gold195_card_snapshot_candidates_private_v1"
PACKET_SCHEMA = "r58_gold195_card_gold_semantic_review_private_v1"


def private_read(path: Path) -> dict:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("not a private absolute regular file")
    before = path.stat()
    if stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1:
        raise ValueError("private file permissions")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_ino, opened.st_dev) != (before.st_ino, before.st_dev):
            raise ValueError("private file identity changed")
        return json.load(stream)


def verified_cards(path: Path) -> dict:
    data = private_read(path)
    if data.get("schema") != PRIVATE_SCHEMA or data.get("status") != "CANDIDATE_ONLY_NOT_APPROVED":
        raise ValueError("snapshot source schema")
    rows = data.get("cards")
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty card list")
    cards = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("card record")
        identity = row.get("story_uuid")
        content = row.get("snapshot_card_json")
        original_hash = row.get("card_sha256")
        if (not isinstance(identity, str) or not identity or identity in cards
                or not isinstance(content, dict) or not content
                or not isinstance(original_hash, str)
                or hashlib.sha256(card_utf8(content)).hexdigest() != original_hash
                or row.get("source_kind") != "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST"
                or row.get("review_status") != "NOT_APPROVED_FOR_SYSTEM"):
            raise ValueError("card identity, hash or provenance mismatch")
        cards[identity] = row
    return cards


def build(root: Path, cards: dict, collect: bool = False):
    baseline, records = assemble(root, collect=True)
    if baseline["counts"]["source_rows_checked"] != 195:
        raise ValueError("source mismatch")
    counts = Counter()
    review = []
    for p in records:
        counts["gold_rows"] += 1
        identity = p.get("story_uuid")
        card = cards.get(identity)
        if card is None:
            counts["missing_card"] += 1
            continue
        counts["card_hash_bound"] += 1
        history = p["frozen_messages"]
        leading = history[0]["role"] == "assistant"
        if leading:
            counts["leading_assistant_context_requires_review"] += 1
        else:
            counts["user_first_structural_input"] += 1
        if collect:
            # Review the original source card as evidence, not as an approved System.
            # All Gold history and target are kept, including orphan Assistant text.
            row = {
                "schema": PACKET_SCHEMA,
                "case_id": p["case_id"],
                "corpus": p["corpus"],
                "story_uuid": identity,
                "source_target_sha256": p["target_sha256"],
                "source_record_sha256": p["source_record_sha256"],
                "card_snapshot_sha256": card["card_sha256"],
                "card_snapshot_version": card["snapshot_version"],
                "card_source_archive": card["source_archive"],
                "card_source_kind": card["source_kind"],
                "card_snapshot": card["snapshot_card_json"],
                "original_history": history[:-2],
                "current_user_text": p["current_user_text"],
                "target_assistant_text": p["target_assistant_text"],
                "source_history_starts_with_assistant": leading,
                "semantic_review": {
                    "character_relationships": "UNREVIEWED",
                    "hard_facts_and_forbidden_rules": "UNREVIEWED",
                    "chronology_and_future_leakage": "UNREVIEWED",
                    "player_agency": "UNREVIEWED",
                    "literary_chinese_and_npc_initiative": "UNREVIEWED",
                    "age_safety_content_boundaries": "UNREVIEWED",
                    "snapshot_is_acceptable_offline_design": "UNREVIEWED",
                },
                "candidate_messages": None,
                "candidate_status": "PRIVATE_REVIEW_ONLY_NOT_TRAIN_READY",
                "world_component_id": None,
                "split": None,
                "quality_v1_admitted": False,
            }
            review.append(row)
    return {
        "schema": "r58_gold195_card_gold_review_binding_safe_v1",
        "status": "SOURCE_CARD_AND_GOLD_BOUND__SEMANTIC_REVIEW_PENDING",
        "counts": dict(sorted(counts.items())),
        "private_review_output_written": False,
        "card_snapshot_approved_for_system": False,
        "world_component_verified": False,
        "reviewers_completed": 0,
        "quality_v1_admitted": 0,
        "r50_accessed": False,
        "gpu_authorized": False,
    }, review


def write_private(target: Path, root: Path, rows):
    if not target.is_absolute() or target.exists() or target.is_symlink():
        raise ValueError("private output must be new absolute path")
    parent = target.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or root.resolve() == parent.resolve()
            or root.resolve() in parent.resolve().parents):
        raise ValueError("unsafe private output directory")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        for row in rows:
            out.write(canon(row) + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-card-candidates", type=Path, required=True)
    parser.add_argument("--private-review-output", type=Path)
    args = parser.parse_args()
    try:
        cards = verified_cards(args.private_card_candidates)
        receipt, rows = build(args.repo_root, cards, bool(args.private_review_output))
        if args.private_review_output:
            write_private(args.private_review_output, args.repo_root, rows)
            receipt["private_review_output_written"] = True
    except Exception:
        receipt = {
            "schema": "r58_gold195_card_gold_review_binding_safe_v1",
            "status": "SOURCE_OR_CARD_INPUT_INVALID__HOLD",
            "quality_v1_admitted": 0, "r50_accessed": False,
        }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if receipt["status"] == "SOURCE_CARD_AND_GOLD_BOUND__SEMANTIC_REVIEW_PENDING" else 42


if __name__ == "__main__":
    raise SystemExit(main())

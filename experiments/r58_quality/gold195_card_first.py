#!/usr/bin/env python3
"""R58: offline card-first Gold195 review draft. No training admission.

A card must be explicitly provided, versioned, and source-bound in a PRIVATE
manifest. Historical production request replay is neither attempted nor required.
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


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path):
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ValueError("private manifest must be a mode 0600 regular file")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "r58_gold195_card_binding_private_v1":
        raise ValueError("manifest schema")
    entries = raw.get("cards")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest cards missing")
    cards = {}
    for e in entries:
        if not isinstance(e, dict):
            raise ValueError("card format")
        world = e.get("story_uuid")
        version = e.get("card_version")
        body = e.get("card_text")
        checksum = e.get("card_sha256")
        source = e.get("source_ref")
        if not all(isinstance(x, str) and x.strip() for x in
                   (world, version, body, checksum, source)):
            raise ValueError("card fields missing")
        if sha(body.encode("utf-8")) != checksum or world in cards:
            raise ValueError("card digest mismatch or duplicate story")
        # The source_ref records the claimed offline authority; code cannot
        # authenticate that source or determine literary/character correctness.
        cards[world] = e
    return cards


def bind(p: dict, cards: dict):
    world = p.get("story_uuid")
    if not world:
        return None, "MISSING_SOURCE_STORY_UUID"
    card = cards.get(world)
    if card is None:
        return None, "TRUSTED_CARD_NOT_PROVIDED"
    history = p["frozen_messages"]
    # R58 CPU132 proved leading Assistant history compatible with the actual
    # ms-swift 4.5.3 last_round and data_collator path. Keep it unmodified.
    if history[0]["role"] not in ("user", "assistant"):
        return None, "INVALID_HISTORY_START_ROLE"
    if history[-2]["role"] != "user" or history[-1]["role"] != "assistant":
        return None, "ROLE_BOUNDARY_INVALID"
    target = history[-1]["content"]
    if sha(target.encode("utf-8")) != p["target_sha256"]:
        raise ValueError("source target changed")
    messages = [
        {"role": "system", "content": card["card_text"]},
        *history[:-1],
    ]
    draft = {
        "schema": "r58_gold195_card_first_review_draft_v1",
        "source_case_id": p["case_id"],
        "source_record_sha256": p["source_record_sha256"],
        "source_target_sha256": p["target_sha256"],
        "story_uuid": world,
        "card_version": card["card_version"],
        "card_sha256": card["card_sha256"],
        "card_source_ref": card["source_ref"],
        "card_design": "EXPLICIT_OFFLINE_DERIVATIVE_NOT_ORIGINAL_PROVIDER_REQUEST",
        "messages": messages,
        "source_history_starts_with_assistant": history[0]["role"] == "assistant",
        "target_text": target,
        "input_messages_sha256": sha(canon(messages)),
        "quality_status": "HOLD",
        "world_component_id": None,
        "split": None,
        "hold_reasons": [
            "CARD_AUTHORITY_AND_CANON_SEMANTIC_REVIEW_PENDING",
            "WORLD_COMPONENT_AND_PROTECTED_ISOLATION_PENDING",
            "QUALITY_V1_SIX_DIMENSION_DOUBLE_REVIEW_PENDING",
            "QWEN_TOKEN_AND_MSSWIFT_LAST_ROUND_PENDING",
        ],
        "training_admitted": False,
    }
    return draft, None


def audit(root: Path, manifest: Path | None = None, collect=False):
    cards = load_manifest(manifest) if manifest else {}
    baseline, packets = assemble(root, collect=True)
    if baseline["counts"]["source_rows_checked"] != 195:
        raise ValueError("frozen source count")
    c = Counter()
    drafts = []
    for p in packets:
        c["source_rows"] += 1
        draft, reason = bind(p, cards)
        if reason:
            c[reason] += 1
        else:
            c["structural_card_drafts"] += 1
            c["assistant_first_drafts" if draft["source_history_starts_with_assistant"]
              else "user_first_drafts"] += 1
            if collect:
                drafts.append(draft)
    return {
        "schema": "r58_gold195_card_first_safe_v1",
        "status": "CARD_FIRST_DRAFT_CHECK_ONLY__NO_TRAINING_ADMISSION",
        "counts": dict(sorted(c.items())),
        "card_worlds_supplied": len(cards),
        "card_semantic_validity_verified_by_script": False,
        "history_orphan_rewritten": False,
        "historical_provider_replay_required": False,
        "source_modified": False,
        "private_output_written": False,
        "r50_accessed": False,
        "quality_v1_admitted": 0,
        "gpu_authorized": False,
    }, drafts


def write_private(path: Path, repo: Path, drafts: list):
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("output must be a new absolute file")
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise ValueError("private output parent unsafe")
    if repo.resolve() == parent.resolve() or repo.resolve() in parent.resolve().parents:
        raise ValueError("private output within Git checkout")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        for draft in drafts:
            stream.write(canon(draft) + b"\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True, type=Path)
    ap.add_argument("--private-card-manifest", type=Path)
    ap.add_argument("--private-draft-output", type=Path)
    args = ap.parse_args()
    try:
        if args.private_draft_output and not args.private_card_manifest:
            raise ValueError("cannot write drafts without source-bound cards")
        summary, drafts = audit(
            args.repo_root, args.private_card_manifest, bool(args.private_draft_output),
        )
        if args.private_draft_output:
            write_private(args.private_draft_output, args.repo_root, drafts)
            summary["private_output_written"] = True
    except Exception:
        summary = {
            "schema": "r58_gold195_card_first_safe_v1",
            "status": "CARD_SOURCE_OR_OUTPUT_UNAVAILABLE__HOLD",
            "r50_accessed": False, "quality_v1_admitted": 0,
        }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if summary["status"] == "CARD_FIRST_DRAFT_CHECK_ONLY__NO_TRAINING_ADMISSION" else 42


if __name__ == "__main__":
    raise SystemExit(main())

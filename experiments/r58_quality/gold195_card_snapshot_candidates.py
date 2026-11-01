#!/usr/bin/env python3
"""Extract private offline story-card SNAPSHOT CANDIDATES from pinned archives.

Never approves or installs cards as System prompts. Default mode emits SAFE counts
only; private output requires an explicitly supplied new 0600 path outside Git.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import zipfile

from gold195_archive_source_discovery import SOURCES, SOURCE_ROOT, digest_file
from gold195_card_source_coverage import gold_ids, MAX_JSON, MAX_NESTED


def content_sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def card_utf8(card):
    return json.dumps(card, ensure_ascii=False, sort_keys=True,
                      indent=2).encode("utf-8")


def find_cards(source, name, items, metrics, depth=0):
    if depth > 3:
        return
    with zipfile.ZipFile(source) as z:
        if len(z.infolist()) > 7000:
            raise ValueError("members cap")
        for info in z.infolist():
            if info.is_dir():
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix == ".zip":
                if info.file_size <= MAX_NESTED:
                    find_cards(io.BytesIO(z.read(info)), name, items, metrics, depth + 1)
                else:
                    metrics["oversize_nested_zip"] += 1
            elif suffix == ".json":
                if info.file_size > MAX_JSON:
                    metrics["oversize_json"] += 1
                    continue
                try:
                    raw = json.loads(z.read(info))
                except (ValueError, UnicodeError, RecursionError):
                    metrics["bad_json"] += 1
                    continue
                if not isinstance(raw, dict):
                    continue
                story = raw.get("story")
                if not isinstance(story, dict):
                    continue
                v2 = story.get("v2_data")
                ident = story.get("id") or story.get("uuid") or raw.get("story_id")
                if not isinstance(ident, str) or not ident.strip() or not isinstance(v2, dict) or not v2:
                    continue
                payload = card_utf8(v2)
                digest = content_sha(payload)
                previous = items.get(ident)
                if previous is not None and previous["card_sha256"] != digest:
                    metrics["conflicting_story_snapshot_versions"] += 1
                    continue
                if previous is None:
                    items[ident] = {
                        "story_uuid": ident,
                        "snapshot_card_json": v2,
                        "card_sha256": digest,
                        "snapshot_version": "export-snapshot-sha256:" + digest,
                        "source_archive": name,
                        "source_member_raw_sha256": content_sha(
                            json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()),
                        "source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
                        "review_status": "NOT_APPROVED_FOR_SYSTEM",
                    }
                metrics["card_objects_found"] += 1


def audit(root: Path, include_private=False):
    gold = gold_ids(root)
    relevant = {x for ids in gold.values() for x in ids if x}
    all_cards = {}
    counts = Counter()
    for label, rel, pinned_sha, size in SOURCES:
        path = root / SOURCE_ROOT / rel
        if not path.is_file() or path.is_symlink() or path.stat().st_size != size:
            raise ValueError("missing pinned LFS archive")
        if digest_file(path) != pinned_sha:
            raise ValueError("pinned LFS archive hash mismatch")
        find_cards(path, label, all_cards, counts)
    if counts["conflicting_story_snapshot_versions"]:
        raise ValueError("conflicting source snapshots")
    chosen = [all_cards[k] for k in sorted(relevant) if k in all_cards]
    report = {
        "schema": "r58_gold195_offline_card_snapshot_candidate_safe_v1",
        "status": "SOURCE_CARD_CANDIDATES_IDENTIFIED__OWNER_REVIEW_REQUIRED",
        "gold195_world_components_not_certified": True,
        "source_card_identities": len(all_cards),
        "gold_world_ids": len(relevant),
        "gold_world_ids_matched": len(chosen),
        "gold_rows_with_card_candidates": sum(
            k in all_cards for ids in gold.values() for k in ids),
        "source_snapshot_conflict_count": counts["conflicting_story_snapshot_versions"],
        "private_candidate_file_written": False,
        "card_semantics_approved": False,
        "training_admitted": 0,
        "r50_accessed": False,
    }
    return report, chosen if include_private else []


def write_private(file: Path, repo: Path, cards):
    if not file.is_absolute() or file.exists() or file.is_symlink():
        raise ValueError("private path must be new and absolute")
    folder = file.parent
    if not folder.is_dir() or folder.is_symlink() or stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("private output directory must have mode 0700")
    if repo.resolve() == folder.resolve() or repo.resolve() in folder.resolve().parents:
        raise ValueError("private content cannot be in Git checkout")
    payload = {
        "schema": "r58_gold195_card_snapshot_candidates_private_v1",
        "status": "CANDIDATE_ONLY_NOT_APPROVED",
        "cards": cards,
    }
    fd = os.open(file, os.O_EXCL | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-candidates-output", type=Path)
    args = p.parse_args()
    try:
        summary, candidates = audit(args.repo_root, args.private_candidates_output is not None)
        if args.private_candidates_output:
            write_private(args.private_candidates_output, args.repo_root, candidates)
            summary["private_candidate_file_written"] = True
    except Exception:
        summary = {"schema": "r58_gold195_offline_card_snapshot_candidate_safe_v1",
                   "status": "SOURCE_OR_OUTPUT_UNAVAILABLE__HOLD",
                   "training_admitted": 0, "r50_accessed": False}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "SOURCE_CARD_CANDIDATES_IDENTIFIED__OWNER_REVIEW_REQUIRED" else 42


if __name__ == "__main__":
    raise SystemExit(main())

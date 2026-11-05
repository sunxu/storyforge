"""Prepare seven PRIVATE contextual work packets from frozen lexical index.

A lexical hit is a retrieval hint, never semantic world-link evidence.
No GPU, HF Job, model inference, network, Git write or source mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import v03_r50_build_w17_semantic_kit as kit_builder
import v03_r50_full_original_world_inventory as inventory
import v03_r50_verify_seven_gap_coverage as coverage

SCOPED = (2, 4, 7, 10, 17)
CENTER_CHARS = 2800
NEIGHBOR_CHARS = 700
EXPECTED_PER_GAP = 10


def guard(condition: bool, marker: str) -> None:
    if not condition:
        raise ValueError(marker)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def private_source_text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def candidate_context(candidate: dict, messages: list,
                      *, source_rank: int) -> dict:
    """Crosscheck lexical index candidate against exact original source bytes."""
    idx = candidate["source_message_index"]
    guard(type(idx) is int and 0 <= idx < len(messages),
          "CANDIDATE_ORIGINAL_MESSAGE_INDEX_INVALID")
    msg = messages[idx]
    guard(isinstance(msg, dict) and isinstance(msg.get("content"), str),
          "CANDIDATE_NOT_ORIGINAL_TEXT_MESSAGE")
    original = msg["content"]
    start = candidate["excerpt_start_character"]
    excerpt = candidate["excerpt"]
    guard(type(start) is int and 0 <= start <= len(original) and
          isinstance(excerpt, str) and bool(excerpt) and
          original[start:start + len(excerpt)] == excerpt,
          "INDEX_EXCERPT_NOT_VERBATIM_FROM_ORIGINAL")
    guard(msg.get("role") == candidate["source_role"],
          "INDEX_SOURCE_MESSAGE_ROLE_MISMATCH")

    # Focus around the original excerpt, not always the first N characters.
    center_start = max(0, start - 450)
    focus = original[center_start:center_start + CENTER_CHARS]
    neighbors = []
    for offset in (-1, 1):
        j = idx + offset
        if 0 <= j < len(messages):
            other = messages[j]
            if isinstance(other, dict):
                body = other.get("content")
                neighbors.append({
                    "source_message_index": j,
                    "relative_offset": offset,
                    "source_role": other.get("role") if other.get("role") in
                                   ("user", "assistant", "system") else "other",
                    "excerpt": private_source_text(body, NEIGHBOR_CHARS),
                    "truncated": isinstance(body, str) and
                                 len(body) > NEIGHBOR_CHARS,
                })
    return {
        "source_rank": source_rank,
        "original_source_message_index": idx,
        "original_source_role": msg.get("role"),
        "original_message_sha256": sha(original.encode("utf8")),
        "original_message_codepoints": len(original),
        "original_index_lexical_score": candidate["lexical_ranking_score"],
        "original_index_trigram_matches": candidate["matched_trigram_count"],
        "focus_start_character": center_start,
        "focus_excerpt": focus,
        "focus_is_truncated": len(original) > center_start + len(focus),
        "source_neighbors": neighbors,
        "index_excerpt_verbatim_checked": True,
        "semantic_evidence_status": "UNREVIEWED",
    }


def build_packets(index: dict, originals: dict[int, dict]) -> list[dict]:
    coverage.summarize(index)
    guard(set(originals) == set(SCOPED),
          "EXPECTED_FIVE_IMMUTABLE_SOURCE_WORLDS")
    packets = []
    for gap in index["gaps"]:
        locators = gap["candidate_source_excerpts"]
        sources = []
        for rank in SCOPED:
            rows = originals[rank].get("messages")
            guard(isinstance(rows, list), "SOURCE_MESSAGES_MISSING")
            for candidate in locators[str(rank)]["ranked_candidates"]:
                sources.append(candidate_context(candidate, rows,
                                                 source_rank=rank))
        guard(len(sources) <= EXPECTED_PER_GAP, "GAP_CANDIDATE_COUNT_OVER_CAP")
        packets.append({
            "schema": "storyforge-r50-w17-seven-gap-private-context-packet-v1",
            "status": "CONTEXT_EXPANDED__NOT_AI_REVIEWED",
            "gap_index": gap["gap_index"],
            "original_private_missing_evidence_requirement":
                gap["requirement_from_original_private_ai_decision"],
            "original_private_index_sha256": coverage.PINNED_INDEX_SHA256,
            "private_candidate_count": len(sources),
            "private_candidate_contexts": sources,
            "known_old_04_07_link": "PENDING_TRANSITIVE_AI_REVIEW",
            "lexical_retrieval_is_not_semantic_support": True,
            "full_original_message_not_guaranteed": True,
            "historically_valid_card_at_cutoff_not_verified": True,
            "source_world_graph_gate": "HOLD",
            "final_heldout_seal": "NOT_PERFORMED",
            "data_security": "PRIVATE original text, never commit to Git",
        })
    guard(len(packets) == 7, "EXPECTED_EXACTLY_SEVEN_REVIEW_PACKETS")
    return packets


def safe_write_new(path: Path, blob: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(blob)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--old14", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()

    repo = args.repo.resolve()
    outdir = args.output_dir.expanduser().absolute()
    guard((repo / ".git").exists() and
          outdir != repo and repo not in outdir.parents,
          "PRIVATE_OUTPUT_MUST_BE_OUTSIDE_GIT")
    guard(not outdir.exists() and not outdir.is_symlink(),
          "PRIVATE_PACKETS_OUTPUT_ALREADY_EXISTS")
    parent = outdir.parent
    guard(parent.is_dir() and not parent.is_symlink() and
          stat.S_IMODE(parent.stat().st_mode) & 0o077 == 0,
          "PRIVATE_OUTPUT_PARENT_NOT_SAFE")

    indexpath = args.index.expanduser().absolute()
    guard(indexpath.is_file() and not indexpath.is_symlink() and
          repo not in indexpath.parents and
          stat.S_IMODE(indexpath.stat().st_mode) & 0o077 == 0,
          "PRIVATE_INDEX_FILE_NOT_SAFE")
    index_bytes = indexpath.read_bytes()
    guard(sha(index_bytes) == coverage.PINNED_INDEX_SHA256,
          "PRIVATE_SEVEN_GAP_INDEX_SHA_MISMATCH")
    index = json.loads(index_bytes)

    inventory.verify_zip(args.old14, "old14")
    old = inventory.old14_data(args.old14)
    guard({2, 4, 7, 10} <= set(old), "OLD_WORLD_SOURCE_RANKS_MISSING")
    kit_builder.frozen_w17_card(repo)
    new = inventory.new_data(repo)
    originals = {rank: old[rank] for rank in (2, 4, 7, 10)}
    originals[17] = new[17]
    packets = build_packets(index, originals)

    os.mkdir(outdir, mode=0o700)
    manifest = {
        "schema": "storyforge-r50-w17-seven-gap-private-context-manifest-v1",
        "private_index_sha256": coverage.PINNED_INDEX_SHA256,
        "packet_count": 7,
        "packets": [],
        "semantic_graph_gate": "HOLD",
        "final_heldout_seal": "NOT_PERFORMED",
        "ai_review_executed": False,
    }
    for i, packet in enumerate(packets):
        filename = f"gap_{i:02d}.json"
        blob = (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode()
        safe_write_new(outdir / filename, blob)
        manifest["packets"].append({
            "gap_index": i, "file": filename, "sha256": sha(blob),
            "private_candidate_count": packet["private_candidate_count"],
        })
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    safe_write_new(outdir / "manifest.json", data)
    print("R50_W17_SEVEN_GAP_CONTEXT_PACKETS_BUILT__AI_REVIEW_PENDING")
    print("GAP_COUNT=7__PACKET_COUNT=7__NO_SEMANTIC_PASS")
    print("PRIVATE_MANIFEST_SHA256=" + sha(data))
    print("NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            json.JSONDecodeError) as error:
        print("R50_W17_GAP_PACKET_BUILD_HOLD:",
              type(error).__name__, str(error)[:140], file=sys.stderr)
        sys.exit(2)

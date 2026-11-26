"""Escalate W17 seven-gap AI HOLD to full-original-message private evidence.

No external AI/GPU/HF, no Git writes. Never truncate source message bodies.
The complete messages plus +/-2 complete neighbors remain in 0600 private
per-gap dossiers outside Git, pinned to prior validated AI workpaper bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import v03_r50_build_w17_semantic_kit as builder
import v03_r50_full_original_world_inventory as inventory
import v03_r50_verify_seven_gap_workpaper as checker

RANKS = (2, 4, 7, 10, 17)
PINNED_WORKPAPER_SHA256 = "6507ac6caec72aa031e9c70004a3d96781e7de8c0373976036c716aa9c884d9a"
MAX_OUTPUT_BYTES_PER_GAP = 35_000_000


def require(ok: bool, marker: str) -> None:
    if not ok:
        raise ValueError(marker)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_original_source(packet_entry: dict, source_messages: list) -> tuple[int, str]:
    rank = packet_entry["source_rank"]
    i = packet_entry["original_source_message_index"]
    require(type(rank) is int and rank in RANKS and
            type(i) is int and 0 <= i < len(source_messages),
            "SOURCE_MESSAGE_POINTER_OUT_OF_BOUNDS")
    msg = source_messages[i]
    require(isinstance(msg, dict) and isinstance(msg.get("content"), str),
            "ORIGINAL_SOURCE_MESSAGE_NOT_TEXT")
    body = msg["content"]
    require(digest(body.encode("utf8")) == packet_entry["original_message_sha256"]
            and len(body) == packet_entry["original_message_codepoints"],
            "FULL_SOURCE_MESSAGE_HASH_OR_LENGTH_MISMATCH")
    require(msg.get("role") == packet_entry.get("original_source_role"),
            "FULL_SOURCE_ROLE_MISMATCH")
    offset = packet_entry["focus_start_character"]
    excerpt = packet_entry["focus_excerpt"]
    require(type(offset) is int and offset >= 0 and
            type(excerpt) is str and
            body[offset:offset + len(excerpt)] == excerpt,
            "CONTEXT_FOCUS_NOT_VERBATIM_FROM_ORIGINAL")
    return i, body


def full_message(row: dict, *, source_rank: int, index: int,
                 cited: bool) -> dict:
    content = row.get("content")
    require(isinstance(content, str), "NON_TEXT_FULL_MESSAGE_REFERENCED")
    return {
        "source_rank": source_rank,
        "original_source_message_index": index,
        "role": row.get("role") if row.get("role") in
                ("user", "assistant", "system") else "other",
        "original_message_sha256": digest(content.encode("utf8")),
        "original_message_codepoints": len(content),
        "full_source_text": content,
        "complete_original_message_untruncated": True,
        "cited_in_previous_workpaper": cited,
        "source_messages_are_untrusted_data": True,
    }


def build_dossiers(packets: list[dict], workpaper: dict,
                   original: dict[int, dict]) -> list[dict]:
    require(len(packets) == 7 and set(original) == set(RANKS),
            "SOURCE_OR_REVIEW_SCOPE_CHANGED")
    reviews = workpaper.get("gap_reviews")
    require(isinstance(reviews, list) and len(reviews) == 7,
            "REVIEW_WORKPAPER_GAP_SCOPE_CHANGED")
    dossiers = []
    for i, (packet, review) in enumerate(zip(packets, reviews, strict=True)):
        require(packet["gap_index"] == i and review["gap_index"] == i,
                "GAP_REVIEW_ORDER_CHANGED")
        listed = {
            (item["source_rank"], item["original_source_message_index"]): item
            for item in packet["private_candidate_contexts"]
        }
        cited = []
        selected: dict[tuple[int, int], bool] = {}
        for pointer in review["source_refs"]:
            key = (pointer["source_rank"], pointer["source_message_index"])
            require(key in listed, "REVIEWED_MESSAGE_NOT_IN_FROZEN_PACKET")
            rank, mid = key
            msgs = original[rank]["messages"]
            verify_original_source(listed[key], msgs)
            require(key not in cited, "DUPLICATE_REVIEWED_SOURCE_POINTER")
            cited.append(key)
            for j in range(max(0, mid - 2), min(len(msgs), mid + 3)):
                row = msgs[j]
                if isinstance(row, dict) and isinstance(row.get("content"), str):
                    selected[(rank, j)] = selected.get((rank, j), False) or j == mid
        source_rows = [
            full_message(original[rank]["messages"][index],
                         source_rank=rank, index=index, cited=is_cited)
            for (rank, index), is_cited in sorted(selected.items())
        ]
        dossiers.append({
            "schema": "storyforge-r50-w17-private-full-source-gap-dossier-v1",
            "status": "ORIGINAL_MESSAGES_EXTRACTED__AI_REVIEW_PENDING",
            "gap_index": i,
            "source_full_message_count": len(source_rows),
            "prior_workpaper_referenced_source_count": len(cited),
            "original_private_gap_requirement":
                packet["original_private_missing_evidence_requirement"],
            "original_private_ai_remarks": review["private_reasoning"],
            "original_remaining_requirements":
                review["remaining_evidence_requirements"],
            "full_original_messages": source_rows,
            "source_scope": list(RANKS),
            "historical_card_cutoff_verified": False,
            "full_world_story_arc_certified": False,
            "semantic_world_gate": "HOLD",
            "final_heldout_seal": "NOT_PERFORMED",
            "untrusted_source_material_only": True,
            "privacy": "PRIVATE SOURCE CONTENT. NEVER COMMIT OR PRINT.",
        })
    return dossiers


def checked_dir(path: Path, repo: Path, *, must_exist: bool) -> None:
    require(path != repo and repo not in path.parents and not path.is_symlink(),
            "PRIVATE_PATH_INVALID_OR_INSIDE_REPO")
    if must_exist:
        require(path.is_dir() and stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
                "PRIVATE_DIRECTORY_NOT_0700")
    else:
        require(not path.exists(), "PRIVATE_FULL_DOSSIER_ALREADY_EXISTS")


def save_new(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(data)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--packets-dir", required=True, type=Path)
    p.add_argument("--workpaper", required=True, type=Path)
    p.add_argument("--old14", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    repo = args.repo.resolve()
    packet_dir = args.packets_dir.expanduser().absolute()
    output_argument = args.output_dir.expanduser().absolute()
    require(not output_argument.is_symlink(), "PRIVATE_OUTPUT_SYMLINK_FORBIDDEN")
    output = output_argument.resolve(strict=False)
    checked_dir(output, repo, must_exist=False)
    checked_dir(output.parent, repo, must_exist=True)
    original_path = checker.checked_private_workpaper(repo, args.workpaper)
    workpaper_raw = original_path.read_bytes()
    require(digest(workpaper_raw) == PINNED_WORKPAPER_SHA256,
            "REVIEWED_WORKPAPER_SHA256_MISMATCH")
    workpaper = json.loads(workpaper_raw)
    manifest, packets, manifest_sha = checker.load_manifest(packet_dir)
    # Validate every prior decision before relying on its source pointers.
    checker.summarize(manifest, packets, manifest_sha,
                      workpaper, digest(workpaper_raw))
    inventory.verify_zip(args.old14, "old14")
    old = inventory.old14_data(args.old14)
    require({2, 4, 7, 10} <= set(old), "ORIGINAL_OLD_RANKS_MISSING")
    builder.frozen_w17_card(repo)
    new = inventory.new_data(repo)
    sources = {r: old[r] for r in (2, 4, 7, 10)}
    sources[17] = new[17]
    dossiers = build_dossiers(packets, workpaper, sources)

    payloads = []
    for dossier in dossiers:
        data = (json.dumps(dossier, ensure_ascii=False, indent=2) + "\n").encode("utf8")
        require(len(data) <= MAX_OUTPUT_BYTES_PER_GAP,
                "PRIVATE_FULL_DOSSIER_TOO_LARGE_FOR_SAFE_BOUND")
        payloads.append(data)
    os.mkdir(output, 0o700)
    entries = []
    for i, data in enumerate(payloads):
        name = f"gap_{i:02d}_full.json"
        save_new(output / name, data)
        entries.append({
            "gap_index": i,
            "file": name,
            "sha256": digest(data),
            "cited_source_count": dossiers[i]["prior_workpaper_referenced_source_count"],
            "original_full_message_count": dossiers[i]["source_full_message_count"],
        })
    manifest_out = {
        "schema": "storyforge-r50-w17-seven-gap-private-full-source-manifest-v1",
        "input_packet_manifest_sha256": checker.PINNED_MANIFEST_SHA256,
        "input_prior_workpaper_sha256": PINNED_WORKPAPER_SHA256,
        "gap_count": 7,
        "dossiers": entries,
        "historical_card_cutoff_verified": False,
        "full_world_graph_gate": "HOLD",
        "final_heldout_seal": "NOT_PERFORMED",
        "ai_review_performed": False,
    }
    raw_manifest = (json.dumps(manifest_out, ensure_ascii=False, indent=2) + "\n").encode()
    save_new(output / "manifest.json", raw_manifest)
    print("R50_W17_SEVEN_GAP_FULL_MESSAGE_DOSSIERS_BUILT__AI_REVIEW_PENDING")
    print("GAP_COUNT=7__SOURCE_SCOPE_02_04_07_10_17__NO_SEMANTIC_PASS")
    print("PRIVATE_FULL_DOSSIER_MANIFEST_SHA256=" + digest(raw_manifest))
    print("NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as exc:
        print("R50_W17_FULL_SOURCE_DOSSIER_HOLD:", type(exc).__name__,
              str(exc)[:110], file=sys.stderr)
        sys.exit(2)

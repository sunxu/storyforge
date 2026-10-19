"""Strict private W17 7-gap AI workpaper validator.

Never judges truth of AI conclusions. Read-only, SHA-bound to local packets.
Outputs safe categories/counts only; no story text, personal names or Git writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from collections import Counter
from pathlib import Path

import v03_r50_verify_seven_gap_coverage as coverage

ASSESSMENTS = {
    "SUPPORTED_IN_SCOPED_CONTEXT",
    "NOT_SUPPORTED_IN_REVIEWED_SCOPE",
    "INSUFFICIENT_CONTEXT",
    "SOURCE_UNAVAILABLE",
}
CARD_TIMINGS = {"VERIFIED_AS_OF_CUTOFF", "POSTDATE_RISK", "NOT_CHECKED"}
RANKS = (2, 4, 7, 10, 17)
PINNED_MANIFEST_SHA256 = "b4e08232bdd12d9401d78fe6e0ab945a6f5156938c88ef811da9bf52a9b41a3b"


def verify_manifest_sha(raw: bytes, *, expected: str = PINNED_MANIFEST_SHA256) -> None:
    require(digest(raw) == expected, "PRIVATE_MANIFEST_SHA256_MISMATCH")



def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(folder: Path) -> tuple[dict, list[dict], str]:
    require(folder.is_dir() and not folder.is_symlink() and
            stat.S_IMODE(folder.stat().st_mode) & 0o077 == 0,
            "PACKET_DIRECTORY_NOT_PRIVATE")
    mp = folder / "manifest.json"
    require(mp.is_file() and not mp.is_symlink(), "PACKET_MANIFEST_MISSING")
    raw = mp.read_bytes()
    verify_manifest_sha(raw)
    require(stat.S_IMODE(mp.stat().st_mode) & 0o077 == 0,
            "PACKET_MANIFEST_FILE_NOT_PRIVATE")
    manifest_sha = digest(raw)
    manifest = json.loads(raw)
    require(manifest.get("schema") ==
            "storyforge-r50-w17-seven-gap-private-context-manifest-v1" and
            manifest.get("private_index_sha256") == coverage.PINNED_INDEX_SHA256 and
            manifest.get("packet_count") == 7 and
            manifest.get("semantic_graph_gate") == "HOLD" and
            manifest.get("final_heldout_seal") == "NOT_PERFORMED" and
            manifest.get("ai_review_executed") is False,
            "PACKET_MANIFEST_INVALID")
    entries = manifest.get("packets")
    require(isinstance(entries, list) and len(entries) == 7,
            "PACKET_COUNT_INVALID")
    packets = []
    for i, entry in enumerate(entries):
        require(isinstance(entry, dict) and entry.get("gap_index") == i and
                entry.get("file") == f"gap_{i:02d}.json",
                "PACKET_FILE_SCOPE_INVALID")
        f = folder / entry["file"]
        require(f.is_file() and not f.is_symlink() and
                stat.S_IMODE(f.stat().st_mode) & 0o077 == 0,
                "PACKET_FILE_NOT_PRIVATE")
        rawpacket = f.read_bytes()
        require(digest(rawpacket) == entry.get("sha256"),
                "PACKET_CONTENT_DIGEST_MISMATCH")
        packet = json.loads(rawpacket)
        require(packet.get("schema") ==
                "storyforge-r50-w17-seven-gap-private-context-packet-v1" and
                packet.get("gap_index") == i and
                packet.get("status") == "CONTEXT_EXPANDED__NOT_AI_REVIEWED" and
                packet.get("source_world_graph_gate") == "HOLD" and
                packet.get("final_heldout_seal") == "NOT_PERFORMED" and
                packet.get("original_private_index_sha256") ==
                coverage.PINNED_INDEX_SHA256,
                "PACKET_SCOPE_INVALID")
        contexts = packet.get("private_candidate_contexts")
        require(isinstance(contexts, list) and len(contexts) <= 10 and
                len(contexts) == entry.get("private_candidate_count"),
                "PACKET_CONTEXT_COUNT_INVALID")
        seen = set()
        for src in contexts:
            require(isinstance(src, dict), "PACKET_CONTEXT_NOT_OBJECT")
            rank, pos = src.get("source_rank"), src.get("original_source_message_index")
            require(type(rank) is int and rank in RANKS and
                    type(pos) is int and pos >= 0 and
                    (rank, pos) not in seen and
                    src.get("index_excerpt_verbatim_checked") is True,
                    "PACKET_SOURCE_PROVENANCE_INVALID")
            seen.add((rank, pos))
        packets.append(packet)
    return manifest, packets, manifest_sha


def summarize(manifest: dict, packets: list[dict], manifest_sha: str,
              decision: dict, workpaper_sha: str) -> dict:
    require(decision.get("schema") ==
            "storyforge-r50-w17-seven-gap-independent-ai-workpaper-v1",
            "WORKPAPER_SCHEMA_MISMATCH")
    require(decision.get("reviewed_packet_manifest_sha256") == manifest_sha,
            "WORKPAPER_MANIFEST_DIGEST_MISMATCH")
    require(decision.get("source_kit_sha256") == coverage.PINNED_KIT_SHA256 and
            decision.get("prior_private_decision_sha256") ==
            coverage.PINNED_DECISION_SHA256,
            "WORKPAPER_SOURCE_HASH_MISMATCH")
    require(decision.get("semantic_world_graph_gate") == "HOLD" and
            decision.get("heldout_final_seal") == "NOT_PERFORMED" and
            decision.get("model_promotion") is False,
            "PREMATURE_SEMANTIC_PASS_OR_MODEL_PROMOTION")
    entries = decision.get("gap_reviews")
    require(isinstance(entries, list) and len(entries) == 7,
            "EXACT_SEVEN_WORKPAPER_REVIEWS_REQUIRED")
    counts: Counter[str] = Counter()
    safe = []
    for i, row in enumerate(entries):
        require(isinstance(row, dict) and type(row.get("gap_index")) is int and
                row["gap_index"] == i, "WORKPAPER_GAP_ORDER_INVALID")
        outcome = row.get("assessment")
        require(type(outcome) is str and outcome in ASSESSMENTS,
                "WORKPAPER_ASSESSMENT_INVALID")
        refs = row.get("source_refs")
        require(isinstance(refs, list) and len(refs) <= 10,
                "WORKPAPER_SOURCE_REFS_INVALID")
        existing = {
            (e["source_rank"], e["original_source_message_index"])
            for e in packets[i]["private_candidate_contexts"]
        }
        seen = set()
        full_count = 0
        for ref in refs:
            require(isinstance(ref, dict) and type(ref.get("source_rank")) is int
                    and type(ref.get("source_message_index")) is int,
                    "WORKPAPER_REFERENCE_FORMAT_INVALID")
            key = (ref["source_rank"], ref["source_message_index"])
            require(key in existing and key not in seen,
                    "WORKPAPER_REFERENCE_NOT_IN_PINNED_PACKET")
            seen.add(key)
            checked_full = ref.get("full_untruncated_message_reviewed")
            require(type(checked_full) is bool,
                    "WORKPAPER_FULL_MESSAGE_REVIEW_NOT_BOOL")
            # The packet itself must contain the COMPLETE original message.
            # A reviewer might separately see more, but the private packets
            # cannot attest that unseen material was read.
            source = next(
                item for item in packets[i]["private_candidate_contexts"]
                if (item["source_rank"],
                    item["original_source_message_index"]) == key
            )
            fully_contained = (
                source.get("focus_start_character") == 0
                and source.get("focus_is_truncated") is False
                and isinstance(source.get("focus_excerpt"), str)
                and type(source.get("original_message_codepoints")) is int
                and len(source["focus_excerpt"]) ==
                source["original_message_codepoints"]
                and digest(source["focus_excerpt"].encode("utf8")) ==
                source.get("original_message_sha256")
            )
            require(not checked_full or fully_contained,
                    "FULL_MESSAGE_CLAIM_NOT_SUPPORTED_BY_PACKET")
            full_count += int(checked_full)
        reason = row.get("private_reasoning")
        require(type(reason) is str and 30 <= len(reason.strip()) <= 5000,
                "WORKPAPER_PRIVATE_REASONING_MISSING")
        timing = row.get("historical_card_timing")
        require(timing in CARD_TIMINGS,
                "WORKPAPER_HISTORICAL_CARD_STATUS_INVALID")
        needs = row.get("remaining_evidence_requirements")
        require(isinstance(needs, list) and len(needs) <= 12 and
                all(type(n) is str and 1 <= len(n.strip()) <= 400 for n in needs),
                "WORKPAPER_REMAINING_REQUIREMENTS_INVALID")
        # Even a source-supported scoped excerpt is NOT a graph PASS.
        if outcome == "SUPPORTED_IN_SCOPED_CONTEXT":
            require(bool(refs), "SUPPORTED_GAP_NEEDS_EXISTING_SOURCE_REF")
        if outcome in ("INSUFFICIENT_CONTEXT", "SOURCE_UNAVAILABLE"):
            require(bool(needs), "OPEN_GAP_MUST_DECLARE_MISSING_EVIDENCE")
        counts[outcome] += 1
        safe.append({
            "gap_index": i, "assessment": outcome,
            "source_reference_count": len(refs),
            "reported_full_message_review_count": full_count,
            "historical_card_timing": timing,
            "remaining_requirement_count": len(needs),
        })
    return {
        "schema": "storyforge-r50-w17-seven-gap-sanitized-independent-review-v1",
        "reviewed_packet_manifest_sha256": manifest_sha,
        "private_workpaper_sha256": workpaper_sha,
        "reviewer_substantive_independence_verified": False,
        "assessments": safe,
        "assessment_counts": {key: counts[key] for key in sorted(ASSESSMENTS)},
        "semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "no_raw_story_or_reviewer_reasoning_emitted": True,
        "no_git_mutation": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--packets-dir", required=True, type=Path)
    p.add_argument("--workpaper", required=True, type=Path)
    a = p.parse_args()
    repo = a.repo.resolve()
    wp = a.workpaper.expanduser().absolute()
    require((repo / ".git").exists() and repo not in wp.parents and
            not wp.is_symlink() and wp.is_file() and
            stat.S_IMODE(wp.stat().st_mode) & 0o077 == 0,
            "PRIVATE_WORKPAPER_NOT_SAFE")
    manifest, packets, manifest_sha = load_manifest(
        a.packets_dir.expanduser().absolute()
    )
    raw = wp.read_bytes()
    workpaper = json.loads(raw)
    result = summarize(manifest, packets, manifest_sha,
                       workpaper, digest(raw))
    print("R50_W17_SEVEN_GAP_INDEPENDENT_AI_WORKPAPER_VALIDATED__SEMANTIC_HOLD")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as e:
        print("R50_W17_SEVEN_GAP_WORKPAPER_HOLD:", type(e).__name__,
              str(e)[:125], file=sys.stderr)
        sys.exit(2)

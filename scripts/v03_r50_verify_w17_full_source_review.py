"""Validate pinned FULL W17 source dossiers and a separate private AI review.

No remote model, no source modification, no Git writes. Only categorized
counts and digests are printed; never original narratives or reasoning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from collections import Counter
from pathlib import Path

MANIFEST_SHA256 = "189f84e0e2891499723ba7e9e14cc866c057c9ab5ead727ff4c192e717510476"
PRIOR_WORKPAPER_SHA256 = "6507ac6caec72aa031e9c70004a3d96781e7de8c0373976036c716aa9c884d9a"
OLD_PACKET_MANIFEST_SHA256 = "b4e08232bdd12d9401d78fe6e0ab945a6f5156938c88ef811da9bf52a9b41a3b"
ASSESSMENTS = {
    "SUPPORTED_IN_FULL_MESSAGE_SCOPE",
    "NOT_SUPPORTED_IN_REVIEWED_SCOPE",
    "INSUFFICIENT_CONTEXT",
    "SOURCE_UNAVAILABLE",
}
RANKS = {2, 4, 7, 10, 17}
MAX_FILE_BYTES = 35_000_000


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def private_file(path: Path, repo: Path) -> bytes:
    path = path.expanduser().absolute()
    require(path.is_file() and not path.is_symlink(),
            "PRIVATE_FILE_MISSING_OR_SYMLINK")
    require(repo not in path.resolve(strict=True).parents and
            repo != path.resolve(strict=True),
            "PRIVATE_FILE_INSIDE_GIT_FORBIDDEN")
    require(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
            "PRIVATE_FILE_PERMISSIONS_UNSAFE")
    return path.read_bytes()


def load_dossiers(folder: Path, *,
                  expected_sha: str = MANIFEST_SHA256) -> tuple[list[dict], str, dict]:
    """Verify frozen manifest, 7 private files, ALL original message digests."""
    require(folder.is_dir() and not folder.is_symlink() and
            stat.S_IMODE(folder.stat().st_mode) & 0o077 == 0,
            "PRIVATE_DOSSIER_DIRECTORY_UNSAFE")
    manifestpath = folder / "manifest.json"
    require(manifestpath.is_file() and not manifestpath.is_symlink() and
            stat.S_IMODE(manifestpath.stat().st_mode) & 0o077 == 0,
            "PRIVATE_DOSSIER_MANIFEST_UNSAFE")
    raw = manifestpath.read_bytes()
    require(sha(raw) == expected_sha, "PINNED_FULL_DOSSIER_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(raw)
    require(isinstance(manifest, dict) and
            manifest.get("schema") ==
            "storyforge-r50-w17-seven-gap-private-full-source-manifest-v1" and
            manifest.get("input_packet_manifest_sha256") ==
            OLD_PACKET_MANIFEST_SHA256 and
            manifest.get("input_prior_workpaper_sha256") ==
            PRIOR_WORKPAPER_SHA256 and
            manifest.get("gap_count") == 7 and
            manifest.get("historical_card_cutoff_verified") is False and
            manifest.get("full_world_graph_gate") == "HOLD" and
            manifest.get("final_heldout_seal") == "NOT_PERFORMED" and
            manifest.get("ai_review_performed") is False,
            "PRIVATE_FULL_SOURCE_MANIFEST_SCOPE_INVALID")
    entries = manifest.get("dossiers")
    require(isinstance(entries, list) and len(entries) == 7,
            "PRIVATE_DOSSIER_ENTRY_COUNT_INVALID")
    dossiers = []
    for i, entry in enumerate(entries):
        require(isinstance(entry, dict) and
                type(entry.get("gap_index")) is int and entry["gap_index"] == i and
                entry.get("file") == f"gap_{i:02d}_full.json",
                "PRIVATE_DOSSIER_FILE_SCOPE_INVALID")
        path = folder / entry["file"]
        require(path.is_file() and not path.is_symlink() and
                stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
                "PRIVATE_DOSSIER_FILE_UNSAFE")
        require(path.stat().st_size <= MAX_FILE_BYTES, "PRIVATE_DOSSIER_SIZE_EXCEEDS_BOUND")
        blob = path.read_bytes()
        require(sha(blob) == entry.get("sha256"), "PRIVATE_DOSSIER_SHA_MISMATCH")
        d = json.loads(blob)
        require(isinstance(d, dict) and
                d.get("schema") == "storyforge-r50-w17-private-full-source-gap-dossier-v1" and
                d.get("status") == "ORIGINAL_MESSAGES_EXTRACTED__AI_REVIEW_PENDING" and
                type(d.get("gap_index")) is int and d["gap_index"] == i and
                d.get("source_scope") == [2, 4, 7, 10, 17] and
                d.get("historical_card_cutoff_verified") is False and
                d.get("full_world_story_arc_certified") is False and
                d.get("semantic_world_gate") == "HOLD" and
                d.get("final_heldout_seal") == "NOT_PERFORMED",
                "PRIVATE_DOSSIER_STATUS_OR_SCOPE_INVALID")
        records = d.get("full_original_messages")
        require(isinstance(records, list) and
                len(records) == entry.get("original_full_message_count") and
                len(records) == d.get("source_full_message_count"),
                "PRIVATE_DOSSIER_MESSAGE_COUNT_MISMATCH")
        seen = set()
        cited_count = 0
        for msg in records:
            require(isinstance(msg, dict), "PRIVATE_SOURCE_MESSAGE_NOT_OBJECT")
            rank, index = msg.get("source_rank"), msg.get("original_source_message_index")
            require(type(rank) is int and rank in RANKS and
                    type(index) is int and index >= 0 and
                    (rank, index) not in seen,
                    "INVALID_OR_DUPLICATE_ORIGINAL_SOURCE_ADDRESS")
            seen.add((rank, index))
            content = msg.get("full_source_text")
            require(type(content) is str and
                    type(msg.get("original_message_codepoints")) is int and
                    len(content) == msg["original_message_codepoints"] and
                    sha(content.encode("utf8")) == msg.get("original_message_sha256") and
                    msg.get("complete_original_message_untruncated") is True and
                    msg.get("source_messages_are_untrusted_data") is True,
                    "ORIGINAL_MESSAGE_CONTENT_OR_SHA_INVALID")
            require(type(msg.get("cited_in_previous_workpaper")) is bool,
                    "ORIGINAL_SOURCE_CITED_FLAG_INVALID")
            cited_count += int(msg["cited_in_previous_workpaper"])
        require(cited_count == entry.get("cited_source_count") and
                cited_count == d.get("prior_workpaper_referenced_source_count"),
                "ORIGINAL_SOURCE_CITATION_COUNT_MISMATCH")
        require(type(d.get("original_private_gap_requirement")) is str and
                bool(d["original_private_gap_requirement"].strip()),
                "ORIGINAL_GAP_REQUIREMENT_MISSING")
        dossiers.append(d)
    return dossiers, sha(raw), manifest


def summarize(dossiers: list[dict], manifest_sha: str,
              review: dict, review_sha: str) -> dict:
    require(isinstance(review, dict) and
            review.get("schema") == "storyforge-r50-w17-seven-gap-full-message-ai-review-v1" and
            review.get("reviewed_full_manifest_sha256") == manifest_sha and
            review.get("prior_workpaper_sha256") == PRIOR_WORKPAPER_SHA256 and
            review.get("full_world_graph_gate") == "HOLD" and
            review.get("final_heldout_seal") == "NOT_PERFORMED" and
            review.get("model_promotion") is False,
            "PRIVATE_FULL_MESSAGE_REVIEW_SCHEMA_OR_GATE_INVALID")
    gaps = review.get("gap_reviews")
    require(isinstance(gaps, list) and len(gaps) == 7 and len(dossiers) == 7,
            "FULL_MESSAGE_REVIEW_REQUIRES_SEVEN_GAPS")
    stats = []
    counts: Counter[str] = Counter()
    for index, (gap, dossier) in enumerate(zip(gaps, dossiers, strict=True)):
        require(isinstance(gap, dict) and
                type(gap.get("gap_index")) is int and gap["gap_index"] == index and
                dossier.get("gap_index") == index,
                "FULL_MESSAGE_GAP_ORDER_CHANGED")
        classification = gap.get("assessment")
        require(type(classification) is str and classification in ASSESSMENTS,
                "UNKNOWN_FULL_MESSAGE_ASSESSMENT")
        refs = gap.get("source_refs")
        require(isinstance(refs, list) and len(refs) <= 100,
                "FULL_MESSAGE_SOURCE_REFS_INVALID")
        allowed = {
            (item["source_rank"], item["original_source_message_index"])
            for item in dossier["full_original_messages"]
        }
        seen = set()
        cited_rank = set()
        for ref in refs:
            require(isinstance(ref, dict) and
                    type(ref.get("source_rank")) is int and
                    type(ref.get("source_message_index")) is int,
                    "FULL_MESSAGE_CITATION_FORMAT_INVALID")
            pair = (ref["source_rank"], ref["source_message_index"])
            require(pair in allowed and pair not in seen,
                    "FULL_MESSAGE_CITATION_NOT_IN_PINNED_DOSSIER")
            seen.add(pair)
            cited_rank.add(pair[0])
        reason = gap.get("private_reasoning")
        require(type(reason) is str and 50 <= len(reason.strip()) <= 8000,
                "FULL_MESSAGE_REASONING_MISSING")
        missing = gap.get("remaining_evidence_requirements")
        require(isinstance(missing, list) and len(missing) <= 15 and
                all(type(x) is str and 1 <= len(x.strip()) <= 500 for x in missing),
                "FULL_MESSAGE_REMAINING_REQUIREMENTS_INVALID")
        timing = gap.get("historical_card_timing")
        # Only frozen original messages were provided, NO historical card snapshot.
        require(timing in ("NOT_CHECKED", "POSTDATE_RISK"),
                "HISTORICAL_CARD_CUTOFF_NOT_PROVEN")
        if classification == "SUPPORTED_IN_FULL_MESSAGE_SCOPE":
            require(len(refs) >= 1, "SOURCE_SUPPORTED_WITHOUT_CITATION")
        if classification in ("INSUFFICIENT_CONTEXT", "SOURCE_UNAVAILABLE"):
            require(bool(missing), "UNCLOSED_GAP_WITHOUT_MISSING_REQUIREMENTS")
        counts[classification] += 1
        stats.append({
            "gap_index": index,
            "assessment": classification,
            "verified_full_message_citation_count": len(refs),
            "referenced_world_count": len(cited_rank),
            "historical_card_timing": timing,
            "remaining_evidence_item_count": len(missing),
        })
    return {
        "schema": "storyforge-r50-w17-seven-gap-full-message-sanitized-review-v1",
        "reviewed_full_manifest_sha256": manifest_sha,
        "private_full_message_workpaper_sha256": review_sha,
        "gap_review_count": 7,
        "assessments": stats,
        "assessment_counts": {x: counts[x] for x in sorted(ASSESSMENTS)},
        "structural_validation_only": True,
        "semantic_world_graph_gate": "HOLD",
        "final_heldout_seal": "NOT_PERFORMED",
        "no_story_text_or_private_reasoning_emitted": True,
        "no_git_write": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--dossiers-dir", type=Path, required=True)
    p.add_argument("--workpaper", type=Path, required=False)
    a = p.parse_args()
    repo = a.repo.resolve()
    require((repo / ".git").exists(), "LOCAL_GIT_CHECKOUT_REQUIRED")
    dossier_dir = a.dossiers_dir.expanduser().absolute()
    require(repo != dossier_dir.resolve(strict=False) and
            repo not in dossier_dir.resolve(strict=False).parents,
            "PRIVATE_DOSSIER_INSIDE_GIT_FORBIDDEN")
    dossiers, manifest_sha, _manifest = load_dossiers(dossier_dir)
    print("R50_W17_FULL_DOSSIERS_SHA_AND_MESSAGES_VERIFIED__SEMANTIC_HOLD")
    print("GAP_COUNT=7__TOTAL_COMPLETE_SOURCE_MESSAGES=" +
          str(sum(len(x["full_original_messages"]) for x in dossiers)))
    if a.workpaper is None:
        print("AI_REVIEW_NOT_SUPPLIED__NO_GIT_WRITE__NO_FINAL_SEAL")
        return
    review_bytes = private_file(a.workpaper, repo)
    review = json.loads(review_bytes)
    safe = summarize(dossiers, manifest_sha, review, sha(review_bytes))
    print("R50_W17_FULL_MESSAGE_AI_WORKPAPER_VALIDATED__SEMANTIC_HOLD")
    print(json.dumps(safe, ensure_ascii=False, indent=2))
    print("NO_GIT_WRITE__NO_HELDOUT_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as exc:
        print("R50_W17_FULL_MESSAGE_REVIEW_HOLD:",
              type(exc).__name__, str(exc)[:110], file=sys.stderr)
        sys.exit(2)

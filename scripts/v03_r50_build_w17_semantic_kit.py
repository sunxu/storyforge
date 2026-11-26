"""Build a private W17 AI review kit from immutable local source files.

Output ONLY to a new 0600 file outside Git. No inference, GPU, HF or Git write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import v03_r50_full_original_world_inventory as inventory
import v03_r50_w17_source_overlap as overlap

OLD_RANKS = (2, 4, 7, 10)
EXPECTED_PAIRS = {(2, 17), (4, 17), (10, 17)}
SOURCE_SHA = "a197923e1e15344e8c98bd96e593e84781b68c83"


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def frozen_w17_card(repo: Path) -> dict:
    receipt = json.loads((repo / inventory.RECEIPT).read_text(encoding="utf8"))
    require(receipt["source_commit"] == SOURCE_SHA, "SOURCE_COMMIT_MISMATCH")
    entry = next(item for item in receipt["worlds"] if item["number"] == 17)
    root = repo / inventory.ROOT / entry["folder"]
    paths = (root / (entry["folder"] + ".jsonl"), root / "story-cards.json")
    for path in paths:
        require(path.is_file() and not path.is_symlink(), "W17_REQUIRED_FILE_MISSING")
        relative = path.relative_to(repo).as_posix()
        matches = [item for item in receipt["files"] if item["path"] == relative]
        require(len(matches) == 1, "W17_FROZEN_BLOB_RECEIPT_MISSING")
        raw = path.read_bytes()
        require(len(raw) == matches[0]["size_bytes"] and
                git_blob_sha(raw) == matches[0]["git_blob_sha1"],
                "W17_FROZEN_BLOB_MISMATCH")
    return json.loads(paths[1].read_text(encoding="utf8"))


def excerpts(source: dict, text: str) -> dict:
    messages = source["messages"]
    matched = []
    for i, message in enumerate(messages):
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            continue
        if overlap.normalize(message["content"]) != text:
            continue
        neighborhood = []
        for j in range(max(0, i - 2), min(len(messages), i + 3)):
            m = messages[j]
            if not isinstance(m, dict):
                continue
            content = m.get("content")
            neighborhood.append({
                "relative_offset": j - i,
                "role": m.get("role") if m.get("role") in
                        ("user", "assistant", "system") else "other",
                "text_excerpt": content[:750] if isinstance(content, str) else "",
                "excerpt_truncated": isinstance(content, str) and len(content) > 750,
            })
        matched.append({"source_message_index": i, "neighbors": neighborhood})
    return {"matched_message_occurrences": len(matched),
            "context_examples": matched[:4],
            "occurrence_count_truncated": len(matched) > 4}


def kit_from_sources(old: dict[int, dict], new: dict,
                     card: dict, literal: str) -> dict:
    require(len(literal) >= 80, "SHARED_LITERAL_NOT_LONG")
    sources = {}
    for rank in OLD_RANKS:
        info = excerpts(old[rank], literal)
        if rank != 7:
            require(info["matched_message_occurrences"] > 0,
                    "OLD_MATCHED_SOURCE_LITERAL_MISSING")
        story = old[rank].get("story")
        if rank == 7:
            # This linked old world has no exact W17 literal. Supply limited
            # surrounding source context as a review hint, never a conclusion.
            source_messages = [
                item for item in old[rank]["messages"]
                if isinstance(item, dict) and isinstance(item.get("content"), str)
            ]
            samples = (source_messages[:3] + source_messages[-3:])
            info["linked_world_07_context_sample"] = [
                {"role": item.get("role") if item.get("role") in
                         ("assistant", "user", "system") else "other",
                 "text_excerpt": item["content"][:550],
                 "excerpt_truncated": len(item["content"]) > 550}
                for item in samples
            ]
        sources[str(rank)] = {
            "old_rank": rank,
            "known_link_to_old_04": rank == 7,
            **info,
            "story_metadata_excerpt":
                json.dumps(story, ensure_ascii=False)[:2500]
                if isinstance(story, dict) else "",
        }
    newinfo = excerpts(new, literal)
    require(newinfo["matched_message_occurrences"] > 0,
            "W17_MATCHED_SOURCE_LITERAL_MISSING")
    exported = card.get("export_time_card") or {}
    v2 = exported.get("v2_data") if isinstance(exported, dict) else None
    if not isinstance(v2, dict):
        v2 = {}
    char = v2.get("characters")
    chars = []
    if isinstance(char, list):
        for entry in char[:20]:
            if isinstance(entry, dict):
                chars.append({
                    "name": str(entry.get("name", ""))[:100],
                    "brief": str(entry.get("description") or
                                 entry.get("background") or
                                 entry.get("personality") or "")[:1200],
                })
    return {
        "schema": "storyforge-r50-w17-private-ai-semantic-kit-v1",
        "privacy": "PRIVATE UNREDACTED SOURCE MATERIAL - NEVER COMMIT TO GIT",
        "status": "PRIVATE_EVIDENCE_BUILT__AI_REVIEW_PENDING",
        "linked_old_ranks": list(OLD_RANKS),
        "known_historical_link": [4, 7],
        "exact_flagged_pairs": [[2, 17], [4, 17], [10, 17]],
        "shared_literal_322_codepoints": literal,
        "old_world_contexts": sources,
        "w17_context": newinfo,
        "w17_export_card_review_hints": {
            "version_id": str(exported.get("id", ""))[:100],
            "character_briefs": chars,
            "world": json.dumps(v2.get("world"), ensure_ascii=False)[:2200],
            "opening": json.dumps(v2.get("opening"), ensure_ascii=False)[:1200],
            "WARNING": "Export-time card is not automatically valid at test cutoff",
        },
        "independent_ai_review_instructions": [
            "Is the exact 322-character Assistant text generic boilerplate, OOC instruction, or distinctive plot?",
            "Does W17 share the same real character, alias, organization, unique setting or event with old 02,04,10?",
            "Could the known old 04-to-07 world link extend transitively to W17?",
            "Support each pair judgement with source context; unresolved evidence => INSUFFICIENT_EVIDENCE.",
            "These excerpts are bounded; do not certify full semantic graph from this kit alone.",
        ],
        "allowed_pair_judgements": ["CLEAR_WITH_EVIDENCE", "WORLD_LINK",
                                   "INSUFFICIENT_EVIDENCE"],
        "semantic_world_alias_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--old14", required=True, type=Path)
    p.add_argument("--old06-15", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    repo, out = a.repo.resolve(), a.output.resolve()
    require(repo != out and repo not in out.parents and not out.exists(),
            "PRIVATE_OUTPUT_MUST_BE_NEW_OUTSIDE_GIT")
    inventory.verify_zip(a.old14, "old14")
    inventory.verify_zip(a.old06_15, "old06_15")
    source_all = inventory.old14_data(a.old14)
    old15 = inventory.old15_data(a.old06_15)
    old = {k: (old15 if k == 15 else source_all[k]) for k in OLD_RANKS}
    new = inventory.new_data(repo)
    card = frozen_w17_card(repo)
    analysis, literals, _ = overlap.diagnose(
        {k: old[k] for k in (2, 4, 10)}, {17: new[17]})
    pairs = {(x["old_rank"], x["new_rank"]) for x in analysis["flagged_pairs"]}
    require(pairs == EXPECTED_PAIRS, "THREE_SOURCE_FLAGS_CHANGED")
    require(len(literals) == 1, "ONE_SHARED_LITERAL_NOT_REPRODUCED")
    literal = next(iter(literals))
    require(len(literal) == 322, "EXPECTED_322_CHAR_LITERAL_NOT_REPRODUCED")
    report = kit_from_sources(old, new[17], card, literal)
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require((out.parent.stat().st_mode & 0o077) == 0,
            "PRIVATE_OUTPUT_PARENT_PERMISSIONS_UNSAFE")
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf8")
    fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
    print("R50_W17_PRIVATE_AI_KIT_BUILT__SEMANTIC_REVIEW_PENDING")
    print("KIT_SHA256=" + hashlib.sha256(payload).hexdigest())
    print("NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as e:
        print("R50_W17_AI_KIT_HOLD:", type(e).__name__, str(e)[:120], file=sys.stderr)
        sys.exit(2)

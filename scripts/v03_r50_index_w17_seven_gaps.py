"""Seven-gap private lexical source locator for StoryForge R50 W17.

This is a NON-SEMANTIC evidence locator. Source text stays in a private
mode-0600 output outside Git. Nothing is published, inferred or approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path

import v03_r50_build_w17_semantic_kit as kit_builder
import v03_r50_full_original_world_inventory as inventory
import v03_r50_verify_w17_ai_decisions as verifier

RECEIPT = Path(
    "docs/evidence/V03_R50_W17_AI_SEMANTIC_DECISION_SAFE_SUMMARY_20261019.json"
)
SCOPED_RANKS = (2, 4, 7, 10, 17)
MISSING_COUNT = 7
PER_WORLD_CANDIDATES = 2
MAX_EXCERPT = 1000


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\W+", "", value, flags=re.UNICODE)


def ngrams(value: str) -> set[str]:
    value = normalized(value)
    return {value[i:i + size] for size in (2, 3)
            for i in range(max(0, len(value) - size + 1))}


def candidate_messages(query: str, source: dict,
                       *, max_results: int = PER_WORLD_CANDIDATES) -> list[dict]:
    """Rank bounded source excerpts by character n-gram overlap, NOT semantics."""
    wanted = ngrams(query)
    if not wanted:
        return []
    candidates = []
    rows = source.get("messages")
    verifier.guard(isinstance(rows, list), "SOURCE_MESSAGES_NOT_LIST")
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("content"), str):
            continue
        body = row["content"]
        if len(body.strip()) < 12:
            continue
        grams = ngrams(body[:12000])
        hits = wanted & grams
        if not hits:
            continue
        # Always prefer relatively distinctive 3-character matches over
        # generic two-character vocabulary; this is still only retrieval.
        tri = sum(len(x) == 3 for x in hits)
        score = tri * 3 + (len(hits) - tri)
        excerpt_at = 0
        for token in sorted(hits, key=lambda x: (-len(x), x)):
            location = body.casefold().find(token)
            if location >= 0:
                excerpt_at = max(0, location - 300)
                break
        excerpt = body[excerpt_at:excerpt_at + MAX_EXCERPT]
        candidates.append({
            "source_message_index": i,
            "source_role": row.get("role") if row.get("role") in
                           ("user", "assistant", "system") else "other",
            "lexical_ranking_score": score,
            "matched_ngram_count": len(hits),
            "matched_trigram_count": tri,
            "excerpt_start_character": excerpt_at,
            "excerpt": excerpt,
            "excerpt_truncated": len(body) > excerpt_at + MAX_EXCERPT,
        })
    candidates.sort(key=lambda row: (
        -row["lexical_ranking_score"], -row["matched_trigram_count"],
        row["source_message_index"]
    ))
    return candidates[:max_results]


def build_inventory(gaps: list[str], sources: dict[int, dict]) -> dict:
    verifier.guard(len(gaps) == MISSING_COUNT and
                   all(type(g) is str and 1 <= len(g.strip()) <= 400 for g in gaps),
                   "SEVEN_EXACT_PRIVATE_GAPS_REQUIRED")
    verifier.guard(set(sources) == set(SCOPED_RANKS),
                   "W17_SCOPED_SOURCE_RANKS_MISMATCH")
    result = []
    for index, requirement in enumerate(gaps):
        by_source = {}
        for rank in SCOPED_RANKS:
            by_source[str(rank)] = {
                "source_rank": rank,
                "ranked_candidates": candidate_messages(requirement, sources[rank]),
            }
        result.append({
            "gap_index": index,
            "requirement_from_original_private_ai_decision": requirement,
            "candidate_source_excerpts": by_source,
            "evidence_status": "UNREVIEWED",
            "reviewer_instruction": (
                "Read the real original context and source metadata; check "
                "aliases, singular events, character identity and timepoint. "
                "High lexical ranking does NOT establish semantic support."
            ),
        })
    return {
        "schema": "storyforge-r50-w17-seven-gap-private-source-locator-v1",
        "status": "SEVEN_GAP_LEXICAL_LOCATOR_ONLY__AI_REVIEW_NOT_EXECUTED",
        "source_ranks": list(SCOPED_RANKS),
        "known_old_04_to_07_link": "HOLD_REQUIRE_TRANSITIVE_REVIEW",
        "gap_count": MISSING_COUNT,
        "gaps": result,
        "world_graph_admission": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "no_ai_model_inference": True,
        "no_git_write": True,
        "privacy": "Contains raw private AI requirements and source excerpts; NEVER commit.",
    }


def read_sources(repo: Path, old14_zip: Path) -> dict[int, dict]:
    inventory.verify_zip(old14_zip, "old14")
    old = inventory.old14_data(old14_zip)
    verifier.guard({2, 4, 7, 10} <= set(old), "OLD_SOURCE_COVERAGE_INCOMPLETE")
    # Source receipt and W17 transcript/card blob SHA1 and sizes must match.
    kit_builder.frozen_w17_card(repo)
    all_new = inventory.new_data(repo)
    return {**{rank: old[rank] for rank in (2, 4, 7, 10)},
            17: all_new[17]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--kit", required=True, type=Path)
    p.add_argument("--decisions", required=True, type=Path)
    p.add_argument("--old14", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    repo = a.repo.resolve()
    output = a.output.expanduser().absolute()
    verifier.guard((repo / ".git").exists(), "LOCAL_GIT_CHECKOUT_REQUIRED")
    verifier.guard(repo not in output.parents and output != repo,
                   "PRIVATE_OUTPUT_INSIDE_GIT_FORBIDDEN")
    verifier.guard(not output.exists() and not output.is_symlink(),
                   "PRIVATE_OUTPUT_ALREADY_EXISTS_OR_SYMLINK")
    kit_raw = verifier.checked_private(a.kit, repo, "KIT")
    dec_raw = verifier.checked_private(a.decisions, repo, "DECISION")
    verifier.validate(kit_raw, dec_raw)

    archived = json.loads((repo / RECEIPT).read_text(encoding="utf8"))
    verifier.guard(verifier.sha(dec_raw) == archived.get("private_decision_sha256"),
                   "ARCHIVED_PRIVATE_DECISION_HASH_MISMATCH")
    decision = verifier.parse(dec_raw, "DECISION")
    sources = read_sources(repo, a.old14)
    report = build_inventory(decision["remaining_evidence_requirements"], sources)
    report["kit_sha256"] = verifier.PINNED_KIT_SHA256
    report["decision_sha256"] = verifier.sha(dec_raw)
    report["source_scope_note"] = (
        "Four relevant old originals plus W17 original transcript. "
        "This is not the full 50-pair graph or timepoint-card audit."
    )

    parent = output.parent
    verifier.guard(parent.is_dir() and not parent.is_symlink(),
                   "PRIVATE_OUTPUT_DIR_MISSING_OR_SYMLINK")
    verifier.guard(stat.S_IMODE(parent.stat().st_mode) & 0o077 == 0,
                   "PRIVATE_OUTPUT_DIR_NOT_0700")
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    print("R50_W17_SEVEN_GAP_PRIVATE_SOURCE_INDEX_BUILT__SEMANTIC_HOLD")
    print("GAP_COUNT=7__SOURCE_RANK_COUNT=5__AI_REVIEW_NOT_EXECUTED")
    print("PRIVATE_INDEX_SHA256=" + hashlib.sha256(payload).hexdigest())
    print("NO_GIT_WRITE__NO_GPU__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            json.JSONDecodeError) as error:
        print("R50_W17_SEVEN_GAP_INDEX_HOLD:", type(error).__name__,
              str(error)[:120], file=sys.stderr)
        sys.exit(2)

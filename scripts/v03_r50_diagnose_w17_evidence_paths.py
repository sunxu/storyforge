"""Locally classify W17 reviewer evidence-path failures without exposing paths/text.

Never performs AI inference, alters decisions, writes files or touches Git.
Runs against exact SHA-pinned private KIT; prints only safe structural enums,
source ranks and pointer indices. No source text or reviewer reasoning.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import v03_r50_verify_w17_ai_decisions as verifier

KNOWN_ROOTS = {
    "old_world_contexts": "OLD_SOURCE_CONTEXTS",
    "w17_context": "W17_SOURCE_CONTEXT",
    "w17_export_card_review_hints": "W17_CARD_HINTS",
    "shared_literal_322_codepoints": "SHARED_LITERAL",
    "known_historical_link": "HISTORICAL_GRAPH_METADATA",
    "exact_flagged_pairs": "PAIR_SCOPE_METADATA",
    "linked_old_ranks": "SOURCE_SCOPE_METADATA",
    "independent_ai_review_instructions": "REVIEW_INSTRUCTIONS_NOT_EVIDENCE",
}
PAIR_SET = {(2, 17), (4, 17), (10, 17)}


def safe_classification(kit: dict, raw: str, *, old_rank: int,
                        pointer_index: int) -> dict:
    """Never include raw citation, arbitrary path components or raw kit values."""
    result = {
        "old_rank": old_rank,
        "pointer_index": pointer_index,
        "grammar": "NOT_CHECKED",
        "root_class": "UNKNOWN",
        "referenced_old_rank": None,
        "scope": "NOT_CHECKED",
        "exists_in_pinned_kit": False,
        "is_nonempty": False,
        "recommended_action": "KEEP_SEMANTIC_HOLD_AND_INSPECT_PRIVATELY",
    }
    try:
        tokens = verifier.canonical_evidence_path(raw)
    except (TypeError, ValueError):
        result["grammar"] = "INVALID_OR_UNSUPPORTED"
        result["scope"] = "NOT_CHECKED"
        return result
    result["grammar"] = "VALID"
    result["root_class"] = KNOWN_ROOTS.get(tokens[0], "UNKNOWN")
    if (len(tokens) > 1 and tokens[0] == "old_world_contexts" and
            tokens[1] in {"2", "4", "7", "10"}):
        result["referenced_old_rank"] = int(tokens[1])
    try:
        cat = verifier.evidence_scope(tokens, old_rank)
        result["scope"] = "ALLOWED_" + cat.upper()
    except ValueError:
        result["scope"] = "OUTSIDE_SCOPED_ALLOWLIST"
    try:
        value = verifier.resolve_evidence(kit, tokens)
        result["exists_in_pinned_kit"] = True
        result["is_nonempty"] = verifier.meaningful_evidence(value)
    except (ValueError, TypeError):
        pass
    if result["scope"].startswith("ALLOWED_") and result["exists_in_pinned_kit"]:
        result["recommended_action"] = "STRUCTURALLY_ACCEPTED"
    elif result["exists_in_pinned_kit"] and result["scope"] == "OUTSIDE_SCOPED_ALLOWLIST":
        result["recommended_action"] = "VALID_KIT_FIELD_REQUIRES_HUMAN_SCOPE_REVIEW"
    elif result["grammar"] == "VALID":
        result["recommended_action"] = "INVALID_CITATION__REVIEWER_MUST_CORRECT"
    else:
        result["recommended_action"] = "UNSUPPORTED_SYNTAX__REVIEWER_MUST_RECHECK"
    return result


def diagnose(kit: dict, decision: dict) -> dict:
    pairs = decision.get("pair_reviews")
    verifier.guard(isinstance(pairs, list) and len(pairs) == 3,
                   "INVALID_REVIEW_PAIRS")
    seen: set[tuple[int, int]] = set()
    inspections = []
    for row in pairs:
        verifier.guard(isinstance(row, dict), "INVALID_REVIEW_PAIR")
        pair = (row.get("old_rank"), row.get("new_rank"))
        verifier.guard(pair in PAIR_SET and pair not in seen,
                       "INVALID_OR_DUPLICATE_REVIEW_PAIR")
        seen.add(pair)
        citations = row.get("fact_evidence_paths")
        verifier.guard(isinstance(citations, list) and 1 <= len(citations) <= 12,
                       "INVALID_PAIR_EVIDENCE_LIST")
        for i, raw in enumerate(citations):
            inspections.append(safe_classification(
                kit, raw, old_rank=pair[0], pointer_index=i
            ))
    verifier.guard(seen == PAIR_SET, "MISSING_REQUIRED_REVIEW_PAIR")
    failures = [x for x in inspections
                if x["recommended_action"] != "STRUCTURALLY_ACCEPTED"]
    return {
        "schema": "storyforge-r50-w17-private-evidence-path-diagnostic-v1",
        "kit_sha256_pinned": verifier.PINNED_KIT_SHA256,
        "pair_count": 3,
        "pointers_checked": len(inspections),
        "flags": failures,
        "semantic_world_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "private_text_or_full_citation_emitted": False,
        "reviewer_decisions_modified": False,
        "files_written": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--decisions", type=Path, required=True)
    args = ap.parse_args()
    repo = args.repo.resolve()
    verifier.guard((repo / ".git").exists(), "LOCAL_GIT_REPO_REQUIRED")
    kit_bytes = verifier.checked_private(args.kit, repo, "KIT")
    decision_bytes = verifier.checked_private(args.decisions, repo, "DECISION")
    verifier.guard(verifier.sha(kit_bytes) == verifier.PINNED_KIT_SHA256,
                   "PRIVATE_KIT_SHA256_MISMATCH")
    kit = verifier.parse(kit_bytes, "KIT")
    decision = verifier.parse(decision_bytes, "DECISION")
    result = diagnose(kit, decision)
    print("R50_W17_AI_EVIDENCE_PATH_DIAGNOSTIC_DONE__SEMANTIC_HOLD")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as exc:
        print("R50_W17_EVIDENCE_PATH_DIAGNOSTIC_HOLD:",
              type(exc).__name__, str(exc)[:100], file=sys.stderr)
        sys.exit(2)

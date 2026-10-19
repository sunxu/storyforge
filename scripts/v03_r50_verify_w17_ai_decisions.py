"""Validate a private independent W17 AI review; archive only sanitized enums.

This does not perform AI inference or semantic adjudication. No raw story
text or private rationale is written to Git, CI, stdout or the summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path

PINNED_KIT_SHA256 = "0c1dccd8de0926ab416a85ccb77f474e668138938171f0419eb43ce582a99cc3"
AUDIT_BRANCH = "audit/r49-r50-source-intake-20261015"
EVIDENCE_PATH = "docs/evidence/V03_R50_W17_AI_SEMANTIC_DECISION_SAFE_SUMMARY_20261019.json"
PAIRS = {(2, 17), (4, 17), (10, 17)}
DECISIONS = {"CLEAR_WITH_EVIDENCE", "WORLD_LINK", "INSUFFICIENT_EVIDENCE"}
LITERAL_TYPES = {"PLATFORM_TEMPLATE", "GENERIC_DIALOGUE",
                 "STORY_SPECIFIC", "UNCERTAIN"}
TRANSITIVE = {"YES", "NO_WITH_EVIDENCE", "INSUFFICIENT_EVIDENCE"}


def guard(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse(raw: bytes, name: str) -> dict:
    doc = json.loads(raw.decode("utf8"))
    guard(isinstance(doc, dict), f"{name}_NOT_JSON_OBJECT")
    return doc


# Canonical dotted and bracketed JSON evidence pointers; no arbitrary traversal.
BRACKET_KEY = re.compile(r"""\[['"]([A-Za-z_][A-Za-z0-9_]*|[0-9]+)['"]\]""")
BRACKET_INDEX = re.compile(r"\[([0-9]+)\]")
SEGMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")


def canonical_evidence_path(raw: str) -> tuple[str, ...]:
    guard(type(raw) is str and 1 <= len(raw) <= 280,
          "UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH")
    s = raw.strip().strip(chr(96)).strip()
    if s.startswith("$."):
        s = s[2:]
    elif s.startswith("$["):
        s = s[1:]
    s = BRACKET_KEY.sub(r".\1", s)
    s = BRACKET_INDEX.sub(r".\1", s)
    s = s.lstrip(".")
    parts = s.split(".")
    guard(1 <= len(parts) <= 16 and
          all(SEGMENT.fullmatch(part) is not None for part in parts) and
          all(not part.isdecimal() or len(part) <= 3 for part in parts),
          "UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH")
    return tuple(parts)


def evidence_scope(parts: tuple[str, ...], old_rank: int) -> str:
    """Constrain evidence to this old rank, linked 07, W17 or shared literal."""
    if parts == ("shared_literal_322_codepoints",):
        return "context"
    if len(parts) >= 3 and parts[:2] == ("old_world_contexts", str(old_rank)):
        if parts[2] in ("context_examples", "story_metadata_excerpt"):
            return "old"
        if parts[2] in ("matched_message_occurrences",
                        "occurrence_count_truncated"):
            return "context"
    if (len(parts) >= 3 and parts[:2] == ("old_world_contexts", "7") and
            parts[2] == "linked_world_07_context_sample"):
        return "context"
    if parts == ("w17_context",):
        return "new"
    if len(parts) >= 2 and parts[0] == "w17_context":
        if parts[1] == "context_examples":
            return "new"
        if parts[1] in ("matched_message_occurrences",
                        "occurrence_count_truncated"):
            return "context"
    if parts == ("w17_export_card_review_hints",):
        return "new"
    if len(parts) >= 2 and parts[0] == "w17_export_card_review_hints":
        if parts[1] in ("world", "opening", "character_briefs", "version_id"):
            return "new"
    raise ValueError("UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH")


def resolve_evidence(kit: dict, parts: tuple[str, ...]) -> object:
    node: object = kit
    for segment in parts:
        if isinstance(node, dict):
            guard(segment in node, "EVIDENCE_PATH_NOT_FOUND_IN_PINNED_KIT")
            node = node[segment]
        elif isinstance(node, list):
            guard(segment.isdecimal() and int(segment) < len(node),
                  "EVIDENCE_PATH_NOT_FOUND_IN_PINNED_KIT")
            node = node[int(segment)]
        else:
            raise ValueError("EVIDENCE_PATH_NOT_FOUND_IN_PINNED_KIT")
    return node


def meaningful_evidence(value: object) -> bool:
    return value is not None and value is not False and value != "" and (
        not isinstance(value, (dict, list)) or bool(value)
    )


def checked_evidence_paths(kit: dict, paths: list[str], old_rank: int,
                           decision: str) -> None:
    strong_old = strong_new = 0
    seen: set[tuple[str, ...]] = set()
    for index, raw in enumerate(paths):
        try:
            parts = canonical_evidence_path(raw)
            guard(parts not in seen, "DUPLICATE_CANONICAL_EVIDENCE_PATH")
            seen.add(parts)
            category = evidence_scope(parts, old_rank)
            value = resolve_evidence(kit, parts)
            if category == "old" and meaningful_evidence(value):
                strong_old += 1
            elif category == "new" and meaningful_evidence(value):
                strong_new += 1
        except ValueError as exc:
            # Pointer values may contain private data: never echo them.
            raise ValueError(
                f"{exc}__OLD_RANK_{old_rank}__POINTER_INDEX_{index}"
            ) from None
    if decision != "INSUFFICIENT_EVIDENCE":
        guard(strong_old > 0 and strong_new > 0,
              "STRONG_PAIR_DECISION_REQUIRES_TWO_SOURCE_ANCHORS")


def validate(kit_raw: bytes, decision_raw: bytes,
             *, expected_kit_sha: str = PINNED_KIT_SHA256) -> dict:
    """Strictly validate hashes, declared evidence paths and review schema."""
    guard(sha(kit_raw) == expected_kit_sha, "PINNED_PRIVATE_KIT_SHA_MISMATCH")
    kit = parse(kit_raw, "KIT")
    decision = parse(decision_raw, "DECISION")
    guard(kit.get("schema") == "storyforge-r50-w17-private-ai-semantic-kit-v1",
          "KIT_SCHEMA_MISMATCH")
    guard(kit.get("status") == "PRIVATE_EVIDENCE_BUILT__AI_REVIEW_PENDING" and
          kit.get("semantic_world_alias_gate") == "HOLD" and
          kit.get("heldout_final_seal") == "NOT_PERFORMED",
          "KIT_HAS_INVALID_GATE_STATUS")
    guard(kit.get("exact_flagged_pairs") == [[2, 17], [4, 17], [10, 17]],
          "KIT_PAIR_SCOPE_CHANGED")
    guard(kit.get("known_historical_link") == [4, 7], "KIT_LINK_SCOPE_CHANGED")
    shared = kit.get("shared_literal_322_codepoints")
    guard(isinstance(shared, str) and len(shared) == 322,
          "KIT_LITERAL_LENGTH_MISMATCH")
    contexts = kit.get("old_world_contexts")
    guard(isinstance(contexts, dict) and set(contexts) == {"2", "4", "7", "10"},
          "KIT_OLD_WORLD_CONTEXT_SCOPE_CHANGED")
    guard(isinstance(kit.get("w17_context"), dict),
          "KIT_W17_CONTEXT_MISSING")

    must_equal = {
        "schema": "storyforge-r50-w17-private-ai-semantic-adjudication-v1",
        "status": "INDEPENDENT_AI_REVIEW__NOT_FINAL_SEAL",
        "reviewed_kit_sha256": expected_kit_sha,
        "known_04_07_graph_edge": "LINKED_CONFIRMED_IN_PRIOR_SCOPE",
        "full_semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "model_promotion": False,
    }
    for key, expected in must_equal.items():
        guard(type(decision.get(key)) is type(expected) and
              decision[key] == expected, f"DECISION_FIELD_MISMATCH_{key}")

    literal_type = decision.get("shared_literal_type")
    guard(type(literal_type) is str and literal_type in LITERAL_TYPES,
          "SHARED_LITERAL_CLASSIFICATION_INVALID")
    literal_reason = decision.get("shared_literal_evidence")
    guard(type(literal_reason) is str and 8 <= len(literal_reason.strip()) <= 300,
          "SHARED_LITERAL_EVIDENCE_MISSING_OR_OVERSIZED")
    records = decision.get("pair_reviews")
    guard(isinstance(records, list) and len(records) == 3,
          "REQUIRED_THREE_PAIR_REVIEWS")
    seen = set()
    counts: Counter[str] = Counter()
    safe_pairs = []
    for row in records:
        guard(isinstance(row, dict), "INVALID_PAIR_REVIEW")
        old, new = row.get("old_rank"), row.get("new_rank")
        guard(type(old) is int and type(new) is int and
              (old, new) in PAIRS and (old, new) not in seen,
              "INVALID_OR_DUPLICATE_PAIR")
        seen.add((old, new))
        vote = row.get("decision")
        guard(type(vote) is str and vote in DECISIONS,
              "INVALID_PAIR_DECISION")
        reasons = row.get("reasoning")
        guard(type(reasons) is str and 15 <= len(reasons.strip()) <= 8000,
              "PAIR_REASONING_MISSING_OR_OVERSIZED")
        paths = row.get("fact_evidence_paths")
        guard(isinstance(paths, list) and 1 <= len(paths) <= 12 and
              all(type(x) is str for x in paths) and len(paths) == len(set(paths)),
              "PAIR_EVIDENCE_PATHS_INVALID")
        checked_evidence_paths(kit, paths, old, vote)
        counts[vote] += 1
        safe_pairs.append({
            "old_rank": old,
            "new_rank": new,
            "decision": vote,
            "evidence_pointer_count": len(paths),
        })
    guard(seen == PAIRS, "THREE_PAIR_SCOPE_MISMATCH")
    link = decision.get("possible_transitive_link_to_w17")
    guard(type(link) is str and link in TRANSITIVE,
          "TRANSITIVE_LINK_CONCLUSION_INVALID")
    remaining = decision.get("remaining_evidence_requirements")
    guard(isinstance(remaining, list) and len(remaining) <= 30 and
          all(type(x) is str and 1 <= len(x.strip()) <= 400 for x in remaining),
          "MISSING_EVIDENCE_LIST_INVALID")
    if counts["INSUFFICIENT_EVIDENCE"] or link == "INSUFFICIENT_EVIDENCE":
        guard(bool(remaining), "INSUFFICIENT_REVIEW_MISSING_REQUIREMENTS")

    return {
        "schema": "storyforge-r50-w17-sanitized-ai-review-verification-v1",
        "review_source": "OWNER_LOCAL_PRIVATE_AI_REVIEW",
        "verification": "KIT_AND_DECISION_SHA_SCHEMA_AND_RESOLVED_EVIDENCE_POINTERS_ONLY",
        "reviewer_independence_or_correctness_verified_by_script": False,
        "private_kit_sha256": expected_kit_sha,
        "private_decision_sha256": sha(decision_raw),
        "scoped_pair_count": 3,
        "pair_decisions": sorted(safe_pairs, key=lambda r: r["old_rank"]),
        "decision_counts": {key: counts[key] for key in sorted(DECISIONS)},
        "shared_literal_type": literal_type,
        "known_04_07_graph_edge": "LINKED_CONFIRMED_IN_PRIOR_SCOPE",
        "possible_transitive_link_to_w17": link,
        "remaining_evidence_item_count": len(remaining),
        "full_semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "r50_cases_modified": False,
        "model_promotion": False,
        "no_model_generation_or_gpu_by_this_validator": True,
        "privacy": "No raw shared literal, source conversations, free-text rationales, character names, or per-case data in Git.",
    }


def checked_private(path: Path, repo: Path, name: str) -> bytes:
    path = path.expanduser().absolute()
    guard(repo != path and repo not in path.parents,
          f"{name}_FILE_INSIDE_GIT_FORBIDDEN")
    guard(path.is_file() and not path.is_symlink(),
          f"{name}_FILE_MISSING_OR_SYMLINK")
    guard(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
          f"{name}_FILE_NOT_PRIVATE_0600")
    return path.read_bytes()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args],
                                   text=True).strip()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--kit", type=Path, required=True)
    p.add_argument("--decisions", type=Path, required=True)
    p.add_argument("--push", action="store_true", help="Explicit safe Git commit and push")
    a = p.parse_args()
    repo = a.repo.resolve()
    guard((repo / ".git").exists(), "LOCAL_GIT_REPO_REQUIRED")
    kit_raw = checked_private(a.kit, repo, "KIT")
    dec_raw = checked_private(a.decisions, repo, "DECISION")
    result = validate(kit_raw, dec_raw)
    print("R50_W17_PRIVATE_AI_DECISIONS_SCHEMA_VALIDATED__SEMANTIC_HOLD")
    print(json.dumps({"pair_decisions": result["pair_decisions"],
                      "shared_literal_type": result["shared_literal_type"],
                      "possible_transitive_link_to_w17":
                          result["possible_transitive_link_to_w17"],
                      "remaining_evidence_item_count":
                          result["remaining_evidence_item_count"]},
                     ensure_ascii=False))
    if a.push:
        guard(git(repo, "branch", "--show-current") == AUDIT_BRANCH,
              "WRONG_AUDIT_BRANCH")
        guard(not git(repo, "status", "--porcelain"), "GIT_WORKTREE_DIRTY")
        destination = repo / EVIDENCE_PATH
        guard(not destination.exists(), "SANITIZED_EVIDENCE_ALREADY_EXISTS")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2)
                               + "\n", encoding="utf8")
        git(repo, "add", "--", EVIDENCE_PATH)
        git(repo, "commit", "-m",
            "audit(r50): archive privacy-safe W17 independent AI decision summary",
            "--", EVIDENCE_PATH)
        git(repo, "push", "origin", f"HEAD:refs/heads/{AUDIT_BRANCH}")
        print("R50_W17_SAFE_AI_REVIEW_SUMMARY_PUSHED__SEMANTIC_HOLD")
    else:
        print("DRY_RUN_NO_GIT_WRITE__USE_PUSH_ONLY_AFTER_REVIEW")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError,
            subprocess.CalledProcessError) as exc:
        print("R50_W17_PRIVATE_AI_REVIEW_VALIDATION_HOLD:",
              type(exc).__name__, str(exc)[:190], file=sys.stderr)
        sys.exit(2)

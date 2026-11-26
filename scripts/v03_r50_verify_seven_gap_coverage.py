"""Read-only W17 seven-gap lexical source-coverage verifier.

Only prints counts/rank numbers. Does not load a model, modify files, infer
world identity, print gap requirements, or expose narrative excerpts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

PINNED_INDEX_SHA256 = "4ef2ba639183311b62c3b755bfd12f58176294734fea6259ae71fef327782694"
PINNED_KIT_SHA256 = "0c1dccd8de0926ab416a85ccb77f474e668138938171f0419eb43ce582a99cc3"
PINNED_DECISION_SHA256 = "61e4aa21370c2f9f8ef84d648fb600f51e2fa151e30e25999bb328f23da581bf"
RANKS = (2, 4, 7, 10, 17)
EXPECTED_SCHEMA = "storyforge-r50-w17-seven-gap-private-source-locator-v1"


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def summarize(report: dict) -> dict:
    """Validate the private index structure before returning aggregate counts."""
    require(isinstance(report, dict) and report.get("schema") == EXPECTED_SCHEMA,
            "INDEX_SCHEMA_MISMATCH")
    require(report.get("status") ==
            "SEVEN_GAP_LEXICAL_LOCATOR_ONLY__AI_REVIEW_NOT_EXECUTED",
            "SOURCE_INDEX_SEMANTIC_STATUS_MISMATCH")
    require(report.get("source_ranks") == list(RANKS),
            "INDEX_SOURCE_RANK_SCOPE_MISMATCH")
    require(type(report.get("gap_count")) is int and report["gap_count"] == 7,
            "INDEX_GAP_COUNT_MISMATCH")
    require(report.get("kit_sha256") == PINNED_KIT_SHA256,
            "INDEX_KIT_DIGEST_MISMATCH")
    require(report.get("decision_sha256") == PINNED_DECISION_SHA256,
            "INDEX_DECISION_DIGEST_MISMATCH")
    require(report.get("world_graph_admission") == "HOLD" and
            report.get("heldout_final_seal") == "NOT_PERFORMED" and
            report.get("no_ai_model_inference") is True and
            report.get("no_git_write") is True,
            "INDEX_ADMISSION_STATUS_UNSAFE")

    gaps = report.get("gaps")
    require(isinstance(gaps, list) and len(gaps) == 7,
            "SEVEN_ACTUAL_REVIEW_GAPS_REQUIRED")
    per_gap = []
    total = 0
    for index, gap in enumerate(gaps):
        require(isinstance(gap, dict) and
                type(gap.get("gap_index")) is int and
                gap["gap_index"] == index, "INVALID_GAP_INDEX_OR_ORDER")
        text = gap.get("requirement_from_original_private_ai_decision")
        require(type(text) is str and 1 <= len(text.strip()) <= 400,
                "MISSING_OR_INVALID_GAP_REQUIREMENT")
        require(gap.get("evidence_status") == "UNREVIEWED",
                "UNAUTHORIZED_GAP_ADJUDICATION_STATUS")
        entries = gap.get("candidate_source_excerpts")
        require(isinstance(entries, dict) and set(entries) ==
                {str(rank) for rank in RANKS},
                "INVALID_GAP_SOURCE_COVERAGE")
        per_source = {}
        for rank in RANKS:
            entry = entries[str(rank)]
            require(isinstance(entry, dict) and
                    type(entry.get("source_rank")) is int and
                    entry["source_rank"] == rank, "SOURCE_RANK_MISMATCH")
            candidates = entry.get("ranked_candidates")
            require(isinstance(candidates, list) and len(candidates) <= 2,
                    "TOO_MANY_OR_INVALID_SOURCE_CANDIDATES")
            seen = set()
            for candidate in candidates:
                require(isinstance(candidate, dict), "INVALID_SOURCE_CANDIDATE")
                number = candidate.get("source_message_index")
                require(type(number) is int and number >= 0 and
                        number not in seen, "INVALID_DUPLICATE_MESSAGE_INDEX")
                seen.add(number)
                excerpt = candidate.get("excerpt")
                require(type(excerpt) is str and len(excerpt) <= 1000,
                        "INVALID_OR_OVERSIZED_PRIVATE_EXCERPT")
                score = candidate.get("lexical_ranking_score")
                require(type(score) is int and score >= 1,
                        "INVALID_LEXICAL_RANKING_SCORE")
            per_source[str(rank)] = len(candidates)
            total += len(candidates)
        per_gap.append({
            "gap_index": index,
            "candidate_count_by_source_rank": per_source,
            "candidate_count": sum(per_source.values()),
            "worlds_with_lexical_candidates":
                sum(count > 0 for count in per_source.values()),
            "no_lexical_candidate_is_not_evidence_of_absence": True,
            "review_status": "UNREVIEWED",
        })
    return {
        "schema": "storyforge-r50-w17-seven-gap-lexical-coverage-summary-v1",
        "source": "PRIVATE_INDEX_SHA_PINNED_OWNER_SIDE_VERIFICATION",
        "gap_count": 7,
        "source_world_count": 5,
        "source_ranks": list(RANKS),
        "total_bounded_lexical_candidates": total,
        "per_gap": per_gap,
        "semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "private_requirements_or_source_excerpts_emitted": False,
        "no_model_inference": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--index", type=Path, required=True)
    args = p.parse_args()
    repo = args.repo.resolve()
    path = args.index.expanduser().absolute()
    require((repo / ".git").exists(), "REPO_CHECKOUT_REQUIRED")
    require(not path.is_symlink() and path.is_file() and
            repo != path and repo not in path.parents,
            "PRIVATE_INDEX_MISSING_OR_INSIDE_GIT")
    require(not path.parent.is_symlink() and
            stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0 and
            stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
            "PRIVATE_INDEX_PERMISSIONS_UNSAFE")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PINNED_INDEX_SHA256,
            "PRIVATE_INDEX_SHA256_MISMATCH")
    report = json.loads(raw.decode("utf8"))
    result = summarize(report)
    print("R50_W17_SEVEN_GAP_INDEX_COVERAGE_VERIFIED__SEMANTIC_HOLD")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            json.JSONDecodeError) as exc:
        print("R50_W17_GAP_COVERAGE_HOLD:", type(exc).__name__,
              str(exc)[:140], file=sys.stderr)
        sys.exit(2)

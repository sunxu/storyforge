"""R51: create a private, source-linked HOLD worksheet for frozen Gold195.

No source text in Git, terminal output or CI artifacts. No row is approved.
Run on an authorized local checkout only, with a private output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

import v03_r51_gold195_readiness as baseline

SCHEMA = "storyforge-r51-private-gold195-triage-v1"
UNDECIDED = "UNDECIDED__SOURCE_ANCHORED_REVIEW_REQUIRED"
HOLD = "PENDING_NOT_APPROVED"
SOURCE_KEYS = (
    "story_id", "source_story_id", "transcript_id", "session_id",
    "source_session_id", "target_message_id", "target_turn_index",
    "source_turn_index", "source_json_pointer", "source_message_array_index",
    "source_message_ids", "history_source_message_ids",
    "source_turn_indices", "history_source_turn_indices",
    "source_file", "source_archive", "source_archive_path",
    "source_jsonl_member", "source_sha256", "source_archive_sha256",
    "source_jsonl_sha256", "source_zip_sha256",
)


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def flags_for(cohort: int, metadata: dict) -> tuple[bool, bool, bool]:
    if cohort == 87:
        card = "UNVERIFIED" in str(metadata.get("story_card_status", ""))
        pointer = metadata.get("source_json_pointer") is None
    else:
        card = (
            metadata.get("story_card_as_of_target") == "NOT_AVAILABLE_NOT_INJECTED"
            or "UNVERIFIED" in str(metadata.get("story_card_status", ""))
            or "UNVERIFIED" in str(metadata.get("target_time_story_card", ""))
        )
        pointer = (metadata.get("source_message_array_index") is None
                   and metadata.get("source_json_pointer") is None)
    age = metadata.get("source_character_age") == "UNSPECIFIED"
    return card, pointer, age


def make_rows(gold87: list[dict], gold108: list[dict],
              index108: list[dict]) -> tuple[list[dict], dict]:
    # Reject mutated targets, stale index, duplicate source identities and
    # premature approval using the existing real-source readiness contract.
    baseline.inspect_rows(gold87, gold108, index108)
    work: list[dict] = []
    patterns: Counter[str] = Counter()
    risks: Counter[str] = Counter()
    for cohort, source in ((87, gold87), (108, gold108)):
        for offset, row in enumerate(source):
            meta = row["metadata"]
            rank = (int(str(meta["source_file"])[:2]) if cohort == 87
                    else int(index108[offset]["story_number"]))
            card, pointer, age = flags_for(cohort, meta)
            marks = [
                key for key, present in (
                    ("CARD_EVIDENCE_EXPLICITLY_UNVERIFIED", card),
                    ("SOURCE_INDEX_METADATA_ABSENT", pointer),
                    ("AGE_UNSPECIFIED", age),
                ) if present
            ]
            holds = ["CONTENT_OR_RIGHTS_HOLD"]
            if pointer:
                holds.append("SOURCE_POINTER_RECONCILIATION_HOLD")
            # Missing/uncertain card metadata does not prove dependence on
            # the card. Only source-grounded reviewer evidence may assign
            # CONTEXT_ONLY_POSSIBLE or CARD_OR_LONG_RANGE_SOURCE_REQUIRED.
            pattern = ("C" if card else "-") + ("P" if pointer else "-") + (
                "A" if age else "-")
            patterns[pattern] += 1
            risks.update(marks)
            target = row["messages"][-1]["content"]
            work.append({
                "schema": SCHEMA,
                "candidate_id": row["id"],
                "cohort": cohort,
                "source_rank": rank,
                "source_story_id": meta.get("story_id") or meta.get("source_story_id"),
                "original_target_message_id": meta["target_message_id"],
                "original_target_sha256": digest(target),
                "source_reference": {k: meta[k] for k in SOURCE_KEYS
                                     if k in meta and meta[k] is not None},
                "history_fingerprints": [
                    {"role": m["role"], "sha256": digest(m["content"])}
                    for m in row["messages"][:-1]
                ],
                "metadata_risks": marks,
                "historical_card_certified": False,
                "source_archive_replay": "NOT_PERFORMED",
                "triage_route": UNDECIDED,
                "holds": holds,
                "source_review": {
                    "source_anchor_citations": [],
                    "source_pointer_verified": "PENDING",
                    "source_replay_and_history_contiguity": "PENDING",
                    "fact_visibility_at_target_cutoff": "PENDING",
                    "context_only_sufficiency": "PENDING",
                    "card_or_long_range_dependency": "PENDING",
                    "card_version_or_rule_evidence": [],
                    "age_and_consent": "PENDING",
                    "rights_and_license": "PENDING",
                    "forbidden_rule_compliance": "PENDING",
                    "player_agency": "PENDING",
                    "semantic_world_component": None,
                    "exposed_test_and_heldout_isolation": "PENDING",
                    "reviewer_1": {"decision": "PENDING", "citations": []},
                    "reviewer_2": {"decision": "PENDING", "citations": []},
                },
                "training_admission": HOLD,
                "split": None,
            })
    assert len(work) == 195
    summary = {
        "schema": "storyforge-r51-gold195-metadata-triage-counts-v1",
        "source": "FROZEN_GOLD195_METADATA__NOT_FULL_ARCHIVE_REPLAY",
        "rows_created_for_private_review": len(work),
        "explicit_card_unverified": risks["CARD_EVIDENCE_EXPLICITLY_UNVERIFIED"],
        "source_index_metadata_absent": risks["SOURCE_INDEX_METADATA_ABSENT"],
        "age_unspecified": risks["AGE_UNSPECIFIED"],
        "flag_intersections": {
            "card_only": patterns["C--"],
            "card_and_age": patterns["C-A"],
            "pointer_only": patterns["-P-"],
            "none_of_these_three": patterns["---"],
            "other_patterns": sum(v for k, v in patterns.items()
                                  if k not in ("C--", "C-A", "-P-", "---")),
        },
        "unreviewed_rights_or_agency_hold": len(work),
        "source_pointer_reconciliation_hold": sum(
            "SOURCE_POINTER_RECONCILIATION_HOLD" in r["holds"] for r in work),
        "context_only_routes_decided": 0,
        "card_dependent_routes_decided": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "world_split_assigned": 0,
        "source_content_review": "NOT_PERFORMED",
        "github_output_contains_candidate_identifiers": False,
        "r45_holds_reopened": False,
        "r50_heldout_read_or_rewritten": False,
    }
    return work, summary


def write_private(output: Path, rows: list[dict], repo: Path) -> None:
    """Exclusive-create mode 0600, with no Git-tree or public directory writes."""
    out = output.expanduser().absolute()
    root = repo.resolve()
    if out == root or root in out.parents:
        raise ValueError("PRIVATE_WORKPAPER_CANNOT_BE_WRITTEN_INSIDE_GIT_REPOSITORY")
    for ancestor in (out, *out.parents):
        if ancestor.is_symlink():
            raise ValueError("PRIVATE_WORKPAPER_SYMLINK_PATH_FORBIDDEN")
    if not out.parent.is_dir():
        raise ValueError("CREATE_PRIVATE_DIRECTORY_FIRST_WITH_MODE_0700")
    if stat.S_IMODE(out.parent.stat().st_mode) & 0o077:
        raise ValueError("PRIVATE_WORKPAPER_PARENT_MUST_BE_MODE_0700")
    content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True)
                      + "\n" for row in rows)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(out, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New private local JSONL file (parent mode 0700)")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        repo = args.repo.resolve(strict=True)
        # Complete SHA-pinned cohort checks must run before worksheet creation.
        baseline.run(repo)
        a = baseline.read_pinned_rows(
            repo, baseline.GOLD87, 87,
            blob_sha1=baseline.EXPECTED_GIT_SHA1_87)
        b = baseline.read_pinned_rows(
            repo, baseline.GOLD108, 108,
            sha256_digest=baseline.EXPECTED_SHA256_108)
        idx = baseline.read_gold108_index(repo)
        rows, summary = make_rows(a, b, idx)
        write_private(args.output, rows, repo)
    except (OSError, ValueError, KeyError, TypeError, AssertionError,
            json.JSONDecodeError) as exc:
        print("R51_PRIVATE_TRIAGE_HOLD:", type(exc).__name__,
              str(exc)[:100], file=sys.stderr)
        return 2
    print("R51_PRIVATE_GOLD195_HOLD_WORKPAPER_CREATED__NO_ADMISSION")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

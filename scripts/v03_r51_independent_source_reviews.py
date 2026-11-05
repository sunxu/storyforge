"""R51: distribute private Gold108 review tasks to two independent reviewers.

No story content goes to stdout, Git or CI. Reviews are source-cited
context-only feasibility judgments, NOT final dataset admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path

from v03_r51_gold195_private_triage import write_private

TASK_SCHEMA = "storyforge-r51-independent-context-review-task-v1"
RESULT_SCHEMA = "storyforge-r51-independent-context-review-result-v1"
RECON_SCHEMA = "storyforge-r51-private-two-reviewer-reconciliation-v1"
INPUT_SCHEMA = "storyforge-r51-private-gold108-context-review-packet-v1"
ROUTES = {
    "CONTEXT_ONLY_POSSIBLE__HOLD",
    "CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD",
    "INSUFFICIENT_VISIBLE_CONTEXT__HOLD",
    "TARGET_AGENCY_OR_RULE_CONCERN__HOLD",
}
SCOPES = {
    "FROZEN_VISIBLE",
    "PREVIOUS_SOURCE_NOT_IN_INPUT",
    "TARGET",
}


def demand(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)

# Only these fixed parser/validator messages may be exposed as error codes.
# Never echo exception strings originating from original story files or paths.
SAFE_ERROR_REASONS = frozenset({
    "PRIVATE_FILE_MISSING_OR_SYMLINK",
    "PRIVATE_FILE_PERMISSIONS_UNSAFE",
    "PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE",
    "PRIVATE_PATH_SYMLINK",
    "PRIVATE_FILE_EMPTY_OR_INVALID",
    "R51_EXPECTED_108_PACKETS",
    "R51_PACKET_PROVENANCE_OR_ADMISSION_CHANGED",
    "R51_PACKET_DUPLICATE_CANDIDATE",
    "R51_FIRST_ROLE_MISSING",
    "R51_PACKET_BODY_HASH_OR_WINDOW_INVALID",
    "R51_WINDOW_OR_PREVIEW_MISSING",
    "R51_PACKET_SOURCE_CITATION_HASH_CHANGED",
    "BATCH_SIZE_OUT_OF_RANGE",
    "GOLD108_EXPECTED_EIGHT_STORY_RANKS",
    "R51_BATCH_COVERAGE_INVALID",
    "BATCH_NUMBER_OUT_OF_RANGE",
    "UNKNOWN_REVIEWER",
    "REVIEWER_INCOMPLETE_BATCH",
    "REVIEWER_DUPLICATE_OR_UNKNOWN_CANDIDATE",
    "REVIEWER_RESPONSE_SCHEMA_OR_PIN_INVALID",
    "REVIEWER_SOURCE_REASON_REQUIRED",
    "REVIEWER_SOURCE_CITATIONS_REQUIRED",
    "REVIEWER_CITATION_INVALID",
    "REVIEWER_CITATION_NOT_IN_AUTHENTIC_PACKET",
    "REVIEWER_CITATION_DUPLICATED",
    "CONTEXT_ONLY_REQUIRES_VISIBLE_AND_TARGET_CITATIONS",
    "REVIEWER_CANNOT_ADMIT_TRAINING",
    "REVIEWER_BATCH_COVERAGE_MISMATCH",
    "REVIEWER_TASK_SETS_DIVERGED",
    "OUTPUT_DIRECTORY_NOT_PRIVATE",
    "PREPARE_TAKES_NO_REVIEW_RESULTS",
    "TWO_REVIEW_FILES_REQUIRED",
})


def diagnostic_error(stage: str, error: Exception) -> str:
    reason = str(error)
    code = (reason if isinstance(error, ValueError) and
            reason in SAFE_ERROR_REASONS else type(error).__name__)
    return f"R51_REVIEW_TASK_HOLD__{stage}__{code}"


def read_local(path: Path, *, expected_mode: int = 0o600) -> list[dict]:
    path = path.expanduser().absolute()
    demand(path.is_file() and not path.is_symlink(),
           "PRIVATE_FILE_MISSING_OR_SYMLINK")
    demand(stat.S_IMODE(path.stat().st_mode) == expected_mode,
           "PRIVATE_FILE_PERMISSIONS_UNSAFE")
    demand(stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
           "PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE")
    for ancestor in (path.parent, *path.parent.parents):
        demand(not ancestor.is_symlink(), "PRIVATE_PATH_SYMLINK")
    with path.open(encoding="utf-8") as stream:
        rows = [json.loads(x) for x in stream if x.strip()]
    demand(bool(rows) and all(isinstance(x, dict) for x in rows),
           "PRIVATE_FILE_EMPTY_OR_INVALID")
    return rows


def check_packets(packets: list[dict]) -> None:
    demand(len(packets) == 108, "R51_EXPECTED_108_PACKETS")
    seen = set()
    for p in packets:
        demand(p.get("schema") == INPUT_SCHEMA and
               p.get("private_do_not_commit") is True and
               p.get("training_admission") == "PENDING_NOT_APPROVED" and
               p.get("split") is None and
               p.get("historical_card_version_verified") is False,
               "R51_PACKET_PROVENANCE_OR_ADMISSION_CHANGED")
        identifier = p.get("candidate_id")
        demand(isinstance(identifier, str) and identifier not in seen,
               "R51_PACKET_DUPLICATE_CANDIDATE")
        seen.add(identifier)
        demand(p.get("frozen_visible_first_role") in ("assistant", "user"),
               "R51_FIRST_ROLE_MISSING")
        demand(isinstance(p.get("frozen_visible_history"), list) and
               bool(p["frozen_visible_history"]) and
               isinstance(p.get("target_content_for_review_only"), str) and
               hashlib.sha256(p["target_content_for_review_only"].encode()).hexdigest()
               == p["target_sha256"],
               "R51_PACKET_BODY_HASH_OR_WINDOW_INVALID")
        for group in ("frozen_visible_history",
                      "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"):
            value = p.get(group)
            demand(isinstance(value, list), "R51_WINDOW_OR_PREVIEW_MISSING")
            for msg in value:
                demand(isinstance(msg.get("original_source_array_index"), int)
                       and isinstance(msg.get("content"), str)
                       and hashlib.sha256(msg["content"].encode()).hexdigest()
                       == msg.get("source_body_sha256"),
                       "R51_PACKET_SOURCE_CITATION_HASH_CHANGED")


def batches_for(packets: list[dict], size: int = 24) -> list[list[dict]]:
    demand(1 <= size <= 108, "BATCH_SIZE_OUT_OF_RANGE")
    by_rank: dict[int, list[dict]] = defaultdict(list)
    for p in packets:
        by_rank[p["story_rank"]].append(p)
    demand(len(by_rank) == 8, "GOLD108_EXPECTED_EIGHT_STORY_RANKS")
    for group in by_rank.values():
        group.sort(key=lambda p: (
            p["frozen_visible_first_role"] != "assistant",
            hashlib.sha256(p["candidate_id"].encode()).hexdigest(),
        ))
    ordered: list[dict] = []
    ranks = sorted(by_rank)
    while any(by_rank.values()):
        for rank in ranks:
            if by_rank[rank]:
                ordered.append(by_rank[rank].pop(0))
    demand(len(ordered) == 108 and len({p["candidate_id"] for p in ordered}) == 108,
           "R51_BATCH_COVERAGE_INVALID")
    return [ordered[k:k + size] for k in range(0, 108, size)]


def task_for(packet: dict, reviewer: str, batch: int) -> dict:
    # These are original source excerpts. Nothing before the frozen visible
    # history may be considered visible to the prospective trained model.
    return {
        "schema": TASK_SCHEMA,
        "reviewer": reviewer,
        "batch_number": batch,
        "candidate_id": packet["candidate_id"],
        "story_rank": packet["story_rank"],
        "target_sha256": packet["target_sha256"],
        "target_original_array_index": packet["target_original_array_index"],
        "frozen_visible_history": packet["frozen_visible_history"],
        "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT":
            packet["preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"],
        "target_content_for_review_only":
            packet["target_content_for_review_only"],
        "owner_age_consent_content_attested": True,
        "historical_card_version_verified": False,
        "rights_or_license_certified": False,
        "instruction": (
            "Independently judge whether the EXACT frozen visible history "
            "supports the target response. Prior-source messages are "
            "reviewer-only, NEVER model input. Do not reconstruct unverified "
            "cards or treat an unseen fact as visible. Cite original message "
            "array offsets and body SHA256. Report concerns about player "
            "agency, forbidden rules and hidden dependencies. Keep all "
            "conclusions HOLD and send no data to other reviewer."
        ),
        "permitted_routes": sorted(ROUTES),
        "training_admission": "PENDING_NOT_APPROVED",
    }


def build_batch(packets: list[dict], number: int,
                size: int = 24) -> tuple[dict[str, list[dict]], dict]:
    check_packets(packets)
    groups = batches_for(packets, size)
    demand(1 <= number <= len(groups), "BATCH_NUMBER_OUT_OF_RANGE")
    selected = groups[number - 1]
    tasks = {}
    for reviewer in ("A", "B"):
        tasks[reviewer] = [
            task_for(p, reviewer, number) for p in sorted(
                selected, key=lambda p: hashlib.sha256(
                    (reviewer + ":" + p["candidate_id"]).encode()).hexdigest())
        ]
    tally = Counter(x["frozen_visible_first_role"] for x in selected)
    ranks = Counter(x["story_rank"] for x in selected)
    return tasks, {
        "schema": "storyforge-r51-reviewer-batch-counts-v1",
        "status": "INDEPENDENT_REVIEW_TASKS_PREPARED__NO_REVIEWS_YET",
        "batch": number,
        "batch_count": len(groups),
        "reviewer_A_tasks": len(selected),
        "reviewer_B_tasks": len(selected),
        "unique_candidates": len(selected),
        "first_visible_assistant": tally["assistant"],
        "first_visible_user": tally["user"],
        "story_ranks": {str(k): ranks[k] for k in sorted(ranks)},
        "original_text_or_candidate_ids_in_stdout": False,
        "training_admitted": 0,
    }


def citations_for(packet: dict) -> set[tuple[str, int, str]]:
    references = set()
    for key, scope in (
        ("frozen_visible_history", "FROZEN_VISIBLE"),
        ("preceding_source_preview_NOT_PART_OF_FROZEN_INPUT",
         "PREVIOUS_SOURCE_NOT_IN_INPUT"),
    ):
        for msg in packet[key]:
            references.add((scope, msg["original_source_array_index"],
                            msg["source_body_sha256"]))
    references.add((
        "TARGET", packet["target_original_array_index"],
        packet["target_sha256"]))
    return references


def validate_review(results: list[dict], tasks: list[dict],
                    reviewer: str) -> dict[str, dict]:
    demand(reviewer in ("A", "B"), "UNKNOWN_REVIEWER")
    by_id = {r["candidate_id"]: r for r in tasks}
    demand(len(results) == len(by_id), "REVIEWER_INCOMPLETE_BATCH")
    validated = {}
    for result in results:
        candidate = result.get("candidate_id")
        task = by_id.get(candidate)
        demand(task is not None and candidate not in validated,
               "REVIEWER_DUPLICATE_OR_UNKNOWN_CANDIDATE")
        demand(result.get("schema") == RESULT_SCHEMA and
               result.get("reviewer") == reviewer and
               result.get("batch_number") == task["batch_number"] and
               result.get("target_sha256") == task["target_sha256"] and
               result.get("route") in ROUTES,
               "REVIEWER_RESPONSE_SCHEMA_OR_PIN_INVALID")
        note = result.get("rationale")
        demand(isinstance(note, str) and len(note.strip()) >= 12,
               "REVIEWER_SOURCE_REASON_REQUIRED")
        cites = result.get("source_citations")
        demand(isinstance(cites, list) and len(cites) >= 1,
               "REVIEWER_SOURCE_CITATIONS_REQUIRED")
        grounded = citations_for(task)
        cited = []
        for item in cites:
            demand(isinstance(item, dict), "REVIEWER_CITATION_INVALID")
            triple = (item.get("scope"), item.get("original_source_array_index"),
                      item.get("source_body_sha256"))
            demand(triple[0] in SCOPES and triple in grounded,
                   "REVIEWER_CITATION_NOT_IN_AUTHENTIC_PACKET")
            cited.append(triple)
        demand(len(cited) == len(set(cited)),
               "REVIEWER_CITATION_DUPLICATED")
        if result["route"] == "CONTEXT_ONLY_POSSIBLE__HOLD":
            demand(any(c[0] == "FROZEN_VISIBLE" for c in cited) and
                   any(c[0] == "TARGET" for c in cited),
                   "CONTEXT_ONLY_REQUIRES_VISIBLE_AND_TARGET_CITATIONS")
        demand(result.get("training_admission") ==
               "PENDING_NOT_APPROVED", "REVIEWER_CANNOT_ADMIT_TRAINING")
        validated[candidate] = result
    demand(set(validated) == set(by_id), "REVIEWER_BATCH_COVERAGE_MISMATCH")
    return validated


def reconcile(tasks_A: list[dict], tasks_B: list[dict],
              results_A: list[dict], results_B: list[dict]) -> tuple[list[dict], dict]:
    ids_A = {x["candidate_id"] for x in tasks_A}
    ids_B = {x["candidate_id"] for x in tasks_B}
    demand(ids_A == ids_B and len(ids_A) == len(tasks_A) == len(tasks_B),
           "REVIEWER_TASK_SETS_DIVERGED")
    a = validate_review(results_A, tasks_A, "A")
    b = validate_review(results_B, tasks_B, "B")
    merged = []
    count = Counter()
    for candidate in sorted(ids_A):
        ra, rb = a[candidate], b[candidate]
        agree = ra["route"] == rb["route"]
        if agree:
            count["same_route"] += 1
            count[ra["route"]] += 1
        else:
            count["route_disagreement"] += 1
        merged.append({
            "schema": RECON_SCHEMA,
            "candidate_id": candidate,
            "target_sha256": ra["target_sha256"],
            "reviewer_A": ra,
            "reviewer_B": rb,
            "route": ra["route"] if agree else
                "REVIEWER_DISAGREEMENT__HOLD",
            "approved_training_admission": False,
            "training_admission": "PENDING_NOT_APPROVED",
            "source_window_review_only": True,
            "human_source_or_quality_followup_required": True,
        })
    return merged, {
        "schema": "storyforge-r51-two-reviewer-counts-v1",
        "status": "TWO_INDEPENDENT_REVIEWS_RECONCILED__NO_ADMISSION",
        "reviewed_by_A": len(a),
        "reviewed_by_B": len(b),
        "same_route": count["same_route"],
        "route_disagreement": count["route_disagreement"],
        "agreed_context_only_possible_hold":
            count["CONTEXT_ONLY_POSSIBLE__HOLD"],
        "agreed_card_or_long_range_required_hold":
            count["CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD"],
        "agreed_other_hold":
            count["INSUFFICIENT_VISIBLE_CONTEXT__HOLD"] +
            count["TARGET_AGENCY_OR_RULE_CONCERN__HOLD"],
        "train_admitted": 0,
        "validation_admitted": 0,
        "private_rationales_or_candidate_identifiers_in_stdout": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    parser.add_argument("--private-packets", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--review-A", type=Path)
    parser.add_argument("--review-B", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    stage = "PACKET_READ"
    try:
        packets = read_local(args.private_packets)
        stage = "BATCH_BUILD"
        tasks, receipt = build_batch(packets, args.batch, args.batch_size)
        stage = "OUTPUT_DIRECTORY"
        directory = args.out_dir.expanduser().absolute()
        demand(directory.is_dir() and not directory.is_symlink() and
               stat.S_IMODE(directory.stat().st_mode) & 0o077 == 0,
               "OUTPUT_DIRECTORY_NOT_PRIVATE")
        if args.prepare:
            stage = "TASKS_WRITE"
            demand(args.review_A is None and args.review_B is None,
                   "PREPARE_TAKES_NO_REVIEW_RESULTS")
            for reviewer in ("A", "B"):
                write_private(
                    directory / f"R51_BATCH_{args.batch:02d}_REVIEWER_{reviewer}_TASKS.jsonl",
                    tasks[reviewer], Path.cwd().resolve())
            print("R51_TWO_INDEPENDENT_REVIEW_TASKS_PREPARED__NO_ADMISSION")
        else:
            demand(args.review_A is not None and args.review_B is not None,
                   "TWO_REVIEW_FILES_REQUIRED")
            stage = "REVIEWER_A_READ"
            a = read_local(args.review_A)
            stage = "REVIEWER_B_READ"
            b = read_local(args.review_B)
            stage = "REVIEWER_A_VALIDATE"
            validate_review(a, tasks["A"], "A")
            stage = "REVIEWER_B_VALIDATE"
            validate_review(b, tasks["B"], "B")
            stage = "RECONCILE"
            combined, receipt = reconcile(tasks["A"], tasks["B"], a, b)
            stage = "RECONCILED_WRITE"
            write_private(
                directory / f"R51_BATCH_{args.batch:02d}_RECONCILED_PRIVATE.jsonl",
                combined, Path.cwd().resolve())
            print("R51_TWO_INDEPENDENT_SOURCE_REVIEWS_RECONCILED__NO_ADMISSION")
        print(json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(diagnostic_error(stage, exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

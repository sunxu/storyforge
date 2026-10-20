"""R52: prepare private generic-no-card quality tasks from 62 Gold108 candidates.

This is a *new proposed* visible-history-only learning task, not recovered
historical system prompts. No Train/Val admission, source mutation or GPU.
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

QUEUE_SCHEMA = "storyforge-r52-private-owner-eligibility-queue-v1"
PACKET_SCHEMA = "storyforge-r51-private-gold108-context-review-packet-v1"
TASK_SCHEMA = "storyforge-r52-private-no-card-quality-task-v1"
RESULT_SCHEMA = "storyforge-r52-private-no-card-quality-result-v1"
HOLD = "PENDING_NOT_APPROVED"
CONTEXT = "CONTEXT_ONLY_POSSIBLE__HOLD"
ROUTES = frozenset({
    "NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD",
    "TARGET_PLAYER_AGENCY_DEFECT__HOLD",
    "TARGET_CONTINUITY_OR_FACT_DEFECT__HOLD",
    "HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD",
    "INSUFFICIENT_OR_OTHER_QUALITY_HOLD",
})
BATCH_COUNTS = (16, 16, 16, 14)


class Hold(ValueError):
    pass


def demand(ok: bool, code: str) -> None:
    if not ok:
        raise Hold(code)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_private(path: Path) -> list[dict]:
    path = path.expanduser().absolute()
    demand(path.is_file() and not path.is_symlink(), "PRIVATE_FILE_MISSING")
    demand(stat.S_IMODE(path.stat().st_mode) == 0o600,
           "PRIVATE_FILE_MODE_NOT_0600")
    demand(stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
           "PRIVATE_PARENT_NOT_0700")
    with path.open(encoding="utf8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    demand(bool(rows) and all(isinstance(x, dict) for x in rows),
           "PRIVATE_JSONL_INVALID")
    return rows


def join_context(queue: list[dict], packets: list[dict]) -> list[dict]:
    demand(len(queue) == 62 and len(packets) == 108,
           "EXPECTED_62_QUEUE_AND_108_PACKETS")
    source = {}
    for p in packets:
        cid = p.get("candidate_id")
        body = p.get("target_content_for_review_only")
        demand(isinstance(cid, str) and cid not in source and
               p.get("schema") == PACKET_SCHEMA and
               p.get("private_do_not_commit") is True and
               p.get("training_admission") == HOLD and
               p.get("split") is None and
               p.get("historical_card_version_verified") is False and
               isinstance(body, str) and digest(body) == p.get("target_sha256"),
               "SOURCE_PACKET_PIN_OR_STATUS_INVALID")
        for group in ("frozen_visible_history",
                      "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"):
            messages = p.get(group)
            demand(isinstance(messages, list), "SOURCE_MESSAGE_LIST_MISSING")
            for msg in messages:
                demand(isinstance(msg.get("content"), str) and
                       digest(msg["content"]) == msg.get("source_body_sha256") and
                       type(msg.get("original_source_array_index")) is int,
                       "SOURCE_MESSAGE_SHA_OR_INDEX_INVALID")
        source[cid] = p
    demand(len(source) == 108, "SOURCE_PACKET_DUPLICATED")
    tasks, seen = [], set()
    for row in queue:
        cid = row.get("candidate_id")
        demand(isinstance(cid, str) and cid not in seen and cid in source,
               "QUEUE_CANDIDATE_UNKNOWN_OR_REPEATED")
        seen.add(cid)
        p = source[cid]
        demand(row.get("schema") == QUEUE_SCHEMA and
               row.get("private_do_not_commit") is True and
               row.get("r52_queue") == "context_62" and
               row.get("r51_review_relation") == "A_B_AGREE__HOLD" and
               row.get("reviewer_A_route") == CONTEXT and
               row.get("reviewer_B_route") == CONTEXT and
               row.get("reviewer_C_route") is None and
               row.get("training_admission") == HOLD and
               row.get("owner_rights_status") == "OWNER_ATTESTED_FULL_OWNERSHIP" and
               row.get("world_split") is None and
               row.get("target_sha256") == p["target_sha256"] and
               row.get("story_rank") == p["story_rank"] and
               row.get("source_story_id") == p["source_story_id"] and
               row.get("target_original_array_index") ==
               p["target_original_array_index"],
               "QUEUE_PROVENANCE_OR_HOLD_CHANGED")
        tasks.append({
            "schema": TASK_SCHEMA,
            "private_do_not_commit": True,
            "candidate_id": cid,
            "story_rank": p["story_rank"],
            "source_story_id": p["source_story_id"],
            "target_sha256": p["target_sha256"],
            "target_original_array_index": p["target_original_array_index"],
            "frozen_visible_history": p["frozen_visible_history"],
            "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT":
                p["preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"],
            "target_content_for_review_only": p["target_content_for_review_only"],
            "task_basis": "GENERIC_NO_CARD_VISIBLE_CONTEXT_EXPERIMENT_REVIEW_ONLY",
            "historical_card_asof_verified": False,
            "historical_card_in_model_input": False,
            "prior_preview_in_model_input": False,
            "training_admission": HOLD,
            "permitted_routes": sorted(ROUTES),
            "instruction": (
                "Review the exact TARGET as a prospective supervised reply for "
                "a new no-character-card visible-history task. Cite specific "
                "evidence for chronology, world facts, NPC/player action and "
                "agency, and Chinese narrative quality. Previously unsupervised "
                "Assistant defects are not automatically TARGET defects. "
                "Prior source preview is never model input. Never invent or "
                "reconstruct historical persona cards. Preserve HOLD."
            ),
        })
    tasks.sort(key=lambda x: (x["story_rank"], digest(x["candidate_id"])))
    return tasks


def make_batch(queue: list[dict], packets: list[dict],
               batch: int) -> tuple[list[dict], dict]:
    demand(1 <= batch <= 4, "BATCH_NUMBER_OUT_OF_RANGE")
    all_tasks = join_context(queue, packets)
    start = sum(BATCH_COUNTS[:batch - 1])
    tasks = [dict(x, quality_batch_number=batch) for x in
             all_tasks[start:start + BATCH_COUNTS[batch - 1]]]
    demand(len(tasks) == BATCH_COUNTS[batch - 1], "BATCH_SIZE_CHANGED")
    return tasks, {
        "schema": "storyforge-r52-private-no-card-review-counts-v1",
        "status": "R52_NO_CARD_QUALITY_TASKS_PREPARED__NO_ADMISSION",
        "batch": batch,
        "batch_count": 4,
        "tasks": len(tasks),
        "case_count_by_batch": list(BATCH_COUNTS),
        "story_ranks": dict(sorted(
            Counter(str(t["story_rank"]) for t in tasks).items())),
        "no_historical_card_claimed": True,
        "train_admitted": 0, "validation_admitted": 0,
        "private_story_text_or_ids_in_stdout": False,
    }


def authentic_citations(task: dict) -> set[tuple]:
    refs = set()
    for key, scope in (
        ("frozen_visible_history", "FROZEN_VISIBLE"),
        ("preceding_source_preview_NOT_PART_OF_FROZEN_INPUT",
         "PREVIOUS_SOURCE_NOT_IN_INPUT"),
    ):
        for msg in task[key]:
            refs.add((scope, msg["original_source_array_index"],
                      msg["source_body_sha256"]))
    refs.add(("TARGET", task["target_original_array_index"],
              task["target_sha256"]))
    return refs


def validate_results(results: list[dict], tasks: list[dict],
                     batch: int) -> dict:
    demand(len(results) == len(tasks), "QUALITY_RESULT_COUNT_MISMATCH")
    by_id = {t["candidate_id"]: t for t in tasks}
    seen = set()
    routes = Counter()
    citation_count = 0
    for row in results:
        cid = row.get("candidate_id")
        demand(cid in by_id and cid not in seen,
               "QUALITY_RESULT_DUPLICATE_OR_UNKNOWN")
        seen.add(cid)
        task = by_id[cid]
        demand(row.get("schema") == RESULT_SCHEMA and
               row.get("quality_batch_number") == batch and
               row.get("target_sha256") == task["target_sha256"] and
               row.get("review_route") in ROUTES and
               row.get("training_admission") == HOLD,
               "QUALITY_RESULT_SCHEMA_OR_TARGET_CHANGED")
        note = row.get("rationale")
        demand(isinstance(note, str) and len(note.strip()) >= 24,
               "QUALITY_RATIONALE_REQUIRED")
        cites = row.get("source_citations")
        demand(isinstance(cites, list) and bool(cites),
               "QUALITY_CITATIONS_REQUIRED")
        valid = authentic_citations(task)
        triples = []
        for ref in cites:
            demand(isinstance(ref, dict), "QUALITY_CITATION_INVALID")
            triple = (ref.get("scope"), ref.get("original_source_array_index"),
                      ref.get("source_body_sha256"))
            demand(triple in valid, "QUALITY_CITATION_NOT_IN_PACKET")
            triples.append(triple)
        demand(len(triples) == len(set(triples)), "QUALITY_CITATION_DUPLICATED")
        if row["review_route"] == "NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD":
            demand(any(r[0] == "FROZEN_VISIBLE" for r in triples) and
                   any(r[0] == "TARGET" for r in triples),
                   "POSITIVE_QUALITY_REQUIRES_VISIBLE_AND_TARGET")
        citation_count += len(triples)
        routes[row["review_route"]] += 1
    return {
        "schema": "storyforge-r52-no-card-quality-validation-receipt-v1",
        "status": "R52_QUALITY_RESULTS_VALIDATED__NO_ADMISSION",
        "validated": len(seen),
        "route_counts": dict(sorted(routes.items())),
        "source_citations_validated": citation_count,
        "train_admitted": 0, "validation_admitted": 0,
        "private_story_text_or_ids_in_stdout": False,
    }


def write_private(path: Path, rows: list[dict]) -> None:
    demand(not path.exists() and not path.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    old = os.umask(0o077)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    finally:
        os.umask(old)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--context-queue", type=Path, required=True)
    parser.add_argument("--private-packets", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    try:
        output_dir = args.out_dir.expanduser().absolute()
        demand(output_dir.is_dir() and not output_dir.is_symlink() and
               not (stat.S_IMODE(output_dir.stat().st_mode) & 0o077),
               "OUTPUT_DIRECTORY_NOT_PRIVATE")
        demand(Path.cwd().resolve() not in (output_dir, *output_dir.parents),
               "OUTPUT_MUST_BE_OUTSIDE_GIT_WORKDIR")
        tasks, summary = make_batch(read_private(args.context_queue),
                                    read_private(args.private_packets), args.batch)
        task_file = output_dir / (
            f"R52_NO_CARD_BATCH_{args.batch:02d}_QUALITY_TASKS.jsonl")
        if args.prepare:
            demand(args.results is None, "PREPARE_TAKES_NO_RESULTS")
            write_private(task_file, tasks)
        else:
            demand(args.results is not None, "VALIDATE_REQUIRES_RESULTS")
            demand(task_file.is_file(), "TASKS_NOT_PREPARED")
            demand(read_private(task_file) == tasks, "TASKS_CHANGED_SINCE_PREPARE")
            summary = validate_results(read_private(args.results), tasks, args.batch)
        print(summary["status"])
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    except (Hold, ValueError, KeyError, OSError, TypeError,
            json.JSONDecodeError) as exc:
        reason = str(exc) if isinstance(exc, Hold) else type(exc).__name__
        print("R52_QUALITY_HOLD__" + reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

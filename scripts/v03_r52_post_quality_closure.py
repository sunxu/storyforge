"""Fail-closed private closure of four frozen R52 no-card quality review batches.

Produces eligibility *candidates* only; NEVER training rows, splits, admission,
reconstructed historical cards, or GPU jobs. Only safe aggregate to stdout.
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

import v03_r52_no_card_quality_reviews as quality

ROUTE_GOOD = "NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD"
EXPECTED = (
    (1, 16, 50, {ROUTE_GOOD: 11,
                 "TARGET_PLAYER_AGENCY_DEFECT__HOLD": 2,
                 "TARGET_CONTINUITY_OR_FACT_DEFECT__HOLD": 2,
                 "HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD": 1}),
    (2, 16, 58, {ROUTE_GOOD: 12,
                 "TARGET_PLAYER_AGENCY_DEFECT__HOLD": 2,
                 "HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD": 2}),
    (3, 16, 50, {ROUTE_GOOD: 13,
                 "TARGET_PLAYER_AGENCY_DEFECT__HOLD": 1,
                 "TARGET_CONTINUITY_OR_FACT_DEFECT__HOLD": 1,
                 "HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD": 1}),
    (4, 14, 47, {ROUTE_GOOD: 10,
                 "TARGET_PLAYER_AGENCY_DEFECT__HOLD": 4}),
)
HOLD = quality.HOLD


def need(condition: bool, label: str) -> None:
    if not condition:
        raise quality.Hold(label)


def sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_private_dir(path: Path, cwd: Path) -> None:
    need(path.is_dir() and not path.is_symlink(), "PRIVATE_DIR_MISSING")
    need(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
         "PRIVATE_DIR_PERMISSIONS_UNSAFE")
    path = path.resolve()
    cwd = cwd.resolve()
    need(path != cwd and cwd not in path.parents,
         "OUTPUT_INSIDE_REPOSITORY_FORBIDDEN")


def original_history_digest(task: dict) -> str:
    entries = [
        [m.get("role"), m.get("original_source_array_index"),
         m.get("source_body_sha256")]
        for m in task["frozen_visible_history"]
    ]
    blob = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf8")).hexdigest()


def collect(queue_file: Path, packet_file: Path, quality_dir: Path):
    queue = quality.read_private(queue_file)
    packets = quality.read_private(packet_file)
    shortlist, held = [], []
    source_files = {}
    by_story = defaultdict(list)
    observed = Counter()
    candidate_ids = set()
    for batch, n, citations, frozen_routes in EXPECTED:
        tasks, prepared = quality.make_batch(queue, packets, batch)
        task_file = quality_dir / f"R52_NO_CARD_BATCH_{batch:02d}_QUALITY_TASKS.jsonl"
        result_file = quality_dir / f"R52_NO_CARD_BATCH_{batch:02d}_QUALITY_RESULTS.jsonl"
        actual_tasks = quality.read_private(task_file)
        need(tasks == actual_tasks, "FROZEN_TASKS_CHANGED")
        result_rows = quality.read_private(result_file)
        receipt = quality.validate_results(result_rows, tasks, batch)
        need(prepared["tasks"] == n and receipt["validated"] == n and
             receipt["route_counts"] == dict(sorted(frozen_routes.items())) and
             receipt["source_citations_validated"] == citations and
             receipt["train_admitted"] == receipt["validation_admitted"] == 0,
             "FROZEN_BATCH_VERIFICATION_MISMATCH")
        source_files[f"batch_{batch:02d}_task_sha256"] = sha_bytes(task_file)
        source_files[f"batch_{batch:02d}_decision_sha256"] = sha_bytes(result_file)
        results_by_id = {r["candidate_id"]: r for r in result_rows}
        for task in tasks:
            cid = task["candidate_id"]
            need(cid not in candidate_ids and cid in results_by_id,
                 "CANDIDATE_DUPLICATE_OR_MISSING")
            candidate_ids.add(cid)
            result = results_by_id[cid]
            route = result["review_route"]
            first_role = (task["frozen_visible_history"][0].get("role")
                          if task["frozen_visible_history"] else None)
            record = {
                "schema": "storyforge-r52-private-post-quality-case-v1",
                "private_do_not_commit": True,
                "candidate_id": cid,
                "story_rank": task["story_rank"],
                "source_story_id": task["source_story_id"],
                "target_sha256": task["target_sha256"],
                "target_original_array_index": task["target_original_array_index"],
                "frozen_visible_history_sha256": original_history_digest(task),
                "visible_first_role": first_role,
                "visible_history_length": len(task["frozen_visible_history"]),
                "quality_batch": batch,
                "quality_review_route": route,
                "quality_review_rationale_sha256": quality.digest(result["rationale"]),
                "quality_source_citations_count": len(result["source_citations"]),
                "quality_review_status": "FIRST_PASS_ONLY__NO_ADMISSION",
                "experimental_input_contract": "GENERIC_NO_CARD_VISIBLE_CONTEXT_PROPOSED",
                "original_system_prompt_or_card_recovered": False,
                "owner_rights": "OWNER_ATTESTED_FULL_OWNERSHIP",
                "final_quality_and_safety_signoff": "PENDING",
                "linked_world_component_verified": False,
                "v01_train_overlap_verified": False,
                "sealed_r50_test_overlap_verified": False,
                "tokenizer_input_length_verified": False,
                "last_target_only_labels_verified": False,
                "training_admission": HOLD,
                "split": None,
            }
            if route == ROUTE_GOOD:
                record["eligibility_stage"] = "QUALITY_POSSIBLE__NEEDS_GATES"
                shortlist.append(record)
            else:
                record["eligibility_stage"] = "QUALITY_DEFECT_HOLD"
                held.append(record)
            by_story[task["source_story_id"]].append(record)
            observed[route] += 1
    need(len(candidate_ids) == 62 and len(shortlist) == 46 and len(held) == 16,
         "COVERAGE_OR_QUALITY_COUNT_MISMATCH")
    need(observed["TARGET_PLAYER_AGENCY_DEFECT__HOLD"] == 9 and
         observed["TARGET_CONTINUITY_OR_FACT_DEFECT__HOLD"] == 3 and
         observed["HIDDEN_PREMISE_OR_CARD_DEPENDENCY__HOLD"] == 4,
         "DEFECT_ROUTE_COUNT_MISMATCH")
    worlds = []
    seen_story_rank = {}
    for world, rows in sorted(by_story.items()):
        ranks = sorted({r["story_rank"] for r in rows})
        need(len(ranks) == 1 and
             (ranks[0] not in seen_story_rank or seen_story_rank[ranks[0]] == world),
             "STORY_ID_RANK_MISMATCH")
        seen_story_rank[ranks[0]] = world
        worlds.append({
            "schema": "storyforge-r52-private-world-group-preflight-v1",
            "private_do_not_commit": True,
            "source_story_id": world, "source_story_rank": ranks[0],
            "first_pass_possible": sum(r["quality_review_route"] == ROUTE_GOOD for r in rows),
            "quality_holds": sum(r["quality_review_route"] != ROUTE_GOOD for r in rows),
            "linked_or_alias_world_component": "UNRESOLVED",
            "v01_prior_train_component_overlap": "NOT_CHECKED",
            "r50_sealed_heldout_component_overlap": "NOT_CHECKED",
            "world_split": None, "component_isolation_pass": False,
        })
    shortlist.sort(key=lambda r: (r["story_rank"], r["candidate_id"]))
    held.sort(key=lambda r: (r["story_rank"], r["candidate_id"]))
    safe = {
        "schema": "storyforge-r52-post-quality-safe-aggregate-v1",
        "status": "R52_ALL_62_QUALITY_REVIEWS_REVERIFIED__NO_ADMISSION",
        "source_hashes": {
            "r52_context_queue_sha256": sha_bytes(queue_file),
            "r51_private_packets_sha256": sha_bytes(packet_file),
            **source_files,
        },
        "batch_count": 4,
        "cases_revalidated": 62,
        "source_citations_revalidated": 205,
        "quality_possible_first_pass": len(shortlist),
        "quality_holds": len(held),
        "route_counts": dict(sorted(observed.items())),
        "distinct_source_stories_not_linked_worlds": len(worlds),
        "first_pass_review_is_not_quality_signoff": True,
        "original_historical_card_claimed": False,
        "linked_world_isolation_verified": False,
        "world_split_assigned": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "gpu_jobs_authorized": 0,
        "private_candidate_ids_or_story_text_in_stdout": False,
        "next_gate": "OWNER_QUALITY_SAFETY_AND_WORLD_COMPONENT_PROVENANCE",
    }
    return shortlist, held, worlds, safe


def write_new(path: Path, payload: str) -> None:
    old = os.umask(0o077)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf8") as f:
            f.write(payload)
    finally:
        os.umask(old)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--context-queue", type=Path, required=True)
    ap.add_argument("--private-packets", type=Path, required=True)
    ap.add_argument("--quality-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        out = args.out_dir.expanduser().absolute()
        qdir = args.quality_dir.expanduser().absolute()
        ensure_private_dir(out, Path.cwd())
        need(qdir.is_dir() and not qdir.is_symlink(), "QUALITY_DIR_INVALID")
        shortlist, held, worlds, safe = collect(
            args.context_queue.expanduser().absolute(),
            args.private_packets.expanduser().absolute(),
            qdir,
        )
        outputs = {
            "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl":
                "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                        for r in shortlist),
            "R52_PRIVATE_QUALITY_16_HOLD_REGISTER.jsonl":
                "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                        for r in held),
            "R52_PRIVATE_WORLD_COMPONENT_PREFLIGHT.jsonl":
                "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                        for r in worlds),
            "R52_POST_QUALITY_SAFE_AGGREGATE.json":
                json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        }
        need(not any((out / name).exists() or (out / name).is_symlink()
                     for name in outputs), "OUTPUT_ALREADY_EXISTS")
        for name, content in outputs.items():
            write_new(out / name, content)
    except (quality.Hold, OSError, TypeError, KeyError, ValueError,
            json.JSONDecodeError, UnicodeError) as exc:
        reason = str(exc) if isinstance(exc, quality.Hold) else type(exc).__name__
        print("R52_POST_QUALITY_HOLD__" + reason, file=sys.stderr)
        return 2
    print("R52_ALL_62_QUALITY_REVIEWS_REVERIFIED__NO_ADMISSION")
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

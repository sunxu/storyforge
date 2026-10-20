"""R52: seven-world bounded source dossier and 21-pair independent review kit.

No R50 access, split, quality admission or GPU. All private outputs are
exclusive-create files in a 0700 folder; all result routes remain HOLD.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import v03_r52_world_exact_isolation as prior

PACKET_SCHEMA = "storyforge-r51-private-gold108-context-review-packet-v1"
PAIR_SCHEMA = "storyforge-r52-private-world-pair-review-v1"
DECISION_SCHEMA = "storyforge-r52-private-world-pair-decision-v1"
HOLD = "PENDING_NOT_APPROVED"
ROUTES = {
    "LINKED_WORLD_EVIDENCE__HOLD",
    "NO_LINK_OBSERVED_IN_BOUNDED_EVIDENCE__HOLD",
    "INSUFFICIENT_SOURCE_EVIDENCE__HOLD",
}
SAMPLE_LIMIT = 2
EXCERPT_LIMIT = 1300


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise prior.GateHold(reason)


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_source_packets(path: Path) -> list[dict]:
    rows = prior.read_jsonl(path, private=True, count=108)
    seen = set()
    for row in rows:
        cid = row.get("candidate_id")
        target = row.get("target_content_for_review_only")
        require(row.get("schema") == PACKET_SCHEMA and
                row.get("private_do_not_commit") is True and
                isinstance(cid, str) and cid not in seen and
                isinstance(row.get("source_story_id"), str) and
                type(row.get("story_rank")) is int and
                isinstance(target, str) and sha_text(target) == row.get("target_sha256") and
                row.get("training_admission") == HOLD and
                row.get("split") is None and
                row.get("historical_card_version_verified") is False and
                type(row.get("target_original_array_index")) is int,
                "FROZEN_R51_PACKET_CHANGED")
        seen.add(cid)
        for entry in row.get("frozen_visible_history", []):
            require(isinstance(entry, dict) and
                    isinstance(entry.get("content"), str) and
                    sha_text(entry["content"]) == entry.get("source_body_sha256") and
                    type(entry.get("original_source_array_index")) is int,
                    "FROZEN_R51_HISTORY_SHA_MISMATCH")
    require(len(seen) == 108, "R51_PACKETS_NOT_UNIQUE")
    return rows


def sample(row: dict) -> dict:
    history = row["frozen_visible_history"]
    user_messages = [m for m in history if m.get("role") == "user"]
    picked = user_messages[-1] if user_messages else (history[-1] if history else None)
    evidence = []
    if picked is not None:
        text = picked["content"]
        evidence.append({
            "scope": "FROZEN_VISIBLE",
            "story_rank": row["story_rank"],
            "original_source_array_index": picked["original_source_array_index"],
            "source_body_sha256": picked["source_body_sha256"],
            "role": picked.get("role"),
            "excerpt": text[:EXCERPT_LIMIT],
            "excerpt_truncated": len(text) > EXCERPT_LIMIT,
        })
    target = row["target_content_for_review_only"]
    evidence.append({
        "scope": "TARGET",
        "story_rank": row["story_rank"],
        "original_source_array_index": row["target_original_array_index"],
        "source_body_sha256": row["target_sha256"],
        "role": "assistant",
        "excerpt": target[:EXCERPT_LIMIT],
        "excerpt_truncated": len(target) > EXCERPT_LIMIT,
    })
    return {
        "candidate_id": row["candidate_id"],
        "target_sha256": row["target_sha256"],
        "source_array_index": row["target_original_array_index"],
        "bounded_original_message_witnesses": evidence,
    }


def build(rows: list[dict], shortlist: list[dict],
          world_queue: list[dict], world_receipt: dict):
    require(len(rows) == 108 and len(shortlist) == 46 and
            len(world_queue) == 7, "R52_INPUT_CARDINALITY_CHANGED")
    require(world_receipt.get("schema") ==
            "storyforge-r52-world-isolation-exact-screen-v1" and
            world_receipt.get("status") ==
            "R52_V01_EXACT_UUID_SCREEN_PASS__WORLD_GRAPH_AND_SEALED_TEST_HOLD" and
            world_receipt.get("first_pass_candidates") == 46 and
            world_receipt.get("source_story_groups") == 7 and
            all(x == 0 for x in
                world_receipt.get("exact_overlap_with_v01_splits_by_story_count", {}).values()) and
            world_receipt.get("linked_component_graph_reviewed") == 0 and
            world_receipt.get("r50_sealed_heldout_opened") is False and
            world_receipt.get("world_split_assigned") ==
            world_receipt.get("train_admitted") ==
            world_receipt.get("validation_admitted") == 0,
            "EXACT_SCREEN_RECEIPT_NOT_FROZEN")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["source_story_id"]].append(row)
    allowed = {}
    for world in world_queue:
        sid = world.get("source_story_id")
        require(world.get("schema") == "storyforge-r52-private-world-component-review-v1" and
                world.get("private_do_not_commit") is True and
                isinstance(sid, str) and sid not in allowed and
                type(world.get("story_rank")) is int and
                world.get("exact_v01_story_uuid_overlap") is False and
                world.get("owner_component_isolation_signed") is False and
                world.get("train_val_split") is None and
                world.get("training_admission") == HOLD,
                "PRIVATE_WORLD_REVIEW_QUEUE_CHANGED")
        allowed[sid] = world
    require(len(allowed) == 7 and all(sid in grouped for sid in allowed),
            "SEVEN_SOURCE_WORLDS_MISSING_FROM_PACKET")
    selected = Counter()
    raw_ids = {r["candidate_id"]: r for r in rows}
    for item in shortlist:
        cid = item.get("candidate_id")
        require(cid in raw_ids and item.get("source_story_id") ==
                raw_ids[cid]["source_story_id"] and
                item.get("target_sha256") == raw_ids[cid]["target_sha256"] and
                item.get("eligibility_stage") == "QUALITY_POSSIBLE__NEEDS_GATES" and
                item.get("split") is None and item.get("training_admission") == HOLD,
                "SHORTLIST_PINS_OR_HOLD_CHANGED")
        selected[item["source_story_id"]] += 1
    require(set(selected) == set(allowed) and
            all(selected[sid] == world["first_pass_possible"]
                for sid, world in allowed.items()),
            "WORLD_SHORTLIST_COUNT_MISMATCH")
    dossiers = []
    for sid, world in sorted(allowed.items(), key=lambda x: x[1]["story_rank"]):
        packets = sorted(grouped[sid],
                         key=lambda r: (r["target_original_array_index"], r["candidate_id"]))
        require(all(p["story_rank"] == world["story_rank"] for p in packets),
                "WORLD_RANK_OR_ID_CHANGED")
        representative = ([packets[0]] if len(packets) == 1 else
                          [packets[0], packets[-1]])
        dossiers.append({
            "schema": "storyforge-r52-private-world-dossier-v1",
            "private_do_not_commit": True,
            "source_story_id": sid,
            "story_rank": world["story_rank"],
            "frozen_review_packet_cases": len(packets),
            "quality_first_pass_possible": selected[sid],
            "review_scope": "TWO_BOUNDED_R51_FROZEN_WINDOW_EXCERPTS_NOT_FULL_WORLD",
            "all_target_shas_digest": sha_text(json.dumps(
                [(p["target_original_array_index"], p["target_sha256"])
                 for p in packets], sort_keys=True)),
            "representative_witnesses": [sample(p) for p in representative],
            "original_full_world_archive_reviewed": False,
            "historical_export_card_asof_proven": False,
            "semantic_world_linkage_verified": False,
            "training_admission": HOLD,
        })
    pairs = []
    for a, b in combinations(dossiers, 2):
        pairs.append({
            "schema": PAIR_SCHEMA,
            "private_do_not_commit": True,
            "left_story_id": a["source_story_id"],
            "right_story_id": b["source_story_id"],
            "left_rank": a["story_rank"], "right_rank": b["story_rank"],
            "left_source_targets_digest": a["all_target_shas_digest"],
            "right_source_targets_digest": b["all_target_shas_digest"],
            "left_bounded_witnesses": a["representative_witnesses"],
            "right_bounded_witnesses": b["representative_witnesses"],
            "allowed_routes": sorted(ROUTES),
            "review_questions": [
                "Do the stories share the same fictional character/persona under aliases?",
                "Are there unique locations, organizations, events or story rules linking the two?",
                "Is repeated text generic boilerplate rather than distinctive evidence?",
                "What is still unverified in full original stories and historical cards?",
            ],
            "no_link_from_bounded_excerpts_is_not_world_isolation_pass": True,
            "training_admission": HOLD,
        })
    require(len(pairs) == 21, "EXPECTED_21_STORY_PAIRS")
    safe = {
        "schema": "storyforge-r52-world-semantic-kit-safe-aggregate-v1",
        "status": "R52_SEVEN_WORLD_TWENTYONE_PAIR_REVIEW_TASKS_PREPARED__NO_ADMISSION",
        "source_story_dossiers": 7,
        "pairs_pending_independent_review": 21,
        "source_packet_records_indexed": 108,
        "quality_shortlist_bound": 46,
        "representative_witnesses_per_world_max": SAMPLE_LIMIT,
        "original_full_worlds_read": 0,
        "linked_worlds_certified": 0,
        "world_splits_assigned": 0,
        "train_admitted": 0, "validation_admitted": 0,
        "r50_sealed_test_opened": False,
        "private_story_names_or_text_in_stdout": False,
    }
    return dossiers, pairs, safe


def valid_citations(task: dict) -> set[tuple]:
    allowed = set()
    for side in ("left_bounded_witnesses", "right_bounded_witnesses"):
        for witness in task[side]:
            for message in witness["bounded_original_message_witnesses"]:
                allowed.add((
                    message["scope"], message["story_rank"],
                    message["original_source_array_index"],
                    message["source_body_sha256"],
                ))
    return allowed


def check_decisions(tasks: list[dict], decisions: list[dict]) -> dict:
    require(len(tasks) == len(decisions) == 21, "PAIR_DECISION_COUNT_CHANGED")
    by_rank = {(p["left_rank"], p["right_rank"]): p for p in tasks}
    seen = set()
    routes = Counter()
    validated = 0
    for row in decisions:
        key = (row.get("left_rank"), row.get("right_rank"))
        require(row.get("schema") == DECISION_SCHEMA and key in by_rank and
                key not in seen and row.get("training_admission") == HOLD and
                row.get("decision") in ROUTES and
                row.get("reviewer_a_b_analysis_seen") is False,
                "PAIR_DECISION_SCHEMA_OR_IDENTITY_CHANGED")
        seen.add(key)
        p = by_rank[key]
        require(row.get("left_source_targets_digest") ==
                p["left_source_targets_digest"] and
                row.get("right_source_targets_digest") ==
                p["right_source_targets_digest"],
                "PAIR_SOURCE_DIGEST_CHANGED")
        rationale = row.get("rationale")
        require(isinstance(rationale, str) and len(rationale.strip()) >= 30,
                "PAIR_DECISION_RATIONALE_REQUIRED")
        cites = row.get("source_citations")
        require(isinstance(cites, list), "PAIR_DECISION_CITATIONS_INVALID")
        grounded = valid_citations(p)
        used = set()
        for c in cites:
            require(isinstance(c, dict), "PAIR_CITATION_TYPE_INVALID")
            triple = (c.get("scope"), c.get("story_rank"),
                      c.get("original_source_array_index"),
                      c.get("source_body_sha256"))
            require(triple in grounded and triple not in used,
                    "PAIR_CITATION_SHA_OR_SOURCE_INVALID")
            used.add(triple)
        if row["decision"] != "INSUFFICIENT_SOURCE_EVIDENCE__HOLD":
            require({p["left_rank"], p["right_rank"]}.issubset(
                    {v[1] for v in used}),
                    "PAIR_POSITIVE_OR_DISTINCT_NEEDS_BOTH_SIDES")
        routes[row["decision"]] += 1
        validated += len(used)
    return {
        "status": "R52_21_WORLD_PAIR_REVIEWS_VALIDATED__GRAPH_STILL_HOLD",
        "pairs_validated": len(seen),
        "evidence_citations_validated": validated,
        "route_counts": dict(routes),
        "semantic_world_isolation_verified": False,
        "train_admitted": 0,
        "validation_admitted": 0,
        "private_content_emitted": False,
    }


def write_exclusive(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf8") as f:
        f.write(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--validate", action="store_true")
    ap.add_argument("--world-dir", type=Path, required=True)
    ap.add_argument("--post-quality-dir", type=Path, required=True)
    ap.add_argument("--private-packets", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--decisions", type=Path)
    args = ap.parse_args()
    try:
        out = args.out_dir.expanduser().absolute()
        require(out.is_dir() and not out.is_symlink() and
                stat.S_IMODE(out.stat().st_mode) & 0o077 == 0,
                "OUTPUT_DIRECTORY_NOT_PRIVATE")
        world = args.world_dir.expanduser().absolute()
        post = args.post_quality_dir.expanduser().absolute()
        tasks_file = out / "R52_PRIVATE_21_WORLD_PAIR_REVIEW_TASKS.jsonl"
        dossiers_file = out / "R52_PRIVATE_07_WORLD_DOSSIERS.jsonl"
        agg_file = out / "R52_WORLD_SEMANTIC_KIT_SAFE_AGGREGATE.json"
        source_file = world / "R52_PRIVATE_07_WORLD_COMPONENT_REVIEW_QUEUE.jsonl"
        receipt_file = world / "R52_WORLD_EXACT_ISOLATION_SAFE_AGGREGATE.json"
        source = prior.read_jsonl(source_file, private=True, count=7)
        require(receipt_file.is_file() and not receipt_file.is_symlink() and
                stat.S_IMODE(receipt_file.stat().st_mode) == 0o600,
                "WORLD_RECEIPT_NOT_PRIVATE")
        receipt = json.loads(receipt_file.read_text(encoding="utf8"))
        shortlist = prior.read_jsonl(
            post / "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl",
            private=True, count=46)
        rows = read_source_packets(args.private_packets.expanduser().absolute())
        dossiers, tasks, aggregate = build(rows, shortlist, source, receipt)
        if args.prepare:
            require(args.decisions is None, "PREPARE_REQUIRES_NO_DECISIONS")
            outputs = {
                dossiers_file: dossiers,
                tasks_file: tasks,
            }
            require(not any(path.exists() or path.is_symlink()
                            for path in [*outputs, agg_file]),
                    "OUTPUT_ALREADY_EXISTS")
            os.umask(0o077)
            for path, rows_ in outputs.items():
                write_exclusive(path, "".join(
                    json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
                    for x in rows_))
            write_exclusive(agg_file, json.dumps(
                aggregate, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            print(aggregate["status"])
            print(json.dumps(aggregate, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            require(args.decisions is not None, "DECISION_FILE_REQUIRED")
            require(prior.read_jsonl(tasks_file, private=True, count=21) == tasks,
                    "FROZEN_PAIR_TASKS_CHANGED")
            results = prior.read_jsonl(args.decisions.expanduser().absolute(),
                                      private=True, count=21)
            report = check_decisions(tasks, results)
            print(report["status"])
            print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    except (prior.GateHold, OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as exc:
        reason = str(exc) if isinstance(exc, prior.GateHold) else type(exc).__name__
        print("R52_SEMANTIC_REVIEW_HOLD__" + reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

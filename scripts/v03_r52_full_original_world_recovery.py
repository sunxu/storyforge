"""R52 full-original seven-world source recovery and priority-pair review intake.

Uses authenticated 06-15 Git LFS ZIP from R51. Creates private full-story
source files and 21 pair indexes; no training approval, semantic verdict or
R50 test access. All source text remains outside Git and stdout.
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

import v03_r51_gold195_source_replay as replay
import v03_r52_world_exact_isolation as identity
import v03_r52_world_semantic_review_kit as bounded

HOLD = "PENDING_NOT_APPROVED"
ROUTE_PRIORITY = "INSUFFICIENT_SOURCE_EVIDENCE__HOLD"
ROUTE_BOUNDED = "NO_LINK_OBSERVED_IN_BOUNDED_EVIDENCE__HOLD"


def need(ok: bool, code: str) -> None:
    if not ok:
        raise identity.GateHold(code)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json_private(path: Path) -> dict:
    need(path.is_file() and not path.is_symlink() and
         stat.S_IMODE(path.stat().st_mode) == 0o600 and
         stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
         "PRIVATE_RECEIPT_NOT_SAFE")
    obj = json.loads(path.read_text(encoding="utf8"))
    need(isinstance(obj, dict), "PRIVATE_RECEIPT_NOT_JSON_OBJECT")
    return obj


def validate_inputs(packets_path: Path, post: Path, world: Path, review: Path):
    packets = bounded.read_source_packets(packets_path)
    shortlist = identity.read_jsonl(
        post / "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl",
        private=True, count=46)
    queue = identity.read_jsonl(
        world / "R52_PRIVATE_07_WORLD_COMPONENT_REVIEW_QUEUE.jsonl",
        private=True, count=7)
    receipt = read_json_private(
        world / "R52_WORLD_EXACT_ISOLATION_SAFE_AGGREGATE.json")
    dossiers, tasks, _ = bounded.build(packets, shortlist, queue, receipt)
    stored_tasks = identity.read_jsonl(
        review / "R52_PRIVATE_21_WORLD_PAIR_REVIEW_TASKS.jsonl",
        private=True, count=21)
    need(stored_tasks == tasks, "FROZEN_BOUNDED_PAIR_TASKS_MISMATCH")
    decision_path = review / "R52_PRIVATE_21_WORLD_PAIR_DECISIONS.jsonl"
    decisions = identity.read_jsonl(decision_path, private=True, count=21)
    report = bounded.check_decisions(tasks, decisions)
    routes = report["route_counts"]
    need(report["evidence_citations_validated"] == 126 and
         routes.get(ROUTE_PRIORITY) == 3 and
         routes.get(ROUTE_BOUNDED) == 18 and
         routes.get("LINKED_WORLD_EVIDENCE__HOLD", 0) == 0,
         "BOUND_WORLD_21_DECISIONS_CHANGED")
    need({p["source_story_id"] for p in dossiers} ==
         {w["source_story_id"] for w in queue},
         "WORLD_QUEUE_DOSSIER_MISMATCH")
    pinned = {
        "r51_private_packets_sha256": file_sha(packets_path),
        "r52_bounded_tasks_sha256":
            file_sha(review / "R52_PRIVATE_21_WORLD_PAIR_REVIEW_TASKS.jsonl"),
        "r52_bounded_decisions_sha256": file_sha(decision_path),
        "r52_world_exact_receipt_sha256":
            file_sha(world / "R52_WORLD_EXACT_ISOLATION_SAFE_AGGREGATE.json"),
    }
    return packets, dossiers, tasks, decisions, pinned


def extract_full_sources(repo: Path, packets: list[dict],
                         dossiers: list[dict]):
    asset, zip_hashes = replay.pinned_archive(repo)
    raw_zips = replay.discover_raw_zips(asset, zip_hashes)
    groups = defaultdict(list)
    for p in packets:
        groups[p["source_story_id"]].append(p)
    output = []
    for d in dossiers:
        sid, rank = d["source_story_id"], d["story_rank"]
        group = groups[sid]
        need(group and all(p["story_rank"] == rank for p in group),
             "SOURCE_STORY_RANK_ID_MISMATCH")
        original_zip_shas = {p.get("source_original_raw_zip_sha256")
                             for p in group}
        original_jsonl_shas = {p.get("source_original_raw_jsonl_sha256")
                               for p in group}
        need(len(original_zip_shas) == len(original_jsonl_shas) == 1 and
             None not in original_zip_shas | original_jsonl_shas and
             zip_hashes[rank] in original_zip_shas,
             "R51_SOURCE_ARCHIVE_PINS_DIVERGE")
        jsonl = replay.choose_source_jsonl(
            raw_zips[rank], original_jsonl_shas)
        need(replay.sha256(jsonl) in original_jsonl_shas,
             "FULL_ORIGINAL_JSONL_SHA_MISMATCH")
        roots = [json.loads(line) for line in
                 jsonl.decode("utf-8-sig").splitlines() if line.strip()]
        need(len(roots) == 1 and isinstance(roots[0], dict) and
             isinstance(roots[0].get("messages"), list),
             "FULL_ORIGINAL_ROOT_INVALID")
        root = roots[0]
        messages = root["messages"]
        need(len(messages) <= 150000 and bool(messages),
             "FULL_ORIGINAL_MESSAGE_LIMIT")
        verified = []
        for p in group:
            index = p["target_original_array_index"]
            need(0 <= index < len(messages), "FROZEN_TARGET_INDEX_OUT_OF_RANGE")
            target = messages[index]
            need(isinstance(target, dict) and
                 isinstance(target.get("content"), str) and
                 replay.normalize_role(target.get("role")) == "assistant" and
                 target.get("id") == p.get("target_message_id") and
                 replay.sha256(target["content"].encode()) == p["target_sha256"],
                 "ORIGINAL_TARGET_ID_ROLE_SHA_CHANGED")
            history = p["frozen_visible_history"]
            for msg in history:
                j = msg["original_source_array_index"]
                need(0 <= j < index and isinstance(messages[j], dict) and
                     isinstance(messages[j].get("content"), str) and
                     replay.normalize_role(messages[j].get("role")) ==
                     msg["role"] and
                     replay.sha256(messages[j]["content"].encode()) ==
                     msg["source_body_sha256"],
                     "ORIGINAL_HISTORY_INDEX_ROLE_SHA_CHANGED")
            need([m["original_source_array_index"] for m in history] ==
                 list(range(index - len(history), index)),
                 "FROZEN_VISIBLE_HISTORY_NOT_IMMEDIATE")
            verified.append({
                "candidate_id": p["candidate_id"],
                "target_original_array_index": index,
                "target_sha256": p["target_sha256"],
                "visible_history_count": len(history),
            })
        ledger = []
        for i, m in enumerate(messages):
            need(isinstance(m, dict) and
                 isinstance(m.get("id"), str) and
                 isinstance(m.get("content"), str),
                 "ORIGINAL_MESSAGE_ID_OR_CONTENT_INVALID")
            role = replay.normalize_role(m.get("role"))
            need(role in ("user", "assistant", "system"),
                 "ORIGINAL_MESSAGE_ROLE_UNSUPPORTED")
            ledger.append({
                "original_source_array_index": i,
                "original_source_message_id": m["id"],
                "role": role,
                "content": m["content"],
                "source_body_sha256": replay.sha256(
                    m["content"].encode("utf8")),
            })
        output.append({
            "schema": "storyforge-r52-private-full-original-world-v1",
            "private_do_not_commit": True,
            "story_rank": rank, "source_story_id": sid,
            "source_archive_outer_sha256": replay.OUTER_SHA256,
            "original_source_zip_sha256": next(iter(original_zip_shas)),
            "original_source_jsonl_sha256": next(iter(original_jsonl_shas)),
            "original_root_messages": ledger,
            "original_source_story_export_metadata": root.get("story"),
            "original_root_other_metadata": {
                k: v for k, v in root.items() if k not in ("messages", "story")},
            "r51_frozen_target_pins_verified": verified,
            "source_story_complete_export": True,
            "historical_card_version_for_each_target_verified": False,
            "original_generated_system_prompt_reconstructed": False,
            "semantic_independence_certified": False,
            "training_admission": HOLD,
        })
    need(len(output) == 7, "EXPECTED_SEVEN_FULL_SOURCES")
    return output


def create_artifacts(full: list[dict], tasks: list[dict],
                     decisions: list[dict], pins: dict):
    index = {(d["story_rank"]): d for d in full}
    verdicts = {(r["left_rank"], r["right_rank"]): r for r in decisions}
    full_pairs = []
    for p in tasks:
        a, b = p["left_rank"], p["right_rank"]
        route = verdicts[(a, b)]["decision"]
        full_pairs.append({
            "schema": "storyforge-r52-private-full-source-world-pair-task-v1",
            "private_do_not_commit": True,
            "left_rank": a, "right_rank": b,
            "left_source_story_id": index[a]["source_story_id"],
            "right_source_story_id": index[b]["source_story_id"],
            "left_full_original_file":
                f"R52_PRIVATE_FULL_ORIGINAL_STORY_{a:02d}.json",
            "right_full_original_file":
                f"R52_PRIVATE_FULL_ORIGINAL_STORY_{b:02d}.json",
            "left_original_jsonl_sha256":
                index[a]["original_source_jsonl_sha256"],
            "right_original_jsonl_sha256":
                index[b]["original_source_jsonl_sha256"],
            "bounded_decision": route,
            "bounded_rationale_for_review_only":
                verdicts[(a, b)]["rationale"],
            "original_bounded_source_citations":
                verdicts[(a, b)]["source_citations"],
            "full_source_reviewer_decision": "PENDING",
            "full_source_review_notes": None,
            "full_source_evidence_citations": [],
            "shared_people_or_aliases_checked": False,
            "unique_events_settings_rules_checked": False,
            "historic_v01_and_gold87_component_exposure_checked": False,
            "related_world_graph_signed": False,
            "semantic_independence_verified": False,
            "training_admission": HOLD,
        })
    need(len(full_pairs) == 21 and
         sum(x["bounded_decision"] == ROUTE_PRIORITY
             for x in full_pairs) == 3,
         "THREE_PRIORITY_PAIRS_MISSING")
    priority = [p for p in full_pairs if p["bounded_decision"] == ROUTE_PRIORITY]
    outputs = {}
    for story in full:
        filename = f"R52_PRIVATE_FULL_ORIGINAL_STORY_{story['story_rank']:02d}.json"
        outputs[filename] = json.dumps(
            story, ensure_ascii=False, sort_keys=True) + "\n"
    outputs["R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"] = (
        "".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n"
                for p in full_pairs))
    outputs["R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"] = (
        "".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n"
                for p in priority))
    safe = {
        "schema": "storyforge-r52-full-original-world-recovery-safe-aggregate-v1",
        "status": "R52_SEVEN_COMPLETE_ORIGINAL_STORIES_RECOVERED__ALL_21_GRAPH_HOLD",
        "original_source_bundle_sha256": replay.OUTER_SHA256,
        "full_original_story_exports_verified": 7,
        "full_original_source_messages": sum(
            len(d["original_root_messages"]) for d in full),
        "frozen_r51_target_pin_checks_in_seven_worlds": sum(
            len(d["r51_frozen_target_pins_verified"]) for d in full),
        "complete_pair_review_queue": len(full_pairs),
        "priority_insufficient_bounded_pairs": len(priority),
        "remaining_bounded_no_link_pairs": 18,
        "bounded_citations_revalidated": 126,
        "input_hashes": pins,
        "full_source_semantic_review_completed": 0,
        "world_components_certified": 0,
        "quality_admission_signed": 0,
        "train_admitted": 0, "validation_admitted": 0,
        "world_split_assigned": 0,
        "r50_sealed_heldout_opened": False,
        "story_text_or_candidate_ids_in_stdout": False,
    }
    outputs["R52_FULL_ORIGINAL_WORLD_RECOVERY_SAFE_AGGREGATE.json"] = (
        json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return outputs, safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--private-packets", required=True, type=Path)
    p.add_argument("--post-quality-dir", required=True, type=Path)
    p.add_argument("--world-dir", required=True, type=Path)
    p.add_argument("--bounded-review-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        repo = args.repo.resolve(strict=True)
        out = args.out_dir.expanduser().absolute()
        need(out.is_dir() and not out.is_symlink() and
             stat.S_IMODE(out.stat().st_mode) & 0o077 == 0 and
             out.resolve() != repo and repo not in out.resolve().parents,
             "OUTPUT_DIRECTORY_UNSAFE")
        packets, dossiers, tasks, decisions, pins = validate_inputs(
            args.private_packets.expanduser().absolute(),
            args.post_quality_dir.expanduser().absolute(),
            args.world_dir.expanduser().absolute(),
            args.bounded_review_dir.expanduser().absolute())
        full = extract_full_sources(repo, packets, dossiers)
        artifacts, safe = create_artifacts(full, tasks, decisions, pins)
        need(not any((out / name).exists() or (out / name).is_symlink()
                     for name in artifacts), "OUTPUT_ALREADY_EXISTS")
        os.umask(0o077)
        for name, content in artifacts.items():
            fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf8") as stream:
                stream.write(content)
        print(safe["status"])
        print(json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True))
    except (identity.GateHold, OSError, KeyError, TypeError, ValueError,
            json.JSONDecodeError, RuntimeError) as error:
        marker = str(error) if isinstance(error, identity.GateHold) else type(error).__name__
        print("R52_FULL_ORIGINAL_RECOVERY_HOLD__" + marker, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""R52 exact historical UUID screen + seven-story graph review queue.

Read only immutable v0.1 Train/Validation/Test bytes, R52 private shortlist,
16-case holds and frozen per-source-story preflight; never touch R50 sealed
heldout, infer connected components, allocate splits or approve training.
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

HOLD = "PENDING_NOT_APPROVED"
HISTORICAL = {
    "train": ("data/compiled/v0.3/train.jsonl", 65, 15,
              "9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f"),
    "validation": ("data/compiled/v0.3/validation.jsonl", 15, 2,
                   "083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36"),
    "test": ("data/compiled/v0.3/test.jsonl", 20, 2,
             "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"),
}
QUALITY_SCHEMA = "storyforge-r52-private-post-quality-case-v1"
WORLD_SCHEMA = "storyforge-r52-private-world-group-preflight-v1"
AGGREGATE_SCHEMA = "storyforge-r52-post-quality-safe-aggregate-v1"


class GateHold(ValueError):
    pass


def require(cond: bool, marker: str) -> None:
    if not cond:
        raise GateHold(marker)


def sha_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_jsonl(path: Path, *, private: bool, count: int) -> list[dict]:
    require(path.is_file() and not path.is_symlink(), "SOURCE_FILE_MISSING")
    if private:
        require(stat.S_IMODE(path.stat().st_mode) == 0o600 and
                stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
                "PRIVATE_MODE_UNSAFE")
    with path.open(encoding="utf-8-sig") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    require(len(rows) == count and all(isinstance(row, dict) for row in rows),
            "ROW_COUNT_OR_FORMAT_CHANGED")
    return rows


def historical_registry(repo: Path) -> tuple[dict[str, set[str]], dict]:
    by_split = {}
    for name, (rel, count, story_count, pinned_sha) in HISTORICAL.items():
        path = repo / rel
        require(path.is_file() and sha_file(path) == pinned_sha,
                "V01_HISTORIC_SPLIT_SHA256_MISMATCH")
        rows = read_jsonl(path, private=False, count=count)
        stories = set()
        for row in rows:
            meta = row.get("metadata")
            require(isinstance(meta, dict) and
                    isinstance(meta.get("story_id"), str) and
                    bool(meta["story_id"].strip()),
                    "V01_STORY_METADATA_MISSING")
            stories.add(meta["story_id"])
        require(len(stories) == story_count, "V01_STORY_COUNT_CHANGED")
        by_split[name] = stories
    require(not (by_split["train"] & by_split["validation"] or
                 by_split["train"] & by_split["test"] or
                 by_split["validation"] & by_split["test"]),
            "HISTORICAL_SPLITS_NOT_DISJOINT")
    return by_split, {
        "v01_historical_train_rows": 65,
        "v01_historical_validation_rows": 15,
        "v01_historical_test_rows": 20,
        "v01_historical_story_groups": {
            "train": 15, "validation": 2, "test": 2},
        "v01_frozen_sha256_verified": True,
    }


def cases_and_worlds(out: Path):
    shortlist_path = out / "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl"
    held_path = out / "R52_PRIVATE_QUALITY_16_HOLD_REGISTER.jsonl"
    worlds_path = out / "R52_PRIVATE_WORLD_COMPONENT_PREFLIGHT.jsonl"
    agg_path = out / "R52_POST_QUALITY_SAFE_AGGREGATE.json"
    positive = read_jsonl(shortlist_path, private=True, count=46)
    negative = read_jsonl(held_path, private=True, count=16)
    require(agg_path.is_file() and not agg_path.is_symlink() and
            stat.S_IMODE(agg_path.stat().st_mode) == 0o600,
            "R52_AGGREGATE_MISSING_OR_UNSAFE")
    agg = json.loads(agg_path.read_text(encoding="utf-8"))
    require(agg.get("schema") == AGGREGATE_SCHEMA and
            agg.get("status") == "R52_ALL_62_QUALITY_REVIEWS_REVERIFIED__NO_ADMISSION" and
            agg.get("cases_revalidated") == 62 and
            agg.get("quality_possible_first_pass") == 46 and
            agg.get("quality_holds") == 16 and
            agg.get("source_citations_revalidated") == 205 and
            agg.get("train_admitted") == agg.get("validation_admitted") == 0,
            "R52_CLOSURE_AGGREGATE_NOT_PINNED")
    rows = positive + negative
    ids = set()
    members = defaultdict(list)
    for row in rows:
        cid = row.get("candidate_id")
        source_id = row.get("source_story_id")
        require(row.get("schema") == QUALITY_SCHEMA and
                row.get("private_do_not_commit") is True and
                isinstance(cid, str) and cid not in ids and
                isinstance(source_id, str) and bool(source_id.strip()) and
                isinstance(row.get("story_rank"), int) and
                isinstance(row.get("target_sha256"), str) and
                len(row["target_sha256"]) == 64 and
                row.get("split") is None and
                row.get("training_admission") == HOLD and
                row.get("owner_rights") == "OWNER_ATTESTED_FULL_OWNERSHIP" and
                row.get("final_quality_and_safety_signoff") == "PENDING" and
                row.get("linked_world_component_verified") is False,
                "R52_CASE_PROVENANCE_OR_HOLD_CHANGED")
        if row in positive:
            require(row.get("eligibility_stage") == "QUALITY_POSSIBLE__NEEDS_GATES" and
                    row.get("quality_review_route") ==
                    "NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD",
                    "R52_POSITIVE_QUALITY_ROUTE_CHANGED")
        else:
            require(row.get("eligibility_stage") == "QUALITY_DEFECT_HOLD" and
                    row.get("quality_review_route") !=
                    "NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD",
                    "R52_QUALITY_HOLD_ROUTE_CHANGED")
        ids.add(cid)
        members[source_id].append(row)
    require(len(ids) == 62 and len(members) == 7,
            "SOURCE_WORLD_OR_CANDIDATE_COUNT_CHANGED")
    preflight = read_jsonl(worlds_path, private=True, count=7)
    indexed = {r.get("source_story_id"): r for r in preflight}
    require(len(indexed) == 7 and set(indexed) == set(members),
            "WORLD_PREFLIGHT_ID_SET_CHANGED")
    for sid, group in members.items():
        p = indexed[sid]
        ranks = {g["story_rank"] for g in group}
        require(p.get("schema") == WORLD_SCHEMA and
                p.get("private_do_not_commit") is True and len(ranks) == 1 and
                p.get("source_story_rank") in ranks and
                p.get("first_pass_possible") ==
                sum(x["eligibility_stage"] == "QUALITY_POSSIBLE__NEEDS_GATES"
                    for x in group) and
                p.get("quality_holds") ==
                sum(x["eligibility_stage"] == "QUALITY_DEFECT_HOLD"
                    for x in group) and
                p.get("linked_or_alias_world_component") == "UNRESOLVED" and
                p.get("world_split") is None and
                p.get("component_isolation_pass") is False,
                "WORLD_PREFLIGHT_PROVENANCE_CHANGED")
    return positive, negative, members, {
        "r52_46_shortlist_sha256": sha_file(shortlist_path),
        "r52_16_hold_sha256": sha_file(held_path),
        "r52_world_preflight_sha256": sha_file(worlds_path),
        "r52_post_quality_aggregate_sha256": sha_file(agg_path),
    }


def screen(repo: Path, r52: Path) -> tuple[list[dict], dict]:
    positive, held, worlds, pinned = cases_and_worlds(r52)
    historical, old = historical_registry(repo)
    held_ids = {r["source_story_id"] for r in held}
    all_ids = set(worlds)
    overlaps = {
        k: len(all_ids & story_set) for k, story_set in historical.items()
    }
    positives_overlap = {
        k: len({r["source_story_id"] for r in positive} & story_set)
        for k, story_set in historical.items()
    }
    # A revised historical registry or changed Gold108 UUID relation requires
    # an explicit HOLD, not a silent "clean" conclusion.
    require(not any(overlaps.values()), "EXACT_HISTORICAL_UUID_OVERLAP_HOLD")
    review = []
    for sid, group in sorted(worlds.items(),
                             key=lambda item: min(x["story_rank"] for x in item[1])):
        rank = group[0]["story_rank"]
        review.append({
            "schema": "storyforge-r52-private-world-component-review-v1",
            "private_do_not_commit": True,
            "source_story_id": sid,
            "story_rank": rank,
            "first_pass_possible": len(group) -
                sum(x["eligibility_stage"] == "QUALITY_DEFECT_HOLD" for x in group),
            "quality_holds": sum(x["eligibility_stage"] == "QUALITY_DEFECT_HOLD"
                                 for x in group),
            "known_old_04_07_linkage_relevant": rank in (4, 7),
            "exact_v01_story_uuid_overlap": False,
            "semantic_world_alias_review": "PENDING_OWNER_REVIEW",
            "shared_character_identity_review": "PENDING_OWNER_REVIEW",
            "gold87_cross_world_semantic_review": "PENDING_OWNER_REVIEW",
            "v01_prior_train_semantic_review": "PENDING_OWNER_REVIEW",
            "r50_sealed_heldout_check": "NOT_OPENED_PROTECTED",
            "proposed_world_component_id": None,
            "linked_to_other_story_ids": [],
            "manual_evidence_references": [],
            "owner_component_isolation_signed": False,
            "train_val_split": None,
            "training_admission": HOLD,
        })
    safe = {
        "schema": "storyforge-r52-world-isolation-exact-screen-v1",
        "status": "R52_V01_EXACT_UUID_SCREEN_PASS__WORLD_GRAPH_AND_SEALED_TEST_HOLD",
        "r52_source_pins": pinned,
        **old,
        "first_pass_candidates": len(positive),
        "quality_holds": len(held),
        "source_story_groups": len(worlds),
        "exact_overlap_with_v01_splits_by_story_count": overlaps,
        "exact_positive_overlap_by_story_count": positives_overlap,
        "any_quality_held_story_in_inventory": bool(held_ids),
        "semantic_world_independence_verified": False,
        "gold87_semantic_alias_independence_verified": False,
        "r50_sealed_heldout_opened": False,
        "r50_sealed_heldout_isolation_verified": False,
        "linked_component_graph_reviewed": 0,
        "world_split_assigned": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "private_story_text_or_candidate_ids_in_stdout": False,
        "next_gate": "OWNER_LINKED_WORLD_GRAPH_AND_QUALITY_SAFETY_SIGNOFF",
    }
    return review, safe


def create_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--r52-post-quality-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        repo = args.repo.resolve(strict=True)
        prior = args.r52_post_quality_dir.expanduser().absolute()
        out = args.out_dir.expanduser().absolute()
        require(out.is_dir() and not out.is_symlink() and
                stat.S_IMODE(out.stat().st_mode) & 0o077 == 0 and
                out.resolve() != repo and repo not in out.resolve().parents,
                "OUTPUT_DIR_UNSAFE_OR_WITHIN_REPO")
        review, safe = screen(repo, prior)
        artifacts = {
            out / "R52_PRIVATE_07_WORLD_COMPONENT_REVIEW_QUEUE.jsonl":
                "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                        for r in review),
            out / "R52_WORLD_EXACT_ISOLATION_SAFE_AGGREGATE.json":
                json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        }
        require(not any(x.exists() or x.is_symlink() for x in artifacts),
                "OUTPUT_ALREADY_EXISTS")
        os.umask(0o077)
        for path, content in artifacts.items():
            create_private(path, content)
    except (OSError, TypeError, KeyError, ValueError, json.JSONDecodeError) as err:
        marker = str(err) if isinstance(err, GateHold) else type(err).__name__
        print("R52_WORLD_EXACT_HOLD__" + marker, file=sys.stderr)
        return 2
    print(safe["status"])
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

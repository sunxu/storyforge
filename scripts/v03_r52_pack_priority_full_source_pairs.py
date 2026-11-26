"""Create private full-source evidence ZIP for R52's 3 priority world pairs.

Reads the owner's seven authenticated original-world exports locally.
Verifies source-message SHA256 and 104 R51 target pins against a fixed
owner-reported receipt, then bundles only original worlds referenced by the
three unresolved pair edges. Never opens R50 or approves Train/Val/GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

EXPECTED_OUTER_SHA = "b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb"
HOLD = "PENDING_NOT_APPROVED"
PRIORITY = "INSUFFICIENT_SOURCE_EVIDENCE__HOLD"
SAFE_STATUS = "R52_SEVEN_COMPLETE_ORIGINAL_STORIES_RECOVERED__ALL_21_GRAPH_HOLD"


class PackHold(ValueError):
    pass


def require(ok: bool, marker: str) -> None:
    if not ok:
        raise PackHold(marker)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def private_file(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), "PRIVATE_INPUT_MISSING")
    require(stat.S_IMODE(path.stat().st_mode) == 0o600,
            "PRIVATE_FILE_PERMISSIONS_UNSAFE")
    require(stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
            "PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE")
    return path.read_bytes()


def parse_jsonl(raw: bytes, expected: int) -> list[dict]:
    rows = [json.loads(line) for line in raw.decode("utf8").splitlines()
            if line.strip()]
    require(len(rows) == expected and
            all(isinstance(x, dict) for x in rows),
            "PRIVATE_JSONL_COUNT_OR_FORMAT_CHANGED")
    return rows


def validate_source_world(rank: int, raw: bytes) -> tuple[dict, int, int]:
    world = json.loads(raw)
    require(isinstance(world, dict) and
            world.get("schema") == "storyforge-r52-private-full-original-world-v1" and
            world.get("private_do_not_commit") is True and
            world.get("story_rank") == rank and
            isinstance(world.get("source_story_id"), str) and
            world.get("source_archive_outer_sha256") == EXPECTED_OUTER_SHA and
            world.get("training_admission") == HOLD and
            world.get("original_generated_system_prompt_reconstructed") is False and
            world.get("semantic_independence_certified") is False,
            "ORIGINAL_WORLD_PROVENANCE_INVALID")
    msgs = world.get("original_root_messages")
    require(isinstance(msgs, list) and bool(msgs),
            "ORIGINAL_MESSAGE_LIST_INVALID")
    require(len(msgs) <= 150000, "ORIGINAL_STORY_OVERSIZE")
    for i, m in enumerate(msgs):
        require(isinstance(m, dict) and
                m.get("original_source_array_index") == i and
                m.get("role") in ("user", "assistant", "system") and
                isinstance(m.get("original_source_message_id"), str) and
                isinstance(m.get("content"), str) and
                sha(m["content"].encode("utf8")) == m.get("source_body_sha256"),
                "FULL_ORIGINAL_MESSAGE_SHA_OR_INDEX_CHANGED")
    pins = world.get("r51_frozen_target_pins_verified")
    require(isinstance(pins, list), "R51_TARGET_PINS_MISSING")
    target_ids = set()
    for pin in pins:
        require(isinstance(pin, dict) and
                isinstance(pin.get("candidate_id"), str) and
                pin["candidate_id"] not in target_ids,
                "TARGET_CANDIDATE_ID_INVALID")
        target_ids.add(pin["candidate_id"])
        index = pin.get("target_original_array_index")
        require(type(index) is int and 0 <= index < len(msgs) and
                msgs[index]["role"] == "assistant" and
                msgs[index]["source_body_sha256"] == pin.get("target_sha256"),
                "R51_TARGET_PIN_CHANGED")
    return world, len(msgs), len(pins)


def package(source_dir: Path, out_dir: Path, repo: Path) -> dict:
    require(out_dir.is_dir() and not out_dir.is_symlink() and
            stat.S_IMODE(out_dir.stat().st_mode) & 0o077 == 0,
            "OUTPUT_DIR_MUST_BE_PRIVATE")
    repo, out_dir = repo.resolve(strict=True), out_dir.resolve(strict=True)
    require(out_dir != repo and repo not in out_dir.parents,
            "OUTPUT_MUST_BE_OUTSIDE_GIT")
    agg_raw = private_file(
        source_dir / "R52_FULL_ORIGINAL_WORLD_RECOVERY_SAFE_AGGREGATE.json")
    aggregate = json.loads(agg_raw)
    require(aggregate.get("schema") ==
            "storyforge-r52-full-original-world-recovery-safe-aggregate-v1" and
            aggregate.get("status") == SAFE_STATUS and
            aggregate.get("full_original_story_exports_verified") == 7 and
            aggregate.get("full_original_source_messages") == 20577 and
            aggregate.get("frozen_r51_target_pin_checks_in_seven_worlds") == 104 and
            aggregate.get("bounded_citations_revalidated") == 126 and
            aggregate.get("complete_pair_review_queue") == 21 and
            aggregate.get("priority_insufficient_bounded_pairs") == 3 and
            aggregate.get("original_source_bundle_sha256") == EXPECTED_OUTER_SHA and
            aggregate.get("r50_sealed_heldout_opened") is False and
            aggregate.get("world_components_certified") ==
            aggregate.get("world_split_assigned") ==
            aggregate.get("train_admitted") ==
            aggregate.get("validation_admitted") == 0,
            "FULL_RECOVERY_RECEIPT_NOT_FROZEN")
    all_pairs_raw = private_file(
        source_dir / "R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl")
    priority_raw = private_file(
        source_dir / "R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl")
    all_pairs = parse_jsonl(all_pairs_raw, 21)
    priority_pairs = parse_jsonl(priority_raw, 3)
    identities = set()
    priorities = set()
    for item in all_pairs:
        key = (item.get("left_rank"), item.get("right_rank"))
        require(isinstance(key[0], int) and isinstance(key[1], int) and
                key[0] < key[1] and key not in identities and
                item.get("schema") == "storyforge-r52-private-full-source-world-pair-task-v1" and
                item.get("private_do_not_commit") is True and
                item.get("training_admission") == HOLD and
                item.get("full_source_reviewer_decision") == "PENDING" and
                item.get("related_world_graph_signed") is False and
                item.get("semantic_independence_verified") is False,
                "FULL_PAIR_STATUS_OR_ID_CHANGED")
        identities.add(key)
    by_key = {(p["left_rank"], p["right_rank"]): p for p in all_pairs}
    for item in priority_pairs:
        key = (item.get("left_rank"), item.get("right_rank"))
        require(key in by_key and key not in priorities and
                item == by_key[key] and
                item["bounded_decision"] == PRIORITY,
                "PRIORITY_PAIR_MISMATCH")
        priorities.add(key)
    require(sum(p["bounded_decision"] == PRIORITY for p in all_pairs) == 3,
            "PRIORITY_COUNT_CHANGED")
    all_ranks = {x for p in all_pairs for x in
                 (p["left_rank"], p["right_rank"])}
    require(len(all_ranks) == 7 and
            len(identities) == 21, "SEVEN_WORLD_PAIR_COVERAGE_CHANGED")

    source_raw = {}
    message_total = 0
    pin_total = 0
    for rank in sorted(all_ranks):
        filename = f"R52_PRIVATE_FULL_ORIGINAL_STORY_{rank:02d}.json"
        raw = private_file(source_dir / filename)
        world, n, pins = validate_source_world(rank, raw)
        source_raw[rank] = (raw, world)
        message_total += n
        pin_total += pins
    require(message_total == 20577 and pin_total == 104,
            "ORIGINAL_MESSAGE_OR_PIN_TOTAL_CHANGED")
    selected_ranks = {r for p in priority_pairs
                      for r in (p["left_rank"], p["right_rank"])}
    for pair in priority_pairs:
        for side in ("left", "right"):
            rank = pair[f"{side}_rank"]
            raw, world = source_raw[rank]
            require(pair[f"{side}_source_story_id"] == world["source_story_id"] and
                    pair[f"{side}_original_jsonl_sha256"] ==
                    world["original_source_jsonl_sha256"] and
                    pair[f"{side}_full_original_file"] ==
                    f"R52_PRIVATE_FULL_ORIGINAL_STORY_{rank:02d}.json",
                    "PAIR_ORIGINAL_SOURCE_REFERENCE_CHANGED")
    zip_name = "R52_PRIORITY_03_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip"
    receipt_name = "R52_PRIORITY_03_FULL_ORIGINAL_WORLD_REVIEW_SAFE_RECEIPT.json"
    zip_path, receipt_path = out_dir / zip_name, out_dir / receipt_name
    require(not zip_path.exists() and not zip_path.is_symlink() and
            not receipt_path.exists() and not receipt_path.is_symlink(),
            "OUTPUT_ALREADY_EXISTS")
    readme = (
        "StoryForge R52 — full-original source for THREE priority world pairs.\n"
        "All included original text is PRIVATE; never upload to GitHub.\n"
        "Compare each pair using both complete original message histories, "
        "not only the earlier bounded review rationale.\n"
        "Cite each claim using original_source_array_index plus "
        "source_body_sha256; note the exact involved story source rank.\n"
        "Original export story metadata is NOT a historical prompt proof.\n"
        "All pairs remain HOLD. No model training or heldout unsealing.\n"
    ).encode("utf8")
    entries = {
        "README_PRIVATE_REVIEW.txt": readme,
        "R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl":
            priority_raw,
    }
    for rank in sorted(selected_ranks):
        entries[f"R52_PRIVATE_FULL_ORIGINAL_STORY_{rank:02d}.json"] = (
            source_raw[rank][0])
    manifest = {
        "schema": "storyforge-r52-priority03-full-source-review-manifest-v1",
        "three_pair_count": 3,
        "included_complete_original_story_files": len(selected_ranks),
        "source_archive_sha256": EXPECTED_OUTER_SHA,
        "archive_member_sha256": {k: sha(v) for k, v in sorted(entries.items())},
        "training_admission": HOLD,
        "r50_sealed_heldout_included": False,
    }
    entries["SHA256_MANIFEST_PRIVATE.json"] = (
        json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf8")
    os.umask(0o077)
    fd = os.open(zip_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        with zipfile.ZipFile(handle, mode="w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for name in sorted(entries):
                archive.writestr(name, entries[name])
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None and
                set(archive.namelist()) == set(entries),
                "OUTPUT_ZIP_INTEGRITY_HOLD")
    report = {
        "schema": "storyforge-r52-priority03-full-source-package-safe-receipt-v1",
        "status": "R52_PRIORITY_03_COMPLETE_SOURCE_PACKAGE_VERIFIED__GRAPH_HOLD",
        "priority_pairs": 3,
        "source_worlds_in_complete_graph": 7,
        "priority_complete_worlds_packaged": len(selected_ranks),
        "all_original_source_messages_verified": message_total,
        "r51_original_target_pins_verified": pin_total,
        "all_bounded_pair_decisions_preserved": 21,
        "archive_sha256": sha(zip_path.read_bytes()),
        "source_receipt_sha256": sha(agg_raw),
        "all_pair_queue_sha256": sha(all_pairs_raw),
        "priority_pair_queue_sha256": sha(priority_raw),
        "manual_full_source_review_completed": 0,
        "semantic_isolation_verified": False,
        "train_admitted": 0, "validation_admitted": 0,
        "world_split_assigned": 0,
        "r50_sealed_heldout_opened": False,
        "private_text_or_identifiers_emitted": False,
    }
    rfd = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(rfd, "w", encoding="utf8") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--world-full-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        report = package(
            args.world_full_dir.expanduser().absolute(),
            args.out_dir.expanduser().absolute(),
            args.repo.resolve(strict=True),
        )
    except (OSError, PackHold, KeyError, TypeError, ValueError,
            zipfile.BadZipFile, json.JSONDecodeError) as exc:
        reason = str(exc) if isinstance(exc, PackHold) else type(exc).__name__
        print("R52_PRIORITY_03_PACKAGE_HOLD__" + reason, file=sys.stderr)
        return 2
    print(report["status"])
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

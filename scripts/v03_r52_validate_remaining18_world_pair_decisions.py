"""Validate one R52 six-pair full-original world-link review batch.

Strict source ZIP and citation SHA checks; no independent-world certification,
Train/Val allocation, unsealing of R50, or training approval.
"""
from __future__ import annotations
import argparse
import collections
import json
import os
import stat
import sys
import zipfile
from pathlib import Path
import v03_r52_pack_remaining18_full_source_pairs as pack

RESULT_SCHEMA = "storyforge-r52-private-full-source-remaining18-decision-v1"
VALID = frozenset({
    "LINKED_WORLD_EVIDENCE__HOLD",
    "NO_LINK_OBSERVED_IN_FULL_AVAILABLE_SOURCE__HOLD",
    "INSUFFICIENT_FULL_SOURCE_EVIDENCE__HOLD",
})


def verify(zip_path: Path, safe_receipt: Path, decisions: Path, batch: int) -> dict:
    pack.require(batch in (1, 2, 3), "BATCH_MUST_BE_ONE_TWO_THREE")
    raw = pack.private_file(zip_path)
    receipt = json.loads(pack.private_file(safe_receipt))
    pack.require(receipt.get("schema") ==
                 "storyforge-r52-remaining18-full-source-package-safe-receipt-v1" and
                 receipt.get("status") ==
                 "R52_REMAINING_18_FULL_SOURCE_REVIEW_PACKAGE_VERIFIED__GRAPH_HOLD" and
                 receipt.get("archive_sha256") == pack.sha(raw) and
                 receipt.get("remaining_pair_tasks_prepared") == 18 and
                 receipt.get("complete_original_worlds_packaged") == 7 and
                 receipt.get("prior_priority_pairs_excluded") == 3 and
                 receipt.get("all_original_source_messages_verified") == 20577 and
                 receipt.get("r51_original_target_pins_verified") == 104 and
                 receipt.get("train_admitted") == receipt.get("validation_admitted") ==
                 receipt.get("world_split_assigned") == 0 and
                 receipt.get("r50_sealed_heldout_opened") is False,
                 "SOURCE_RECEIPT_OR_PACKAGE_PIN_CHANGED")
    with zipfile.ZipFile(zip_path) as z:
        pack.require(z.testzip() is None, "INPUT_ZIP_CRC_INVALID")
        names = set(z.namelist())
        manifest = json.loads(z.read("SHA256_MANIFEST_PRIVATE.json"))
        pack.require(manifest.get("schema") ==
                     "storyforge-r52-remaining18-full-source-review-manifest-v1" and
                     manifest.get("remaining_pair_count") == 18 and
                     manifest.get("batch_counts") == [6, 6, 6] and
                     manifest.get("complete_original_story_files") == 7 and
                     manifest.get("previous_priority_pair_count") == 3 and
                     manifest.get("source_archive_sha256") == pack.EXPECTED_OUTER_SHA and
                     manifest.get("frozen_all21_queue_sha256") == pack.EXPECTED_ALL21_SHA and
                     manifest.get("frozen_priority3_queue_sha256") == pack.EXPECTED_PRIORITY3_SHA and
                     manifest.get("training_admission") == pack.HOLD and
                     manifest.get("semantic_world_isolation_verified") is False and
                     manifest.get("r50_sealed_heldout_included") is False,
                     "PACKAGE_MANIFEST_PINS_INVALID")
        hashes = manifest.get("archive_member_sha256")
        pack.require(isinstance(hashes, dict) and
                     set(hashes) == names - {"SHA256_MANIFEST_PRIVATE.json"},
                     "PACKAGE_MANIFEST_MEMBER_SET_CHANGED")
        for name, digest in hashes.items():
            pack.require(pack.sha(z.read(name)) == digest,
                         "PACKAGE_MEMBER_SHA_MISMATCH")
        originals = {}
        for name in sorted(names):
            if name.startswith("R52_PRIVATE_FULL_ORIGINAL_STORY_") and name.endswith(".json"):
                code = name[len("R52_PRIVATE_FULL_ORIGINAL_STORY_"):-5]
                pack.require(len(code) == 2 and code.isdigit(),
                             "ORIGINAL_STORY_FILE_NAME_INVALID")
                rank = int(code)
                pack.require(rank not in originals, "DUPLICATE_FULL_STORY")
                world, _, _ = pack.validate_source_world(rank, z.read(name))
                originals[rank] = world
        pack.require(len(originals) == 7 and
                     sum(len(x["original_root_messages"]) for x in originals.values()) == 20577 and
                     sum(len(x["r51_frozen_target_pins_verified"]) for x in originals.values()) == 104,
                     "SOURCE_WORLD_COUNT_OR_PIN_DRIFT")
        all_pairs = pack.parse_jsonl(
            z.read("R52_PRIVATE_REMAINING_18_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"), 18)
        batched = []
        for n in (1, 2, 3):
            batched.extend(pack.parse_jsonl(
                z.read(f"R52_PRIVATE_REMAINING_18_BATCH_{n:02d}_PAIR_TASKS.jsonl"), 6))
        pack.require(all_pairs == batched, "BATCH_TASKS_DIFFER_FROM_FROZEN_18")
        pair_keys = set()
        for task in all_pairs:
            key = (task.get("left_rank"), task.get("right_rank"))
            pack.require(key[0] in originals and key[1] in originals and
                         key[0] < key[1] and key not in pair_keys and
                         task.get("bounded_decision") == pack.BOUNDED and
                         task.get("training_admission") == pack.HOLD and
                         task.get("semantic_independence_verified") is False,
                         "TASK_PAIR_OR_ROUTE_INVALID")
            pair_keys.add(key)
            for side in ("left", "right"):
                world = originals[task[f"{side}_rank"]]
                pack.require(task.get(f"{side}_source_story_id") == world["source_story_id"] and
                             task.get(f"{side}_original_jsonl_sha256") ==
                             world["original_source_jsonl_sha256"],
                             "TASK_SOURCE_UUID_OR_SOURCE_SHA_CHANGED")
        excluded = pack.parse_jsonl(
            z.read("R52_PRIOR_PRIORITY_03_PAIR_IDENTITIES.jsonl"), 3)
        previous = {(p.get("left_rank"), p.get("right_rank")) for p in excluded}
        pack.require(len(previous) == 3 and previous.isdisjoint(pair_keys),
                     "PREVIOUSLY_REVIEWED_PAIRS_REINTRODUCED")
        tasks = all_pairs[(batch - 1) * 6:batch * 6]
        by_key = {(t["left_rank"], t["right_rank"]): t for t in tasks}
        results = pack.parse_jsonl(pack.private_file(decisions), 6)
        seen = set()
        counts = collections.Counter()
        citations = 0
        for row in results:
            key = (row.get("left_rank"), row.get("right_rank"))
            pack.require(key in by_key and key not in seen and
                         row.get("schema") == RESULT_SCHEMA and
                         row.get("batch_number") == batch and
                         row.get("review_route") in VALID and
                         row.get("training_admission") == pack.HOLD and
                         row.get("split") is None and
                         row.get("world_component_certified") is False and
                         row.get("r50_sealed_heldout_opened") is False,
                         "DECISION_ID_OR_HOLD_STATUS_INVALID")
            seen.add(key)
            task = by_key[key]
            for side in ("left", "right"):
                pack.require(row.get(f"{side}_source_story_id") ==
                             task[f"{side}_source_story_id"] and
                             row.get(f"{side}_original_jsonl_sha256") ==
                             task[f"{side}_original_jsonl_sha256"],
                             "DECISION_SOURCE_ID_OR_SHA_MISMATCH")
            pack.require(isinstance(row.get("rationale"), str) and
                         len(row["rationale"].strip()) >= 80,
                         "INDIVIDUAL_DECISION_RATIONALE_TOO_SHORT")
            refs = row.get("source_citations")
            pack.require(isinstance(refs, list) and len(refs) >= 2,
                         "DECISION_CITATIONS_REQUIRED")
            seen_ref = set()
            both = set()
            for cite in refs:
                pack.require(isinstance(cite, dict), "CITATION_NOT_OBJECT")
                rank = cite.get("story_rank")
                index = cite.get("original_source_array_index")
                pack.require(rank in key and type(index) is int and
                             cite.get("scope") == "FULL_ORIGINAL" and
                             0 <= index < len(originals[rank]["original_root_messages"]),
                             "CITATION_SOURCE_OR_INDEX_INVALID")
                expected = originals[rank]["original_root_messages"][index][
                    "source_body_sha256"]
                ref = (rank, index, cite.get("source_body_sha256"))
                pack.require(ref not in seen_ref and
                             cite.get("source_body_sha256") == expected,
                             "CITATION_SHA_MISMATCH_OR_DUPLICATED")
                seen_ref.add(ref)
                both.add(rank)
            pack.require(both == set(key), "EVIDENCE_REQUIRED_FROM_BOTH_WORLDS")
            citations += len(refs)
            counts[row["review_route"]] += 1
    return {
        "schema": "storyforge-r52-remaining18-batch-validation-receipt-v1",
        "status": "R52_REMAINING_18_BATCH_REVIEW_VALIDATED__GRAPH_HOLD",
        "source_zip_sha256": pack.sha(raw),
        "decisions_sha256": pack.sha(pack.private_file(decisions)),
        "batch_number": batch,
        "pairs_validated": len(seen),
        "source_citations_validated": citations,
        "review_route_counts": dict(sorted(counts.items())),
        "world_components_certified": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "world_split_assigned": 0,
        "r50_sealed_heldout_opened": False,
        "private_text_or_story_ids_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--decisions", type=Path, required=True)
    p.add_argument("--batch", type=int, required=True)
    p.add_argument("--receipt-out", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify(args.source_zip, args.source_receipt, args.decisions, args.batch)
        path = args.receipt_out.expanduser().absolute()
        pack.require(path.parent.is_dir() and not path.parent.is_symlink() and
                     stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0 and
                     not path.exists() and not path.is_symlink(),
                     "OUTPUT_RECEIPT_FILE_NOT_PRIVATE_OR_EXISTS")
        old = os.umask(0o077)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf8") as stream:
                json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
        finally:
            os.umask(old)
    except (pack.PackHold, OSError, ValueError, KeyError, TypeError,
            json.JSONDecodeError, zipfile.BadZipFile) as exc:
        why = str(exc) if isinstance(exc, pack.PackHold) else type(exc).__name__
        print("R52_REMAINING18_VALIDATOR_HOLD__" + why, file=sys.stderr)
        return 2
    print(result["status"])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

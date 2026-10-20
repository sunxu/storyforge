"""R52 consolidate 21 full-source pair reviews into an unsigned private graph.

Verifies 3 independent priority results + 18 formally Mac-validated results,
reusing the authenticated seven-story source ZIP. Does NOT infer world
independence from no-link observations, assign split, authorize model training,
or access R50 heldout test content. No private story text emitted to stdout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from collections import Counter
from itertools import combinations
from pathlib import Path

import v03_r52_pack_remaining18_full_source_pairs as packaging
import v03_r52_validate_remaining18_world_pair_decisions as validation
import v03_r52_world_exact_isolation as identity

PRIORITY_SHA = "f9bdee7693fb2ed6f66babafb431c5e83b13185248cc95969c55976f126a0f36"
REMAINING_SHA = {
    1: "4c1c5159bfdf9d984b5319e20827ebd1d99846be310a81bff4e24243a5e279d9",
    2: "c860d69a8a74aff2fbe0c1e55dca40624384a24a2158e4a4f7e9d59168f1f00e",
    3: "1e171dda7fef17eba7e287246c498712ff5306a01a28d549a947e496614fa394",
}
ZIP_SHA = "4076ac6de54ad41d3617628555ee35e6f5066e3a38084a4e5211051f9840f74f"
NO_LINK = "NO_LINK_OBSERVED_IN_FULL_AVAILABLE_SOURCE__HOLD"
HOLD = packaging.HOLD


def demand(ok: bool, code: str) -> None:
    if not ok:
        raise packaging.PackHold(code)


def read_receipt(path: Path) -> dict:
    obj = json.loads(packaging.private_file(path))
    demand(isinstance(obj, dict), "RECEIPT_NOT_OBJECT")
    return obj


def referenced_citations(row: dict, worlds: dict[int, dict]) -> int:
    a, b = row["left_rank"], row["right_rank"]
    citations = row.get("source_citations")
    demand(isinstance(citations, list) and len(citations) >= 2,
           "SOURCE_CITATIONS_MISSING")
    sides = set()
    seen = set()
    for c in citations:
        demand(isinstance(c, dict), "SOURCE_CITATION_NOT_OBJECT")
        rank, idx = c.get("story_rank"), c.get("original_source_array_index")
        demand(rank in (a, b) and type(idx) is int and
               0 <= idx < len(worlds[rank]["original_root_messages"]) and
               c.get("scope") == "FULL_ORIGINAL",
               "SOURCE_CITATION_OUTSIDE_ORIGINAL")
        pin = worlds[rank]["original_root_messages"][idx]["source_body_sha256"]
        key = (rank, idx, c.get("source_body_sha256"))
        demand(c.get("source_body_sha256") == pin and key not in seen,
               "SOURCE_CITATION_SHA_OR_DUPLICATE")
        seen.add(key)
        sides.add(rank)
    demand(sides == {a, b}, "BOTH_WORLDS_REQUIRE_SOURCE_CITATIONS")
    return len(citations)


def recover_worlds(zip_path: Path) -> tuple[dict[int, dict], dict]:
    demand(packaging.sha(packaging.private_file(zip_path)) == ZIP_SHA,
           "FULL_SOURCE_ZIP_SHA_CHANGED")
    worlds = {}
    with zipfile.ZipFile(zip_path) as z:
        demand(z.testzip() is None, "FULL_SOURCE_ZIP_CRC_FAILED")
        manifest = json.loads(z.read("SHA256_MANIFEST_PRIVATE.json"))
        members = manifest.get("archive_member_sha256")
        demand(manifest.get("schema") ==
               "storyforge-r52-remaining18-full-source-review-manifest-v1" and
               manifest.get("remaining_pair_count") == 18 and
               manifest.get("batch_counts") == [6,6,6] and
               manifest.get("complete_original_story_files") == 7 and
               manifest.get("source_archive_sha256") == packaging.EXPECTED_OUTER_SHA and
               manifest.get("frozen_all21_queue_sha256") == packaging.EXPECTED_ALL21_SHA and
               manifest.get("frozen_priority3_queue_sha256") == packaging.EXPECTED_PRIORITY3_SHA and
               isinstance(members, dict) and
               set(members) == set(z.namelist()) - {"SHA256_MANIFEST_PRIVATE.json"},
               "FROZEN_FULL_SOURCE_MANIFEST_CHANGED")
        for name, value in members.items():
            demand(packaging.sha(z.read(name)) == value,
                   "FULL_SOURCE_MEMBER_SHA_DRIFT")
        for name in z.namelist():
            if name.startswith("R52_PRIVATE_FULL_ORIGINAL_STORY_") and name.endswith(".json"):
                suffix = name.removeprefix("R52_PRIVATE_FULL_ORIGINAL_STORY_").removesuffix(".json")
                demand(len(suffix) == 2 and suffix.isdigit(), "WORLD_SOURCE_FILENAME_INVALID")
                rank = int(suffix)
                demand(rank not in worlds, "DUPLICATE_WORLD_RANK")
                worlds[rank], _, _ = packaging.validate_source_world(rank, z.read(name))
        prior = packaging.parse_jsonl(
            z.read("R52_PRIOR_PRIORITY_03_PAIR_IDENTITIES.jsonl"), 3)
        rest = packaging.parse_jsonl(
            z.read("R52_PRIVATE_REMAINING_18_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"), 18)
    demand(len(worlds) == 7 and
           sum(len(w["original_root_messages"]) for w in worlds.values()) == 20577 and
           sum(len(w["r51_frozen_target_pins_verified"]) for w in worlds.values()) == 104,
           "WORLD_SOURCE_COUNTS_CHANGED")
    remaining_keys = {(p["left_rank"], p["right_rank"]) for p in rest}
    priority_keys = {(p["left_rank"], p["right_rank"]) for p in prior}
    keys = set(combinations(sorted(worlds), 2))
    demand(len(remaining_keys) == 18 and len(priority_keys) == 3 and
           remaining_keys.isdisjoint(priority_keys) and
           remaining_keys | priority_keys == keys and
           all(p.get("original_bounded_route") == packaging.PRIORITY for p in prior),
           "FROZEN_COMPLETE_GRAPH_21_KEYS_MISMATCH")
    for row in rest:
        demand(row.get("bounded_decision") == packaging.BOUNDED and
               row.get("training_admission") == HOLD and
               row.get("semantic_independence_verified") is False,
               "FROZEN_REMAINING_TASK_STATUS_CHANGED")
        for side in ("left", "right"):
            world = worlds[row[f"{side}_rank"]]
            demand(row.get(f"{side}_source_story_id") == world["source_story_id"] and
                   row.get(f"{side}_original_jsonl_sha256") ==
                   world["original_source_jsonl_sha256"],
                   "SOURCE_ORIGINAL_UUID_OR_SHA_CHANGED")
    return worlds, {"priority_keys": priority_keys,
                    "remaining_keys": remaining_keys,
                    "rest": rest}


def consolidate(zip_path: Path, zip_receipt: Path,
                priority_results: Path, priority_receipt: Path,
                batch_folder: Path, post_quality: Path) -> tuple[list, list, dict]:
    worlds, pairset = recover_worlds(zip_path)
    source_receipt = read_receipt(zip_receipt)
    demand(source_receipt.get("status") ==
           "R52_REMAINING_18_FULL_SOURCE_REVIEW_PACKAGE_VERIFIED__GRAPH_HOLD" and
           source_receipt.get("archive_sha256") == ZIP_SHA and
           source_receipt.get("remaining_pair_tasks_prepared") == 18 and
           source_receipt.get("prior_priority_pairs_excluded") == 3,
           "FULL_SOURCE_PACKAGE_RECEIPT_CHANGED")
    pri_raw = packaging.private_file(priority_results)
    demand(packaging.sha(pri_raw) == PRIORITY_SHA,
           "PRIORITY_DECISIONS_PIN_CHANGED")
    pri = packaging.parse_jsonl(pri_raw, 3)
    receipt = read_receipt(priority_receipt)
    demand(receipt.get("schema") ==
           "storyforge-r52-full-source-priority03-validation-receipt-v1" and
           receipt.get("status") ==
           "R52_PRIORITY_03_FULL_SOURCE_DECISIONS_VALIDATED__GRAPH_HOLD" and
           receipt.get("source_package_sha256") ==
           "4b5afbb8f6e44f88dea5c5b173577d7fca98c01162e463e64ea831c7618adcd7" and
           receipt.get("decisions_sha256") == PRIORITY_SHA and
           receipt.get("priority_pairs_validated") == 3 and
           receipt.get("source_citations_validated") == 15 and
           receipt.get("semantic_world_isolation_verified") is False and
           receipt.get("train_admitted") == receipt.get("validation_admitted") ==
           receipt.get("world_split_assigned") == 0 and
           receipt.get("r50_sealed_heldout_opened") is False,
           "PRIORITY_VERIFICATION_RECEIPT_CHANGED")
    combined = {}
    counts = Counter()
    refs = 0
    for result in pri:
        key = (result.get("left_rank"), result.get("right_rank"))
        demand(key in pairset["priority_keys"] and key not in combined and
               result.get("schema") ==
               "storyforge-r52-private-full-source-priority-pair-decision-v1" and
               result.get("full_source_review_route") == NO_LINK and
               result.get("training_admission") == HOLD and
               result.get("train_val_split") is None and
               result.get("semantic_world_component_certified") is False and
               result.get("graph_owner_signed") is False and
               result.get("other_worlds_v01_gold87_semantic_overlaps_cleared") is False and
               result.get("r50_sealed_heldout_opened") is False,
               "PRIORITY_REVIEW_INVALID_OR_PREMATURE_SIGNOFF")
        for side in ("left", "right"):
            world = worlds[result[f"{side}_rank"]]
            demand(result.get(f"{side}_source_story_id") == world["source_story_id"] and
                   result.get(f"{side}_original_jsonl_sha256") ==
                   world["original_source_jsonl_sha256"],
                   "PRIORITY_SOURCE_ID_SHA_INVALID")
        refs += referenced_citations(result, worlds)
        counts[result["full_source_review_route"]] += 1
        combined[key] = (result, "PRIORITY_03")
    demand(refs == 15, "PRIORITY_CITATION_COUNT_CHANGED")

    for batch in (1,2,3):
        dec_path = batch_folder / f"R52_REMAINING_18_BATCH_{batch:02d}_FULL_SOURCE_DECISIONS.jsonl"
        dec_raw = packaging.private_file(dec_path)
        demand(packaging.sha(dec_raw) == REMAINING_SHA[batch],
               "BATCH_DECISION_PIN_CHANGED")
        formal_path = batch_folder / f"R52_REMAINING_18_BATCH_{batch:02d}_VALIDATION_RECEIPT.json"
        official = read_receipt(formal_path)
        computed = validation.verify(zip_path, zip_receipt, dec_path, batch)
        demand(computed == official and computed.get("pairs_validated") == 6 and
               computed.get("source_citations_validated") == 24 and
               computed.get("review_route_counts") == {NO_LINK: 6} and
               computed.get("world_components_certified") == 0,
               "OFFICIAL_BATCH_RECEIPT_NOT_REPRODUCIBLE")
        rows = packaging.parse_jsonl(dec_raw, 6)
        for result in rows:
            key = (result["left_rank"], result["right_rank"])
            demand(key in pairset["remaining_keys"] and key not in combined and
                   result.get("review_route") == NO_LINK,
                   "REMAINING_DUPLICATE_OR_ROUTE_CHANGED")
            n = referenced_citations(result, worlds)
            refs += n
            counts[result["review_route"]] += 1
            combined[key] = (result, f"BATCH_{batch:02d}")
    demand(set(combined) == set(combinations(sorted(worlds), 2)) and
           refs == 87 and counts == {NO_LINK: 21},
           "GRAPH_EDGES_OR_CITATIONS_INCOMPLETE")

    eligible = identity.read_jsonl(
        post_quality / "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl",
        private=True, count=46)
    held = identity.read_jsonl(
        post_quality / "R52_PRIVATE_QUALITY_16_HOLD_REGISTER.jsonl",
        private=True, count=16)
    case_counts = Counter(x.get("source_story_id") for x in eligible)
    demand(set(case_counts) == {w["source_story_id"] for w in worlds.values()} and
           len({x.get("candidate_id") for x in eligible + held}) == 62 and
           all(x.get("training_admission") == HOLD and x.get("split") is None
               for x in eligible + held),
           "FIRST_PASS_46_PRIVATE_SHORTLIST_CHANGED")
    edge_rows = []
    for (a,b), (result, source) in sorted(combined.items()):
        edge_rows.append({
            "schema": "storyforge-r52-private-21-world-graph-evidence-edge-v1",
            "private_do_not_commit": True,
            "left_rank": a, "right_rank": b,
            "left_source_story_id": worlds[a]["source_story_id"],
            "right_source_story_id": worlds[b]["source_story_id"],
            "source_review_batch": source,
            "full_source_route": NO_LINK,
            "evidence_source_citations": result["source_citations"],
            "source_decision_sha256": (
                PRIORITY_SHA if source == "PRIORITY_03" else
                REMAINING_SHA[int(source[-2:])]),
            "source_reason_for_owner_review_only": result["rationale"],
            "linked_world_or_semantic_alias_final_review": "PENDING_OWNER",
            "known_unexported_or_hidden_aliases_ruled_out": False,
            "independent_world_component_certified": False,
            "world_split": None,
            "training_admission": HOLD,
        })
    owners = []
    for rank, world in sorted(worlds.items()):
        owners.append({
            "schema": "storyforge-r52-private-7-world-graph-owner-queue-v1",
            "private_do_not_commit": True,
            "story_rank": rank, "source_story_id": world["source_story_id"],
            "quality_first_pass_possible": case_counts[world["source_story_id"]],
            "original_message_count": len(world["original_root_messages"]),
            "pair_edges_in_full_graph": 6,
            "linked_world_component_id": None,
            "full_story_alias_review_owner_signed": False,
            "historic_gold87_semantic_exposure_checked": False,
            "v01_train_and_val_semantic_exposure_checked": False,
            "unsealed_r50_heldout_used": False,
            "quality_and_safety_signoff": "PENDING",
            "final_component_isolation": "NOT_VERIFIED",
            "world_split": None,
            "training_admission": HOLD,
        })
    safe = {
        "schema": "storyforge-r52-all21-world-graph-audit-safe-aggregate-v1",
        "status": "R52_FULL_SOURCE_21_21_REVIEW_RECEIPTS_RECONCILED__GRAPH_HOLD",
        "original_complete_story_groups": 7,
        "original_messages_sha_verified": 20577,
        "r51_source_target_pins_within_seven_stories": 104,
        "priority_pairs_verified": 3,
        "remaining_pairs_formal_receipts_verified": 18,
        "distinct_edges_reconciled": 21,
        "source_citations_reverified": refs,
        "full_source_route_counts": dict(counts),
        "first_pass_quality_possible": 46,
        "quality_hold": 16,
        "semantic_world_independence_certified": False,
        "linked_world_component_owner_signatures": 0,
        "historic_gold87_v01_semantic_exposure_checked": False,
        "training_split_allocated": 0,
        "train_admitted": 0, "validation_admitted": 0,
        "r50_sealed_heldout_opened": False,
        "private_character_names_story_text_or_ids_emitted": False,
        "source_bundle_sha256": ZIP_SHA,
        "priority_decisions_sha256": PRIORITY_SHA,
        "batch_decisions_sha256": {str(k):v for k,v in REMAINING_SHA.items()},
    }
    return edge_rows, owners, safe


def exclusive_write(path: Path, value: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf8") as stream:
        stream.write(value)


def required_input_status(source_zip: Path, source_receipt: Path,
                          priority_decisions: Path, priority_receipt: Path,
                          remaining18_dir: Path, post_quality_dir: Path) -> dict:
    """List only safe input labels for missing/unsafe files, never paths/IDs."""
    expected = {
        "SOURCE_ZIP": source_zip,
        "SOURCE_RECEIPT": source_receipt,
        "PRIORITY03_DECISIONS": priority_decisions,
        "PRIORITY03_RECEIPT": priority_receipt,
        "R52_FIRST_PASS_46": post_quality_dir /
            "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl",
        "R52_QUALITY_HOLD_16": post_quality_dir /
            "R52_PRIVATE_QUALITY_16_HOLD_REGISTER.jsonl",
    }
    for batch in (1, 2, 3):
        expected[f"BATCH{batch:02d}_DECISIONS"] = remaining18_dir / (
            f"R52_REMAINING_18_BATCH_{batch:02d}_FULL_SOURCE_DECISIONS.jsonl")
        expected[f"BATCH{batch:02d}_RECEIPT"] = remaining18_dir / (
            f"R52_REMAINING_18_BATCH_{batch:02d}_VALIDATION_RECEIPT.json")
    issues = {}
    for label, file in expected.items():
        if not file.is_file() or file.is_symlink():
            issues[label] = "PRIVATE_INPUT_MISSING_OR_SYMLINK"
        elif stat.S_IMODE(file.stat().st_mode) != 0o600:
            issues[label] = "PRIVATE_INPUT_FILE_MODE_UNSAFE"
        elif stat.S_IMODE(file.parent.stat().st_mode) & 0o077:
            issues[label] = "PRIVATE_INPUT_PARENT_MODE_UNSAFE"
    return issues


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--priority-decisions", type=Path, required=True)
    p.add_argument("--priority-receipt", type=Path, required=True)
    p.add_argument("--remaining18-dir", type=Path, required=True)
    p.add_argument("--post-quality-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        out = args.out_dir.expanduser().absolute()
        cwd = Path.cwd().resolve()
        demand(out.is_dir() and not out.is_symlink() and
               stat.S_IMODE(out.stat().st_mode) & 0o077 == 0 and
               out.resolve() != cwd and cwd not in out.resolve().parents,
               "OUTPUT_DIR_IS_NOT_PRIVATE_OR_OUTSIDE_WORKTREE")
        problems = required_input_status(
            args.source_zip.expanduser().absolute(),
            args.source_receipt.expanduser().absolute(),
            args.priority_decisions.expanduser().absolute(),
            args.priority_receipt.expanduser().absolute(),
            args.remaining18_dir.expanduser().absolute(),
            args.post_quality_dir.expanduser().absolute(),
        )
        if problems:
            print("R52_GRAPH_21_INPUT_PREFLIGHT_HOLD__" +
                  "__".join(sorted(problems)), file=sys.stderr)
            return 2
        edges, owners, safe = consolidate(
            args.source_zip.expanduser().absolute(),
            args.source_receipt.expanduser().absolute(),
            args.priority_decisions.expanduser().absolute(),
            args.priority_receipt.expanduser().absolute(),
            args.remaining18_dir.expanduser().absolute(),
            args.post_quality_dir.expanduser().absolute())
        entries = {
            "R52_PRIVATE_21_WORLD_GRAPH_EVIDENCE_EDGES.jsonl":
                "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
                        for x in edges),
            "R52_PRIVATE_07_WORLD_GRAPH_OWNER_SIGNOFF_QUEUE.jsonl":
                "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
                        for x in owners),
            "R52_ALL_21_WORLD_GRAPH_SAFE_AGGREGATE.json":
                json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        }
        demand(all(not (out / x).exists() and not (out / x).is_symlink()
                   for x in entries), "PRIVATE_OUTPUT_EXISTS")
        old = os.umask(0o077)
        try:
            for name, content in entries.items():
                exclusive_write(out / name, content)
        finally:
            os.umask(old)
    except (packaging.PackHold, OSError, KeyError, TypeError, ValueError,
            zipfile.BadZipFile, json.JSONDecodeError) as error:
        marker = str(error) if isinstance(error, packaging.PackHold) else type(error).__name__
        print("R52_GRAPH_21_CLOSURE_HOLD__" + marker, file=sys.stderr)
        return 2
    print(safe["status"])
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

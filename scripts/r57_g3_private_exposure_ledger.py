"""Owner-local R57 G3: tag all Gold195 by exact historical target exposure.

This is NOT an admission/sampling/reviewer decision. All 195 entries remain
HOLD. The detailed target digest + story UUID ledger is strictly PRIVATE.
Only immutable file SHA/Git blob pins, eight known source paths, and stdout
safe aggregate counts are used. Do not access R50 or start any training.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact

SCHEMA_PRIVATE = "storyforge-r57-g3-private-exact-target-exposure-ledger-v1"
SCHEMA_SAFE = "storyforge-r57-g3-exact-target-exposure-count-only-v1"
TRAIN_IDS = ("V01_TRAIN", "R46_TRAIN", "R54_TRAIN")
VALIDATION_IDS = ("V01_VALIDATION", "R46_VALIDATION", "R54_VALIDATION")
LEDGER_FILENAME = re.compile(r"^R57_G3_[A-Za-z0-9_-]{8,80}_PRIVATE\.json$")


class LedgerHold(ValueError):
    """A frozen source, overlap contract or storage boundary was not satisfied."""


def _world(record):
    metadata = record["metadata"]
    world = metadata.get("story_id") or metadata.get("source_story_id")
    if not isinstance(world, str) or not world:
        raise LedgerHold("original Gold story identifier missing")
    return world


def _v01_worlds(payload):
    worlds = set()
    for line in payload.splitlines():
        try:
            record = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise LedgerHold("v0.1 source malformed") from exc
        metadata = record.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("story_id"), str):
            raise LedgerHold("v0.1 historical story provenance absent")
        if not metadata["story_id"]:
            raise LedgerHold("v0.1 historical story identity empty")
        worlds.add(metadata["story_id"])
    return worlds


def prepare_ledger(payloads):
    """Accept already authenticated eight source bytes; return private + safe objects.

    The CLI rechecks every byte pin before invoking this function. Neither
    return object asserts signed alias-graph or training admission approval.
    """
    report = exact.replay_payloads(payloads, require_all=True)
    pair = next(
        x for x in report["exact_pairwise"]
        if {x["a"], x["b"]} == {"R46_TRAIN", "R54_TRAIN"}
    )
    if pair["role_content_full_exact"] != 5 or pair["role_content_history_exact"] != 5:
        raise LedgerHold("five exact R46/R54 full-message replay differs")
    rows = {name: exact._shape(payload, name)[0] for name, payload in payloads.items()}
    historical_sets = {
        name: {sample["target"] for sample in samples}
        for name, samples in rows.items()
    }
    train = set().union(*(historical_sets[x] for x in TRAIN_IDS))
    validation = set().union(*(historical_sets[x] for x in VALIDATION_IDS))
    v01_train_worlds = _v01_worlds(payloads["V01_TRAIN"])
    v01_validation_worlds = _v01_worlds(payloads["V01_VALIDATION"])
    records = []
    pool_counts = {}
    categories = (
        "TRAIN_ONLY", "VALIDATION_ONLY", "BOTH_TRAIN_AND_VALIDATION",
        "NO_EXACT_TARGET_IN_PRIOR_SFT",
    )
    for source in ("GOLD87", "GOLD108"):
        buckets = dict.fromkeys(categories, 0)
        same_uuid_train = 0
        same_uuid_validation = 0
        exact_matches = rows[source]
        for i, line in enumerate(payloads[source].splitlines()):
            item = json.loads(line)
            metadata = item.get("metadata")
            if not isinstance(metadata, dict) or metadata.get("training_admission") != "PENDING_NOT_APPROVED":
                raise LedgerHold("Gold case historical admission flag altered")
            target_sha256 = exact_matches[i]["target"]
            in_train = target_sha256 in train
            in_validation = target_sha256 in validation
            if in_train and in_validation:
                category = "BOTH_TRAIN_AND_VALIDATION"
            elif in_train:
                category = "TRAIN_ONLY"
            elif in_validation:
                category = "VALIDATION_ONLY"
            else:
                category = "NO_EXACT_TARGET_IN_PRIOR_SFT"
            origin_world_uuid = _world(item)
            old_train_uuid = origin_world_uuid in v01_train_worlds
            old_validation_uuid = origin_world_uuid in v01_validation_worlds
            same_uuid_train += old_train_uuid
            same_uuid_validation += old_validation_uuid
            buckets[category] += 1
            records.append({
                "gold_source": source,
                "source_row_ordinal_1_based": i + 1,
                "target_sha256_private": target_sha256,
                "source_story_uuid_private": origin_world_uuid,
                "historical_exact_target_class": category,
                "historical_exact_target_sources": [
                    name for name in (*TRAIN_IDS, *VALIDATION_IDS)
                    if target_sha256 in historical_sets[name]
                ],
                "same_uuid_as_v01_train": old_train_uuid,
                "same_uuid_as_v01_validation": old_validation_uuid,
                "world_alias_graph_verified": False,
                "case_level_rights_quality_safety_verified": False,
                "dataset_v04_decision": "HOLD_NOT_REVIEWED",
            })
        pool_counts[source] = {
            "rows": len(exact_matches),
            "categories": buckets,
            "same_uuid_as_v01_train_rows": same_uuid_train,
            "same_uuid_as_v01_validation_rows": same_uuid_validation,
        }
    overall = {category: sum(p["categories"][category] for p in pool_counts.values())
               for category in categories}
    if (
        overall != {
            "TRAIN_ONLY": 57,
            "VALIDATION_ONLY": 15,
            "BOTH_TRAIN_AND_VALIDATION": 9,
            "NO_EXACT_TARGET_IN_PRIOR_SFT": 114,
        }
        or pool_counts["GOLD87"]["categories"] != {
            "TRAIN_ONLY": 20, "VALIDATION_ONLY": 0,
            "BOTH_TRAIN_AND_VALIDATION": 0, "NO_EXACT_TARGET_IN_PRIOR_SFT": 67,
        }
        or pool_counts["GOLD108"]["categories"] != {
            "TRAIN_ONLY": 37, "VALIDATION_ONLY": 15,
            "BOTH_TRAIN_AND_VALIDATION": 9, "NO_EXACT_TARGET_IN_PRIOR_SFT": 47,
        }
    ):
        raise LedgerHold("frozen eight-source exposure counts differ from Owner evidence")
    if pool_counts["GOLD87"]["same_uuid_as_v01_train_rows"] != 21:
        raise LedgerHold("frozen Gold87/v0.1 shared story UUID count differs")
    if len(records) != 195:
        raise LedgerHold("Gold195 case rows missing")
    private = {
        "schema": SCHEMA_PRIVATE,
        "evidence_tier": "OWNER_LOCAL_FROZEN_BYTES__NOT_ALIAS_VERIFIED",
        "training_authorized": False,
        "source_content_protected_evaluation_accessed": False,
        "rows": records,
    }
    safe = {
        "schema": SCHEMA_SAFE,
        "status": "G3_EXACT_TARGET_MEMBERSHIP_REPLAY_PASS__ALL_195_REMAIN_HOLD",
        "gold195_rows": len(records),
        "by_gold_pool": pool_counts,
        "category_counts": overall,
        "historical_ever_train_exact": overall["TRAIN_ONLY"] + overall["BOTH_TRAIN_AND_VALIDATION"],
        "historical_ever_validation_exact": overall["VALIDATION_ONLY"] + overall["BOTH_TRAIN_AND_VALIDATION"],
        "no_exact_target_match": overall["NO_EXACT_TARGET_IN_PRIOR_SFT"],
        "source_byte_pins_verified_by_cli": False,
        "world_alias_graph_verified": False,
        "semantic_novelty_verified": False,
        "independent_rights_quality_safety_review_complete": False,
        "reviewer_admission_approved": False,
        "dataset_v04_admitted": 0,
        "r50_content_accessed": False,
        "training_authorized": False,
    }
    return private, safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--private-ledger-name", type=str)
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        private_dir = args.private_root.resolve(strict=True)
        if repo == private_dir or repo in private_dir.parents or private_dir in repo.parents:
            raise LedgerHold("private input/output must be outside the Git checkout")
        if args.private_ledger_name and not LEDGER_FILENAME.fullmatch(args.private_ledger_name):
            raise LedgerHold("private ledger name does not meet restrictive filename contract")
        payloads = {}
        for name in exact.SOURCE_IDS:
            loc, relative, _ = frozen.SOURCE_PATHS[name]
            root = repo if loc == "REPO" else private_dir
            raw = frozen._read(root, relative, frozen.MAX_SOURCE_BYTES)
            exact.verify_source_pin(name, raw)
            payloads[name] = raw
        private, safe = prepare_ledger(payloads)
        safe["source_byte_pins_verified_by_cli"] = True
        if args.private_ledger_name:
            # Never open a user-defined path or overwrite a prior local audit.
            out = frozen._guard_path(private_dir, args.private_ledger_name)
            if out.is_symlink() or out.exists():
                raise LedgerHold("private ledger already exists")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(out, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as sink:
                json.dump(private, sink, ensure_ascii=False, sort_keys=True, indent=2)
                sink.write("\n")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        error = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G3_EXACT_LEDGER_HOLD: {type(exc).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

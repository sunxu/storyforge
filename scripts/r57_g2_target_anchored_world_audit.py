"""R57 G2: recover historical SFT story UUIDs by exact Gold195 target SHA.

The compiled R46/R54 Trainer rows have no provenance metadata. Since every
historical compiled target is present exactly once in the frozen Gold195,
a uniquely matched final-Assistant SHA can recover an observed story UUID
without guesses from narrative text. This is NOT a semantic alias graph,
signed world isolation, heldout clearance or Dataset v0.4 admission.
No network, R50, model, GPU, or private output is used.
"""

import argparse
import itertools
import json
import sys
from pathlib import Path

import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact

SCHEMA = "storyforge-r57-g2-target-anchored-world-uuid-count-only-v1"
NAMES = tuple(exact.SOURCE_IDS)
TRAIN = ("V01_TRAIN", "R46_TRAIN", "R54_TRAIN")
VALIDATION = ("V01_VALIDATION", "R46_VALIDATION", "R54_VALIDATION")
GOLD = ("GOLD87", "GOLD108")
R46_R54 = ("R46_TRAIN", "R46_VALIDATION", "R54_TRAIN", "R54_VALIDATION")
TARGET_CATEGORIES = (
    "TRAIN_ONLY", "VALIDATION_ONLY",
    "BOTH_TRAIN_AND_VALIDATION", "NO_EXACT_TARGET_IN_PRIOR_SFT",
)


class WorldJoinHold(ValueError):
    """A target cannot be uniquely and faithfully linked to frozen provenance."""


def _source_world(record, name):
    if not isinstance(record, dict) or not isinstance(record.get("metadata"), dict):
        raise WorldJoinHold("historical source world metadata missing")
    metadata = record["metadata"]
    primary = metadata.get("story_id")
    secondary = metadata.get("source_story_id")
    if name == "GOLD108":
        if (bool(primary) == bool(secondary)):
            raise WorldJoinHold("ambiguous Gold108 world provenance")
        world = primary or secondary
    else:
        world = primary
        if secondary:
            raise WorldJoinHold("unexpected mixed world metadata")
    if not isinstance(world, str) or not world:
        raise WorldJoinHold("empty world source identifier")
    return world


def _records(raw):
    return [json.loads(line) for line in raw.splitlines()]


def audit(payloads):
    """Compare eight already authenticated source payloads; emit SAFE counts only."""
    if set(payloads) != set(NAMES):
        raise WorldJoinHold("all eight authentic source collections required")
    raw_report = exact.replay_payloads(payloads, require_all=True)
    pairs = raw_report["exact_pairwise"]
    r46_r54_pair = next(row for row in pairs
                        if {row["a"], row["b"]} == {"R46_TRAIN", "R54_TRAIN"})
    if (r46_r54_pair["role_content_full_exact"],
            r46_r54_pair["role_content_history_exact"]) != (5, 5):
        raise WorldJoinHold("five exact R46/R54 message/history matches not replayed")
    hashed = {name: exact._shape(payloads[name], name)[0] for name in NAMES}
    gold_lookup = {}
    for name in GOLD:
        original_rows = _records(payloads[name])
        for record, sample in zip(original_rows, hashed[name], strict=True):
            sha = sample["target"]
            if sha in gold_lookup:
                raise WorldJoinHold("Gold target fingerprint is not unique")
            gold_lookup[sha] = _source_world(record, name)
    if len(gold_lookup) != 195:
        raise WorldJoinHold("Gold195 unique target lookup incomplete")
    historical_world_rows = {}
    mapped_counts = {}
    for name in NAMES:
        if name in R46_R54:
            missing = sum(sample["target"] not in gold_lookup for sample in hashed[name])
            if missing:
                raise WorldJoinHold("compiled Trainer has targets absent from Gold195")
            worlds = [gold_lookup[sample["target"]] for sample in hashed[name]]
            mapped_counts[name] = len(worlds)
        elif name in GOLD or name.startswith("V01_"):
            worlds = [
                _source_world(record, name) for record in _records(payloads[name])
            ]
            mapped_counts[name] = 0  # direct metadata, not target-based recovery
        else:
            raise WorldJoinHold("unrecognized source collection")
        if len(worlds) != len(hashed[name]):
            raise WorldJoinHold("historical source-to-world row alignment failed")
        historical_world_rows[name] = worlds
    if {name: mapped_counts[name] for name in R46_R54} != {
        "R46_TRAIN": 49, "R46_VALIDATION": 15,
        "R54_TRAIN": 31, "R54_VALIDATION": 9,
    }:
        raise WorldJoinHold("not all compiled target hashes have a unique Gold link")
    world_sets = {name: set(worlds) for name, worlds in historical_world_rows.items()}
    pairwise = []
    for a, b in itertools.combinations(NAMES, 2):
        shared = world_sets[a] & world_sets[b]
        pairwise.append({
            "a": a,
            "b": b,
            "shared_exact_story_uuids": len(shared),
            "a_rows_with_shared_story_uuid": sum(w in shared for w in historical_world_rows[a]),
            "b_rows_with_shared_story_uuid": sum(w in shared for w in historical_world_rows[b]),
        })
    train_uuids = set().union(*(world_sets[x] for x in TRAIN))
    validation_uuids = set().union(*(world_sets[x] for x in VALIDATION))
    train_hashes = set().union(*({s["target"] for s in hashed[x]} for x in TRAIN))
    validation_hashes = set().union(*({s["target"] for s in hashed[x]} for x in VALIDATION))
    pool_counts = {}
    for name in GOLD:
        tab = {cat: {
            "rows": 0,
            "also_historical_train_world_uuid": 0,
            "also_historical_validation_world_uuid": 0,
            "also_any_historical_world_uuid": 0,
        } for cat in TARGET_CATEGORIES}
        for sample, uuid in zip(hashed[name], historical_world_rows[name], strict=True):
            train_seen = sample["target"] in train_hashes
            val_seen = sample["target"] in validation_hashes
            category = (
                "BOTH_TRAIN_AND_VALIDATION" if train_seen and val_seen else
                "TRAIN_ONLY" if train_seen else
                "VALIDATION_ONLY" if val_seen else
                "NO_EXACT_TARGET_IN_PRIOR_SFT"
            )
            row = tab[category]
            row["rows"] += 1
            row["also_historical_train_world_uuid"] += uuid in train_uuids
            row["also_historical_validation_world_uuid"] += uuid in validation_uuids
            row["also_any_historical_world_uuid"] += uuid in (train_uuids | validation_uuids)
        pool_counts[name] = tab
    totals = {category: sum(pool_counts[name][category]["rows"] for name in GOLD)
              for category in TARGET_CATEGORIES}
    if totals != {
        "TRAIN_ONLY": 57,
        "VALIDATION_ONLY": 15,
        "BOTH_TRAIN_AND_VALIDATION": 9,
        "NO_EXACT_TARGET_IN_PRIOR_SFT": 114,
    }:
        raise WorldJoinHold("case-level exposure differs from frozen 57/15/9/114")
    within_sft_world = {}
    for prefix in ("V01", "R46", "R54"):
        a, b = prefix + "_TRAIN", prefix + "_VALIDATION"
        shared = world_sets[a] & world_sets[b]
        within_sft_world[prefix] = {
            "train_validation_shared_story_uuid_count": len(shared),
            "train_rows_with_shared_uuid": sum(w in shared for w in historical_world_rows[a]),
            "validation_rows_with_shared_uuid": sum(w in shared for w in historical_world_rows[b]),
        }
    return {
        "schema": SCHEMA,
        "status": "EIGHT_SOURCE_TARGET_ANCHORED_STORY_UUID_REPLAY_PASS__SEMANTIC_ALIAS_HOLD",
        "source_row_counts": {name: len(hashed[name]) for name in NAMES},
        "source_unique_story_uuid_counts": {name: len(world_sets[name]) for name in NAMES},
        "compiled_trainer_rows_uniquely_mapped_to_gold195": {
            name: mapped_counts[name] for name in R46_R54
        },
        "pairwise_exact_uuid_overlap": pairwise,
        "within_run_train_val_uuid_overlap": within_sft_world,
        "gold_target_exposure_cross_uuid_counts": pool_counts,
        "gold_target_exposure_totals": totals,
        "source_byte_pins_verified_by_cli": False,
        "world_uuid_observed_from_gold_provenance": True,
        "cross_uuid_story_alias_components_verified": False,
        "semantic_near_duplicate_verified": False,
        "ms_swift_template_and_mask_verified": False,
        "world_isolation_certified": False,
        "independent_case_admission_review_completed": False,
        "dataset_v04_admitted": 0,
        "r50_content_accessed": False,
        "training_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        private = args.private_root.resolve(strict=True)
        if repo == private or repo in private.parents or private in repo.parents:
            raise WorldJoinHold("private Trainer area cannot be within the Git checkout")
        payloads = {}
        for name in NAMES:
            tag, relative, _ = frozen.SOURCE_PATHS[name]
            root = repo if tag == "REPO" else private
            raw = frozen._read(root, relative, frozen.MAX_SOURCE_BYTES)
            exact.verify_source_pin(name, raw)
            payloads[name] = raw
        result = audit(payloads)
        result["source_byte_pins_verified_by_cli"] = True
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        # Do not expose caller paths, original hashes, or narrative in errors.
        detail = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print("R57_G2_UUID_JOIN_HOLD: " + type(exc).__name__ + ": " + detail, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

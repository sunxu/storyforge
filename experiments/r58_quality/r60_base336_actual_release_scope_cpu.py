"""Owner-local read-only audit: source-reuse pairs vs actual 293/43 release.

Requires Owner-private frozen six dirs, roster, 22-case provisional scope and
immutable exploratory release. Never writes datasets or calls DB/models/GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import r60_base336_exploratory_release_verify as release_verify
import r60_base336_exploratory_split as split
import r60_base336_story_json_shape_cpu as frozen
import r60_base336_world_cross_split_private_roster_cpu as roster
import r60_base_start_cpu336_template_audit as audit
import r60_real_private_batch as private

SCHEMA = "r60_base336_actual_release_scope_safe_v1"


class Hold(ValueError):
    pass


def row_hash(row: dict) -> str:
    return hashlib.sha256(split._encode([row]).rstrip(b"\n")).hexdigest()


def classify_positions(held: list[dict], rows: list[dict], data: dict[str, bytes]) -> dict[int, str]:
    """Map unique frozen source positions to release split by exact row bytes.

    Reject a duplicated exact row appearing in both release splits: row-only
    serialization cannot prove a unique provenance assignment in that case.
    """
    if len(held) != 336 or len(rows) != 336:
        raise Hold("FROZEN_POSITION_COUNT_HOLD")
    expected = Counter(row_hash(row) for row in rows)
    observed = {side: Counter(row_hash(json.loads(line)) for line in data[side].splitlines())
                for side in ("train", "validation")}
    if observed["train"] + observed["validation"] != expected:
        raise Hold("RELEASE_ROW_MAPPING_HOLD")
    ambiguous = set(observed["train"]) & set(observed["validation"])
    if ambiguous:
        raise Hold("CROSS_SPLIT_IDENTICAL_ROW_PROVENANCE_HOLD")
    result = {}
    for entry, row in zip(held, rows, strict=True):
        key = row_hash(row)
        side = "train" if key in observed["train"] else "validation"
        position = entry["position"]
        if type(position) is not int or position in result:
            raise Hold("DUPLICATE_FROZEN_POSITION_HOLD")
        result[position] = side
    if Counter(result.values()) != Counter({"train": 293, "validation": 43}):
        raise Hold("ROW_ASSIGNMENT_COUNT_HOLD")
    return result


def run(args: argparse.Namespace) -> dict:
    release_dir = args.release_dir
    scope_path = args.scope_file
    roster_dir = args.roster_dir
    if release_dir.is_symlink() or scope_path.is_symlink() or roster_dir.is_symlink():
        raise Hold("SYMLINK_INPUT_HOLD")
    if release_dir.parent != private.BASE:
        # The existing release verifier requires a direct Owner-private child.
        # Nested stage copies are verified separately by GPU stage contracts.
        raise Hold("RELEASE_PATH_HOLD")

    verified = release_verify.verify(release_dir)
    if verified["status"] != "BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD":
        raise Hold("RELEASE_VERIFY_HOLD")

    cases, manifest = frozen._frozen(args)
    roster_raw = private.read_private(roster_dir / roster.FILENAME, 300000)
    roster_doc = json.loads(roster_raw)
    generated, stats = split.split(cases, manifest, roster_doc)
    if stats["rows"] != {"train": 293, "validation": 43} or stats["crossing_known_world_groups_after_split"] != 0:
        raise Hold("SPLIT_STATS_HOLD")
    release_manifest = json.loads(private.read_private(
        release_dir / release_verify.MANIFEST, 200000))
    if release_manifest.get("roster_sha256") != hashlib.sha256(roster_raw).hexdigest():
        raise Hold("RELEASE_ROSTER_BINDING_HOLD")
    if release_manifest.get("statistics") != stats:
        raise Hold("RELEASE_SPLIT_STATS_BINDING_HOLD")
    for side in ("train", "validation"):
        stored = private.read_private(release_dir / f"{side}.jsonl", split.MAX_DATA_FILE)
        if stored != generated[side]:
            raise Hold("RECONSTRUCTED_RELEASE_BYTES_HOLD")

    held = manifest["remaining_full_r50_hold"]
    rows = audit.prepare(cases, manifest)
    position_splits = classify_positions(held, rows, generated)
    story_side = defaultdict(set)
    for item in held:
        p = item["position"]
        story_side[cases[p - 1]["source"]["story_id"]].add(position_splits[p])
    if any(len(sides) != 1 for sides in story_side.values()):
        raise Hold("STORY_SPLIT_INTEGRITY_HOLD")

    scope = json.loads(private.read_private(scope_path, 300000))
    if (scope.get("schema") != "r60_base336_source_reuse_minimal_provisional_hold_scope_private_v1"
            or scope.get("unique_frozen_candidate_positions") != 22
            or scope.get("distinct_story_count") != 11
            or len(scope.get("exact_source_reuse_pairs_PRIVATE", [])) != 6):
        raise Hold("SOURCE_SCOPE_SCHEMA_HOLD")
    if scope.get("source_pins_PRIVATE", {}).get("roster_sha256_PRIVATE") != hashlib.sha256(roster_raw).hexdigest():
        raise Hold("SCOPE_ROSTER_BINDING_HOLD")

    scoped_positions = scope["frozen_candidate_positions_1based_PRIVATE"]
    if (len(scoped_positions) != 22 or len(set(scoped_positions)) != 22
            or not set(scoped_positions).issubset(position_splits)):
        raise Hold("SCOPE_POSITION_BINDING_HOLD")
    actual_counts = Counter(position_splits[pos] for pos in scoped_positions)
    resolved_pairs, still_crossing = 0, 0
    for pair in scope["exact_source_reuse_pairs_PRIVATE"]:
        a, b = pair["train_story_id_PRIVATE"], pair["validation_story_id_PRIVATE"]
        if a == b or a not in story_side or b not in story_side:
            raise Hold("SOURCE_PAIR_STORY_HOLD")
        expected_a = set(pair["train_candidate_positions_1based_PRIVATE"])
        expected_b = set(pair["validation_candidate_positions_1based_PRIVATE"])
        actual_a = {x["position"] for x in held if cases[x["position"] - 1]["source"]["story_id"] == a}
        actual_b = {x["position"] for x in held if cases[x["position"] - 1]["source"]["story_id"] == b}
        if expected_a != actual_a or expected_b != actual_b:
            raise Hold("SOURCE_PAIR_POSITION_BINDING_HOLD")
        resolved_pairs += 1
        still_crossing += next(iter(story_side[a])) != next(iter(story_side[b]))

    return {
        "schema": SCHEMA,
        "status": "FINAL_293_43_RELEASE_SCOPE_REPLAY_PASS__SEMANTIC_HOLD",
        "release_rows_verified": 336,
        "release_sha256_verified": True,
        "reconstructed_release_bytes_equal": True,
        "release_roster_and_stats_bound": True,
        "final_train_rows": 293,
        "final_validation_rows": 43,
        "source_reuse_pairs_checked": resolved_pairs,
        "source_reuse_pairs_crossing_final_splits": still_crossing,
        "source_reuse_pairs_colocated_final_split": resolved_pairs-still_crossing,
        "provisional_22_case_final_train_count": actual_counts["train"],
        "provisional_22_case_final_validation_count": actual_counts["validation"],
        "actual_training_release_input_proven": False,
        "historical_request_effective_source_proven": False,
        "reviewer_independence_verified": False,
        "world_semantic_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "database_accessed": False,
        "database_modified": False,
        "model_requests": 0,
        "gpu_started": False,
        "private_files_modified": False,
        "private_values_emitted": False,
        "train_admitted": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for key in ("old", "plan", "v2", "v3", "audit", "quarantine", "roster", "release"):
        parser.add_argument(f"--{key}-dir", type=Path, required=True)
    parser.add_argument("--scope-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception:  # noqa: BLE001 - fail closed without exposing private values
        result = {
            "schema": SCHEMA,
            "status": "FINAL_RELEASE_SCOPE_REPLAY_HOLD",
            "safe_failure_phase": "SOURCE_OR_RELEASE_BINDING",
            "database_accessed": False,
            "database_modified": False,
            "model_requests": 0,
            "gpu_started": False,
            "private_files_modified": False,
            "private_values_emitted": False,
            "train_admitted": 0,
        }
        print(json.dumps(result, sort_keys=True))
        return 42
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

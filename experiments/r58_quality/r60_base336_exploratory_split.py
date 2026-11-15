"""R60 336-only exploratory split publisher. No GPU, no training admission.

Rebuilds all 339 frozen V123 candidates, verifies the existing 3/336
quarantine, and groups all known cross-split equal world JSON roster edges.
Exact world equality is conservatively grouped for split safety; semantic
identity and R50 protected-world isolation remain unverified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import r60_base_start_cpu336_template_audit as audit
import r60_base_start_world_split_preview as preview
import r60_base336_world_cross_split_private_roster_cpu as roster
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_exploratory_split_private_v1"
SAFE = "storyforge_r60_base336_exploratory_split_safe_v1"
ROSTER = roster.FILENAME
MAX_ROSTER = 300_000


class Hold(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _encode(rows: list[dict]) -> bytes:
    return b"".join(
        (json.dumps(r, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")) + "\n").encode()
        for r in rows
    )


def split(cases: list[dict], frozen: dict, roster_doc: dict) -> tuple[dict, dict]:
    check = preview.preview(cases, frozen)
    if (check["held_candidate_cases"] != 336
            or check["held_candidate_worlds"] != 172
            or check["provisional_train_cases"] != 276
            or check["provisional_validation_cases"] != 60):
        raise Hold("FROZEN_336_SCOPE_HOLD")
    if (type(roster_doc) is not dict
            or roster_doc.get("schema") != roster.SCHEMA
            or roster_doc.get("semantic_review_completed") is not False
            or roster_doc.get("train_admitted") != 0
            or roster_doc.get("scope") !=
            "FROZEN_336_CASES_172_STORIES__8_CROSSING_WORLD_JSON_VALUES"):
        raise Hold("WORLD_ROSTER_SCHEMA_HOLD")
    groups = roster_doc.get("groups_PRIVATE")
    if type(groups) is not list or len(groups) != 8:
        raise Hold("WORLD_ROSTER_COUNT_HOLD")
    held = frozen["remaining_full_r50_hold"]
    excluded = {x["position"] for x in frozen["excluded_known5"]}
    if len(held) != 336 or len(excluded) != 3:
        raise Hold("KNOWN5_SCOPE_HOLD")
    story_positions: dict[str, set[int]] = defaultdict(set)
    for x in held:
        pos = x["position"]
        story_positions[cases[pos - 1]["source"]["story_id"]].add(pos)
    parent = {story: story for story in story_positions}

    def root(story: str) -> str:
        while parent[story] != story:
            parent[story] = parent[parent[story]]
            story = parent[story]
        return story

    def union(a: str, b: str) -> None:
        ra, rb = root(a), root(b)
        parent[max(ra, rb)] = min(ra, rb)

    seen_groups = set()
    union_stories = set()
    for group in groups:
        if type(group) is not dict:
            raise Hold("WORLD_GROUP_SHAPE_HOLD")
        no = group.get("group_ordinal")
        if type(no) is not int or not 1 <= no <= 8 or no in seen_groups:
            raise Hold("WORLD_GROUP_INDEX_HOLD")
        seen_groups.add(no)
        members = group.get("members_PRIVATE")
        if type(members) is not list or len(members) < 2:
            raise Hold("WORLD_GROUP_MEMBERS_HOLD")
        group_stories = []
        for member in members:
            story = member.get("story_id_PRIVATE")
            positions = member.get("candidate_positions_1based_PRIVATE")
            if (story not in story_positions
                    or type(positions) is not list
                    or positions != sorted(story_positions[story])
                    or member.get("split") not in ("train", "validation")
                    or member["split"] != (
                        "validation" if int.from_bytes(
                            hashlib.sha256(preview.SALT + story.encode()).digest()[:8],
                            "big") % 100 < preview.VAL_PERCENT else "train"
                    )):
                raise Hold("WORLD_ROSTER_SOURCE_BINDING_HOLD")
            group_stories.append(story)
        if len(group_stories) != len(set(group_stories)):
            raise Hold("WORLD_GROUP_DUPLICATE_HOLD")
        union_stories.update(group_stories)
        for story in group_stories[1:]:
            union(group_stories[0], story)
    if seen_groups != set(range(1, 9)) or len(union_stories) != 38:
        raise Hold("WORLD_ROSTER_COVERAGE_HOLD")
    if sum(len(story_positions[s]) for s in union_stories) != 82:
        raise Hold("WORLD_ROSTER_82_HOLD")

    components: dict[str, set[str]] = defaultdict(set)
    for story in parent:
        components[root(story)].add(story)
    assignments = {}
    forced_train = 0
    for members in components.values():
        initial = {
            "validation" if int.from_bytes(
                hashlib.sha256(preview.SALT + s.encode()).digest()[:8],
                "big") % 100 < preview.VAL_PERCENT else "train"
            for s in members
        }
        # Any connected component containing Train must be kept together.
        # All singleton stories preserve the already-frozen preview slot.
        side = "train" if "train" in initial else "validation"
        forced_train += len(members) > 1 and len(initial) > 1
        for story in members:
            assignments[story] = side
    if len(assignments) != 172:
        raise Hold("SPLIT_WORLD_COUNT_HOLD")
    for group in groups:
        members = group["members_PRIVATE"]
        if len({assignments[m["story_id_PRIVATE"]] for m in members}) != 1:
            raise Hold("KNOWN_WORLD_SPLIT_CROSSING_HOLD")
    rows = audit.prepare(cases, frozen)
    grouped: dict[str, list[dict]] = {"train": [], "validation": []}
    split_positions: dict[str, list[int]] = {"train": [], "validation": []}
    for item, row in zip(held, rows, strict=True):
        pos = item["position"]
        if pos in excluded:
            raise Hold("KNOWN5_LEAK_HOLD")
        side = assignments[cases[pos - 1]["source"]["story_id"]]
        grouped[side].append(row)
        split_positions[side].append(pos)
    if (sum(map(len, grouped.values())) != 336
            or not grouped["train"] or not grouped["validation"]
            or set(split_positions["train"]) & set(split_positions["validation"])):
        raise Hold("FINAL_SPLIT_ACCOUNTING_HOLD")
    return {
        "train": _encode(grouped["train"]),
        "validation": _encode(grouped["validation"]),
    }, {
        "rows": {k: len(v) for k, v in grouped.items()},
        "stories": dict(Counter(assignments.values())),
        "known_world_group_count": 8,
        "known_world_affected_stories": len(union_stories),
        "known_world_affected_cases": 82,
        "crossing_known_world_groups_after_split": 0,
        "connected_components": len(components),
        "merged_cross_split_components": forced_train,
        "excluded_known5": 3,
        "semantic_world_isolation_verified": False,
        "r50_semantic_isolation_verified": False,
        "reviewer_execution_independence_verified": False,
        "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
    }


def execute(args: argparse.Namespace) -> dict:
    if (args.output_dir.parent != private.BASE
            or not args.output_dir.name.startswith("r60-base336-exploratory-")
            or args.output_dir.exists() or args.output_dir.is_symlink()):
        raise Hold("CREATE_ONLY_OUTPUT_HOLD")
    private.private_dir(args.roster_dir, create=False)
    cases, report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir,
        args.audit_dir)
    crosswalk = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(cases, report, _sha(crosswalk))
    actual = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if actual != expected:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    roster_raw = private.read_private(args.roster_dir / ROSTER, MAX_ROSTER)
    payload, stats = split(cases, actual, json.loads(roster_raw))
    manifest = {
        "schema": SCHEMA,
        "status": "EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED",
        "case_pool": 336,
        "data_sha256": {name: _sha(raw) for name, raw in payload.items()},
        "roster_sha256": _sha(roster_raw),
        "crosswalk_sha256": _sha(crosswalk),
        "statistics": stats,
        "train_admitted": 0,
        "gpu_started": False,
    }
    if args.write:
        private.private_dir(args.output_dir, create=True)
        for name in ("train", "validation"):
            private.write_new(args.output_dir / f"{name}.jsonl", payload[name])
        private.write_new(
            args.output_dir / "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json",
            _encode([manifest]),
        )
    return {
        "schema": SAFE,
        "status": ("BASE336_EXPLORATORY_SPLIT_CREATED__GPU_HOLD"
                   if args.write else
                   "BASE336_EXPLORATORY_SPLIT_PREFLIGHT__NO_WRITE"),
        "candidate_rows": 336,
        "train_rows": stats["rows"]["train"],
        "validation_rows": stats["rows"]["validation"],
        "train_stories": stats["stories"].get("train", 0),
        "validation_stories": stats["stories"].get("validation", 0),
        "known_world_cross_split_groups": 0,
        "r50_semantic_isolation_verified": False,
        "reviewer_independence_verified": False,
        "actual_final_collator_verified": False,
        "gpu_stage_prepared": False,
        "train_admitted": 0,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit",
                 "quarantine", "roster", "output"):
        parser.add_argument(f"--{name}-dir", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private content or path disclosure
        print(json.dumps({
            "schema": SAFE, "status": "BASE336_EXPLORATORY_SPLIT_HOLD",
            "train_admitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

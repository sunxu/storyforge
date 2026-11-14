"""Offline evidence-only cross-story linkage screen for R60 Base 336 held cases.

Links frozen story IDs through exact target/history hashes or reused source
session/message IDs. These are high-confidence structural signals only, not a
semantic alias/world classification. No train/val admission or exports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import r60_base_start_world_split_preview as split
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_world_linkage_screen_safe_v1"


class Hold(ValueError):
    pass


def screen(cases: list[dict], manifest: dict) -> dict:
    base = split.preview(cases, manifest)
    if base["held_candidate_cases"] != 336 or base["held_candidate_worlds"] != 172:
        raise Hold("SOURCE_SCOPE_HOLD")
    positions = [item["position"] for item in manifest["remaining_full_r50_hold"]]
    parent = {}

    def root(world: str) -> str:
        if world not in parent:
            parent[world] = world
        while parent[world] != world:
            parent[world] = parent[parent[world]]
            world = parent[world]
        return world

    def union(a: str, b: str) -> bool:
        a, b = root(a), root(b)
        if a == b:
            return False
        parent[max(a, b)] = min(a, b)
        return True

    keys: dict[str, dict[str, set[str]]] = {
        kind: defaultdict(set) for kind in (
            "target_exact_sha", "history_exact_sha", "source_session",
            "source_message",
        )
    }
    for pos in positions:
        case = cases[pos - 1]
        src = case.get("source")
        if type(src) is not dict:
            raise Hold("SOURCE_FIELDS_HOLD")
        world = src.get("story_id")
        if type(world) is not str or not world:
            raise Hold("STORY_ID_HOLD")
        root(world)
        for kind, value in (
            ("target_exact_sha", case.get("assistant_target_sha256")),
            ("history_exact_sha", case.get("history_messages_sha256")),
            ("source_session", src.get("session_id")),
        ):
            if type(value) is not str or not value:
                raise Hold("LINK_KEY_HOLD")
            keys[kind][value].add(world)
        for name in ("assistant_message_id", "prior_user_message_id",
                     "previous_assistant_message_id", "previous_user_message_id"):
            value = src.get(name)
            if type(value) is not str or not value:
                raise Hold("SOURCE_MESSAGE_HOLD")
            keys["source_message"][value].add(world)
    if len(parent) != 172:
        raise Hold("WORLD_COUNT_HOLD")
    edge_counts = {}
    linked_pairs = set()
    for kind, mapping in keys.items():
        edges = set()
        for owners in mapping.values():
            ordered = sorted(owners)
            if len(ordered) > 1:
                for i, a in enumerate(ordered):
                    for b in ordered[i + 1:]:
                        edges.add((a, b))
                        linked_pairs.add((a, b))
        edge_counts[kind] = len(edges)
    for a, b in sorted(linked_pairs):
        union(a, b)
    components = defaultdict(set)
    for world in parent:
        components[root(world)].add(world)
    slots = {}
    for world in parent:
        value = int.from_bytes(
            hashlib.sha256(split.SALT + world.encode()).digest()[:8], "big") % 100
        slots[world] = "validation" if value < split.VAL_PERCENT else "train"
    crossing = sum(
        {"train", "validation"}.issubset({slots[w] for w in members})
        for members in components.values()
    )
    return {
        "schema": SCHEMA,
        "status": "BASE336_EXACT_WORLD_LINK_SCREEN_PASS__SEMANTIC_HOLD",
        "cases_checked": 336,
        "distinct_story_ids": 172,
        "exact_linked_story_pairs": len(linked_pairs),
        "edge_counts": edge_counts,
        "structural_components": len(components),
        "multi_story_components": sum(len(v) > 1 for v in components.values()),
        "cross_train_validation_components": crossing,
        "source_story_id_split_disjoint": True,
        "structural_linked_split_disjoint": crossing == 0,
        "semantic_alias_completeness_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "model_requests": 0, "hf_jobs_submitted": 0,
        "gpu_started": False, "database_modified": False,
        "private_values_emitted": False,
    }


def run(args: argparse.Namespace) -> dict:
    cases, report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(cases, report, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if saved != expected:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    return screen(cases, saved)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        ap.add_argument(f"--{name}-dir", required=True, type=Path)
    args = ap.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - fixed code; no source IDs or private text
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_WORLD_LINKAGE_HOLD",
            "train_admitted": 0, "model_requests": 0,
            "hf_jobs_submitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

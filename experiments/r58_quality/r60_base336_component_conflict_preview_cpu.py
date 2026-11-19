"""Owner-only, read-only counterfactual isolation graph for Base336 P2-C.

Private IDs never reach stdout. Candidate edges are NOT reviewer-certified facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import defaultdict
from pathlib import Path

from r60_independent_reviewer_offline import load_evidence, packet_and_pin

from storyforge_dataset.world_isolation import component_split_conflicts

SAFE_SCHEMA = "storyforge_r60_base336_component_conflict_preview_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_base336_component_conflict_preview_private_v1"


class Hold(Exception):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)


def read_file(path: Path, limit: int = 100_000) -> bytes:
    require(path.is_file() and not path.is_symlink(), "SOURCE_FILE_HOLD")
    require(0 < path.stat().st_size <= limit, "SOURCE_SIZE_HOLD")
    data = path.read_bytes()
    require(len(data) <= limit, "SOURCE_SIZE_HOLD")
    return data


def load_roster(path: Path, packet: dict) -> tuple[dict[str, dict], dict[str, set[int]]]:
    data = read_file(path, 5_242_880)
    require(hashlib.sha256(data).hexdigest() == packet["roster_sha256_PRIVATE"], "ROSTER_PIN_HOLD")
    roster = json.loads(data)
    groups = roster["groups_PRIVATE"]
    require(len(groups) == 8, "ROSTER_GROUP_COUNT_HOLD")
    stories: dict[str, dict] = {}
    positions: dict[str, set[int]] = defaultdict(set)
    for ordinal, group in enumerate(groups, 1):
        require(group["group_ordinal"] == ordinal, "ROSTER_ORDER_HOLD")
        for member in group["members_PRIVATE"]:
            sid = member["story_id_PRIVATE"]
            split = member["split"]
            require(split in ("train", "validation"), "ROSTER_SPLIT_HOLD")
            if sid in stories:
                require(stories[sid]["split"] == split, "ROSTER_SPLIT_DRIFT_HOLD")
            else:
                stories[sid] = {"split": split}
            positions[sid].update(member["candidate_positions_1based_PRIVATE"])
    require(len(stories) == 38, "ROSTER_STORY_COUNT_HOLD")
    require(len(set().union(*positions.values())) == 82, "ROSTER_CASE_COUNT_HOLD")
    require(sum(x["split"] == "train" for x in stories.values()) == 28, "ROSTER_TRAIN_COUNT_HOLD")
    require(sum(x["split"] == "validation" for x in stories.values()) == 10, "ROSTER_VALIDATION_COUNT_HOLD")
    return stories, positions


def check_b_safe(path: Path | None) -> bool:
    if path is None:
        return False
    value = json.loads(read_file(path))
    require(value.get("schema") == "storyforge_r60_base336_independent_review_safe_v1", "B_SAFE_SCHEMA_HOLD")
    require(value.get("status") == "REVIEW_FORMS_COMPLETE__OWNER_INDEPENDENCE_CHECK_PENDING", "B_SAFE_STATUS_HOLD")
    require(value.get("review_edges_expected") == 10 and value.get("review_edges_filled") == 10, "B_SAFE_COVERAGE_HOLD")
    counts = value.get("decision_counts", {})
    require(counts.get("SAME_SEMANTIC_COMPONENT") == 10 and all(counts.get(k) == 0 for k in ("INDEPENDENT_TEMPLATE_ONLY", "INSUFFICIENT_EVIDENCE", "PENDING")), "B_SAFE_DECISIONS_HOLD")
    require(value.get("reference_binding_verified_for_filled") == 10, "B_SAFE_REFERENCES_HOLD")
    require(value.get("source_versions_reviewed_count") == 10, "B_SAFE_SOURCE_VERSIONS_HOLD")
    require(value.get("reviewer_independence_independently_verified") is False, "B_SAFE_INDEPENDENCE_HOLD")
    require(value.get("source_version_actual_sent_verified") is False, "B_SAFE_ACTUAL_SENT_HOLD")
    require(value.get("p2_c") == "HOLD" and value.get("train_admitted") == 0, "B_SAFE_GATE_HOLD")
    return True


def build(packet: dict, stories: dict[str, dict], positions: dict[str, set[int]], b_safe_present: bool) -> tuple[dict, dict]:
    parent = {sid: sid for sid in stories}

    def find(sid: str) -> str:
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid

    crossing = []
    for edge in packet["edges_PRIVATE"]:
        a, b = edge["source_a_PRIVATE"], edge["source_b_PRIVATE"]
        require(a in stories and b in stories and a != b, "EDGE_STORY_HOLD")
        require(stories[a]["split"] == edge["split_a"] and stories[b]["split"] == edge["split_b"], "EDGE_SPLIT_HOLD")
        if edge["cross_split"]:
            require(stories[a]["split"] != stories[b]["split"], "EDGE_CROSS_SPLIT_HOLD")
            crossing.append(edge)
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_a] = root_b
        else:
            require(stories[a]["split"] == stories[b]["split"], "EDGE_SAME_SPLIT_HOLD")
    require(len(crossing) == 10, "CROSS_EDGE_COUNT_HOLD")

    components: dict[str, set[str]] = defaultdict(set)
    for sid in stories:
        components[find(sid)].add(sid)
    cross_components = [group for group in components.values() if len({stories[x]["split"] for x in group}) > 1]
    cross_components.sort(key=lambda group: (len(group), sorted(group)))
    assignments = [
        {"world_component_id": find(sid), "split": meta["split"]}
        for sid, meta in stories.items()
    ]
    # Use the existing shared helper; this is NOT an independently reviewed assignment.
    conflicts = component_split_conflicts(assignments)
    require(len(conflicts) == len(cross_components) == 6, "COMPONENT_CONFLICT_COUNT_HOLD")
    affected_stories = set().union(*cross_components)
    affected_cases = set().union(*(positions[s] for s in affected_stories))
    require(len(affected_stories) == 16 and len(affected_cases) == 35, "AFFECTED_SCOPE_DRIFT_HOLD")
    component_rows = []
    for ordinal, group in enumerate(cross_components, 1):
        cases = sorted(set().union(*(positions[s] for s in group)))
        component_rows.append({
            "candidate_component_ordinal": ordinal,
            "story_members_PRIVATE": [
                {"story_id_PRIVATE": sid, "split": stories[sid]["split"], "candidate_positions_1based_PRIVATE": sorted(positions[sid])}
                for sid in sorted(group)
            ],
            "candidate_cases_1based_PRIVATE": cases,
            "component_decision": "HOLD__COUNTERFACTUAL_SAME_COMPONENT_EDGES",
        })
    private = {
        "schema": PRIVATE_SCHEMA,
        "assumption": "ALL_TEN_CROSS_SPLIT_CANDIDATE_EDGES_TREATED_AS_SAME__NOT_OWNER_CERTIFIED",
        "reviewer_b_safe_summary_seen": b_safe_present,
        "source_actual_sent_verified": False,
        "owner_approved": False,
        "train_admitted": 0,
        "cross_split_components_PRIVATE": component_rows,
        "candidate_edge_ordinals_PRIVATE": [e["edge_ordinal"] for e in crossing],
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "BASE336_COMPONENT_CONFLICT_PREVIEW_READY__P2_C_HOLD",
        "candidate_cross_split_edges": 10,
        "candidate_cross_split_components": len(cross_components),
        "component_story_sizes": sorted(map(len, cross_components)),
        "candidate_affected_stories": len(affected_stories),
        "candidate_affected_cases": len(affected_cases),
        "reviewer_b_aggregate_checked": b_safe_present,
        "reviewer_b_independence_verified": False,
        "reviewer_edge_level_binding_verified_here": False,
        "semantic_component_identity_owner_certified": False,
        "all_38_stories_semantic_isolation_verified": False,
        "historical_actual_sent_verified": False,
        "r50_complete_exclusion_verified": False,
        "p2_c": "HOLD",
        "p2_b_48_prompts": "NOT_GENERATED",
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }
    return private, safe


def write_new(path: Path, payload: dict) -> None:
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer-b-safe", type=Path)
    args = parser.parse_args()
    try:
        packet, _ = packet_and_pin(args.packet)
        load_evidence(packet, args.inputs)
        stories, positions = load_roster(args.roster, packet)
        b_safe = check_b_safe(args.reviewer_b_safe)
        private, safe = build(packet, stories, positions, b_safe)
        root = Path.home() / ".local/share/storyforge/r60/private"
        require(args.output_dir.parent == root, "OUTPUT_PARENT_HOLD")
        require(root.is_dir() and not root.is_symlink(), "PRIVATE_ROOT_HOLD")
        require(stat.S_IMODE(root.stat().st_mode) == 0o700, "PRIVATE_ROOT_MODE_HOLD")
        require(not args.output_dir.exists() and not args.output_dir.is_symlink(), "OUTPUT_EXISTS_HOLD")
        os.mkdir(args.output_dir, 0o700)
        write_new(args.output_dir / "R60_BASE336_COMPONENT_CONFLICT_PREVIEW_PRIVATE.json", private)
        write_new(args.output_dir / "R60_BASE336_COMPONENT_CONFLICT_PREVIEW_SAFE.json", safe)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
    except Exception as exc:  # noqa: BLE001 - safe reason only
        reason = str(exc) if type(exc) is Hold else "UNEXPECTED_HOLD"
        print(json.dumps({"status": "HOLD", "reason_code": reason, "private_values_emitted": False}))
        raise SystemExit(42) from None


if __name__ == "__main__":
    main()

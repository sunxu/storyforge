"""Validate frozen 8-group private roster and create independent review template.

No database, source text, model requests, or training admission. Does not edit
the original roster. The template is Owner-local, create-only, mode 0600.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

import r60_base336_world_cross_split_private_roster_cpu as roster
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_world_group_decisions_template_private_v1"
SAFE = "storyforge_r60_base336_world_group_decisions_template_safe_v1"
FILENAME = "R60_BASE336_WORLD_GROUP_DECISIONS_TEMPLATE_PRIVATE.json"
ROSTER_LIMIT = 5242880


class Hold(ValueError):
    pass


def validate(payload: dict) -> list[dict]:
    if (type(payload) is not dict or payload.get("schema") != roster.SCHEMA
            or payload.get("train_admitted") != 0
            or payload.get("semantic_review_completed") is not False
            or payload.get("actual_sent_version_verified") is not False):
        raise Hold("ROSTER_HEADER_HOLD")
    groups = payload.get("groups_PRIVATE")
    if (type(groups) is not list or len(groups) != 8
            or [g.get("group_ordinal") for g in groups] != list(range(1, 9))
            or sum(g.get("current_world_cross_split") is True for g in groups) != 7):
        raise Hold("GROUP_CONTRACT_HOLD")
    seen = set()
    affected = set()
    for group in groups:
        if (group.get("semantic_verdict") != "UNREVIEWED"
                or type(group.get("members_PRIVATE")) is not list
                or len(group["members_PRIVATE"]) < 2):
            raise Hold("GROUP_VERDICT_HOLD")
        splits = set()
        for member in group["members_PRIVATE"]:
            sid = member.get("story_id_PRIVATE")
            split = member.get("split")
            positions = member.get("candidate_positions_1based_PRIVATE")
            versions = member.get("archived_revision_ids_PRIVATE")
            current = member.get("current_world_match")
            if (type(sid) is not str or not sid or split not in ("train", "validation")
                    or type(positions) is not list or not positions
                    or any(type(x) is not int or not 1 <= x <= 1000 for x in positions)
                    or type(versions) is not list
                    or any(type(x) is not int or x < 1 for x in versions)
                    or type(current) is not bool or (not current and not versions)):
                raise Hold("MEMBER_CONTRACT_HOLD")
            key = (sid, split)
            if key in seen and sid not in affected:
                # A Story may legitimately occur in multiple groups.
                pass
            seen.add(key)
            affected.add(sid)
            splits.add(split)
        if splits != {"train", "validation"}:
            raise Hold("GROUP_CROSSING_HOLD")
    if len(affected) != 38:
        raise Hold("AFFECTED_STORIES_HOLD")
    return groups


def build_template(groups: list[dict], digest: str) -> dict:
    return {
        "schema": SCHEMA,
        "roster_sha256_PRIVATE": digest,
        "review_protocol": "SOURCE_QUOTED_INDEPENDENT_GROUP_REVIEW",
        "not_historical_actual_sent_evidence": True,
        "not_auto_admission": True,
        "train_admitted": 0,
        "group_reviews_PRIVATE": [
            {
                "group_ordinal": g["group_ordinal"],
                "source_group_member_count": len(g["members_PRIVATE"]),
                "decision": "HOLD",
                "reason_code": "SEMANTIC_EVIDENCE_NOT_REVIEWED",
                "world_source_exact_quote_PRIVATE": "",
                "world_source_field_PRIVATE": "",
                "source_revision_evidence_PRIVATE": "",
                "generic_template_vs_shared_world_analysis_PRIVATE": "",
                "source_verified": False,
                "historical_actual_sent_verified": False,
                "reviewer_independence_verified": False,
            }
            for g in groups
        ],
        "all_decisions_pending": True,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
    }


def run(roster_dir: Path) -> dict:
    private.private_dir(roster_dir, create=False)
    source = roster_dir / roster.FILENAME
    raw = private.read_private(source, ROSTER_LIMIT)
    groups = validate(json.loads(raw))
    output = roster_dir / FILENAME
    if output.exists() or output.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    doc = build_template(groups, hashlib.sha256(raw).hexdigest())
    private.write_new(
        output, (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    if stat.S_IMODE(output.stat().st_mode) != 0o600:
        raise Hold("OUTPUT_PERMISSION_HOLD")
    return {
        "schema": SAFE,
        "status": "BASE336_EIGHT_GROUP_DECISION_TEMPLATE_PRIVATE_READY__ALL_HOLD",
        "groups": 8,
        "source_bound": True,
        "template_file_created": True,
        "all_decisions_pending": True,
        "world_content_read": False,
        "database_accessed": False,
        "database_modified": False,
        "model_requests": 0,
        "gpu_started": False,
        "train_admitted": 0,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--roster-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(run(args.roster_dir), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private values never shown
        print(json.dumps({
            "schema": SAFE, "status": "BASE336_EIGHT_GROUP_TEMPLATE_HOLD",
            "database_modified": False, "gpu_started": False,
            "train_admitted": 0, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build a blind, small Gold195 literary quality pilot from PRIVATE review material.

One representative frozen Gold per source world, two independently shuffled
reviewer packets and a private owner-only crosswalk. The card snapshot is
unapproved and is presented only as REVIEW EVIDENCE. Never a training set.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat

from gold195_six_dimension_review_tasks import build, RUBRIC, SEVERE, FLOORS
from gold195_source_review_packet import canon

PILOT_SCHEMA = "r58_gold195_literary_pilot13_blind_private_v1"
CROSSWALK_SCHEMA = "r58_gold195_literary_pilot13_owner_crosswalk_private_v1"
EXPECTED_WORLDS = 13
EXPECTED_SOURCE = 195


def select_world_pilot(tasks):
    if len(tasks) != EXPECTED_SOURCE:
        raise ValueError("195 review source required")
    groups = defaultdict(list)
    for task in tasks:
        if (task.get("schema") != "r58_gold195_six_dimension_review_task_private_v1"
                or task.get("review_status") != "UNREVIEWED"
                or task.get("review_results") != []
                or task.get("training_authorized") is not False
                or task.get("quality_v1_admitted") is not False
                or task.get("world_component_id") is not None
                or task.get("split") is not None):
            raise ValueError("unexpectedly admitted review source")
        world = task.get("story_uuid")
        if not isinstance(world, str) or not world:
            raise ValueError("world identity missing")
        groups[world].append(task)
    if len(groups) != EXPECTED_WORLDS:
        raise ValueError("unexpected number of source world IDs")
    chosen = []
    for world, pool in sorted(groups.items()):
        if len({t["card_snapshot_sha256"] for t in pool}) != 1:
            raise ValueError("multiple cards for same world")
        # Stable review sampling, never based on literary score or model identity.
        chosen.append(min(
            pool, key=lambda t: hashlib.sha256(
                (world + "/" + t["target_sha256"]).encode("utf-8")
            ).hexdigest()
        ))
    return chosen


def reviewer_template():
    return {
        "decision": None,  # PASS | HOLD | REJECT; reviewer must fill
        "scores": {key: None for key in RUBRIC},
        "severe_flags": {key: None for key in SEVERE},
        "card_snapshot_suitable_for_offline_training": None,
        "card_conflicts_with_visible_history_or_gold": None,
        "specific_source_quotes": [],
        "specific_target_quotes": [],
        "literary_quality_notes": None,
        "uncertainty": None,
    }


def blind_material(task, blind_id):
    # No Gold case ID, source world UUID or corpus/model name in reviewer copy.
    return {
        "schema": PILOT_SCHEMA,
        "blind_id": blind_id,
        "input_design": "EXPORT_TIME_CARD_IS_UNAPPROVED_REVIEW_EVIDENCE",
        "messages": task["messages"],
        "target_text": task["target_text"],
        "rubric": RUBRIC,
        "dimension_floors": FLOORS,
        "serious_flags": list(SEVERE),
        "reviewer_instructions": (
            "独立审阅中文文笔、人物一致性、NPC 主动推进、玩家自主权、硬设定"
            "及剧情连续性。当前 System 为待审离线快照，不代表原生产提示。"
            "必须核对目标回复与可见历史是否冲突；若快照有未来剧情、"
            "不可确认的硬设定或严重玩家越权，标注 HOLD/REJECT。"
            "引用必须是可见原文子串。不得猜测模型来源或他人评分。"
        ),
        "response": reviewer_template(),
        "quality_v1_admitted": False,
        "training_authorized": False,
    }


def prepare(private_input: Path, private_dir: Path, repo: Path):
    if (not private_input.is_absolute() or private_input.is_symlink()
            or not private_input.is_file()
            or stat.S_IMODE(private_input.stat().st_mode) != 0o600
            or private_input.stat().st_nlink != 1):
        raise ValueError("private source required")
    if (not private_dir.is_absolute() or private_dir.exists()
            or private_dir.is_symlink() or not private_dir.parent.is_dir()
            or private_dir.parent.is_symlink()
            or stat.S_IMODE(private_dir.parent.stat().st_mode) & 0o077
            or repo.resolve() == private_dir.resolve()
            or repo.resolve() in private_dir.resolve().parents):
        raise ValueError("private fresh output directory required")
    receipt, tasks = build(private_input, collect=True)
    if (receipt["counts"].get("source_rows_checked") != 195
            or receipt["counts"].get("review_tasks_prepared") != 195):
        raise ValueError("unprepared quality review rows")
    selected = select_world_pilot(tasks)
    rng = secrets.SystemRandom()
    packets = {"A": [], "B": []}
    crosswalk = []
    used_blind = set()
    for t in selected:
        blind_ids = {}
        for slot in ("A", "B"):
            blind_id = "r58q-" + secrets.token_hex(12)
            if blind_id in used_blind:
                raise ValueError("blind label collision")
            used_blind.add(blind_id)
            blind_ids[slot] = blind_id
            packets[slot].append(blind_material(t, blind_id))
        crosswalk.append({
            "source_case_id": t["case_id"],
            "story_uuid": t["story_uuid"],
            "source_target_sha256": t["target_sha256"],
            "card_snapshot_sha256": t["card_snapshot_sha256"],
            "source_history_starts_with_assistant":
                t["source_history_starts_with_assistant"],
            "reviewer_a_blind_id": blind_ids["A"],
            "reviewer_b_blind_id": blind_ids["B"],
        })
    for slot in packets:
        rng.shuffle(packets[slot])
    owner = {
        "schema": CROSSWALK_SCHEMA,
        "source_review_file_sha256": hashlib.sha256(private_input.read_bytes()).hexdigest(),
        "selected": crosswalk,
        "reviewer_results_received": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }
    private_dir.mkdir(mode=0o700)
    payloads = {
        "reviewer_A.private.jsonl":
            b"".join(canon(x) + b"\n" for x in packets["A"]),
        "reviewer_B.private.jsonl":
            b"".join(canon(x) + b"\n" for x in packets["B"]),
        "owner_crosswalk.private.json":
            canon(owner),
    }
    for name, content in payloads.items():
        target = private_dir / name
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(content)
    roles = Counter(
        "assistant" if x["source_history_starts_with_assistant"] else "user"
        for x in selected
    )
    return {
        "schema": "r58_gold195_literary_pilot13_safe_v1",
        "status": "GOLD195_BLIND_PILOT13_PREPARED__REVIEWS_NOT_PERFORMED",
        "source_rows_checked": 195,
        "source_worlds": EXPECTED_WORLDS,
        "pilot_cases": len(selected),
        "reviewer_packets": 2,
        "reviewer_cases_each": len(selected),
        "pilot_assistant_first": roles["assistant"],
        "pilot_user_first": roles["user"],
        "reviewer_decisions_fabricated": False,
        "source_cards_semantically_approved": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "protected_test_body_accessed": False,
        "private_text_emitted": False,
    }



def safe_preflight(private_input: Path, private_dir: Path, repo: Path):
    """Inspect validation stages without exposing private values or writing files."""
    safe = {
        "schema": "r58_gold195_literary_pilot13_safe_v1",
        "status": "GOLD195_PILOT13_PREFLIGHT_HOLD",
        "reason_code": "UNDETERMINED",
        "source_rows_checked": 0,
        "review_tasks_prepared": 0,
        "pilot_cases": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "private_text_emitted": False,
        "no_output_written": True,
    }
    if not private_input.is_absolute() or not private_input.is_file() or private_input.is_symlink():
        safe["reason_code"] = "PRIVATE_INPUT_NOT_FOUND_OR_PATH_INVALID"
        return safe
    st = private_input.stat()
    if stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1:
        safe["reason_code"] = "PRIVATE_INPUT_PERMISSIONS_INVALID"
        return safe
    if not private_dir.is_absolute() or private_dir.is_symlink():
        safe["reason_code"] = "OUTPUT_PATH_INVALID"
        return safe
    if private_dir.exists():
        safe["reason_code"] = "OUTPUT_ALREADY_EXISTS"
        return safe
    if not private_dir.parent.is_dir() or private_dir.parent.is_symlink():
        safe["reason_code"] = "OUTPUT_PARENT_MISSING_OR_SYMLINK"
        return safe
    if stat.S_IMODE(private_dir.parent.stat().st_mode) & 0o077:
        safe["reason_code"] = "OUTPUT_PARENT_NOT_PRIVATE_0700"
        return safe
    if repo.resolve() == private_dir.resolve() or repo.resolve() in private_dir.resolve().parents:
        safe["reason_code"] = "OUTPUT_INSIDE_REPOSITORY"
        return safe
    try:
        receipt, tasks = build(private_input, collect=True)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError):
        safe["reason_code"] = "PRIVATE_SOURCE_SCHEMA_OR_CARD_HASH_INVALID"
        return safe
    counts = receipt.get("counts", {})
    safe["source_rows_checked"] = counts.get("source_rows_checked", 0)
    safe["review_tasks_prepared"] = counts.get("review_tasks_prepared", 0)
    safe["assistant_first_prepared"] = counts.get("assistant_first_review_tasks_prepared", 0)
    safe["user_first_prepared"] = counts.get("user_first_review_tasks_prepared", 0)
    if safe["source_rows_checked"] != EXPECTED_SOURCE:
        safe["reason_code"] = "SOURCE_ROW_COUNT_MISMATCH"
        return safe
    if safe["review_tasks_prepared"] != EXPECTED_SOURCE:
        safe["reason_code"] = "REVIEW_TASKS_INCOMPLETE"
        safe["history_shape_hold"] = counts.get("HISTORY_INPUT_SHAPE_HOLD", 0)
        return safe
    safe["source_world_count"] = len({x.get("story_uuid") for x in tasks
                                      if isinstance(x.get("story_uuid"), str)})
    if safe["source_world_count"] != EXPECTED_WORLDS:
        safe["reason_code"] = "WORLD_COUNT_NOT_13"
        return safe
    try:
        selected = select_world_pilot(tasks)
    except (ValueError, KeyError, TypeError):
        safe["reason_code"] = "WORLD_SELECTION_OR_CARD_CONFLICT"
        return safe
    safe["pilot_cases"] = len(selected)
    safe["status"] = "GOLD195_PILOT13_PREFLIGHT_READY__NO_OUTPUT"
    safe["reason_code"] = "READY"
    return safe

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-card-gold-review", type=Path, required=True)
    p.add_argument("--private-output-dir", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--diagnose-only", action="store_true",
                   help="SAFE stage report; does not create review files")
    a = p.parse_args()
    try:
        preflight = safe_preflight(
            a.private_card_gold_review, a.private_output_dir, a.repo_root)
        if preflight["reason_code"] != "READY":
            result, code = preflight, 42
        elif a.diagnose_only:
            result, code = preflight, 0
        else:
            result = prepare(a.private_card_gold_review, a.private_output_dir,
                             a.repo_root)
            code = 0
    except Exception:
        result = {
            "schema": "r58_gold195_literary_pilot13_safe_v1",
            "status": "GOLD195_PILOT13_PRIVATE_SOURCE_OR_OUTPUT_INVALID__HOLD",
            "reason_code": "UNEXPECTED_WRITE_OR_RUNTIME_FAILURE",
            "training_authorized": False, "quality_v1_admitted": 0,
            "private_text_emitted": False,
        }
        code = 42
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

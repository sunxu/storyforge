"""Offline, read-only Common2 vs original R45 Train49/Validation15 story check.
No private IDs, paths, hashes or source text in output. Semantic isolation stays HOLD.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

SCHEMA = "storyforge_r60_common2_r45_story_gate_safe_v1"
PINS = {
    "train": ("e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742", 49),
    "validation": ("5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963", 15),
}
RECOVERY_SCHEMA = "storyforge_r60_qd20_common2_supabase_recovery_private_v1"
RECOVERY_STATUS = "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT"


class Hold(ValueError):
    pass


def private_bytes(path):
    if path.is_symlink():
        raise Hold("PRIVATE_INPUT_LINK_HOLD")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or not 0 < st.st_size <= 12_000_000:
        raise Hold("PRIVATE_INPUT_MODE_SIZE_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        pre = os.fstat(f.fileno())
        data = f.read(12_000_001)
        post = os.fstat(f.fileno())
    if len(data) != st.st_size or (pre.st_dev, pre.st_ino, pre.st_size, pre.st_mtime_ns) != (post.st_dev, post.st_ino, post.st_size, post.st_mtime_ns):
        raise Hold("PRIVATE_INPUT_CHANGED_HOLD")
    return data


def source_id(v):
    if type(v) is not str or not v or len(v) > 256:
        raise Hold("SOURCE_ID_SCHEMA_HOLD")
    return v


def r45_split(path, kind):
    data = private_bytes(path)
    expected_sha, expected_count = PINS[kind]
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise Hold("R45_ORIGINAL_SHA_HOLD")
    lines = data.splitlines()
    if len(lines) != expected_count:
        raise Hold("R45_SPLIT_COUNT_HOLD")
    stories = set()
    for line in lines:
        record = json.loads(line)
        if type(record) is not dict or type(record.get("metadata")) is not dict:
            raise Hold("R45_ORIGINAL_SCHEMA_HOLD")
        stories.add(source_id(record["metadata"].get("source_story_id")))
    return stories


def common2(path):
    data = json.loads(private_bytes(path))
    if (type(data) is not dict or data.get("schema") != RECOVERY_SCHEMA
            or data.get("status") != RECOVERY_STATUS or type(data.get("train_admitted")) is not int
            or data["train_admitted"] != 0 or type(data.get("cases")) is not list
            or len(data["cases"]) != 2):
        raise Hold("COMMON2_RECOVERY_CONTRACT_HOLD")
    stories, targets = set(), set()
    for row in data["cases"]:
        if type(row) is not dict or row.get("last_three_exact_source_match") is not True:
            raise Hold("COMMON2_SOURCE_ATTESTATION_HOLD")
        stories.add(source_id(row.get("story_id")))
        target = source_id(row.get("assistant_message_id"))
        if target in targets:
            raise Hold("COMMON2_DUPLICATE_TARGET_HOLD")
        targets.add(target)
    return stories


def audit(train, validation, recovery):
    result = {
        "schema": SCHEMA, "status": "COMMON2_R45_STORY_GATE_HOLD",
        "reason_code": "UNVERIFIED", "r45_original_sha_verified": False,
        "r45_train_rows_checked": 0, "r45_validation_rows_checked": 0,
        "common2_cases_checked": 0, "train_story_overlap_count": None,
        "validation_story_overlap_count": None,
        "common2_r45_exact_story_disjoint_verified": False,
        "r45_semantic_world_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "final_heldout_seal_verified": False,
        "train_admitted": 0, "gpu_started": False, "hf_jobs_submitted": 0,
        "database_accessed": False, "private_values_emitted": False,
    }
    try:
        if len({str(p.resolve(strict=False)) for p in (train, validation, recovery)}) != 3:
            raise Hold("INPUT_PATH_COLLISION_HOLD")
        tr, va = r45_split(train, "train"), r45_split(validation, "validation")
        result.update(r45_original_sha_verified=True, r45_train_rows_checked=49,
                      r45_validation_rows_checked=15)
        sources = common2(recovery)
        result["common2_cases_checked"] = 2
        result["train_story_overlap_count"] = len(sources & tr)
        result["validation_story_overlap_count"] = len(sources & va)
        clean = not result["train_story_overlap_count"] and not result["validation_story_overlap_count"]
        result["common2_r45_exact_story_disjoint_verified"] = clean
        result["status"] = ("COMMON2_R45_ORIGINAL_STORY_IDS_DISJOINT__SEMANTIC_TRAIN_HOLD"
                            if clean else "COMMON2_R45_ORIGINAL_STORY_OVERLAP__TRAIN_HOLD")
        result["reason_code"] = "EXACT_R45_SPLIT_STORY_DISJOINT" if clean else "R45_STORY_OVERLAP"
    except Exception as e:
        codes = {
            "PRIVATE_INPUT_LINK_HOLD", "PRIVATE_INPUT_MODE_SIZE_HOLD",
            "PRIVATE_INPUT_CHANGED_HOLD", "SOURCE_ID_SCHEMA_HOLD",
            "R45_ORIGINAL_SHA_HOLD", "R45_SPLIT_COUNT_HOLD", "R45_ORIGINAL_SCHEMA_HOLD",
            "COMMON2_RECOVERY_CONTRACT_HOLD", "COMMON2_SOURCE_ATTESTATION_HOLD",
            "COMMON2_DUPLICATE_TARGET_HOLD", "INPUT_PATH_COLLISION_HOLD",
        }
        result["reason_code"] = str(e) if type(e) is Hold and str(e) in codes else "INPUT_OR_RUNTIME_HOLD"
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--r45-original-train", type=Path, required=True)
    p.add_argument("--r45-original-validation", type=Path, required=True)
    p.add_argument("--common2-recovery", type=Path, required=True)
    a = p.parse_args()
    result = audit(a.r45_original_train, a.r45_original_validation, a.common2_recovery)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["common2_r45_exact_story_disjoint_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())

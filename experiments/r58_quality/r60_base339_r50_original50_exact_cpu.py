"""Offline exact-ID overlap of R60 339 candidates and pinned R50 original 50.

Rebuild V123 and quarantine from immutable sources; validate R50 provenance
hash/size using existing R50 reader. Never leak IDs or admit training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private
from scripts import r60_r50_common2_exact_source_isolation_cpu as common2
from scripts import r60_r50_original50_complement_cpu as r50

SCHEMA = "storyforge_r60_base339_r50_original50_exact_safe_v1"


class Hold(ValueError):
    pass


def evaluate(cases: list[dict], manifest: dict, r50_rows: list[dict]) -> dict:
    partition = manifest
    if (partition.get("schema") != quarantine.SCHEMA
            or len(partition.get("excluded_known5", [])) != 3
            or len(partition.get("remaining_full_r50_hold", [])) != 336
            or partition.get("train_admitted") != 0):
        raise Hold("QUARANTINE_CONTRACT_HOLD")
    protected_stories, protected_sessions, protected_messages = (
        common2.r50_sources(r50_rows))
    overlaps = {"story": 0, "session": 0, "message": 0}
    all_positions = set()
    held_overlap = 0
    for category in ("excluded_known5", "remaining_full_r50_hold"):
        for entry in partition[category]:
            pos = entry["position"]
            if type(pos) is not int or not 1 <= pos <= len(cases) or pos in all_positions:
                raise Hold("CANDIDATE_POSITION_HOLD")
            all_positions.add(pos)
            src = cases[pos - 1]["source"]
            story = common2.source_id(src.get("story_id"))
            session = common2.source_id(src.get("session_id"))
            msgs = {
                common2.source_id(src.get(k))
                for k in ("assistant_message_id", "prior_user_message_id",
                          "previous_assistant_message_id", "previous_user_message_id")
            }
            is_story = story in protected_stories
            is_session = session in protected_sessions
            is_message = bool(msgs & protected_messages)
            overlaps["story"] += is_story
            overlaps["session"] += is_session
            overlaps["message"] += is_message
            if category == "remaining_full_r50_hold":
                held_overlap += is_story or is_session or is_message
    if len(all_positions) != 339:
        raise Hold("CANDIDATE_COUNT_HOLD")
    return {
        "schema": SCHEMA,
        "status": ("R50_ORIGINAL50_EXACT_HELD_KEYS_DISJOINT__OTHER_GATES_HOLD"
                   if held_overlap == 0 else
                   "R50_ORIGINAL50_EXACT_HELD_OVERLAP__TRAIN_HOLD"),
        "r50_original_provenance_sha_verified": True,
        "r50_original_cases_checked": 50,
        "candidate_cases_checked": 339,
        "known5_excluded_cases": 3,
        "still_held_cases": 336,
        "all_candidate_exact_story_overlap": overlaps["story"],
        "all_candidate_exact_session_overlap": overlaps["session"],
        "all_candidate_exact_message_overlap": overlaps["message"],
        "remaining_336_exact_key_overlap": held_overlap,
        "remaining_336_exact_keys_disjoint_verified": held_overlap == 0,
        "r50_complete_exclusion_verified": False,
        "semantic_world_alias_isolation_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "model_requests": 0,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
    }


def execute(args: argparse.Namespace) -> dict:
    cases, crosswalk = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    frozen = quarantine.construct(
        cases, crosswalk, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if frozen != saved:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    original = r50.jsonl(args.r50_original_provenance, 50, "provenance")
    return evaluate(cases, saved, original)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    p.add_argument("--r50-original-provenance", type=Path, required=True)
    args = p.parse_args()
    try:
        safe = execute(args)
        print(json.dumps(safe, sort_keys=True))
        return 0 if safe["remaining_336_exact_keys_disjoint_verified"] else 42
    except Exception as exc:  # noqa: BLE001 - fixed safe error codes only
        code = str(exc)
        allowed = {"QUARANTINE_DRIFT_HOLD", "QUARANTINE_CONTRACT_HOLD",
                   "CANDIDATE_POSITION_HOLD", "CANDIDATE_COUNT_HOLD"}
        print(json.dumps({
            "schema": SCHEMA, "status": "R50_ORIGINAL50_EXACT_AUDIT_HOLD",
            "reason_code": code if type(exc) is Hold and code in allowed
                           else "SOURCE_OR_RUNTIME_HOLD",
            "train_admitted": 0, "model_requests": 0,
            "hf_jobs_submitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

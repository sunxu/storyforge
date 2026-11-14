"""Preview world-disjoint Train/Val split for R60 Base-start dev ONLY.

The known-five R50 exclusions remain excluded, the remaining 336 stay HOLD.
No SFT artifact, admission, model request, DB read, GPU job or file write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base_start_world_split_preview_safe_v1"
SALT = b"storyforge-r60-base-start-world-split-preview-v1"
VAL_PERCENT = 20


class Hold(ValueError):
    pass


def preview(cases: list[dict], manifest: dict) -> dict:
    if (manifest.get("schema") != quarantine.SCHEMA
            or manifest.get("status") !=
            "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD"
            or manifest.get("r50_complete_exclusion_verified") is not False
            or manifest.get("train_admitted") != 0):
        raise Hold("QUARANTINE_CONTRACT_HOLD")
    excluded = manifest.get("excluded_known5")
    held = manifest.get("remaining_full_r50_hold")
    if (not isinstance(excluded, list) or not isinstance(held, list)
            or len(excluded) + len(held) != 339):
        raise Hold("QUARANTINE_COUNT_HOLD")
    assignments = {}
    excluded_positions = set()
    for item in excluded:
        pos = item.get("position")
        if (type(pos) is not int or pos in excluded_positions
                or item.get("reason_code") !=
                "R50_KNOWN5_SOURCE_STORY_OVERLAP"):
            raise Hold("QUARANTINE_EXCLUSION_HOLD")
        excluded_positions.add(pos)
        if cases[pos - 1]["source"]["story_id"] not in (
                quarantine.known.KNOWN_R50_STORIES):
            raise Hold("QUARANTINE_SOURCE_MISMATCH_HOLD")
    held_positions = set()
    for item in held:
        pos = item.get("position")
        if (type(pos) is not int or not 1 <= pos <= len(cases)
                or pos in held_positions or pos in excluded_positions
                or item.get("status") !=
                "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD"):
            raise Hold("QUARANTINE_HELD_HOLD")
        held_positions.add(pos)
        world = cases[pos - 1]["source"]["story_id"]
        if world in quarantine.known.KNOWN_R50_STORIES:
            raise Hold("KNOWN5_HELD_CROSSOVER_HOLD")
        if world not in assignments:
            slot = int.from_bytes(
                hashlib.sha256(SALT + world.encode("utf-8")).digest()[:8],
                "big",
            ) % 100
            assignments[world] = "validation" if slot < VAL_PERCENT else "train"
    if len(cases) != 1000 or len(excluded_positions) != 3 or len(held_positions) != 336:
        raise Hold("EXPECTED_OWNER_SCOPE_HOLD")
    counts = Counter(assignments[cases[p - 1]["source"]["story_id"]]
                     for p in held_positions)
    worlds = Counter(assignments.values())
    if counts["train"] + counts["validation"] != 336:
        raise Hold("PREVIEW_ACCOUNTING_HOLD")
    return {
        "schema": SCHEMA,
        "status": "BASE_START_SPLIT_PREVIEW_ONLY__ALL_HELD_NO_ADMISSION",
        "base_model": "Qwen/Qwen3.8-27B",
        "inherit_previous_adapter": False,
        "known5_excluded_cases": len(excluded_positions),
        "held_candidate_cases": len(held_positions),
        "held_candidate_worlds": len(assignments),
        "provisional_train_cases": counts["train"],
        "provisional_validation_cases": counts["validation"],
        "provisional_train_worlds": worlds["train"],
        "provisional_validation_worlds": worlds["validation"],
        "split_deterministic": True,
        "train_validation_story_disjoint": True,
        "all_provisional_rows_train_admitted": False,
        "r50_complete_exclusion_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "tokenizer_verified": False,
        "collator_verified": False,
        "training_dataset_created": False,
        "model_requests": 0,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
        "train_admitted": 0,
    }


def execute(old_dir: Path, plan_dir: Path, v2_dir: Path, v3_dir: Path,
            audit_dir: Path, quarantine_dir: Path) -> dict:
    private.private_dir(quarantine_dir, create=False)
    cases, crosswalk_report = identity.verified_cases_report(
        old_dir, plan_dir, v2_dir, v3_dir, audit_dir)
    raw = private.read_private(
        audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(
        cases, crosswalk_report, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if saved != expected:
        raise Hold("QUARANTINE_SNAPSHOT_DRIFT_HOLD")
    return preview(cases, saved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        out = execute(args.old_dir, args.plan_dir, args.v2_dir,
                      args.v3_dir, args.audit_dir, args.quarantine_dir)
        print(json.dumps(out, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        reason = str(exc)
        if (type(exc) not in {Hold, identity.Hold,
                             quarantine.Hold, private.Hold}
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{3,79}", reason)):
            reason = "BASE_SPLIT_PREVIEW_LOCAL_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE_SPLIT_PREVIEW_HOLD",
            "reason_code": reason, "train_admitted": 0,
            "gpu_started": False, "private_values_emitted": False,
            "model_requests": 0, "database_modified": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

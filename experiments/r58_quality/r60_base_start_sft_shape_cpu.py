"""CPU-only static SFT shape preflight for Base-start 336 HELD candidates.

No tokenizer/collator claims, training examples, disk writes or external calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import r60_base_start_world_split_preview as split
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base_start_sft_shape_safe_v1"
ROLES = ("user", "assistant", "user")


class Hold(ValueError):
    pass


def inspect(cases: list[dict], manifest: dict) -> dict:
    partition = split.preview(cases, manifest)
    if partition["held_candidate_cases"] != 336:
        raise Hold("SHAPE_SOURCE_COUNT_HOLD")
    target_sizes, context_sizes = [], []
    failures = Counter()
    source_provenance = Counter()
    roles = Counter()
    for row in manifest["remaining_full_r50_hold"]:
        case = cases[row["position"] - 1]
        history = case.get("history_messages")
        target = case.get("target_text")
        if (not isinstance(history, list) or len(history) != 3
                or not isinstance(target, str) or not target):
            failures["HISTORY_OR_TARGET_SHAPE"] += 1
            continue
        if tuple(m.get("role") if isinstance(m, dict) else None
                 for m in history) != ROLES:
            failures["ROLE_SEQUENCE"] += 1
            continue
        if any(not isinstance(m.get("content"), str)
               or not m["content"] for m in history):
            failures["EMPTY_HISTORY_CONTENT"] += 1
            continue
        if (case["history_messages_sha256"] !=
                private.digest(history)
                or case["assistant_target_sha256"] !=
                private.digest(target)):
            failures["SOURCE_HASH"] += 1
            continue
        source_provenance[str(case.get("historical_system_provenance"))] += 1
        roles["FINAL_ASSISTANT_ONLY_PLANNED_NOT_COLLATED"] += 1
        context_sizes.append(sum(len(m["content"]) for m in history))
        target_sizes.append(len(target))
    validated = len(target_sizes)
    if validated + sum(failures.values()) != 336:
        raise Hold("SHAPE_ACCOUNTING_HOLD")
    def stats(nums):
        if not nums:
            return {"min": 0, "max": 0, "mean": 0}
        return {"min": min(nums), "max": max(nums),
                "mean": round(sum(nums) / len(nums), 2)}
    return {
        "schema": SCHEMA,
        "status": ("BASE_SFT_STATIC_SHAPE_PASS__ALL_HELD"
                   if not failures else "BASE_SFT_STATIC_SHAPE_HOLD"),
        "candidate_count": 336,
        "validated_three_message_cases": validated,
        "static_failure_counts": dict(sorted(failures.items())),
        "history_character_stats": stats(context_sizes),
        "target_character_stats": stats(target_sizes),
        "historical_system_provenance_counts":
            dict(sorted(source_provenance.items())),
        "expected_input_role_sequence": list(ROLES),
        "constructed_system_required_if_used": True,
        "actual_historical_system_verified": False,
        "actual_collator_last_assistant_mask_verified": False,
        "real_tokenizer_verified": False,
        "train_validation_story_disjoint": True,
        "r50_complete_exclusion_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "all_candidates_held": True,
        "training_dataset_created": False,
        "train_admitted": 0,
        "model_requests": 0, "database_modified": False,
        "gpu_started": False, "private_values_emitted": False,
    }


def execute(old_dir: Path, plan_dir: Path, v2_dir: Path, v3_dir: Path,
            audit_dir: Path, quarantine_dir: Path) -> dict:
    private.private_dir(quarantine_dir, create=False)
    cases, report = identity.verified_cases_report(
        old_dir, plan_dir, v2_dir, v3_dir, audit_dir)
    raw = private.read_private(
        audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    frozen = quarantine.construct(
        cases, report, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if saved != frozen:
        raise Hold("QUARANTINE_REPORT_DRIFT_HOLD")
    return inspect(cases, saved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        safe = execute(args.old_dir, args.plan_dir, args.v2_dir,
                       args.v3_dir, args.audit_dir, args.quarantine_dir)
        print(json.dumps(safe, sort_keys=True))
        return 0 if safe["status"] == "BASE_SFT_STATIC_SHAPE_PASS__ALL_HELD" else 42
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        reason = str(exc)
        if (type(exc) not in {Hold, split.Hold, quarantine.Hold,
                             identity.Hold, private.Hold}
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{3,79}", reason)):
            reason = "BASE_STATIC_SFT_LOCAL_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE_SFT_STATIC_SHAPE_HOLD",
            "reason_code": reason, "private_values_emitted": False,
            "model_requests": 0, "gpu_started": False,
            "train_admitted": 0, "database_modified": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

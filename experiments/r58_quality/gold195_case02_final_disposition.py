#!/usr/bin/env python3
"""R58 Case02: private final evidence disposition, always quality HOLD.

Produces a PRIVATE case02 decision template from existing original A/B + Grok
arbiter, without changing source reviews or adding new external model requests.
Can validate a filled decision file, but never auto-admit Gold to training.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import stat

from gold195_grok_web_followup_validate import followup, check_arbiter
from gold195_grok_web_validate import read_private_json, check_review
from gold195_grok_web_export import FLAGS

SCHEMA = "r58_case02_severe_final_disposition_private_v1"
CHOICES = ("CONFIRMED_SEVERE", "NOT_SUPPORTED_WITH_EVIDENCE", "UNRESOLVED")
MAX_BYTES = 64 * 1024


def evidence(pilot: Path, follow: Path):
    receipt = followup(pilot, follow)
    if (receipt["review_states"]["case02_arbiter"] !=
            "ARBITER_DISPUTES_SEVERE__MANUAL_RESOLUTION_REQUIRED"
            or not receipt["case03_retries_both_provisional_pass"]):
        raise ValueError("source followup is not the expected frozen state")
    manifest = read_private_json(pilot / "review-manifest.private.json")
    original = manifest["cases"][1]
    a = read_private_json(pilot / "case02-reviewer-A.json")
    b = read_private_json(pilot / "case02-reviewer-B.json")
    third = read_private_json(follow / "case02-independent-severe-arbitration.json")
    target = original["target_text"]
    if (check_review(a, target) != "SEVERE_FLAG"
            or check_review(b, target) != "PROVISIONAL_REVIEW_PASS"
            or check_arbiter(third, target) !=
            "ARBITER_DISPUTES_SEVERE__MANUAL_RESOLUTION_REQUIRED"):
        raise ValueError("original review evidence inconsistent")
    flags = [key for key in FLAGS if a["severe_flags"][key]]
    return original, a, b, third, flags


def make_template(pilot: Path, follow: Path):
    original, a, b, third, flags = evidence(pilot, follow)
    return {
        "schema": SCHEMA,
        "case_label": "case02",
        "case_id": original["case_id"],
        "target_sha256": original["target_sha256"],
        "original_severe_flags": flags,
        "original_A": a,
        "original_B": b,
        "arbiter_result": third,
        "decision": "UNRESOLVED",
        "actual_source_evidence": [],
        "gold_exact_quotes": [],
        "independent_reasoning": "",
        "uncertainty": "REQUIRES_EVIDENCE_BASED_FINAL_DECISION",
        "decision_maker": "",
        "decision_completed": False,
        "quality_v1_admitted": False,
        "training_authorized": False,
    }


def validate_decision(obj, pilot: Path, follow: Path):
    original, a, b, third, flags = evidence(pilot, follow)
    if (not isinstance(obj, dict) or obj.get("schema") != SCHEMA
            or obj.get("case_label") != "case02"
            or obj.get("case_id") != original["case_id"]
            or obj.get("target_sha256") != original["target_sha256"]
            or obj.get("original_severe_flags") != flags
            or obj.get("original_A") != a
            or obj.get("original_B") != b
            or obj.get("arbiter_result") != third
            or obj.get("quality_v1_admitted") is not False
            or obj.get("training_authorized") is not False):
        raise ValueError("decision altered source or contract")
    choice = obj.get("decision")
    if choice not in CHOICES:
        raise ValueError("invalid disposition choice")
    if choice == "UNRESOLVED":
        if obj.get("decision_completed") is not False:
            raise ValueError("unresolved cannot be completed")
        return "CASE02_UNRESOLVED__HOLD"
    if (obj.get("decision_completed") is not True
            or not isinstance(obj.get("decision_maker"), str)
            or not obj["decision_maker"].strip()
            or not isinstance(obj.get("independent_reasoning"), str)
            or len(obj["independent_reasoning"].strip()) < 30):
        raise ValueError("missing independent disposition")
    quotes = obj.get("gold_exact_quotes")
    facts = obj.get("actual_source_evidence")
    if (not isinstance(quotes, list) or not quotes or len(quotes) > 12
            or any(not isinstance(x, str) or not x.strip()
                   or len(x) > 120 or x not in original["target_text"]
                   for x in quotes)
            or not isinstance(facts, list) or not facts or len(facts) > 12
            or any(not isinstance(x, str) or not x.strip() or len(x) > 500
                   for x in facts)):
        raise ValueError("direct evidence missing or quotes not in Gold")
    if choice == "CONFIRMED_SEVERE":
        return "CASE02_SEVERE_CONFIRMED__EXCLUDE_FROM_TRAINING"
    return "CASE02_SEVERE_NOT_SUPPORTED__OTHER_QUALITY_GATES_HOLD"


def private_write(path: Path, repo: Path, value):
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError("destination must be new absolute file")
    parent = path.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) & 0o077
            or repo.resolve() == parent.resolve()
            or repo.resolve() in parent.resolve().parents):
        raise ValueError("private output directory")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument("--private-pilot-dir", required=True, type=Path)
    p.add_argument("--private-followup-dir", required=True, type=Path)
    exclusive = p.add_mutually_exclusive_group()
    exclusive.add_argument("--private-decision-template-output", type=Path)
    exclusive.add_argument("--private-decision-input", type=Path)
    args = p.parse_args()
    try:
        if args.private_decision_input:
            path = args.private_decision_input
            if (not path.is_absolute() or not path.is_file() or path.is_symlink()
                    or stat.S_IMODE(path.stat().st_mode) != 0o600
                    or not 0 < path.stat().st_size < MAX_BYTES):
                raise ValueError("decision input unsafe")
            result = validate_decision(
                read_private_json(path), args.private_pilot_dir, args.private_followup_dir)
            wrote = False
        else:
            obj = make_template(args.private_pilot_dir, args.private_followup_dir)
            if args.private_decision_template_output:
                private_write(args.private_decision_template_output, args.repo_root, obj)
            wrote = bool(args.private_decision_template_output)
            result = "CASE02_DISPOSITION_TEMPLATE_READY__NO_DECISION"
        receipt = {
            "schema": "r58_case02_severe_final_disposition_safe_v1",
            "status": result,
            "template_written": wrote,
            "case02_original_A_severe_preserved": True,
            "case02_original_B_provisional_pass_preserved": True,
            "arbiter_disagrees_with_severe_preserved": True,
            "case01_case03_originals_untouched": True,
            "source_text_emitted": False,
            "quality_v1_admitted": 0,
            "gpu_authorized": False,
            "r50_accessed": False,
            "network_called": False,
        }
        code = 0
    except Exception:
        receipt = {
            "schema": "r58_case02_severe_final_disposition_safe_v1",
            "status": "CASE02_SOURCE_OR_DECISION_INVALID__HOLD",
            "quality_v1_admitted": 0,
            "network_called": False, "r50_accessed": False,
        }
        code = 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

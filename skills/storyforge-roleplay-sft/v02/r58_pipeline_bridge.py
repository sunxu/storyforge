"""R58 Skill v0.2 PREVIEW: strict Round1 discovery + fail-closed gate/freeze.

This adapter must not authorize any real private content or train/validation cases.
The pinned G1/G2 evidence preflight is read-only and currently HOLD. No HF/DB.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from r58_evidence_preflight import MATRIX_PATH, PINS, Hold, git_blob, safe_json, verify

SCHEMA = "storyforge-r58-v02-pipeline-bridge-safe-v1"
CATEGORIES = ("original", "dice_cocreate", "ai_assisted")
REQUIRED = frozenset((
    "story_id", "story_type", "moderation_status", "not_deleted",
    "assistant_completed", "session_count", "has_world", "has_character",
    "has_characters", "has_opening", "source_type",
))
MAX_CSV_BYTES = 5_000_000


def boolean(value: str | None) -> bool:
    token = str(value if value is not None else "").strip().lower()
    if token in ("t", "true", "1", "yes"):
        return True
    if token in ("f", "false", "0", "no", ""):
        return False
    raise Hold("unknown boolean in metadata")


def count(value: str | None) -> int:
    token = str(value if value is not None else "").strip()
    if not re.fullmatch(r"[0-9]+", token):
        raise Hold("invalid metadata count")
    return int(token)


def eligible(row: dict[str, str]) -> bool:
    """Matches the frozen Round1 metadata predicate, not v0.1 shortlist."""
    return (
        row["story_type"].strip() == "v2_sandbox"
        and row["moderation_status"].strip() in ("approved", "override_approved")
        and boolean(row["not_deleted"])
        and count(row["assistant_completed"]) >= 50
        and count(row["session_count"]) >= 2
        and boolean(row["has_world"])
        and (boolean(row["has_character"]) or boolean(row["has_characters"]))
        and boolean(row["has_opening"])
        and row["source_type"].strip() in CATEGORIES
    )


def inspect_inventory(path: Path) -> dict:
    """Only SAFE counts; never select, write, or print candidate IDs."""
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_CSV_BYTES:
        raise Hold("private metadata inventory missing/unsafe")
    counts = {source: 0 for source in CATEGORIES}
    total = 0
    seen_ids = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED <= set(reader.fieldnames):
            raise Hold("private metadata inventory schema mismatch")
        for row in reader:
            total += 1
            sid = row["story_id"]
            if not isinstance(sid, str) or not sid.strip() or sid.strip().lower() in seen_ids:
                raise Hold("missing/duplicate story identifier")
            seen_ids.add(sid.strip().lower())
            if any(row.get(field) is None for field in REQUIRED):
                raise Hold("missing metadata value")
            # All numeric/bool cells are validated even if earlier conditions fail.
            for key in ("not_deleted", "has_world", "has_character", "has_characters", "has_opening"):
                boolean(row[key])
            count(row["assistant_completed"])
            count(row["session_count"])
            if eligible(row):
                counts[row["source_type"].strip()] += 1
    return {
        "schema": SCHEMA,
        "status": "METADATA_DISCOVERY_ONLY__FROZEN_PILOT_UNCHANGED__G1_G2_HOLD",
        "inventory_rows": total,
        "metadata_eligible": sum(counts.values()),
        "metadata_eligible_by_source": counts,
        "selected_new_worlds": 0,
        "max_pilot_worlds": 5,
        "max_reply_targets": 20,
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
        "private_ids_printed": False,
        "candidate_text_accessed": False,
    }


def evidence_preflight(repo: Path) -> dict:
    if repo.is_symlink() or not repo.is_dir():
        raise Hold("invalid Git root")
    path = repo / MATRIX_PATH
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 50_000:
        raise Hold("matrix missing or unsafe")
    matrix = safe_json(path.read_bytes())
    sources = {key: safe_json(git_blob(repo, sha)) for key, (sha, _name) in PINS.items()}
    return verify(matrix, sources)


def pipeline_decision(action: str, preflight: dict) -> dict:
    """Future certificate gates are deliberately not implemented in this preview."""
    if action not in ("gate", "freeze"):
        raise Hold("unsupported protected operation")
    if not isinstance(preflight, dict) or preflight.get("status") != "G1_G2_SAFE_EVIDENCE_RECONCILED__BOTH_HOLD":
        raise Hold("unrecognized evidence state")
    if preflight.get("g1_clearance") != "HOLD" or preflight.get("g2_clearance") != "HOLD":
        raise Hold("invalid clearance state")
    if preflight.get("training_admitted") != 0 or preflight.get("expansion_allowed") is not False:
        raise Hold("invalid admission contract")
    return {
        "schema": SCHEMA,
        "action": action,
        "status": "HOLD_G1_G2_UNPROVEN__NO_V01_EXECUTION",
        "g1": "HOLD", "g2": "HOLD",
        "candidate_input_read": False,
        "v01_gate_or_freeze_called": False,
        "output_data_written": False,
        "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    discovery = sub.add_parser("shortlist", help="metadata-only counts, no new selection")
    discovery.add_argument("--inventory", type=Path, required=True)
    for operation in ("gate", "freeze"):
        cmd = sub.add_parser(operation, help="verify G1/G2 then refuse while HOLD")
        cmd.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "shortlist":
            result = inspect_inventory(args.inventory)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        result = pipeline_decision(args.action, evidence_preflight(args.repo_root))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 42
    except (Hold, OSError, UnicodeError, TypeError, ValueError, csv.Error):
        print("R58_SKILL_V02_PIPELINE: HOLD (source evidence invalid/unavailable)", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

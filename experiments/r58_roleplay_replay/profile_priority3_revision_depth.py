#!/usr/bin/env python3
"""R58 offline revision-depth inventory; no database, network, or private output."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from capture_priority3 import Hold, MAX_INPUT_BYTES
from preflight_priority3_history import derive_case
from verify_priority3_private import read_private_file, verify


def classify(row: dict) -> dict:
    derived = derive_case(row)
    if derived["eleven_message_structure"] != "PASS":
        raise Hold("conditional 11-message structure is not established")
    window = row["history24"][-11:]
    if len(window) != 11 or window[0]["role"] != "user":
        raise Hold("unexpected source history window")
    counters = {
        role: {"total": 0, "revision_0": 0, "revision_1": 0,
               "revision_2_plus": 0}
        for role in ("user", "assistant")
    }
    for message in window:
        role, value = message["role"], message.get("mutation_revision")
        if role not in counters or type(value) is not int or value < 0:
            raise Hold("source revision data invalid")
        counters[role]["total"] += 1
        key = "revision_0" if value == 0 else (
            "revision_1" if value == 1 else "revision_2_plus"
        )
        counters[role][key] += 1
    if counters["assistant"]["total"] != 5 or counters["user"]["total"] != 6:
        raise Hold("unexpected source role totals")
    return {
        "cohort": derived["cohort"],
        "conditional_window_count": 11,
        "role_counts": counters,
        "revision_cause_certified": False,
        "body_edited_certified": False,
        "historical_content_as_of_request": "HOLD",
    }


def check(folder: Path) -> dict:
    integrity = verify(folder)
    if integrity["case_fingerprints_verified"] != 12:
        raise Hold("private integrity verification not complete")
    source = read_private_file(folder / "source.private.jsonl", MAX_INPUT_BYTES)
    rows = [json.loads(line) for line in source.splitlines() if line.strip()]
    cases = [classify(item) for item in rows]
    if len(cases) != 3 or {case["cohort"] for case in cases} != {
        "AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"
    }:
        raise Hold("unexpected source cohorts")
    return {
        "status": "R58_REVISION_DEPTH_INVENTORY_PASS__ASOF_RUNTIME_HOLD",
        "cases": sorted(cases, key=lambda c: c["cohort"]),
        "source_bundle_integrity": "PASS",
        "private_source_modified": False,
        "historical_content_unchanged": "HOLD",
        "provider_request_byte_exact": "HOLD",
        "training_admission": "HOLD",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize revision depths in the fixed Priority3 11-message windows"
    )
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.private_dir), sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError):
        print("R58_REVISION_DEPTH_INVENTORY: HOLD", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

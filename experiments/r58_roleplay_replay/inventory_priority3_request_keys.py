#!/usr/bin/env python3
"""SAFE local inventory: does frozen target metadata contain an explicit request key?

Only prints known key names and boolean presence, never values, IDs or text.
Do not infer original runtime request identity from missing fields.
"""
import argparse
import json
from pathlib import Path
import sys

from capture_priority3 import Hold, MAX_INPUT_BYTES
from verify_priority3_private import read_private_file, verify

KEYS = ("requestId", "request_id", "apiRequestId", "api_request_id",
        "analyticsEventId", "analytics_event_id", "relayRequestId")
COHORTS = {"AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"}


def inventory(folder: Path) -> dict:
    if verify(folder)["case_fingerprints_verified"] != 12:
        raise Hold("source checksum HOLD")
    source = read_private_file(folder / "source.private.jsonl", MAX_INPUT_BYTES)
    rows = [json.loads(line) for line in source.splitlines() if line.strip()]
    if len(rows) != 3:
        raise Hold("exactly three sources required")
    cases = []
    for row in rows:
        cohort = row["case"]["cohort"]
        meta = row["target"].get("metadata") or {}
        if cohort not in COHORTS or not isinstance(meta, dict):
            raise Hold("target metadata invalid")
        cases.append({
            "cohort": cohort,
            "known_request_key_present": {name: bool(meta.get(name))
                                          for name in KEYS},
        })
    if {c["cohort"] for c in cases} != COHORTS:
        raise Hold("cohort scope invalid")
    return {
        "status": "R58_LOCAL_REQUEST_KEY_INVENTORY_COMPLETE__DIRECT_LINK_HOLD",
        "cases": sorted(cases, key=lambda c: c["cohort"]),
        "exact_target_request_join_verified": False,
        "provider_prompt_byte_exact": "HOLD",
        "training_admission": "HOLD",
    }


def main():
    p = argparse.ArgumentParser(description="R58 local request metadata keys only")
    p.add_argument("--private-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(inventory(args.private_dir), sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, KeyError, TypeError):
        print("R58_REQUEST_KEY_INVENTORY: HOLD", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

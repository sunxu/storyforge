"""Read-only v1/v2 Pilot5 crosswalk; validates receipts without adjudicating prose.

No network, private story output, HF Jobs, DB writes, or training admission.
Uses the frozen v1/v2 verification paths rather than reimplementing reviewers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import r60_pilot5_v2_replay_execute as replay
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SAFE = "storyforge_r60_pilot5_v2_crosswalk_safe_v1"


def audit(quality_dir: Path, output_dir: Path) -> dict:
    result = {
        "schema": SAFE,
        "status": "PILOT5_V2_CROSSWALK_HOLD",
        "v1_cases": 0,
        "v1_valid_reviews": 0,
        "planned_slots": 0,
        "v2_recorded": 0,
        "v2_success": 0,
        "v2_attempt_holds": 0,
        "unresolved_slots": 0,
        "model_requests": 0,
        "database_modified": False,
        "gpu_started": False,
        "train_admitted": 0,
        "private_values_emitted": False,
    }
    try:
        # Reuse the canonical source/config/manifest and all original receipt
        # validations, including exact SHA and reviewer-side bindings.
        _config, _cases, slots = replay.verify(quality_dir, output_dir)
        seen = 0
        for pos in range(1, 6):
            receipt = json.loads(private.read_private(
                quality_dir / quality.receipt_name(pos), quality.MAX_CASE_BYTES,
            ))
            seen += len(receipt["reviews"])
        if seen != 7:
            raise replay.Hold("V1_EXPECTED_VALID_REVIEWS_HOLD")
        result["v1_cases"] = 5
        result["v1_valid_reviews"] = seen
        result["planned_slots"] = len(slots)
        for slot in slots:
            path = replay.receipt_file(
                output_dir, slot["position"], slot["side"],
            )
            if replay.verify_existing_slot(path, slot):
                row = json.loads(private.read_private(path, quality.MAX_CASE_BYTES))
                result["v2_recorded"] += 1
                if row["attempt_status"] == "SUCCESS":
                    result["v2_success"] += 1
                else:
                    result["v2_attempt_holds"] += 1
        result["unresolved_slots"] = len(slots) - result["v2_success"]
        result["status"] = (
            "PILOT5_V2_CROSSWALK_INTEGRITY_PASS__QUALITY_HOLD"
            if result["v2_recorded"] == len(slots)
            else "PILOT5_V2_CROSSWALK_PARTIAL__QUALITY_HOLD"
        )
    except (ValueError, OSError, TypeError, KeyError, IndexError, UnicodeError):
        result["status"] = "PILOT5_V2_CROSSWALK_HOLD"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.quality_dir, args.output_dir)
    print(json.dumps(result, sort_keys=True))
    return 42 if result["status"] == "PILOT5_V2_CROSSWALK_HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())

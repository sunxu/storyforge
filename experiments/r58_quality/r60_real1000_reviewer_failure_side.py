"""Owner-private read-only diagnostic of failed reviewer sides in REAL1000.

No API requests, no private strings, no source values in stdout. Inspect each
existing immutable receipt through the original frozen source/receipt validator.
When a receipt has exactly one successful reviewer, the other slot is known.
When neither succeeded, the original v1 record does not identify which error
belongs to which side, so report ambiguity rather than guessing.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import r60_real_quality_batch as batch
import r60_real_private_batch as private


SCHEMA = "storyforge_r60_real1000_reviewer_failure_side_safe_v1"


def inspect(folder: Path) -> dict:
    safe = {
        "schema": SCHEMA,
        "status": "REVIEWER_FAILURE_SIDE_AUDIT_HOLD",
        "model_requests": 0,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
        "train_admitted": 0,
    }
    try:
        with batch.expand.locked(folder):
            config = batch.validate_config(folder)
            cases, pool_sha = batch.frozen_pool(Path(config["source"]))
            if config["pool_sha256"] != pool_sha:
                raise batch.Hold("FROZEN_POOL_CHANGED_HOLD")
            summary = batch.inspected_records(folder, config, cases, pool_sha)
            sides = Counter()
            errors_by_side = {"a": Counter(), "b": Counter()}
            unknown_errors = Counter()
            ambiguous_cases = 0
            for position in range(1, summary["cases_reviewed"] + 1):
                record = json.loads(private.read_private(
                    folder / batch.receipt_name(position), batch.MAX_CASE_BYTES))
                # Receipt identity/contents were fully checked by inspected_records.
                present = {
                    item["reviewer_key"].removeprefix("ai-model-")
                    for item in record["reviews"]
                }
                if len(present) == 2:
                    sides["both_valid"] += 1
                elif len(present) == 1:
                    side = next(iter({"a", "b"} - present))
                    sides[f"only_{next(iter(present))}_valid"] += 1
                    if len(record["attempt_holds"]) != 1:
                        raise batch.Hold("ATTEMPT_SIDE_COUNT_HOLD")
                    errors_by_side[side].update(record["attempt_holds"])
                else:
                    sides["neither_valid"] += 1
                    ambiguous_cases += 1
                    unknown_errors.update(record["attempt_holds"])
            return {
                **safe,
                "status": "REVIEWER_FAILURE_SIDE_AUDIT_PASS__NO_REQUEST",
                "cases_reviewed": summary["cases_reviewed"],
                "validity": dict(sorted(sides.items())),
                "known_error_counts_by_side": {
                    side: dict(sorted(errors.items()))
                    for side, errors in errors_by_side.items()
                },
                "ambiguous_error_cases": ambiguous_cases,
                "unassigned_error_counts": dict(sorted(unknown_errors.items())),
            }
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    result = inspect(args.output_dir)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].endswith("PASS__NO_REQUEST") else 42


if __name__ == "__main__":
    raise SystemExit(main())

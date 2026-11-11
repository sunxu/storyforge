"""Owner-only: derive conservative Claude∩Codex PASS training candidates.

Only a create-only position manifest is produced; no quality admission, model
calls, database calls, or source text export. Original judgments remain frozen.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot
import r60_real1000_s1_compare_cpu as compare
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_double_pass_candidates_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_real1000_double_pass_candidates_private_v1"
OUTPUT_NAME = "R60_DOUBLE_PASS_TRAIN_CANDIDATES_PRIVATE.json"


class Hold(ValueError):
    pass


def select(rows: list[dict], *, comparison_sha256: str) -> tuple[dict, dict]:
    if (len(rows) != 20
            or len({r["pilot_position"] for r in rows}) != 20
            or {r["pilot_position"] for r in rows} != set(range(1, 21))):
        raise Hold("COMPARE_ROWS_HOLD")
    candidates = []
    counts = Counter()
    for row in rows:
        if (row["claude_review_kind"] == "VALID_ADVISORY"
                and row["claude_decision_raw"] == "PASS"
                and row["codex_decision"] == "PASS"
                and not any(row["claude_severe_flags"].values())
                and not any(row["codex_severe_flags"].values())
                and all(row["claude_scores"][key] >= minimum
                        and row["codex_scores"][key] >= minimum
                        for key, minimum in private.FLOORS.items())):
            candidates.append({"pilot_position": row["pilot_position"],
                               "status": "TRAIN_CANDIDATE__NOT_ADMITTED"})
            counts["DOUBLE_PASS"] += 1
        else:
            counts["NOT_DOUBLE_PASS"] += 1
    candidates.sort(key=lambda r: r["pilot_position"])
    manifest = {
        "schema": PRIVATE_SCHEMA,
        "status": "DOUBLE_PASS_TRAIN_CANDIDATES__NOT_ADMITTED",
        "comparison_sha256": comparison_sha256,
        "candidates": candidates,
        "historical_system_verified": False,
        "world_component_verified": False,
        "r50_exclusion_verified": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
    }
    safe = {
        "schema": SCHEMA,
        "status": "DOUBLE_PASS_CANDIDATES_READY__TRAIN_ADMISSION_HOLD",
        "cases_checked": len(rows),
        "double_pass_candidates": counts["DOUBLE_PASS"],
        "not_double_pass": counts["NOT_DOUBLE_PASS"],
        "training_context_checks_pending": True,
        "independent_owner_adjudications": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }
    return safe, manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--blind-dir", type=Path, required=True)
    p.add_argument("--owner-map-dir", type=Path, required=True)
    p.add_argument("--codex-result", type=Path, required=True)
    p.add_argument("--comparison-file", type=Path, required=True)
    p.add_argument("--private-report-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        safe_cmp, expected = compare.compare(
            args.sample_dir, args.review_dir, args.blind_dir,
            args.owner_map_dir, args.codex_result)
        if safe_cmp["cases"] != 20:
            raise Hold("COMPARE_GATE_HOLD")
        existing = json.loads(private.read_private(
            args.comparison_file, 150000))
        if existing != expected:
            raise Hold("FROZEN_COMPARISON_MISMATCH_HOLD")
        safe, manifest = select(
            expected["rows"],
            comparison_sha256=pilot.sha(pilot.canonical(expected)))
        if (args.private_report_dir.exists()
                or args.private_report_dir.is_symlink()):
            raise Hold("OUTPUT_EXISTS_HOLD")
        private.private_dir(args.private_report_dir, create=True)
        private.write_new(args.private_report_dir / OUTPUT_NAME,
                          pilot.canonical(manifest))
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - no private diagnostics printed
        reason = str(exc) if isinstance(exc, Hold) else "DOUBLE_PASS_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "DOUBLE_PASS_CANDIDATES_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0, "train_admitted": 0,
            "model_inference_calls": 0, "database_accessed": False,
            "gpu_job_started": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

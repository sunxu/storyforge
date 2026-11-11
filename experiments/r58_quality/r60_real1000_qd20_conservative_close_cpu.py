"""Read-only conservative closeout of an incomplete Qwen/DeepSeek Pilot20.

Incomplete reviews are NOT relabeled HOLD or PASS; their cases are excluded
from strict dual-PASS nomination. This is a policy-screen closeout, not a
completed model experiment or training admission. No network calls or writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import r60_real1000_qd20_compare_cpu as comparison
import r60_real1000_qwen_deepseek20_live as live
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_qd20_conservative_close_safe_v1"


class Hold(ValueError):
    pass


def closeout(analysis: dict, inspected: dict, diagnostics: dict) -> dict:
    if (analysis.get("cases") != 20 or inspected.get("cases") != 20
            or inspected.get("complete_provider_reviews", -1) not in range(41)
            or inspected.get("complete_two_provider_pairs", -1) not in range(21)
            or inspected.get("remaining_provider_reviews") !=
            40 - inspected["complete_provider_reviews"]
            or analysis.get("complete_new_pairs") !=
            inspected["complete_two_provider_pairs"]
            or analysis.get("new_qwen_deepseek_double_pass_in_complete_pairs") !=
            inspected.get("double_pass_on_completed_pairs")
            or analysis.get("old_and_new_review_sets_are_not_ground_truth") is not True
            or diagnostics.get("model_inference_calls_this_run") != 0):
        raise Hold("CLOSEOUT_INPUT_MISMATCH_HOLD")
    complete = analysis["complete_new_pairs"]
    return {
        "schema": SCHEMA,
        "status": "QD20_CONSERVATIVE_QUALITY_SCREEN_CLOSED__TRAIN_ADMISSION_HOLD",
        "cases_total": 20,
        "provider_reviews_saved": inspected["complete_provider_reviews"],
        "provider_reviews_unavailable": inspected["remaining_provider_reviews"],
        "cases_with_both_provider_reviews": complete,
        "cases_excluded_for_missing_provider_reviews": 20 - complete,
        "new_strict_double_pass_nominations": (
            analysis["new_qwen_deepseek_double_pass_in_complete_pairs"]),
        "old_claude_codex_double_pass": analysis["old_claude_codex_double_pass"],
        "nominations_in_both_model_pairs": (
            analysis["double_pass_intersection_on_complete_pairs"]),
        "new_only_double_pass_needs_evidence_check": (
            analysis["new_double_pass_not_old_double_pass"]),
        "old_only_double_pass_needs_evidence_check": (
            analysis["old_double_pass_but_new_not_double_pass_on_complete_pairs"]),
        "old_double_pass_missing_provider_reviews": (
            analysis["old_double_pass_missing_new_provider_review"]),
        "failed_response_snapshots": diagnostics["private_failed_model_snapshots"],
        "offline_replay_still_invalid": diagnostics[
            "offline_replay_outcomes"].get("STILL_INVALID_UNCHANGED", 0),
        "missing_reviews_imputed_as_hold": 0,
        "missing_reviews_imputed_as_pass": 0,
        "trial_claimed_complete": complete == 20,
        "quality_ground_truth_established": False,
        "training_context_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "model_inference_calls": 0,
        "private_values_emitted": False,
        "database_accessed": False,
        "gpu_job_started": False,
    }


def run(args: argparse.Namespace) -> dict:
    analysis = comparison.run(args)
    source, _packets, progress = live.load_input(args.review_dir)
    private.private_dir(args.live_dir, create=False)
    cfg = json.loads(private.read_private(args.live_dir / live.CONFIG_NAME, 12000))
    if (progress["processed"] != 20
            or cfg.get("packets_sha256") != source["packets_sha256"]):
        raise Hold("FROZEN_QD20_CONFIG_HOLD")
    inspected = live.inspect(args.live_dir, cfg)
    diagnostics = live.inspect_failure_snapshots(args.live_dir, cfg)
    return closeout(analysis, inspected, diagnostics)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--blind-dir", type=Path, required=True)
    parser.add_argument("--owner-map-dir", type=Path, required=True)
    parser.add_argument("--codex-result", type=Path, required=True)
    parser.add_argument("--live-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - no private errors or paths
        code = str(exc) if isinstance(exc, Hold) else "CLOSEOUT_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "QD20_CONSERVATIVE_CLOSEOUT_HOLD",
            "reason_code": code,
            "train_admitted": 0,
            "quality_v1_admitted": 0,
            "model_inference_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

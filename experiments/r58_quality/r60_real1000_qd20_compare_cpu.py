"""CPU-only Qwen/DeepSeek Pilot20 comparison with frozen Claude/Codex.

Reads Owner-private originals and the new immutable receipts. No API, GPU,
training admission or private identifiers in stdout. Partial pairs are allowed.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_qwen_deepseek20_live as live
import r60_real1000_s1_compare_cpu as s1
import r60_real1000_pilot20_local_review as pilot
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_qd20_compare_safe_v1"


class Hold(ValueError):
    pass


def compare_rows(old_rows: list[dict], new_receipts: dict) -> dict:
    if (len(old_rows) != 20
            or {r["pilot_position"] for r in old_rows} != set(range(1, 21))):
        raise Hold("OLD_COMPARE_ROWS_HOLD")
    old = {r["pilot_position"]: r for r in old_rows}
    both = []
    old_dual = set()
    new_dual = set()
    incomplete_old_pass = set()
    for p in range(1, 21):
        r = old[p]
        old_pass = (
            r["claude_review_kind"] == "VALID_ADVISORY"
            and r["claude_decision_raw"] == "PASS"
            and r["codex_decision"] == "PASS"
            and not any(r["claude_severe_flags"].values())
            and not any(r["codex_severe_flags"].values())
            and all(r["claude_scores"][key] >= floor
                    and r["codex_scores"][key] >= floor
                    for key, floor in private.FLOORS.items())
        )
        if old_pass:
            old_dual.add(p)
        if not all((p, k) in new_receipts for k in live.MODELS):
            if old_pass:
                incomplete_old_pass.add(p)
            continue
        q = new_receipts[(p, "qwen")]["result"]
        d = new_receipts[(p, "deepseek")]["result"]
        new_pass = q["decision"] == d["decision"] == "PASS"
        both.append(p)
        if new_pass:
            new_dual.add(p)
    return {
        "schema": SCHEMA,
        "status": ("QD20_OLD_NEW_COMPARE_COMPLETE__REFERENCE_NOT_GROUND_TRUTH"
                   if len(both) == 20 else
                   "QD20_OLD_NEW_COMPARE_PARTIAL__MISSING_PROVIDER_REVIEWS"),
        "cases": 20,
        "complete_new_pairs": len(both),
        "old_claude_codex_double_pass": len(old_dual),
        "new_qwen_deepseek_double_pass_in_complete_pairs": len(new_dual),
        "double_pass_intersection_on_complete_pairs": len(old_dual & new_dual),
        "new_double_pass_not_old_double_pass": len(new_dual - old_dual),
        "old_double_pass_but_new_not_double_pass_on_complete_pairs":
            len((old_dual & set(both)) - new_dual),
        "old_double_pass_missing_new_provider_review":
            len(incomplete_old_pass),
        "old_and_new_review_sets_are_not_ground_truth": True,
        "model_inference_calls": 0,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "private_values_emitted": False,
        "database_accessed": False,
        "gpu_job_started": False,
    }


def run(args: argparse.Namespace) -> dict:
    safe, expected = s1.compare(
        args.sample_dir, args.review_dir, args.blind_dir,
        args.owner_map_dir, args.codex_result)
    if safe["cases"] != 20:
        raise Hold("S1_SOURCE_HOLD")
    private.private_dir(args.live_dir, create=False)
    raw_cfg = json.loads(private.read_private(args.live_dir / live.CONFIG_NAME, 12000))
    source_cfg, _packets, progress = live.load_input(args.review_dir)
    if (progress["processed"] != 20
            or raw_cfg["packets_sha256"] != source_cfg["packets_sha256"]):
        raise Hold("QD20_FROZEN_SOURCE_HOLD")
    receipts, _ = live.read_receipts(args.live_dir, raw_cfg)
    return compare_rows(expected["rows"], receipts)


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
    except Exception as exc:  # noqa: BLE001 - private material never in logs
        reason = str(exc) if isinstance(exc, Hold) else "QD20_COMPARE_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "QD20_COMPARE_HOLD",
            "reason_code": reason, "train_admitted": 0,
            "quality_v1_admitted": 0, "private_values_emitted": False,
            "model_inference_calls": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

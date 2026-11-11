"""Owner-private evidence packet for the three QD20 vs Claude/Codex double-PASS disagreements.

Reuses frozen source crosswalk and immutable model receipts; writes create-only
private text for evidence-based review, not a new model vote or admission.
Only aggregate counts ever reach stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot
import r60_real1000_qd20_compare_cpu as compare
import r60_real1000_qwen_deepseek20_live as live
import r60_real1000_s1_compare_cpu as s1
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_qd20_disagreement_packet_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_real1000_qd20_disagreement_packet_private_v1"
OUTPUT_NAME = "R60_QD20_DISAGREEMENT_EVIDENCE_PRIVATE.json"


class Hold(ValueError):
    pass


def prepare(old_rows: list[dict], receipts: dict,
            packets: list[dict], packet_sha: str) -> tuple[dict, dict]:
    report = compare.compare_rows(old_rows, receipts)
    if (len(packets) != 20 or
            len(old_rows) != 20 or
            len(receipts) < 1):
        raise Hold("DISAGREEMENT_INPUT_HOLD")
    old = {r["pilot_position"]: r for r in old_rows}
    old_passes = set()
    new_passes = set()
    for pos in range(1, 21):
        r = old[pos]
        old_pass = (
            r["claude_review_kind"] == "VALID_ADVISORY"
            and r["claude_decision_raw"] == "PASS"
            and r["codex_decision"] == "PASS"
            and all(r["claude_scores"][k] >= minimum and
                    r["codex_scores"][k] >= minimum
                    for k, minimum in private.FLOORS.items())
            and not any(r["claude_severe_flags"].values())
            and not any(r["codex_severe_flags"].values())
        )
        if old_pass:
            old_passes.add(pos)
        if (pos, "qwen") in receipts and (pos, "deepseek") in receipts:
            if (receipts[(pos, "qwen")]["result"]["decision"] == "PASS"
                    and receipts[(pos, "deepseek")]["result"]["decision"] == "PASS"):
                new_passes.add(pos)
    disagreements = sorted(old_passes ^ new_passes)
    cases = []
    for pos in disagreements:
        packet = packets[pos - 1]
        if packet.get("pilot_position") != pos:
            raise Hold("PILOT_POSITION_HOLD")
        r = old[pos]
        cases.append({
            "pilot_position": pos,
            "category": ("NEW_ONLY_DOUBLE_PASS"
                         if pos in new_passes else "OLD_ONLY_DOUBLE_PASS"),
            "prior_messages": packet["history_messages"],
            "assistant_target": packet["assistant_target"],
            "target_char_bin": packet["target_char_bin"],
            "old_claude_codex": {
                "claude_review_kind": r["claude_review_kind"],
                "claude_decision": r["claude_decision_raw"],
                "codex_decision": r["codex_decision"],
                "claude_scores": r["claude_scores"],
                "codex_scores": r["codex_scores"],
                "claude_severe_flags": r["claude_severe_flags"],
                "codex_severe_flags": r["codex_severe_flags"],
            },
            "new_qwen_deepseek": {
                m: receipts[(pos, m)]["result"] for m in live.MODELS
            },
            "owner_evidence_decision": "NOT_REVIEWED",
            "train_admitted": False,
        })
    if len(cases) != (report["new_double_pass_not_old_double_pass"] +
                      report["old_double_pass_but_new_not_double_pass_on_complete_pairs"]):
        raise Hold("DISAGREEMENT_COUNT_HOLD")
    by_type = Counter(x["category"] for x in cases)
    manifest = {
        "schema": PRIVATE_SCHEMA,
        "status": "DISAGREEMENT_EVIDENCE_FOR_OWNER__NO_ADJUDICATION",
        "packets_sha256": packet_sha,
        "cases": cases,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
    }
    safe = {
        "schema": SCHEMA,
        "status": "QD20_DISAGREEMENT_PACKET_READY__OWNER_EVIDENCE_PENDING",
        "cases_for_evidence_review": len(cases),
        "new_only_double_pass": by_type["NEW_ONLY_DOUBLE_PASS"],
        "old_only_double_pass": by_type["OLD_ONLY_DOUBLE_PASS"],
        "new_review_pairs_complete": report["complete_new_pairs"],
        "model_inference_calls": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "private_values_emitted": False,
        "database_accessed": False,
        "gpu_job_started": False,
    }
    return safe, manifest


def run(args: argparse.Namespace) -> dict:
    old_safe, old_private = s1.compare(
        args.sample_dir, args.review_dir, args.blind_dir,
        args.owner_map_dir, args.codex_result)
    if old_safe["cases"] != 20:
        raise Hold("OLD_SOURCE_HOLD")
    cfg, packets, progress = live.load_input(args.review_dir)
    private.private_dir(args.live_dir, create=False)
    config = json.loads(private.read_private(args.live_dir / live.CONFIG_NAME, 12000))
    if (progress["processed"] != 20
            or config["packets_sha256"] != cfg["packets_sha256"]):
        raise Hold("NEW_SOURCE_HOLD")
    receipts, _counts = live.read_receipts(args.live_dir, config)
    safe, manifest = prepare(
        old_private["rows"], receipts, packets["packets"],
        config["packets_sha256"])
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    private.private_dir(args.output_dir, create=True)
    private.write_new(args.output_dir / OUTPUT_NAME, pilot.canonical(manifest))
    return safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--blind-dir", type=Path, required=True)
    parser.add_argument("--owner-map-dir", type=Path, required=True)
    parser.add_argument("--codex-result", type=Path, required=True)
    parser.add_argument("--live-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never print private sources
        code = str(exc) if isinstance(exc, Hold) else "DISAGREEMENT_PACKET_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "QD20_DISAGREEMENT_PACKET_HOLD",
            "reason_code": code, "model_inference_calls": 0,
            "private_values_emitted": False,
            "quality_v1_admitted": 0, "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

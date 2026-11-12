"""Prepare/verify private blind reviews of exactly two QD20 common dual-PASS cases.

Strictly reuse frozen Pilot20, S1 Claude/Codex and immutable Qwen/DeepSeek
receipts. Blind output does not contain provider votes or original positions.
CPU-only; no inference, training, database access, or source modifications.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot
import r60_real1000_qd20_compare_cpu as compare
import r60_real1000_qd20_evidence_review_cpu as review
import r60_real1000_qwen_deepseek20_live as live
import r60_real1000_s1_compare_cpu as s1
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_qd20_common_pass_blind_safe_v1"
BLIND_SCHEMA = "storyforge_r60_qd20_common_pass_blind_private_v1"
DECISION_SCHEMA = "storyforge_r60_qd20_common_pass_decisions_private_v1"
BLIND_NAME = "R60_QD20_COMMON2_BLIND_PRIVATE.json"
TEMPLATE_NAME = "R60_QD20_COMMON2_DECISIONS_TEMPLATE_PRIVATE.json"
DECISION_NAME = "R60_QD20_COMMON2_DECISIONS_PRIVATE.json"


class Hold(ValueError):
    pass


def extract(old_rows: list[dict], receipts: dict, packets: list[dict],
            source_sha: str) -> tuple[dict, dict]:
    stats = compare.compare_rows(old_rows, receipts)
    if (len(packets) != 20
            or stats["double_pass_intersection_on_complete_pairs"] != 2
            or stats["complete_new_pairs"] != 14):
        raise Hold("COMMON2_FROZEN_COUNTS_HOLD")
    old = {r["pilot_position"]: r for r in old_rows}
    selected = []
    for pos in range(1, 21):
        row = old[pos]
        old_pass = (
            row["claude_review_kind"] == "VALID_ADVISORY"
            and row["claude_decision_raw"] == "PASS"
            and row["codex_decision"] == "PASS"
            and not any(row["claude_severe_flags"].values())
            and not any(row["codex_severe_flags"].values())
            and all(row["claude_scores"][k] >= floor
                    and row["codex_scores"][k] >= floor
                    for k, floor in private.FLOORS.items())
        )
        new_pass = (
            all((pos, m) in receipts for m in live.MODELS)
            and all(receipts[(pos, m)]["result"]["decision"] == "PASS"
                    for m in live.MODELS)
        )
        if old_pass and new_pass:
            packet = packets[pos - 1]
            if packet["pilot_position"] != pos:
                raise Hold("PACKET_ORDER_HOLD")
            history = packet["history_messages"]
            if (len(history) != 3 or
                    [m.get("role") for m in history]
                    != ["user", "assistant", "user"]):
                raise Hold("THREE_MESSAGES_HOLD")
            selected.append({
                "blind_index": len(selected) + 1,
                "history_messages": history,
                "assistant_target": packet["assistant_target"],
            })
    if len(selected) != 2:
        raise Hold("COMMON2_SELECTION_HOLD")
    blind = {
        "schema": BLIND_SCHEMA,
        "status": "COMMON2_BLIND_NO_MODEL_VOTES",
        "frozen_source_sha256": source_sha,
        "cases": selected,
    }
    template = {
        "schema": DECISION_SCHEMA,
        "blind_sha256": pilot.sha(pilot.canonical(blind)),
        "reviewer_independent_of_model_votes": False,
        "cases": [{
            "blind_index": i,
            "decision": "EVIDENCE_REVIEW_NOT_STARTED",
            "scores": {},
            "severe_flags": {},
            "quote_source": "",
            "exact_quote": "",
            "reason_cn": "",
        } for i in (1, 2)],
        "train_admitted": 0,
    }
    return blind, template


def validate(blind: dict, result: dict) -> dict:
    cases = blind.get("cases")
    if (blind.get("schema") != BLIND_SCHEMA or
            blind.get("status") != "COMMON2_BLIND_NO_MODEL_VOTES" or
            not isinstance(cases, list) or len(cases) != 2 or
            [x.get("blind_index") for x in cases] != [1, 2] or
            result.get("schema") != DECISION_SCHEMA or
            result.get("blind_sha256") != pilot.sha(pilot.canonical(blind)) or
            result.get("reviewer_independent_of_model_votes") is not True or
            result.get("train_admitted") != 0 or
            not isinstance(result.get("cases"), list) or
            len(result["cases"]) != 2 or
            {x.get("blind_index") for x in result["cases"]} != {1, 2}):
        raise Hold("COMMON2_REVIEW_BINDING_HOLD")
    counts = Counter()
    for decision in result["cases"]:
        if (set(decision) != {"blind_index", "decision", "scores",
                             "severe_flags", "quote_source", "exact_quote",
                             "reason_cn"} or
                decision["decision"] not in review.DECISIONS or
                not isinstance(decision["scores"], dict) or
                set(decision["scores"]) != set(private.FLOORS) or
                any(type(v) is not int or not 1 <= v <= 5
                    for v in decision["scores"].values()) or
                not isinstance(decision["severe_flags"], dict) or
                set(decision["severe_flags"]) != set(private.SEVERE) or
                any(type(v) is not bool
                    for v in decision["severe_flags"].values()) or
                not isinstance(decision["reason_cn"], str) or
                not 10 <= len(decision["reason_cn"]) <= 1200 or
                not isinstance(decision["exact_quote"], str) or
                not 4 <= len(decision["exact_quote"]) <= 300):
            raise Hold("COMMON2_REVIEW_ROW_HOLD")
        case = cases[decision["blind_index"] - 1]
        texts = {
            "assistant_target": case["assistant_target"],
            "history_user_1": case["history_messages"][0]["content"],
            "history_assistant_2": case["history_messages"][1]["content"],
            "history_user_3": case["history_messages"][2]["content"],
        }
        if (decision["quote_source"] not in texts or
                decision["exact_quote"] not in texts[decision["quote_source"]]):
            raise Hold("COMMON2_NONEXACT_QUOTE_HOLD")
        severe = any(decision["severe_flags"].values())
        if decision["decision"] == "PASS" and (
                severe or any(
                    decision["scores"][k] < floor
                    for k, floor in private.FLOORS.items())):
            raise Hold("COMMON2_PASS_BELOW_FLOOR_HOLD")
        if severe and decision["decision"] != "REJECT":
            raise Hold("COMMON2_SEVERE_DECISION_HOLD")
        counts[decision["decision"]] += 1
    return {
        "schema": SCHEMA,
        "status": "QD20_COMMON2_BLIND_REVIEW_VALIDATED__NOT_GROUND_TRUTH",
        "cases_reviewed": 2,
        "review_decisions": {d: counts[d] for d in review.DECISIONS},
        "exact_quote_evidence_cases": 2,
        "reviewer_independence_self_attested_not_proven": True,
        "quality_ground_truth_established": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "private_values_emitted": False,
        "database_accessed": False,
        "gpu_job_started": False,
    }


def frozen_input(args: argparse.Namespace) -> tuple[dict, dict]:
    s1_report, s1_data = s1.compare(
        args.sample_dir, args.review_dir, args.s1_blind_dir,
        args.owner_map_dir, args.codex_result)
    if s1_report["cases"] != 20:
        raise Hold("S1_SOURCE_HOLD")
    source, packets, progress = live.load_input(args.review_dir)
    private.private_dir(args.live_dir, create=False)
    cfg = json.loads(private.read_private(
        args.live_dir / live.CONFIG_NAME, 12000))
    if (progress["processed"] != 20 or
            cfg["packets_sha256"] != source["packets_sha256"]):
        raise Hold("QD20_SOURCE_HOLD")
    receipts, _ = live.read_receipts(args.live_dir, cfg)
    return extract(s1_data["rows"], receipts, packets["packets"],
                   cfg["packets_sha256"])


def run(args: argparse.Namespace) -> dict:
    blind, template = frozen_input(args)
    if args.command == "prepare":
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise Hold("OUTPUT_EXISTS_HOLD")
        private.private_dir(args.output_dir, create=True)
        private.write_new(args.output_dir / BLIND_NAME, pilot.canonical(blind))
        private.write_new(args.output_dir / TEMPLATE_NAME,
                          pilot.canonical(template))
        return {
            "schema": SCHEMA,
            "status": "QD20_COMMON2_BLIND_PACKET_READY__REVIEW_PENDING",
            "blind_cases": 2,
            "model_votes_in_blind_packet": 0,
            "train_admitted": 0,
            "quality_v1_admitted": 0,
            "model_inference_calls": 0,
            "private_values_emitted": False,
        }
    private.private_dir(args.output_dir, create=False)
    stored = json.loads(private.read_private(
        args.output_dir / BLIND_NAME, 200000))
    if stored != blind:
        raise Hold("COMMON2_BLIND_TAMPERING_HOLD")
    if args.decisions is None:
        raise Hold("DECISIONS_REQUIRED_HOLD")
    decisions = json.loads(private.read_private(args.decisions, 200000))
    return validate(stored, decisions)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--sample-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--s1-blind-dir", type=Path, required=True)
    parser.add_argument("--owner-map-dir", type=Path, required=True)
    parser.add_argument("--codex-result", type=Path, required=True)
    parser.add_argument("--live-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - private errors must be redacted
        code = str(exc) if isinstance(exc, Hold) else "COMMON2_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "QD20_COMMON2_BLIND_HOLD",
            "reason_code": code, "quality_v1_admitted": 0,
            "train_admitted": 0, "model_inference_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

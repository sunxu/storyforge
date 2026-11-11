"""Prepare and validate blind, Owner-private evidence checks for QD20 disagreements.

Two-stage CPU-only workflow. A separate reviewer reads the blind 3-case pack
WITHOUT any old/new model decisions. Its judgments are validated against
verbatim snippets, not inferred from model votes. No external model calls.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot
import r60_real1000_qd20_disagreement_packet_cpu as evidence
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_qd20_evidence_review_safe_v1"
BLIND_SCHEMA = "storyforge_r60_qd20_evidence_blind_private_v1"
DECISION_SCHEMA = "storyforge_r60_qd20_evidence_decisions_private_v1"
PACK_NAME = "R60_QD20_DISAGREEMENT_BLIND_PRIVATE.json"
DECISION_NAME = "R60_QD20_DISAGREEMENT_DECISIONS_PRIVATE.json"
TEMPLATE_NAME = "R60_QD20_DISAGREEMENT_DECISIONS_TEMPLATE_PRIVATE.json"
STATUS_UNREVIEWED = "EVIDENCE_REVIEW_NOT_STARTED"
DIMENSIONS = tuple(private.FLOORS)
DECISIONS = ("PASS", "HOLD", "REJECT")


class Hold(ValueError):
    pass


def source_cases(source: dict) -> list[dict]:
    if (source.get("schema") != evidence.PRIVATE_SCHEMA
            or source.get("status") !=
            "DISAGREEMENT_EVIDENCE_FOR_OWNER__NO_ADJUDICATION"
            or source.get("train_admitted") != 0
            or not isinstance(source.get("cases"), list)
            or len(source["cases"]) != 3
            or len({x["pilot_position"] for x in source["cases"]}) != 3
            or Counter(x["category"] for x in source["cases"])
            != {"NEW_ONLY_DOUBLE_PASS": 2, "OLD_ONLY_DOUBLE_PASS": 1}):
        raise Hold("SOURCE_PACKET_HOLD")
    for row in source["cases"]:
        if (row.get("owner_evidence_decision") != "NOT_REVIEWED"
                or row.get("train_admitted") is not False
                or not isinstance(row.get("assistant_target"), str)
                or not row["assistant_target"]
                or not isinstance(row.get("prior_messages"), list)
                or len(row["prior_messages"]) != 3
                or [x.get("role") for x in row["prior_messages"]]
                != ["user", "assistant", "user"]):
            raise Hold("SOURCE_ROW_HOLD")
    return source["cases"]


def prepare(source: dict) -> tuple[dict, dict]:
    rows = source_cases(source)
    blind = {
        "schema": BLIND_SCHEMA,
        "status": "QD20_BLIND_EVIDENCE__NO_MODEL_VOTES_SHOWN",
        "source_packet_sha256": pilot.sha(pilot.canonical(source)),
        "cases": [{
            "blind_index": i,
            "history_messages": row["prior_messages"],
            "assistant_target": row["assistant_target"],
            "review_questions": [
                "目标回复是否存在严重玩家代行动、代发言或违背玩家选择？",
                "角色身份、已出现事实或明确规则是否自相矛盾？",
                "中文叙事、NPC主动性、连续性是否达到原Rubric下限？",
                ("给出可从当前三消息及目标回复逐字定位的证据；"
                 "无法从局部上下文核验的世界规则必须HOLD"),
            ],
        } for i, row in enumerate(rows, 1)],
    }
    template = {
        "schema": DECISION_SCHEMA,
        "source_packet_sha256": blind["source_packet_sha256"],
        "reviewer_independent_of_model_votes": False,
        "cases": [{
            "blind_index": i,
            "decision": STATUS_UNREVIEWED,
            "scores": {},
            "severe_flags": {},
            "quote_source": "",
            "exact_quote": "",
            "reason_cn": "",
        } for i in range(1, 4)],
        "train_admitted": 0,
    }
    return blind, template


def verify(source: dict, blind: dict, result: dict) -> dict:
    rows = source_cases(source)
    correct_blind, _ = prepare(source)
    if (blind != correct_blind or
            result.get("schema") != DECISION_SCHEMA or
            result.get("source_packet_sha256") !=
            correct_blind["source_packet_sha256"] or
            result.get("reviewer_independent_of_model_votes") is not True or
            result.get("train_admitted") != 0 or
            not isinstance(result.get("cases"), list) or
            len(result["cases"]) != 3 or
            {x.get("blind_index") for x in result["cases"]} != {1, 2, 3}):
        raise Hold("BLIND_OR_REVIEW_CONTRACT_HOLD")
    counts = Counter()
    reasons = Counter()
    for item in result["cases"]:
        if (set(item) != {"blind_index", "decision", "scores",
                          "severe_flags", "quote_source", "exact_quote",
                          "reason_cn"} or
                item["decision"] not in DECISIONS or
                not isinstance(item["scores"], dict) or
                set(item["scores"]) != set(DIMENSIONS) or
                any(type(item["scores"][k]) is not int
                    or not 1 <= item["scores"][k] <= 5
                    for k in DIMENSIONS) or
                not isinstance(item["severe_flags"], dict) or
                set(item["severe_flags"]) != set(private.SEVERE) or
                any(type(item["severe_flags"][k]) is not bool
                    for k in private.SEVERE) or
                not isinstance(item["exact_quote"], str)
                or not 4 <= len(item["exact_quote"]) <= 300 or
                not isinstance(item["reason_cn"], str)
                or not 10 <= len(item["reason_cn"]) <= 1200):
            raise Hold("REVIEW_ROW_CONTRACT_HOLD")
        row = rows[item["blind_index"] - 1]
        texts = {
            "assistant_target": row["assistant_target"],
            "history_user_1": row["prior_messages"][0]["content"],
            "history_assistant_2": row["prior_messages"][1]["content"],
            "history_user_3": row["prior_messages"][2]["content"],
        }
        if (item["quote_source"] not in texts or
                item["exact_quote"] not in texts[item["quote_source"]]):
            raise Hold("REVIEW_NONEXACT_QUOTE_HOLD")
        flags = item["severe_flags"]
        scores = item["scores"]
        if (item["decision"] == "PASS" and
                (any(flags.values()) or any(
                    scores[k] < private.FLOORS[k] for k in DIMENSIONS))):
            raise Hold("PASS_CONTRACT_CONFLICT_HOLD")
        if (any(flags.values()) and item["decision"] != "REJECT"):
            raise Hold("SEVERE_FLAG_DECISION_CONFLICT_HOLD")
        counts[item["decision"]] += 1
        reasons["WITH_VERBATIM_EVIDENCE"] += 1
    return {
        "schema": SCHEMA,
        "status": "QD20_THREE_BLIND_EVIDENCE_REVIEWS_VALIDATED__ADMISSION_HOLD",
        "evidence_cases": len(rows),
        "review_decisions": {k: counts[k] for k in DECISIONS},
        "exact_quote_evidence_cases": reasons["WITH_VERBATIM_EVIDENCE"],
        "reviewer_independence_self_attested_not_proven": True,
        "quality_ground_truth_established": False,
        "r50_complete_exclusion_verified": False,
        "training_context_verified": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_inference_calls_by_this_script": 0,
        "private_values_emitted": False,
        "database_accessed": False,
        "gpu_job_started": False,
    }


def load_source(directory: Path) -> dict:
    private.private_dir(directory, create=False)
    return json.loads(private.read_private(
        directory / evidence.OUTPUT_NAME, 200000))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--blind-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path)
    args = parser.parse_args()
    try:
        source = load_source(args.source_dir)
        if args.command == "prepare":
            if args.blind_dir.exists() or args.blind_dir.is_symlink():
                raise Hold("BLIND_OUTPUT_ALREADY_EXISTS_HOLD")
            blind, template = prepare(source)
            private.private_dir(args.blind_dir, create=True)
            private.write_new(args.blind_dir / PACK_NAME, pilot.canonical(blind))
            private.write_new(args.blind_dir / TEMPLATE_NAME,
                              pilot.canonical(template))
            result = {
                "schema": SCHEMA,
                "status": "QD20_THREE_BLIND_PACKETS_READY__REVIEW_PENDING",
                "blind_cases": 3,
                "model_votes_in_blind_packet": 0,
            }
        else:
            if args.decisions is None:
                raise Hold("DECISIONS_PATH_REQUIRED_HOLD")
            private.private_dir(args.blind_dir, create=False)
            blind = json.loads(private.read_private(
                args.blind_dir / PACK_NAME, 200000))
            decisions = json.loads(private.read_private(
                args.decisions, 200000))
            result = verify(source, blind, decisions)
        result.update({
            "quality_v1_admitted": 0, "train_admitted": 0,
            "private_values_emitted": False,
            "model_inference_calls_by_this_script": 0,
        })
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - do not reveal private data
        code = str(exc) if isinstance(exc, Hold) else "BLIND_EVIDENCE_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "QD20_BLIND_EVIDENCE_HOLD",
            "reason_code": code,
            "quality_v1_admitted": 0, "train_admitted": 0,
            "private_values_emitted": False,
            "model_inference_calls_by_this_script": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

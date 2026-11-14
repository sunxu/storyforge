"""StoryForge R60 V2 selective, create-only missing-side reviewer replay.

Only SINGLE_PASS_REPAIR_FIRST slots. Owner Mac private, frozen V1 and plan
verified before each batch. Never changes V1, source, rubric, DB or Gold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_v1_repair_plan as planner
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_real1000_v2_priority_replay_private_v1"
SAFE = "storyforge_r60_real1000_v2_priority_replay_safe_v1"
CONFIG = "R60_V2_PRIORITY_REPLAY_CONFIG_PRIVATE.json"
PREFIX = "R60_V2_REPLAY_"
PLAN_PRIORITY = "SINGLE_PASS_REPAIR_FIRST"
MAX_CONFIG = 16000
MAX_RECEIPT = 24000
MAX_BATCH = 25
SUSPEND = {
    "MODEL_HTTP_401_HOLD", "MODEL_HTTP_403_HOLD", "MODEL_HTTP_429_HOLD",
    "MODEL_HTTP_500_HOLD", "MODEL_HTTP_502_HOLD", "MODEL_HTTP_503_HOLD",
    "MODEL_HTTP_504_HOLD", "MODEL_TRANSPORT_HOLD",
}
TECHNICAL = (
    ai.SAFE_HTTP_HOLDS
    | {"MODEL_JSON_INVALID", "MODEL_REPLY_OVERSIZE", "MODEL_PROTOCOL_HOLD",
       "QUALITY_FLOOR_DECISION_INCONSISTENT",
       "SEVERE_FLAG_DECISION_INCONSISTENT"}
) - SUSPEND


class Hold(ValueError):
    pass


def receipt_name(index: int) -> str:
    return f"{PREFIX}{index:04d}_PRIVATE.json"


def _plan_state(old_dir: Path, plan_dir: Path) -> tuple[dict, list[dict], list[dict], bytes]:
    private.private_dir(old_dir, create=False)
    private.private_dir(plan_dir, create=False)
    with batch.expand.locked(old_dir):
        cfg = batch.validate_config(old_dir)
        cases, sha = batch.frozen_pool(Path(cfg["source"]))
        if sha != cfg["pool_sha256"]:
            raise Hold("FROZEN_SOURCE_CHANGED_HOLD")
        summary = batch.inspected_records(old_dir, cfg, cases, sha)
        if summary["cases_reviewed"] != 1000:
            raise Hold("V1_NOT_COMPLETE_HOLD")
        v1 = [
            json.loads(private.read_private(
                old_dir / batch.receipt_name(i), batch.MAX_CASE_BYTES))
            for i in range(1, 1001)
        ]
        expected = planner.build(cases, v1, sha)
        raw = private.read_private(plan_dir / planner.NAME,
                                   planner.MAX_PLAN_BYTES)
        plan = json.loads(raw)
        if plan != expected:
            raise Hold("PLAN_OR_V1_CHANGED_HOLD")
        if plan["priorities"].get(PLAN_PRIORITY, 0) != sum(
            row["priority"] == PLAN_PRIORITY for row in plan["entries"]
        ):
            raise Hold("PLAN_PRIORITY_COUNT_HOLD")
        selected = [row for row in plan["entries"]
                    if row["priority"] == PLAN_PRIORITY]
        if any(len(row["missing_slots"]) != 1 for row in selected):
            raise Hold("PLAN_MISSING_SIDE_HOLD")
        return cfg, cases, selected, raw


def _config_payload(old_dir: Path, plan_dir: Path, source_sha: str,
                    plan_raw: bytes, selected: list[dict]) -> dict:
    return {
        "schema": SCHEMA, "old_dir": str(old_dir),
        "plan_dir": str(plan_dir), "pool_sha256": source_sha,
        "plan_file_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "selected_count": len(selected),
        "priority": PLAN_PRIORITY,
    }


def _inspect(directory: Path, old_dir: Path, plan_dir: Path) -> tuple[dict, list[dict], list[dict], dict]:
    private.private_dir(directory, create=False)
    if directory in (old_dir, plan_dir):
        raise Hold("OUTPUT_ALIAS_HOLD")
    old, cases, selected, raw = _plan_state(old_dir, plan_dir)
    cfg = json.loads(private.read_private(directory / CONFIG, MAX_CONFIG))
    expected = _config_payload(old_dir, plan_dir, old["pool_sha256"], raw, selected)
    if cfg != expected:
        raise Hold("V2_CONFIG_OR_PLAN_CHANGED_HOLD")
    rows = sorted(path for path in directory.glob(PREFIX + "*_PRIVATE.json")
                  if path.name != CONFIG)
    if len(rows) > len(selected):
        raise Hold("V2_OVERFLOW_HOLD")
    counts = Counter()
    for i, path in enumerate(rows, 1):
        if path.name != receipt_name(i):
            raise Hold("V2_SEQUENCE_HOLD")
        row = json.loads(private.read_private(path, MAX_RECEIPT))
        item = selected[i - 1]
        source = cases[item["position"] - 1]
        side = item["missing_slots"][0]["side"]
        if (not isinstance(row, dict)
                or row.get("schema") != SCHEMA
                or row.get("ordinal") != i
                or row.get("position") != item["position"]
                or row.get("case_key") != source["case_key"]
                or row.get("history_messages_sha256") !=
                source["history_messages_sha256"]
                or row.get("assistant_target_sha256") !=
                source["assistant_target_sha256"]
                or row.get("v1_receipt_sha256") != item["original_receipt_sha256"]
                or row.get("side") != side):
            raise Hold("V2_CASE_BINDING_HOLD")
        model = old["model_" + side]
        if row.get("model_id") != model:
            raise Hold("V2_MODEL_BINDING_HOLD")
        signed = {key: value for key, value in row.items()
                  if key != "receipt_sha256"}
        if row.get("receipt_sha256") != private.digest(signed):
            raise Hold("V2_RECEIPT_SIGNATURE_HOLD")
        result = row.get("result")
        if row.get("status") == "TECHNICAL_HOLD":
            if result is not None or row.get("reason_code") not in TECHNICAL:
                raise Hold("V2_TECHNICAL_FORMAT_HOLD")
        else:
            if row.get("reason_code") is not None:
                raise Hold("V2_REASON_FORMAT_HOLD")
            valid = ai.parse_model_response(result)
            if row.get("status") != "V2_" + valid["decision"]:
                raise Hold("V2_QUALITY_FORMAT_HOLD")
        counts[row["status"]] += 1
    summary = {
        "schema": SAFE,
        "status": ("V2_PRIORITY_REPLAY_COMPLETE__NO_ADMISSION"
                   if len(rows) == len(selected)
                   else "V2_PRIORITY_REPLAY_IN_PROGRESS__NO_ADMISSION"),
        "original_cases_preserved": 1000,
        "priority": PLAN_PRIORITY,
        "planned_slots": len(selected),
        "reviewed_slots": len(rows),
        "remaining_slots": len(selected) - len(rows),
        "result_counts": dict(sorted(counts.items())),
        "train_admitted": 0, "quality_v1_admitted": 0,
        "gpu_started": False, "database_modified": False,
        "private_values_emitted": False,
        "model_requests": 0,
    }
    return old, cases, selected, summary


def initialize(directory: Path, old_dir: Path, plan_dir: Path) -> dict:
    if (directory.exists() or directory.is_symlink()
            or directory.parent != private.BASE
            or not directory.name.startswith("r60-real1000-v2-priority-replay-")
            or directory in (old_dir, plan_dir)):
        raise Hold("V2_OUTPUT_PATH_HOLD")
    old, _cases, selected, raw = _plan_state(old_dir, plan_dir)
    private.private_dir(directory, create=True)
    payload = _config_payload(
        old_dir, plan_dir, old["pool_sha256"], raw, selected)
    private.write_new(directory / CONFIG,
                      (json.dumps(payload, sort_keys=True) + "\n").encode())
    return _inspect(directory, old_dir, plan_dir)[3]


def inspect(directory: Path, old_dir: Path, plan_dir: Path) -> dict:
    with batch.expand.locked(directory):
        return _inspect(directory, old_dir, plan_dir)[3]


def advance(directory: Path, old_dir: Path, plan_dir: Path, count: int,
            *, execute: bool, allow_private_data_egress: bool) -> dict:
    if not execute or not allow_private_data_egress:
        raise Hold("V2_EXPLICIT_EXECUTION_REQUIRED")
    if type(count) is not int or not 1 <= count <= MAX_BATCH:
        raise Hold("V2_BATCH_SIZE_HOLD")
    with batch.expand.locked(directory):
        old, cases, selected, progress = _inspect(
            directory, old_dir, plan_dir)
        start = progress["reviewed_slots"]
        for index in range(start, min(start + count, len(selected))):
            item = selected[index]
            pos = item["position"]
            case = cases[pos - 1]
            side = item["missing_slots"][0]["side"]
            model = old["model_" + side]
            profile = old["protocol_" + side]
            key_env = "DASHSCOPE_API_KEY" if side == "a" else "DEEPSEEK_API_KEY"
            key = os.environ.get(key_env, "")
            if not key:
                raise Hold("V2_REVIEWER_KEY_MISSING_HOLD")
            answer = None
            reason = None
            try:
                answer = ai.model_request(
                    old["endpoint_" + side], model, key,
                    ai.prompt_for_case(case), old["timeout"],
                    old["json_mode"], protocol=profile,
                )
            except ai.Hold as exc:
                reason = str(exc)
                if reason in SUSPEND:
                    raise Hold("V2_REVIEWER_SERVICE_UNAVAILABLE_HOLD") from exc
                if reason not in TECHNICAL:
                    raise Hold("V2_UNEXPECTED_REVIEW_ERROR_HOLD") from exc
            row = {
                "schema": SCHEMA, "ordinal": index + 1, "position": pos,
                "case_key": case["case_key"],
                "history_messages_sha256": case["history_messages_sha256"],
                "assistant_target_sha256": case["assistant_target_sha256"],
                "v1_receipt_sha256": item["original_receipt_sha256"],
                "side": side, "model_id": model,
                "status": ("TECHNICAL_HOLD" if reason else
                           "V2_" + answer["decision"]),
                "reason_code": reason, "result": answer,
            }
            row["receipt_sha256"] = private.digest(row)
            blob = (json.dumps(row, ensure_ascii=False, sort_keys=True)
                    + "\n").encode("utf-8")
            if len(blob) > MAX_RECEIPT:
                raise Hold("V2_RECEIPT_TOO_LARGE_HOLD")
            private.write_new(directory / receipt_name(index + 1), blob)
        return _inspect(directory, old_dir, plan_dir)[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for mode in ("init", "inspect", "advance"):
        sub = subs.add_parser(mode)
        sub.add_argument("--old-dir", type=Path, required=True)
        sub.add_argument("--plan-dir", type=Path, required=True)
        sub.add_argument("--output-dir", type=Path, required=True)
        if mode == "advance":
            sub.add_argument("--max-cases", type=int, default=5)
            sub.add_argument("--execute", action="store_true")
            sub.add_argument("--allow-private-data-egress", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args.output_dir, args.old_dir, args.plan_dir)
        elif args.command == "inspect":
            result = inspect(args.output_dir, args.old_dir, args.plan_dir)
        else:
            result = advance(
                args.output_dir, args.old_dir, args.plan_dir, args.max_cases,
                execute=args.execute,
                allow_private_data_egress=args.allow_private_data_egress,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        print(json.dumps({
            "schema": SAFE, "status": "V2_PRIORITY_REPLAY_HOLD",
            "model_requests": 0, "gpu_started": False,
            "train_admitted": 0, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

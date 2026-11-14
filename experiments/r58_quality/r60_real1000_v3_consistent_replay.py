"""R60 V3 create-only repair with frozen V1/V2 chain and strict B instructions.

V3 only targets the V2 technical failures and not-yet-reviewed priority
slots. Existing V2 PASS/HOLD/REJECT replies are never re-requested.
No model request without both explicit CLI egress flags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_v2_priority_replay as v2
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_real1000_v3_consistent_replay_private_v1"
SAFE = "storyforge_r60_real1000_v3_consistent_replay_safe_v1"
CONFIG = "R60_V3_CONSISTENT_CONFIG_PRIVATE.json"
PREFIX = "R60_V3_CONSISTENT_"
MAX_CONFIG = 16000
MAX_RECEIPT = 24000
MAX_BATCH = 25
RETRYABLE = v2.TECHNICAL


class Hold(ValueError):
    pass


def receipt_name(ordinal: int) -> str:
    return f"{PREFIX}{ordinal:04d}_PRIVATE.json"


def source_state(old_dir: Path, plan_dir: Path, v2_dir: Path):
    """Re-verify full V1 and V2, lock V2's current receipt-chain snapshot."""
    with batch.expand.locked(v2_dir):
        old, cases, selected, safe = v2._inspect(
            v2_dir, old_dir, plan_dir)
        completed = safe["reviewed_slots"]
        digests = []
        queue = []
        for index, item in enumerate(selected):
            ordinal = index + 1
            previous = None
            if index < completed:
                data = private.read_private(
                    v2_dir / v2.receipt_name(ordinal), v2.MAX_RECEIPT)
                digests.append(hashlib.sha256(data).hexdigest())
                previous = json.loads(data)
                if previous["status"] != "TECHNICAL_HOLD":
                    continue
            target = item["missing_slots"][0]
            queue.append({
                "position": item["position"],
                "v2_ordinal": ordinal,
                "side": target["side"],
                "case_key": item["case_key"],
                "history_messages_sha256": item["history_messages_sha256"],
                "assistant_target_sha256": item["assistant_target_sha256"],
                "v1_receipt_sha256": item["original_receipt_sha256"],
                "v2_receipt_sha256": (
                    previous["receipt_sha256"] if previous else None
                ),
                "source_status": (
                    "V2_TECHNICAL_HOLD" if previous else "V2_UNREVIEWED"
                ),
                "v2_reason_code": (
                    previous["reason_code"] if previous else None
                ),
            })
        if len(digests) != completed:
            raise Hold("V2_SNAPSHOT_COUNT_HOLD")
        chain = hashlib.sha256(
            json.dumps(digests, separators=(",", ":")).encode()
        ).hexdigest()
        # B-side decision consistency errors take precedence, then all
        # other existing technical failures, then not-yet-reviewed cases.
        def priority(item):
            if (item["side"] == "b"
                    and item["v2_reason_code"] in {
                        "QUALITY_FLOOR_DECISION_INCONSISTENT",
                        "SEVERE_FLAG_DECISION_INCONSISTENT",
                    }):
                return (0, item["v2_ordinal"])
            if item["source_status"] == "V2_TECHNICAL_HOLD":
                return (1, item["v2_ordinal"])
            return (2, item["v2_ordinal"])

        queue.sort(key=priority)
        fingerprint = {
            "v1_source_sha256": old["pool_sha256"],
            "v2_completed": completed,
            "v2_receipt_chain_sha256": chain,
            "v3_queue_sha256": private.digest(queue),
            "planned_slots": len(queue),
            "strict_b_instruction_sha256": hashlib.sha256(
                ai.REVIEW_INSTRUCTIONS_V3_CONSISTENT.encode()
            ).hexdigest(),
        }
        return old, cases, queue, fingerprint


def _config(old_dir, plan_dir, v2_dir, fingerprint):
    return {
        "schema": SCHEMA,
        "old_dir": str(old_dir),
        "plan_dir": str(plan_dir),
        "v2_dir": str(v2_dir),
        **fingerprint,
    }


def _inspect(directory: Path, old_dir: Path, plan_dir: Path,
             v2_dir: Path):
    private.private_dir(directory, create=False)
    if directory in (old_dir, plan_dir, v2_dir):
        raise Hold("OUTPUT_ALIAS_HOLD")
    old, cases, queue, fingerprint = source_state(
        old_dir, plan_dir, v2_dir)
    config = json.loads(private.read_private(
        directory / CONFIG, MAX_CONFIG))
    if config != _config(old_dir, plan_dir, v2_dir, fingerprint):
        raise Hold("V3_SOURCE_OR_CONFIG_DRIFT_HOLD")
    files = sorted(path for path in directory.glob(PREFIX + "*_PRIVATE.json")
                   if path.name != CONFIG)
    if len(files) > len(queue):
        raise Hold("V3_OVERFLOW_HOLD")
    counts = Counter()
    sides = Counter()
    for index, path in enumerate(files):
        ordinal = index + 1
        if path.name != receipt_name(ordinal):
            raise Hold("V3_SEQUENCE_HOLD")
        row = json.loads(private.read_private(path, MAX_RECEIPT))
        item = queue[index]
        expected = {
            "schema": SCHEMA,
            "ordinal": ordinal,
            "position": item["position"],
            "case_key": item["case_key"],
            "history_messages_sha256": item["history_messages_sha256"],
            "assistant_target_sha256": item["assistant_target_sha256"],
            "v1_receipt_sha256": item["v1_receipt_sha256"],
            "v2_receipt_sha256": item["v2_receipt_sha256"],
            "side": item["side"],
            "model_id": old["model_" + item["side"]],
            "instruction_profile": (
                "V3_STRICT_B" if item["side"] == "b" else "V1_DEFAULT_A"
            ),
        }
        if any(row.get(k) != val for k, val in expected.items()):
            raise Hold("V3_CASE_BINDING_HOLD")
        signed = {k: value for k, value in row.items()
                  if k != "receipt_sha256"}
        if row.get("receipt_sha256") != private.digest(signed):
            raise Hold("V3_SIGNATURE_HOLD")
        if row.get("status") == "TECHNICAL_HOLD":
            if row.get("result") is not None or row.get(
                    "reason_code") not in RETRYABLE:
                raise Hold("V3_TECHNICAL_FORMAT_HOLD")
        else:
            if row.get("reason_code") is not None:
                raise Hold("V3_REASON_FORMAT_HOLD")
            parsed = ai.parse_model_response(row["result"])
            if row["status"] != "V3_" + parsed["decision"]:
                raise Hold("V3_DECISION_FORMAT_HOLD")
        counts[row["status"]] += 1
        sides[item["side"]] += 1
    safe = {
        "schema": SAFE,
        "status": ("V3_CONSISTENT_REPLAY_COMPLETE__NO_ADMISSION"
                   if len(files) == len(queue)
                   else "V3_CONSISTENT_REPLAY_IN_PROGRESS__NO_ADMISSION"),
        "v1_cases_preserved": 1000,
        "v2_receipts_preserved": fingerprint["v2_completed"],
        "planned_slots": len(queue),
        "reviewed_slots": len(files),
        "remaining_slots": len(queue) - len(files),
        "result_counts": dict(sorted(counts.items())),
        "reviewed_by_side": dict(sorted(sides.items())),
        "model_requests": 0,
        "database_modified": False, "gpu_started": False,
        "private_values_emitted": False, "train_admitted": 0,
        "quality_v1_admitted": 0,
    }
    return old, cases, queue, safe


def initialize(directory, old_dir, plan_dir, v2_dir):
    if (directory.exists() or directory.is_symlink()
            or directory.parent != private.BASE
            or not directory.name.startswith(
                "r60-real1000-v3-consistent-replay-")
            or directory in (old_dir, plan_dir, v2_dir)):
        raise Hold("V3_OUTPUT_PATH_HOLD")
    _old, _cases, _queue, fingerprint = source_state(
        old_dir, plan_dir, v2_dir)
    private.private_dir(directory, create=True)
    content = (json.dumps(
        _config(old_dir, plan_dir, v2_dir, fingerprint),
        sort_keys=True, separators=(",", ":")) + "\n").encode()
    private.write_new(directory / CONFIG, content)
    return _inspect(directory, old_dir, plan_dir, v2_dir)[3]


def inspect(directory, old_dir, plan_dir, v2_dir):
    with batch.expand.locked(directory):
        return _inspect(directory, old_dir, plan_dir, v2_dir)[3]


def advance(directory, old_dir, plan_dir, v2_dir, count, *,
            execute=False, allow_private_data_egress=False):
    if not execute or not allow_private_data_egress:
        raise Hold("V3_EXPLICIT_EXECUTION_REQUIRED")
    if type(count) is not int or not 1 <= count <= MAX_BATCH:
        raise Hold("V3_BATCH_SIZE_HOLD")
    with batch.expand.locked(directory):
        old, cases, queue, state = _inspect(
            directory, old_dir, plan_dir, v2_dir)
        start = state["reviewed_slots"]
        for index in range(start, min(start + count, len(queue))):
            item = queue[index]
            side = item["side"]
            key_name = ("DASHSCOPE_API_KEY" if side == "a"
                        else "DEEPSEEK_API_KEY")
            key = os.environ.get(key_name)
            if not key:
                raise Hold("V3_REVIEWER_KEY_MISSING_HOLD")
            case = cases[item["position"] - 1]
            instructions = (
                ai.REVIEW_INSTRUCTIONS_V3_CONSISTENT
                if side == "b" else ai.REVIEW_INSTRUCTIONS
            )
            reason = None
            answer = None
            try:
                answer = ai.model_request(
                    old["endpoint_" + side],
                    old["model_" + side], key,
                    ai.prompt_for_case(case),
                    old["timeout"], old["json_mode"],
                    protocol=old["protocol_" + side],
                    instructions=instructions,
                )
            except ai.Hold as exc:
                reason = str(exc)
                if reason in v2.SUSPEND:
                    raise Hold("V3_SERVICE_UNAVAILABLE_HOLD") from exc
                if reason not in RETRYABLE:
                    raise Hold("V3_UNEXPECTED_MODEL_ERROR_HOLD") from exc
            row = {
                "schema": SCHEMA, "ordinal": index + 1,
                "position": item["position"],
                "case_key": item["case_key"],
                "history_messages_sha256": item["history_messages_sha256"],
                "assistant_target_sha256": item["assistant_target_sha256"],
                "v1_receipt_sha256": item["v1_receipt_sha256"],
                "v2_receipt_sha256": item["v2_receipt_sha256"],
                "side": side, "model_id": old["model_" + side],
                "instruction_profile": (
                    "V3_STRICT_B" if side == "b" else "V1_DEFAULT_A"
                ),
                "status": ("TECHNICAL_HOLD" if reason
                           else "V3_" + answer["decision"]),
                "reason_code": reason,
                "result": answer,
            }
            row["receipt_sha256"] = private.digest(row)
            blob = (json.dumps(row, ensure_ascii=False, sort_keys=True)
                    + "\n").encode()
            if len(blob) > MAX_RECEIPT:
                raise Hold("V3_RECEIPT_SIZE_HOLD")
            private.write_new(
                directory / receipt_name(index + 1), blob)
        return _inspect(directory, old_dir, plan_dir, v2_dir)[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for mode in ("init", "inspect", "advance"):
        p = sub.add_parser(mode)
        p.add_argument("--old-dir", type=Path, required=True)
        p.add_argument("--plan-dir", type=Path, required=True)
        p.add_argument("--v2-dir", type=Path, required=True)
        p.add_argument("--output-dir", type=Path, required=True)
        if mode == "advance":
            p.add_argument("--max-cases", type=int, default=5)
            p.add_argument("--execute", action="store_true")
            p.add_argument("--allow-private-data-egress", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(
                args.output_dir, args.old_dir, args.plan_dir, args.v2_dir)
        elif args.command == "inspect":
            result = inspect(
                args.output_dir, args.old_dir, args.plan_dir, args.v2_dir)
        else:
            result = advance(
                args.output_dir, args.old_dir, args.plan_dir, args.v2_dir,
                args.max_cases, execute=args.execute,
                allow_private_data_egress=args.allow_private_data_egress)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        code = str(exc)
        if (type(exc) not in {Hold, v2.Hold, batch.Hold, ai.Hold, private.Hold}
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{3,79}", code)):
            code = "V3_LOCAL_RUNTIME_HOLD"
        print(json.dumps({
            "schema": SAFE, "status": "V3_CONSISTENT_REPLAY_HOLD",
            "reason_code": code,
            "model_requests": (
                0 if args.command in ("init", "inspect") else None
            ), "gpu_started": False, "train_admitted": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

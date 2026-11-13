"""Bounded create-only Pilot5 v2 failed-side replay; dry-run by default.

Never modifies v1 receipts. Executes ONLY planned failed slots with explicit
--execute --allow-private-data-egress; each attempted slot creates a new
0600 receipt, including failed attempts. No automatic retries or training.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import r60_pilot5_v2_replay_plan as plan
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_pilot5_v2_replay_attempt_private_v1"
SAFE = "storyforge_r60_pilot5_v2_replay_execute_safe_v1"
PREFIX = "R60_PILOT5_V2_REPLAY_SLOT_"
VALID_SLOTS = ((1, "b"), (3, "a"), (3, "b"))
# Fixed error catalog: never expose provider-originated text.
HOLD_CODES = frozenset({
    "MODEL_JSON_INVALID", "QUALITY_FLOOR_DECISION_INCONSISTENT",
    "MODEL_TRANSPORT_HOLD", "MODEL_REPLY_OVERSIZE", "MODEL_PROTOCOL_HOLD",
    "SEVERE_FLAG_DECISION_INCONSISTENT",
}) | ai.SAFE_HTTP_HOLDS


class Hold(ValueError):
    pass


def receipt_file(output_dir: Path, position: int, side: str) -> Path:
    return output_dir / f"{PREFIX}{position:04d}_{side.upper()}_PRIVATE.json"


def verify(quality_dir: Path, output_dir: Path) -> tuple[dict, list[dict], list[dict]]:
    # Verify the v1 frozen source, every immutable receipt, and the v2 plan.
    original = quality.inspect(quality_dir)
    if original["cases_reviewed"] != plan.PILOT5:
        raise Hold("V1_REVIEW_COUNT_HOLD")
    config = quality.validate_config(quality_dir)
    cases, pool_hash = quality.frozen_pool(Path(config["source"]))
    if pool_hash != config["pool_sha256"]:
        raise Hold("POOL_HASH_MISMATCH_HOLD")
    private.private_dir(output_dir, create=False)
    manifest = json.loads(private.read_private(
        output_dir / plan.PLAN_NAME, quality.MAX_CASE_BYTES,
    ))
    if (
        manifest.get("schema") != plan.SCHEMA
        or manifest.get("pool_sha256") != pool_hash
        or manifest.get("quality_batch_config_digest") != private.digest(config)
        or manifest.get("original_receipt_count") != plan.PILOT5
        or manifest.get("original_v1_preserved") is not True
        or manifest.get("training_authorized") is not False
        or manifest.get("model_requests_performed") != 0
    ):
        raise Hold("REPLAY_MANIFEST_BINDING_HOLD")
    slots = manifest.get("slots")
    if not isinstance(slots, list) or len(slots) != len(VALID_SLOTS):
        raise Hold("REPLAY_SLOT_COUNT_HOLD")
    if tuple((s.get("position"), s.get("side")) for s in slots) != VALID_SLOTS:
        raise Hold("REPLAY_SLOT_ORDER_HOLD")
    for slot in slots:
        position, side = slot["position"], slot["side"]
        case = cases[position - 1]
        receipt = json.loads(private.read_private(
            quality_dir / quality.receipt_name(position),
            quality.MAX_CASE_BYTES,
        ))
        signed = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        if (
            receipt["receipt_sha256"] != private.digest(signed)
            or slot.get("original_receipt_sha256") != receipt["receipt_sha256"]
            or slot.get("history_messages_sha256") != case["history_messages_sha256"]
            or slot.get("assistant_target_sha256") != case["assistant_target_sha256"]
            or slot.get("model_id") != config["model_" + side]
            or slot.get("protocol") != config["protocol_" + side]
            or slot.get("status") != "REPLAY_NOT_AUTHORIZED"
            or "ai-model-" + side in {x.get("reviewer_key") for x in receipt["reviews"]}
            or slot.get("original_failure") not in receipt["attempt_holds"]
        ):
            raise Hold("SLOT_V1_BINDING_HOLD")
    return config, cases, slots


def run(quality_dir: Path, output_dir: Path, *, execute: bool,
        allow_private_data_egress: bool, max_requests: int) -> dict:
    safe = {
        "schema": SAFE,
        "status": "PILOT5_V2_REPLAY_HOLD",
        "planned_slots": 0, "already_recorded_slots": 0,
        "model_requests": 0, "successes": 0, "attempt_holds": 0,
        "gpu_started": False, "database_modified": False,
        "train_admitted": 0, "private_values_emitted": False,
    }
    try:
        if type(max_requests) is not int or not 1 <= max_requests <= 3:
            raise Hold("MAX_REQUESTS_BOUNDS_HOLD")
        config, cases, slots = verify(quality_dir, output_dir)
        existing = [receipt_file(output_dir, s["position"], s["side"]).exists()
                    for s in slots]
        safe["planned_slots"] = len(slots)
        safe["already_recorded_slots"] = sum(existing)
        if not execute:
            safe["status"] = "PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST"
            return safe
        if not allow_private_data_egress or not config["allow_remote"]:
            raise Hold("PRIVATE_EGRESS_NOT_AUTHORIZED")
        # Only missing slots; never replay an already-recorded attempt.
        pending = [s for s, done in zip(slots, existing) if not done]
        for slot in pending[:max_requests]:
            position, side = slot["position"], slot["side"]
            case = cases[position - 1]
            key = os.getenv("R60_CLAUDE_KEY" if side == "a" else "R60_DEEPSEEK_KEY", "")
            if not key:
                raise Hold("REVIEWER_API_KEY_MISSING")
            # Re-check v1 immediately before each remote request; frozen pool
            # and original reviewer records must remain valid.
            verify(quality_dir, output_dir)
            safe["model_requests"] += 1
            answer = None
            failure = None
            try:
                answer = ai.model_request(
                    config["endpoint_" + side], config["model_" + side],
                    key, ai.prompt_for_case(case), config["timeout"],
                    config["json_mode"], protocol=config["protocol_" + side],
                )
            except ai.Hold as exc:
                failure = str(exc) if str(exc) in HOLD_CODES else "MODEL_PROTOCOL_HOLD"
            result = {
                "schema": SCHEMA, "position": position, "side": side,
                "original_receipt_sha256": slot["original_receipt_sha256"],
                "history_messages_sha256": slot["history_messages_sha256"],
                "assistant_target_sha256": slot["assistant_target_sha256"],
                "original_failure": slot["original_failure"],
                "model_id": slot["model_id"], "protocol": slot["protocol"],
                "attempt_status": "SUCCESS" if answer is not None else "HOLD",
                "failure_code": failure,
                "review": answer,
                "train_admitted": 0,
            }
            # Fail-closed and create-only. No v1 modifications.
            private.write_new(
                receipt_file(output_dir, position, side),
                json.dumps(result, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n",
            )
            safe["successes" if answer is not None else "attempt_holds"] += 1
        safe["status"] = "PILOT5_V2_REPLAY_ATTEMPTS_SAVED__NO_PROMOTION"
    except (ValueError, OSError, TypeError, KeyError, IndexError, UnicodeError):
        safe["status"] = "PILOT5_V2_REPLAY_HOLD"
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-private-data-egress", action="store_true")
    parser.add_argument("--max-requests", type=int, default=3)
    args = parser.parse_args()
    safe = run(args.quality_dir, args.output_dir, execute=args.execute,
               allow_private_data_egress=args.allow_private_data_egress,
               max_requests=args.max_requests)
    print(json.dumps(safe, sort_keys=True))
    return 0 if safe["status"] != "PILOT5_V2_REPLAY_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())

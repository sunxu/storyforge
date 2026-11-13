"""R60 REAL1000 DeepSeek-only provisional review for frozen positions 256..1000.

Create-only private records; never promotes Gold/Train. The old dual-review
255-case batch is audited unchanged before every operation. No implicit network.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import r60_real_ai_dual_review as ai
import r60_real_private_batch as private
import r60_real_quality_batch as batch

SCHEMA = "storyforge_r60_deepseek_single_private_v1"
SAFE = "storyforge_r60_deepseek_single_safe_v1"
CONFIG = "R60_DEEPSEEK_SINGLE_CONFIG_PRIVATE.json"
PREFIX = "R60_DEEPSEEK_SINGLE_"
FIRST = 256
LAST = 1000
MODEL = "deepseek-flash"
URL = "https://api.deepseek.com/chat/completions"
PROTOCOL = "deepseek-chat"
MAX_CASES = 25
MAX_FILE = 24000
AUTH_HOLDS = {"MODEL_HTTP_401_HOLD", "MODEL_HTTP_403_HOLD",
              "MODEL_HTTP_429_HOLD", "MODEL_TRANSPORT_HOLD",
              "MODEL_HTTP_500_HOLD", "MODEL_HTTP_502_HOLD",
              "MODEL_HTTP_503_HOLD", "MODEL_HTTP_504_HOLD"}


class Hold(ValueError):
    pass


def receipt_name(position: int) -> str:
    return f"{PREFIX}{position:04d}_PRIVATE.json"


def old_state(old_dir: Path) -> tuple[dict, list[dict], str]:
    config = batch.validate_config(old_dir)
    cases, pool_sha = batch.frozen_pool(Path(config["source"]))
    if config["pool_sha256"] != pool_sha:
        raise Hold("SOURCE_DRIFT_HOLD")
    inspected = batch.inspected_records(old_dir, config, cases, pool_sha)
    if inspected["cases_reviewed"] != FIRST - 1:
        raise Hold("OLD_BATCH_255_EXPECTED_HOLD")
    if (config["model_b"] != MODEL or
            config["endpoint_b"] != URL or
            config["protocol_b"] != PROTOCOL):
        raise Hold("OLD_BATCH_DEEPSEEK_IDENTITY_HOLD")
    return config, cases, pool_sha


def verify(directory: Path, old_dir: Path) -> tuple[dict, list[dict], dict]:
    private.private_dir(directory, create=False)
    if directory == old_dir:
        raise Hold("OUTPUT_ALIAS_HOLD")
    original, cases, pool_sha = old_state(old_dir)
    config = json.loads(private.read_private(directory / CONFIG, 16000))
    if (set(config) != {"schema", "source", "pool_sha256",
                         "old_dir", "old_completed", "model",
                         "endpoint", "protocol", "receipt_sha256"}
            or config["schema"] != SCHEMA
            or config["source"] != original["source"]
            or config["pool_sha256"] != pool_sha
            or config["old_dir"] != str(old_dir)
            or config["old_completed"] != FIRST - 1
            or config["model"] != MODEL
            or config["endpoint"] != URL
            or config["protocol"] != PROTOCOL):
        raise Hold("SINGLE_CONFIG_MISMATCH_HOLD")
    signed = {k: v for k, v in config.items() if k != "receipt_sha256"}
    if config["receipt_sha256"] != private.digest(signed):
        raise Hold("SINGLE_CONFIG_SIGNATURE_HOLD")

    positions = sorted(directory.glob(PREFIX + "*_PRIVATE.json"))
    status = Counter()
    errors = Counter()
    expected_position = FIRST
    for path in positions:
        if (expected_position > LAST
                or path.name != receipt_name(expected_position)):
            raise Hold("SINGLE_POSITION_SEQUENCE_HOLD")
        row = json.loads(private.read_private(path, MAX_FILE))
        source = cases[expected_position - 1]
        if (not isinstance(row, dict)
                or row.get("schema") != SCHEMA
                or row.get("position") != expected_position
                or row.get("pool_sha256") != pool_sha
                or row.get("case_key") != source["case_key"]
                or row.get("history_messages_sha256") !=
                source["history_messages_sha256"]
                or row.get("assistant_target_sha256") !=
                source["assistant_target_sha256"]
                or row.get("model") != MODEL
                or row.get("protocol") != PROTOCOL):
            raise Hold("SINGLE_SOURCE_BINDING_HOLD")
        signature = {k: v for k, v in row.items() if k != "receipt_sha256"}
        if row.get("receipt_sha256") != private.digest(signature):
            raise Hold("SINGLE_RECEIPT_SIGNATURE_HOLD")
        if row.get("status") == "TECHNICAL_HOLD":
            if (row.get("response") is not None
                    or row.get("reason_code") not in (
                        {"MODEL_JSON_INVALID", "MODEL_REPLY_OVERSIZE",
                         "MODEL_PROTOCOL_HOLD",
                         "QUALITY_FLOOR_DECISION_INCONSISTENT",
                         "SEVERE_FLAG_DECISION_INCONSISTENT",
                         "MODEL_HTTP_400_HOLD", "MODEL_HTTP_404_HOLD",
                         "MODEL_HTTP_408_HOLD", "MODEL_HTTP_413_HOLD"})):
                raise Hold("SINGLE_TECHNICAL_SCHEMA_HOLD")
            errors[row["reason_code"]] += 1
        else:
            response = ai.parse_model_response(row.get("response"))
            expected = {"PASS": "PROVISIONAL_PASS",
                        "HOLD": "PROVISIONAL_HOLD",
                        "REJECT": "PROVISIONAL_REJECT"}[response["decision"]]
            if row.get("status") != expected or row.get("reason_code") is not None:
                raise Hold("SINGLE_REVIEW_SCHEMA_HOLD")
        status[row["status"]] += 1
        expected_position += 1
    done = expected_position - FIRST
    return config, cases, {
        "schema": SAFE,
        "status": "SINGLE_REVIEW_COMPLETE__NOT_ADMITTED"
        if expected_position > LAST else "SINGLE_REVIEW_IN_PROGRESS__NOT_ADMITTED",
        "base_cases_preserved": FIRST - 1,
        "single_cases_reviewed": done,
        "total_positions_attempted": FIRST - 1 + done,
        "remaining_single_cases": LAST - FIRST + 1 - done,
        "single_decisions": dict(sorted(status.items())),
        "technical_hold_counts": dict(sorted(errors.items())),
        "model_requests": 0,
        "private_values_emitted": False,
        "database_modified": False,
        "gpu_started": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "full_dual_review_claimed": False,
    }


def initialize(old_dir: Path, directory: Path) -> dict:
    if (directory.parent != private.BASE
            or not directory.name.startswith("r60-quality-fast1000-deepseek-single-")
            or directory.exists() or directory.is_symlink()
            or old_dir == directory):
        raise Hold("SINGLE_PRIVATE_OUTPUT_PATH_HOLD")
    old, _cases, sha = old_state(old_dir)
    private.private_dir(directory, create=True)
    config = {
        "schema": SCHEMA, "source": old["source"],
        "pool_sha256": sha, "old_dir": str(old_dir),
        "old_completed": FIRST - 1,
        "model": MODEL, "endpoint": URL, "protocol": PROTOCOL,
    }
    config["receipt_sha256"] = private.digest(config)
    private.write_new(directory / CONFIG, (
        json.dumps(config, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8"))
    return verify(directory, old_dir)[2]


def advance(old_dir: Path, directory: Path, max_cases: int,
            execute: bool, allow_private_data_egress: bool) -> dict:
    if not execute or not allow_private_data_egress:
        raise Hold("SINGLE_REMOTE_APPROVAL_REQUIRED")
    if type(max_cases) is not int or not 1 <= max_cases <= MAX_CASES:
        raise Hold("SINGLE_BATCH_LIMIT_HOLD")
    with batch.expand.locked(directory):
        config, cases, prior = verify(directory, old_dir)
        position = FIRST + prior["single_cases_reviewed"]
        for current in range(position, min(position + max_cases, LAST + 1)):
            case = cases[current - 1]
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not key:
                raise Hold("DEEPSEEK_KEY_MISSING_HOLD")
            prompt = ai.prompt_for_case(case)
            response = None
            reason = None
            try:
                response = ai.model_request(
                    config["endpoint"], MODEL, key, prompt, 180,
                    False, protocol=PROTOCOL,
                )
            except ai.Hold as exc:
                reason = str(exc)
                if reason in AUTH_HOLDS:
                    # No irreversible record on auth, rate or service outage.
                    raise Hold("DEEPSEEK_SERVICE_BLOCKED_HOLD") from exc
                if reason not in {
                    "MODEL_JSON_INVALID", "MODEL_REPLY_OVERSIZE",
                    "MODEL_PROTOCOL_HOLD", "MODEL_HTTP_400_HOLD",
                    "MODEL_HTTP_404_HOLD", "MODEL_HTTP_408_HOLD",
                    "MODEL_HTTP_413_HOLD",
                    "QUALITY_FLOOR_DECISION_INCONSISTENT",
                    "SEVERE_FLAG_DECISION_INCONSISTENT",
                }:
                    raise Hold("DEEPSEEK_UNKNOWN_TECHNICAL_HOLD") from exc
            record = {
                "schema": SCHEMA, "position": current,
                "pool_sha256": config["pool_sha256"],
                "case_key": case["case_key"],
                "history_messages_sha256": case["history_messages_sha256"],
                "assistant_target_sha256": case["assistant_target_sha256"],
                "model": MODEL, "protocol": PROTOCOL,
                "status": ("TECHNICAL_HOLD" if reason else
                           "PROVISIONAL_" + response["decision"]),
                "reason_code": reason, "response": response,
            }
            record["receipt_sha256"] = private.digest(record)
            data = (json.dumps(record, ensure_ascii=False, sort_keys=True)
                    + "\n").encode("utf-8")
            if len(data) > MAX_FILE:
                raise Hold("SINGLE_RECORD_SIZE_HOLD")
            private.write_new(directory / receipt_name(current), data)
        return verify(directory, old_dir)[2]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="mode", required=True)
    for name in ("init", "inspect", "advance"):
        sub = commands.add_parser(name)
        sub.add_argument("--old-dir", type=Path, required=True)
        sub.add_argument("--output-dir", type=Path, required=True)
        if name == "advance":
            sub.add_argument("--max-cases", type=int, default=25)
            sub.add_argument("--execute", action="store_true")
            sub.add_argument("--allow-private-data-egress", action="store_true")
    args = p.parse_args()
    try:
        if args.mode == "init":
            result = initialize(args.old_dir, args.output_dir)
        elif args.mode == "inspect":
            result = verify(args.output_dir, args.old_dir)[2]
        else:
            result = advance(args.old_dir, args.output_dir, args.max_cases,
                             args.execute, args.allow_private_data_egress)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        print(json.dumps({
            "schema": SAFE, "status": "SINGLE_REVIEW_HOLD",
            "private_values_emitted": False, "train_admitted": 0,
            "gpu_started": False, "database_modified": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())

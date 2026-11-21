"""Offline Gold48 judge contract lock; reads blind packet only, never Owner key.

No network, HF credentials, scoring calls, source attribution or review unblinding.
A locked contract is NOT permission to transfer private story text to a provider.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .gold48_blind import PACK_SCHEMA, private_input
from .gold48_hf_judge import validate_item
from .hf_blind_stage import private_folder, write_once
from .hf_literary_review import canonical

SCHEMA = "storyforge_r60_gold48_judge_lock_private_v1"
CONFIG_SCHEMA = "storyforge_r60_gold48_judge_config_private_v1"
SAFE_SCHEMA = "storyforge_r60_gold48_judge_lock_safe_v1"
MODEL_ID = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
PROVIDER_ID = re.compile(r"[a-z0-9-]+\Z")


class LockHold(ValueError):
    """Only reason codes, never private payloads."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise LockHold(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_packet(path: Path) -> tuple[bytes, int]:
    private_folder(path.parent)
    raw = private_input(path, limit=64 * 1024 * 1024)
    require(raw.endswith(b"\n"), "BLIND_PACKET_FRAMING_HOLD")
    lines = raw.splitlines()
    require(len(lines) == 240 and all(lines), "BLIND_PACKET_COUNT_HOLD")
    ids: set[str] = set()
    histories: Counter[str] = Counter()
    blank = 0
    for line in lines:
        try:
            obj = json.loads(line)
            validate_item(obj)
        except (ValueError, TypeError, KeyError):
            raise LockHold("BLIND_PACKET_ITEM_HOLD") from None
        require(obj["schema"] == PACK_SCHEMA
                and line == canonical(obj), "BLIND_PACKET_CANONICAL_HOLD")
        ids.add(obj["blind_id"])
        histories[digest(canonical(obj["visible_messages"]))] += 1
        blank += int(not obj["target_text"].strip())
    require(len(ids) == 240
            and len(histories) == 48
            and set(histories.values()) == {5},
            "BLIND_PACKET_48X5_HOLD")
    require(blank == 1, "BLIND_PACKET_NO_RESPONSE_COUNT_HOLD")
    return raw, blank


def read_config(path: Path) -> dict:
    try:
        config = json.loads(private_input(path, limit=65536))
    except (ValueError, TypeError):
        raise LockHold("JUDGE_CONFIG_JSON_HOLD") from None
    require(type(config) is dict
            and set(config) == {"schema", "reviewers", "max_cost_usd"}
            and config["schema"] == CONFIG_SCHEMA,
            "JUDGE_CONFIG_FIELDS_HOLD")
    reviewers = config["reviewers"]
    require(type(reviewers) is list and len(reviewers) == 2,
            "JUDGE_INDEPENDENT_SLOTS_HOLD")
    models = set()
    providers = set()
    for position, entry in enumerate(reviewers, 1):
        require(type(entry) is dict
                and set(entry) == {
                    "reviewer_id", "model", "provider", "temperature",
                    "max_tokens",
                }
                and entry["reviewer_id"] == f"J{position}"
                and type(entry["model"]) is str
                and MODEL_ID.fullmatch(entry["model"]) is not None
                and type(entry["provider"]) is str
                and PROVIDER_ID.fullmatch(entry["provider"]) is not None
                and type(entry["temperature"]) in {int, float}
                and entry["temperature"] == 0
                and type(entry["max_tokens"]) is int
                and 1024 <= entry["max_tokens"] <= 4096,
                "JUDGE_REVIEWER_CONFIG_HOLD")
        models.add(entry["model"])
        providers.add(entry["provider"])
    require(len(models) == len(providers) == 2,
            "JUDGE_DISTINCT_MODELS_PROVIDERS_HOLD")
    money = config["max_cost_usd"]
    require(type(money) in {float, int} and 0 < money <= 1000,
            "JUDGE_BUDGET_HOLD")
    return config


def prepare(*, packet: Path, config: Path, output: Path | None) -> dict:
    """Validate a 240-item blind pack and optional private config; no API calls."""
    raw, no_response = read_packet(packet)
    settings = read_config(config)
    judge_code = Path(__file__).with_name("gold48_hf_judge.py")
    require(judge_code.is_file() and not judge_code.is_symlink(),
            "JUDGE_SOURCE_FILE_HOLD")
    # Inputs frozen by hash, not copied to the contract or any public output.
    record = {
        "schema": SCHEMA,
        "packet_sha256": digest(raw),
        "judge_source_sha256": digest(judge_code.read_bytes()),
        "config": settings,
        "expected_answers": 240,
        "expected_cases": 48,
        "expected_no_response_fixed_scores": no_response * 2,
        "expected_paid_judge_scores": (240 - no_response) * 2,
        "max_total_api_calls": (240 - no_response) * 2,
        "bill_to": "adradar",
        "max_concurrent_calls": 1,
        "automatic_retries": 0,
        "fixed_no_response_policy": "all_six_one_no_severe_no_quotes_not_ai_judge",
        "independent_human_reviewers_claimed": False,
        "model_judge_independence_attested": False,
        "private_transfer_authorized": False,
        "paid_calls_authorized": False,
        "unblinding_authorized": False,
        "quality_v1_admitted": 0,
    }
    payload = canonical(record) + b"\n"
    safe = {
        "schema": SAFE_SCHEMA,
        "status": ("GOLD48_JUDGE_CONFIG_LOCKED__NO_API_NO_TRANSFER"
                   if output is not None else
                   "GOLD48_JUDGE_CONFIG_PREFLIGHT_PASS__NO_OUTPUT_NO_API"),
        "answers": 240,
        "reviewer_slots": 2,
        "fixed_no_response_scores": no_response * 2,
        "planned_paid_judge_scores": (240 - no_response) * 2,
        "max_api_calls": (240 - no_response) * 2,
        "api_calls": 0,
        "cost_usd": 0,
        "private_transfer_authorized": False,
        "owner_mapping_accessed": False,
        "private_values_emitted": False,
        "quality_v1_admitted": 0,
    }
    if output is not None:
        require(output.is_absolute() and not output.exists()
                and not output.is_symlink(), "JUDGE_LOCK_EXISTS_HOLD")
        for parent in (output, *output.parents):
            require(not (parent / ".git").exists()
                    and not (parent / ".git").is_symlink(),
                    "PRIVATE_OUTPUT_INSIDE_GIT_HOLD")
        private_folder(output.parent)
        write_once(output, payload)
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", type=Path, help="Omit for no-write preflight")
    args = parser.parse_args()
    try:
        result = prepare(packet=args.pack, config=args.config, output=args.out)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (LockHold, ValueError, OSError) as exc:
        code = str(exc) if isinstance(exc, LockHold) else "JUDGE_LOCK_INPUT_HOLD"
        print(json.dumps({
            "status": "GOLD48_JUDGE_LOCK_HOLD", "reason": code,
            "api_calls": 0, "private_values_emitted": False,
        }))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()

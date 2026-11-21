"""One Gold48 blind review at a time, with pre-call create-only consumption.

This is deliberately NOT a batch runner. Owner selects one item + reviewer;
real HF requests need separate explicit transfer, billing, and spending-cap
confirmations. Crash/timeout after attempt marker => HOLD, never auto retry.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .gold48_blind import private_input
from .gold48_hf_judge import JudgeHold, judge_one, make_hf_client, validate_item
from .gold48_judge_lock import SCHEMA as LOCK_SCHEMA
from .gold48_judge_lock import LockHold, digest, read_packet, require
from .hf_blind_stage import private_folder, write_once
from .hf_literary_review import canonical

RECEIPT_SCHEMA = "storyforge_r60_gold48_judge_score_private_v1"
ATTEMPT_SCHEMA = "storyforge_r60_gold48_judge_attempt_private_v1"
SAFE_SCHEMA = "storyforge_r60_gold48_judge_step_safe_v1"


@contextmanager
def single_call_guard(root: Path) -> Iterator[None]:
    """Advisory local one-call-at-a-time lock, released on process death."""
    private_folder(root)
    path = root / ".gold48_single_call.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        mode = os.fstat(fd)
        require(stat.S_ISREG(mode.st_mode)
                and stat.S_IMODE(mode.st_mode) == 0o600
                and mode.st_nlink == 1, "JUDGE_CALL_LOCK_FILE_HOLD")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LockHold("JUDGE_CONCURRENT_EXECUTION_HOLD") from None
        yield
    finally:
        os.close(fd)


def read_locked_packet(packet: Path, lock_path: Path) -> tuple[dict, list[dict]]:
    require(packet.parent.name == "reviewers"
            and packet.name == "GOLD48_BLIND_240_PRIVATE.jsonl"
            and lock_path.parent.name == "owner"
            and lock_path.name == "GOLD48_JUDGE_LOCK_PRIVATE.json"
            and packet.parent.parent == lock_path.parent.parent,
            "JUDGE_LOCK_FOLDER_BINDING_HOLD")
    private_folder(lock_path.parent)
    raw, blank = read_packet(packet)
    try:
        lock = json.loads(private_input(lock_path, limit=65536))
    except (ValueError, TypeError):
        raise LockHold("JUDGE_LOCK_JSON_HOLD") from None
    judge_path = Path(__file__).with_name("gold48_hf_judge.py")
    require(type(lock) is dict and lock.get("schema") == LOCK_SCHEMA
            and lock.get("packet_sha256") == digest(raw)
            and lock.get("judge_source_sha256") == digest(judge_path.read_bytes())
            and lock.get("expected_answers") == 240
            and lock.get("expected_cases") == 48
            and lock.get("expected_no_response_fixed_scores") == blank * 2
            and lock.get("expected_paid_judge_scores") == 478
            and lock.get("max_total_api_calls") == 478
            and lock.get("bill_to") == "adradar"
            and lock.get("max_concurrent_calls") == 1
            and lock.get("automatic_retries") == 0
            and lock.get("fixed_no_response_policy") ==
            "all_six_one_no_severe_no_quotes_not_ai_judge"
            and lock.get("private_transfer_authorized") is False
            and lock.get("paid_calls_authorized") is False
            and lock.get("unblinding_authorized") is False
            and lock.get("quality_v1_admitted") == 0,
            "JUDGE_LOCK_IDENTITY_HOLD")
    config = lock.get("config")
    require(type(config) is dict
            and config.get("schema") == "storyforge_r60_gold48_judge_config_private_v1"
            and type(config.get("reviewers")) is list
            and len(config["reviewers"]) == 2
            and type(config.get("max_cost_usd")) in (int, float)
            and 0 < config["max_cost_usd"] <= 1000,
            "JUDGE_LOCK_CONFIG_HOLD")
    reviewers = config["reviewers"]
    require([r.get("reviewer_id") for r in reviewers if type(r) is dict]
            == ["J1", "J2"]
            and len({r["model"] for r in reviewers}) == 2
            and len({r["provider"] for r in reviewers}) == 2,
            "JUDGE_LOCK_REVIEWER_HOLD")
    rows = [json.loads(line) for line in raw.splitlines()]
    return lock, rows


def safe_state(*, status: str, scores: int, paid_attempts: int) -> dict:
    return {
        "schema": SAFE_SCHEMA, "status": status,
        "score_records_written": scores,
        "paid_api_attempts": paid_attempts,
        "cost_usd": None if paid_attempts else 0,
        "billing_reconciled": False,
        "owner_mapping_accessed": False,
        "private_values_emitted": False,
        "unblinded": False,
        "quality_v1_admitted": 0,
    }


def step(
    *, packet: Path, lock_path: Path, output_dir: Path,
    reviewer_id: str, position: int,
    approve_private_transfer: bool, approve_paid_calls: bool,
    confirm_hf_spending_cap: bool, hf_token: str | None,
    client_factory: Callable[..., Any] = make_hf_client,
) -> dict:
    """One and only one item; no retries, no generalized scheduling."""
    require(reviewer_id in {"J1", "J2"} and type(position) is int
            and 1 <= position <= 240, "JUDGE_SLOT_POSITION_HOLD")
    lock, rows = read_locked_packet(packet, lock_path)
    item = validate_item(rows[position - 1])
    selection = lock["config"]["reviewers"][int(reviewer_id[1]) - 1]
    require(selection["reviewer_id"] == reviewer_id,
            "JUDGE_LOCK_REVIEWER_HOLD")
    # Both approvals are separate from the offline lock. Owner must check the
    # actual HF organization budget setting; CLI cannot prove its value.
    require(approve_private_transfer is True, "PRIVATE_TRANSFER_NOT_AUTHORIZED")
    require(approve_paid_calls is True, "PAID_CALLS_NOT_AUTHORIZED")
    require(confirm_hf_spending_cap is True, "HF_BILLING_LIMIT_NOT_CONFIRMED")
    require(output_dir.is_absolute() and not output_dir.is_symlink()
            and output_dir.name == reviewer_id
            and output_dir.parent.name == "reviews"
            and output_dir.parent.parent == packet.parent.parent,
            "JUDGE_OUTPUT_FOLDER_HOLD")
    for p in (output_dir, *output_dir.parents):
        require(not (p / ".git").exists() and not (p / ".git").is_symlink(),
                "PRIVATE_OUTPUT_INSIDE_GIT_HOLD")
    private_folder(packet.parent.parent)
    private_folder(output_dir.parent)
    private_folder(output_dir)
    with single_call_guard(output_dir.parent):
        entry = f"{position:03d}"
        marker_path = output_dir / f"{entry}.attempt.private.json"
        score_path = output_dir / f"{entry}.score.private.json"
        require(not marker_path.exists() and not marker_path.is_symlink()
                and not score_path.exists() and not score_path.is_symlink(),
                "JUDGE_ITEM_ALREADY_ATTEMPTED_HOLD")
        no_reply = not item["target_text"].strip()
        if not no_reply:
            require(isinstance(hf_token, str) and bool(hf_token),
                    "HF_INFERENCE_TOKEN_MISSING_HOLD")
        # Permanent consumption BEFORE any external request. Unknown outcome stays
        # HOLD; never automatically resubmit or overwrite this item+reviewer.
        marker = {
            "schema": ATTEMPT_SCHEMA,
            "reviewer_id": reviewer_id, "position": position,
            "blind_id": item["blind_id"],
            "item_sha256": digest(canonical(item)),
            "lock_sha256": digest(private_input(lock_path, limit=65536)),
            "model": selection["model"], "provider": selection["provider"],
            "paid_call_planned": not no_reply,
            "owner_transfer_confirmed_for_this_execution": True,
            "owner_billing_confirmed_for_this_execution": True,
            "hf_spend_cap_owner_confirmed": True,
        }
        write_once(marker_path, canonical(marker) + b"\n")
        try:
            client = (None if no_reply else client_factory(
                hf_token=hf_token, fixed_provider=selection["provider"]))
            score = judge_one(
                item=item, client=client, model=selection["model"],
                temperature=selection["temperature"],
                max_tokens=selection["max_tokens"],
                private_transfer_authorized=True,
            )
            receipt = {
                "schema": RECEIPT_SCHEMA,
                "reviewer_id": reviewer_id, "position": position,
                "blind_id": item["blind_id"],
                "item_sha256": marker["item_sha256"],
                "lock_sha256": marker["lock_sha256"],
                "model": selection["model"], "provider": selection["provider"],
                "score_origin": ("fixed_no_response_rule" if no_reply else "ai_judge"),
                "paid_api_attempted": not no_reply,
                "cost_usd": None if not no_reply else 0,
                "billing_reconciled": False,
                "response": score,
            }
            write_once(score_path, canonical(receipt) + b"\n")
        except JudgeHold:
            raise
        except Exception:  # noqa: BLE001 - never leak provider/token/private text
            raise LockHold("JUDGE_EXECUTION_OR_WRITE_HOLD") from None
        return safe_state(
            status="GOLD48_JUDGE_ONE_SCORED__NO_UNBLIND",
            scores=1, paid_attempts=int(not no_reply),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer", choices=["J1", "J2"], required=True)
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--approve-private-transfer", action="store_true")
    parser.add_argument("--approve-paid-calls", action="store_true")
    parser.add_argument("--confirm-hf-spending-cap", action="store_true")
    args = parser.parse_args()
    try:
        report = step(
            packet=args.pack, lock_path=args.lock,
            output_dir=args.output_dir, reviewer_id=args.reviewer,
            position=args.position,
            approve_private_transfer=args.approve_private_transfer,
            approve_paid_calls=args.approve_paid_calls,
            confirm_hf_spending_cap=args.confirm_hf_spending_cap,
            hf_token=os.environ.get("GOLD48_HF_INFERENCE_TOKEN"),
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    except (LockHold, JudgeHold, ValueError, OSError) as exc:
        code = (str(exc) if isinstance(exc, (LockHold, JudgeHold))
                else "JUDGE_STEP_INPUT_OR_IO_HOLD")
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "GOLD48_JUDGE_STEP_HOLD",
            "reason": code, "cost_usd": None,
            "private_values_emitted": False, "quality_v1_admitted": 0,
        }, ensure_ascii=False, sort_keys=True))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()

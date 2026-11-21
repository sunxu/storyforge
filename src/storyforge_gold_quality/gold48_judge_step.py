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
import re
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
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



# The HF SDK may redact an exception that includes private prompts/credentials.
# Capture only bounded structural metadata; do not log request/response bodies.
EXCEPTION_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,79}\Z")
TRACE_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
FINISH_REASONS = {"stop", "length", "tool_calls", "content_filter"}


def exception_metadata(exc: Exception) -> dict:
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    if type(status) is not int and response is not None:
        status = getattr(response, "status_code", None)
    request_id = None
    headers = getattr(response, "headers", None)
    if headers is not None:
        for key in ("x-request-id", "x-amzn-trace-id", "x-correlation-id"):
            try:
                candidate = headers.get(key)
            except (AttributeError, TypeError, ValueError):
                candidate = None
            if type(candidate) is str and TRACE_ID.fullmatch(candidate):
                request_id = candidate
                break
    return {
        "exception_class": name if EXCEPTION_NAME.fullmatch(name) else "OtherException",
        "http_status": (status if type(status) is int and 100 <= status <= 599
                        else None),
        "provider_request_id": request_id,
    }


class SafeDiagnosticClient:
    """Bounded diagnostics plus exact quote-field repair, preserving scores."""

    def __init__(self, client: Any, *, item: dict, provider: str) -> None:
        self.client = client
        self.item = item
        self.provider = provider
        self.info: dict = {"phase": "before_api_call"}
        self.original_content_sha256: str | None = None
        self.quote_relocations = {"source_to_target": 0, "target_to_source": 0}

    def chat_completion(self, **kwargs: Any) -> Any:
        # Both settings request direct final answers, not hidden reasoning.
        if self.provider == "deepinfra":
            kwargs["extra_body"] = {"reasoning_effort": "none"}
        elif self.provider in {"fireworks-ai", "deepseek-official"}:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        else:
            raise LockHold("JUDGE_UNSUPPORTED_PROVIDER_HOLD")
        self.info = {"phase": "api_call_started"}
        try:
            result = self.client.chat_completion(**kwargs)
        except Exception as exc:
            self.info = {"phase": "api_exception", **exception_metadata(exc)}
            raise
        self.info = {
            "phase": "api_response_received",
            "choices_present": False,
            "content_present": False,
            "content_chars": None,
            "json_valid": None,
            "finish_reason": None,
        }
        choices = getattr(result, "choices", None)
        if not isinstance(choices, (list, tuple)) or not choices:
            return result
        self.info["choices_present"] = True
        choice = choices[0]
        finish = getattr(choice, "finish_reason", None)
        self.info["finish_reason"] = (
            finish if type(finish) is str and finish in FINISH_REASONS else None
        )
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if type(content) is str:
            self.info["content_present"] = bool(content.strip())
            self.info["content_chars"] = len(content)
            self.original_content_sha256 = digest(content.encode("utf-8"))
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                self.info["json_valid"] = False
            else:
                self.info["json_valid"] = True
                if type(parsed) is dict:
                    sources = parsed.get("specific_source_quotes")
                    targets = parsed.get("specific_target_quotes")
                    if (type(sources) is list and type(targets) is list
                            and all(type(q) is str for q in sources + targets)):
                        history = [m["content"] for m in self.item["visible_messages"]]
                        target_text = self.item["target_text"]
                        wrong_source = [
                            q for q in sources
                            if q not in ("",)
                            and not any(q in body for body in history)
                            and q in target_text
                        ]
                        wrong_target = [
                            q for q in targets
                            if q not in ("",)
                            and q not in target_text
                            and any(q in body for body in history)
                        ]
                        if wrong_source or wrong_target:
                            fixed = dict(parsed)
                            fixed["specific_source_quotes"] = [
                                q for q in sources if q not in wrong_source
                            ] + wrong_target
                            fixed["specific_target_quotes"] = [
                                q for q in targets if q not in wrong_target
                            ] + wrong_source
                            self.quote_relocations = {
                                "source_to_target": len(wrong_source),
                                "target_to_source": len(wrong_target),
                            }
                            # judge_one sees only the reclassified exact quote.
                            # All six scores, flags and notes remain identical.
                            corrected = canonical(fixed).decode("utf-8")
                            return SimpleNamespace(choices=[
                                SimpleNamespace(message=SimpleNamespace(
                                    content=corrected
                                ))
                            ])
        return result


def write_safe_failure(
    *, path: Path, position: int, reviewer_id: str,
    stage: dict, error_reason: str,
) -> None:
    reason = (error_reason if re.fullmatch(r"[A-Z0-9_]{1,80}", error_reason)
              else "JUDGE_FAILURE_HOLD")
    record = {
        "schema": "storyforge_r60_gold48_judge_diagnostic_safe_v1",
        "position": position, "reviewer_id": reviewer_id,
        "reason": reason, "sdk": stage,
        "private_values_emitted": False,
        "http_body_logged": False, "token_logged": False,
        "score_record_written": False,
    }
    write_once(path, canonical(record) + b"\n")


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
    official_revision: Path | None = None,
) -> dict:
    """One item, non-thinking execution revision; no automatic retries."""
    require(reviewer_id in {"J1", "J2"} and type(position) is int
            and 1 <= position <= 240, "JUDGE_SLOT_POSITION_HOLD")
    require(os.environ.get("HF_DEBUG", "").casefold() not in
            {"1", "true", "yes", "on"}, "HF_DEBUG_PRIVATE_PAYLOAD_HOLD")
    lock, rows = read_locked_packet(packet, lock_path)
    item = validate_item(rows[position - 1])
    selection = lock["config"]["reviewers"][int(reviewer_id[1]) - 1]
    require(selection["reviewer_id"] == reviewer_id,
            "JUDGE_LOCK_REVIEWER_HOLD")
    revision_sha256 = None
    if official_revision is not None:
        require(
            reviewer_id == "J1"
            and official_revision ==
                packet.parent.parent / "owner" /
                "GOLD48_J1_OFFICIAL_REVISION_PRIVATE.json"
            and selection["model"] == "deepseek-ai/DeepSeek-V4.1-Flash"
            and selection["provider"] == "fireworks-ai",
            "J1_OFFICIAL_REVISION_BINDING_HOLD",
        )
        raw_revision = private_input(official_revision, limit=65536)
        try:
            revision = json.loads(raw_revision)
        except (TypeError, ValueError):
            raise LockHold("J1_OFFICIAL_REVISION_INVALID_HOLD") from None
        require(
            type(revision) is dict
            and revision.get("schema") ==
                "storyforge_r60_gold48_j1_official_revision_private_v1"
            and revision.get("status") ==
                "J1_OFFICIAL_REVISION_PREPARED__NO_EXTERNAL_CALLS"
            and revision.get("lock_sha256") ==
                digest(private_input(lock_path, limit=65536))
            and revision.get("reviewer_id") == "J1"
            and revision.get("frozen_model") == selection["model"]
            and revision.get("frozen_provider") == selection["provider"]
            and revision.get("actual_model") == "deepseek-flash"
            and revision.get("model_version") == "DeepSeek-V4.1-Flash-1017"
            and revision.get("actual_provider") == "deepseek-official"
            and revision.get("api_origin") == "https://api.deepseek.com"
            and revision.get("response_format") == "json_object"
            and revision.get("thinking") == "disabled"
            and revision.get("frozen_judge_sha256") ==
                lock["judge_source_sha256"],
            "J1_OFFICIAL_REVISION_INVALID_HOLD",
        )
        revision_sha256 = digest(raw_revision)
        selection = {**selection, "model": "deepseek-flash",
                     "provider": "deepseek-official"}
        require(client_factory is not make_hf_client,
                "J1_OFFICIAL_CLIENT_FACTORY_MISSING_HOLD")
    # Both approvals are separate from the offline lock. Owner must check the
    # actual HF organization budget setting; CLI cannot prove its value.
    require(approve_private_transfer is True, "PRIVATE_TRANSFER_NOT_AUTHORIZED")
    require(approve_paid_calls is True, "PAID_CALLS_NOT_AUTHORIZED")
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
        diagnostic_path = output_dir / f"{entry}.diagnostic.private.json"
        require(not marker_path.exists() and not marker_path.is_symlink()
                and not score_path.exists() and not score_path.is_symlink(),
                "JUDGE_ITEM_ALREADY_ATTEMPTED_HOLD")
        require(not diagnostic_path.exists() and not diagnostic_path.is_symlink(),
                "JUDGE_DIAGNOSTIC_ALREADY_EXISTS_HOLD")
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
            "hf_spend_cap_owner_confirmed": confirm_hf_spending_cap is True,
        }
        if revision_sha256 is not None:
            marker["execution_revision_sha256"] = revision_sha256
        write_once(marker_path, canonical(marker) + b"\n")
        diagnostic = None
        try:
            client = (None if no_reply else client_factory(
                hf_token=hf_token, fixed_provider=selection["provider"]))
            diagnostic = None if no_reply else SafeDiagnosticClient(
                client, item=item, provider=selection["provider"]
            )
            score = judge_one(
                item=item, client=diagnostic, model=selection["model"],
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
            if revision_sha256 is not None:
                receipt["execution_revision_sha256"] = revision_sha256
            if diagnostic is not None:
                audit = {
                    "schema": "storyforge_r60_gold48_execution_revision_private_v1",
                    "revision": "no_thinking_exact_quote_reclassification_v1",
                    "reviewer_id": reviewer_id, "position": position,
                    "blind_id": item["blind_id"],
                    "lock_sha256": marker["lock_sha256"],
                    "model": selection["model"], "provider": selection["provider"],
                    "reasoning_mode": "disabled",
                    "original_model_content_sha256":
                        diagnostic.original_content_sha256,
                    "quote_relocations": diagnostic.quote_relocations,
                    "model_scores_or_flags_changed": False,
                    "model_quote_text_changed": False,
                }
                if revision_sha256 is not None:
                    audit["revision"] = "j1_deepseek_official_json_object_v1"
                    audit["execution_revision_sha256"] = revision_sha256
                    audit["api_origin"] = "https://api.deepseek.com"
                    audit["response_format"] = "json_object"
                    audit["model_version"] = "DeepSeek-V4.1-Flash-1017"
                write_once(
                    output_dir / f"{entry}.execution.private.json",
                    canonical(audit) + b"\n",
                )
            write_once(score_path, canonical(receipt) + b"\n")
        except JudgeHold as exc:
            if not no_reply:
                write_safe_failure(
                    path=diagnostic_path, position=position,
                    reviewer_id=reviewer_id,
                    stage=(diagnostic.info if diagnostic is not None
                           else {"phase": "client_not_constructed"}),
                    error_reason=str(exc),
                )
            raise
        except Exception as exc:  # noqa: BLE001 - safe metadata only
            if not no_reply:
                stage = (diagnostic.info if diagnostic is not None
                         else {"phase": "client_factory_exception",
                               **exception_metadata(exc)})
                write_safe_failure(
                    path=diagnostic_path, position=position,
                    reviewer_id=reviewer_id, stage=stage,
                    error_reason="JUDGE_EXECUTION_OR_WRITE_HOLD",
                )
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

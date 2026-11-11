"""R60 shared fail-closed case isolation for Qwen A25 and GLM B25.

One engine per job. Each frozen review case is attempted independently.
Only known reviewer validation errors become technical-failure receipts;
unexpected exceptions / engine failure halt. A technical failure is NEVER a
quality HOLD and NEVER a successful checkpoint. Append-only, recoverable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

SCHEMA = "storyforge_r60_review_case_isolation_safe_v1"
FAIL_PREFIX = "technical_failure_"
FAIL_SUFFIX = ".safe.json"
REVIEW_ERROR_CODES = frozenset({
    "REVIEW_PROMPT_TOKEN_BUDGET_HOLD",
    "MODEL_GENERATION_INCOMPLETE_HOLD",
    "MODEL_JSON_HOLD", "MODEL_RESPONSE_SCHEMA_HOLD",
    "MODEL_SCORE_OR_SEVERE_HOLD", "MODEL_NOTES_TYPE_HOLD",
    "MODEL_NOTES_TOO_SHORT_HOLD", "MODEL_UNCERTAINTY_TYPE_HOLD",
    "MODEL_UNCERTAINTY_HOLD", "MODEL_SEVERE_MUST_REJECT",
    "MODEL_SEVERE_EVIDENCE_HOLD", "MODEL_NONEXACT_QUOTE_HOLD",
    "MODEL_BELOW_QUALITY_FLOOR_HOLD",
    "QUOTE_REPAIR_FIELD_HOLD", "QUOTE_REPAIR_CANDIDATES_HOLD",
    "QUOTE_REPAIR_ITEMS_HOLD", "QUOTE_REPAIR_SELECTION_HOLD",
    "QUOTE_REPAIR_NONQUOTE_CHANGED_HOLD",
    "QUOTE_REPAIR_VALIDATION_HOLD",
    "QUOTE_REPAIR_TOKEN_ENCODING_HOLD",
    "QUOTE_REPAIR_TOKEN_BUDGET_HOLD",
    "QUOTE_REPAIR_GENERATION_HOLD", "QUOTE_REPAIR_INCOMPLETE_HOLD",
    "QUOTE_REPAIR_JSON_HOLD",
})


class IsolationHold(ValueError):
    pass


def emit(event: str, **data: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **data},
                     sort_keys=True, separators=(",", ":")), flush=True)


def canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(payload: object) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def failure_name(pos: int) -> str:
    return f"{FAIL_PREFIX}{pos:04d}{FAIL_SUFFIX}"


def create_failure(path: Path, *, position: int, worker: object, row: dict,
                   model: str, revision: str, reason: str) -> None:
    if reason not in REVIEW_ERROR_CODES:
        raise IsolationHold("UNKNOWN_REVIEW_ERROR_CODE_HOLD")
    record = {
        "schema": SCHEMA, "position": position,
        "model": model, "revision": revision,
        "input_sha256": worker.input_digest(row),
        "policy": worker.POLICY,
        "technical_reason_code": reason,
    }
    record["receipt_sha256"] = sha(record)
    data = canonical(record) + b"\n"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def validate_failure(path: Path, position: int, worker: object, row: dict,
                     model: str, revision: str) -> str:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= 4096):
        raise IsolationHold("TECHNICAL_RECEIPT_FILE_HOLD")
    try:
        record = json.loads(path.read_bytes())
    except (ValueError, TypeError, OSError) as exc:
        raise IsolationHold("TECHNICAL_RECEIPT_JSON_HOLD") from exc
    if not isinstance(record, dict):
        raise IsolationHold("TECHNICAL_RECEIPT_SCHEMA_HOLD")
    expected = {
        "schema", "position", "model", "revision", "input_sha256",
        "policy", "technical_reason_code", "receipt_sha256",
    }
    without_receipt = {k: v for k, v in record.items()
                       if k != "receipt_sha256"}
    if (set(record) != expected or record["schema"] != SCHEMA
            or record["position"] != position
            or record["model"] != model or record["revision"] != revision
            or record["input_sha256"] != worker.input_digest(row)
            or record["policy"] != worker.POLICY
            or record["technical_reason_code"] not in REVIEW_ERROR_CODES
            or record["receipt_sha256"] != sha(without_receipt)):
        raise IsolationHold("TECHNICAL_RECEIPT_IDENTITY_HOLD")
    return record["technical_reason_code"]


def inspect_attempts(worker: object, rows: list[dict], output: Path,
                     model: str, revision: str, *, resume: bool,
                     target: int) -> tuple[int, int, int]:
    if output.is_symlink() or not output.is_dir():
        raise IsolationHold("OUTPUT_DIRECTORY_HOLD")
    files = list(output.iterdir())
    if not resume and files:
        raise IsolationHold("OUTPUT_NOT_EMPTY_HOLD")
    successes, failures = set(), set()
    for item in files:
        if item.is_symlink() or not item.is_file():
            raise IsolationHold("OUTPUT_FOREIGN_FILE_HOLD")
        m = re.fullmatch(r"review_(\d{4})\.private\.json", item.name)
        f = re.fullmatch(r"technical_failure_(\d{4})\.safe\.json",
                         item.name)
        if (m is None) == (f is None):
            raise IsolationHold("OUTPUT_FOREIGN_FILE_HOLD")
        position = int((m or f).group(1))
        if not 1 <= position <= target:
            raise IsolationHold("OUTPUT_POSITION_HOLD")
        (successes if m else failures).add(position)
    if successes & failures:
        raise IsolationHold("OUTPUT_DUPLICATE_ATTEMPT_HOLD")
    attempts = successes | failures
    if attempts != set(range(1, len(attempts) + 1)):
        raise IsolationHold("OUTPUT_NONCONTIGUOUS_ATTEMPTS_HOLD")
    for pos in sorted(successes):
        if worker.read_checkpoint(output / worker.checkpoint_name(pos),
                                  pos, rows[pos - 1], model, revision) is None:
            raise IsolationHold("OUTPUT_CHECKPOINT_MISSING_HOLD")
    for pos in sorted(failures):
        validate_failure(output / failure_name(pos), pos, worker,
                         rows[pos - 1], model, revision)
    return len(attempts), len(successes), len(failures)


def run_isolated(worker: object, rows: list[dict], output: Path,
                 local: Path, *, model: str, revision: str,
                 limit: int, batch_size: int, max_model_len: int,
                 max_output_tokens: int, wall_seconds: int,
                 resume: bool, hf_tokenizer: object, vllm: object,
                 min_remaining_seconds: int = 120,
                 attempt_diagnostic_guard: object = None,
                 stop_after_attempts: int | None = None) -> dict:
    if (limit < 1 or limit > len(rows) or batch_size < 1 or batch_size > 100
            or max_model_len != 32768 or max_output_tokens != 2400
            or not 120 <= wall_seconds <= 43200):
        raise IsolationHold("ISOLATION_SCOPE_OR_BUDGET_HOLD")
    if stop_after_attempts is not None and (not 1 <= stop_after_attempts <= limit or resume):
        raise IsolationHold("PROBE_STOP_SCOPE_HOLD")
    attempted, successes, failures = inspect_attempts(
        worker, rows, output, model, revision, resume=resume, target=limit)
    if attempted:
        emit("ISOLATION_RESUME_VERIFIED", attempted=attempted,
             verified=successes, technical_failures=failures)
    original_tokenizer = hf_tokenizer.from_pretrained
    original_llm = vllm.LLM
    engine = None
    tokenizer_cache = None
    engine_count = 0
    init_started = False

    def load_tokenizer(name, *args, **kwargs):
        nonlocal tokenizer_cache
        if name == str(local):
            if kwargs.get("revision") not in (None, revision):
                raise IsolationHold("LOCAL_TOKENIZER_REVISION_HOLD")
            stripped = dict(kwargs)
            stripped.pop("revision", None)
            return original_tokenizer(str(local), *args, **stripped)
        if name != model or kwargs.get("revision") != revision:
            raise IsolationHold("TOKENIZER_IDENTITY_HOLD")
        if tokenizer_cache is None:
            stripped = dict(kwargs)
            stripped.pop("revision")
            emit("LOCAL_TOKENIZER_INIT")
            tokenizer_cache = original_tokenizer(str(local), *args, **stripped)
        return tokenizer_cache

    def load_engine(*args, **kwargs):
        nonlocal engine, engine_count, init_started
        if (args or kwargs.get("model") != model
                or kwargs.get("revision") != revision
                or kwargs.get("tokenizer_revision") != revision):
            raise IsolationHold("MODEL_IDENTITY_HOLD")
        if engine is None:
            if init_started:
                raise IsolationHold("ENGINE_REINIT_AFTER_FAILURE_HOLD")
            init_started = True
            adapted = dict(kwargs)
            adapted["model"] = str(local)
            adapted["tokenizer"] = str(local)
            adapted.pop("revision")
            adapted.pop("tokenizer_revision")
            emit("REAL_ENGINE_INIT_START")
            try:
                engine = original_llm(**adapted)
            except Exception as exc:
                emit("REAL_ENGINE_INIT_HOLD",
                     exception_class=type(exc).__name__)
                raise
            engine_count += 1
            emit("REAL_ENGINE_READY", engine_init_count=engine_count)
        return engine

    hf_tokenizer.from_pretrained = staticmethod(load_tokenizer)
    vllm.LLM = load_engine
    start_time = time.monotonic()
    try:
        while attempted < limit:
            if stop_after_attempts is not None and attempted >= stop_after_attempts:
                emit("ISOLATION_PROBE_STOP", attempted=attempted,
                     stop_after_attempts=stop_after_attempts,
                     target=limit, verified=successes,
                     technical_failures=failures)
                break
            remaining = wall_seconds - (time.monotonic() - start_time)
            if remaining < min_remaining_seconds:
                emit("ISOLATION_WALL_BUDGET_HOLD", attempted=attempted,
                     target=limit)
                break
            pos = attempted + 1
            if (pos - 1) % batch_size == 0:
                emit("BATCH_START", start=pos,
                     batch_size=min(batch_size, limit - pos + 1),
                     already_attempted=attempted)
            file = output / worker.checkpoint_name(pos)
            if file.exists() or (output / failure_name(pos)).exists():
                raise IsolationHold("POSITION_ALREADY_EXISTS_HOLD")
            emit("CASE_START", position=pos)
            try:
                worker.inference(rows, output, model, revision, pos, 1,
                                 max_model_len, max_output_tokens,
                                 max(min_remaining_seconds, int(remaining)))
            except Exception as exc:
                if not isinstance(exc, worker.ReviewError):
                    emit("UNEXPECTED_RUNTIME_HOLD", position=pos,
                         exception_class=type(exc).__name__)
                    raise
                reason = str(exc)
                # Unknown reviewer error strings never reach a log or receipt.
                if reason not in REVIEW_ERROR_CODES:
                    emit("UNKNOWN_REVIEW_FAILURE_HOLD", position=pos)
                    raise IsolationHold("UNKNOWN_REVIEW_ERROR_CODE_HOLD") from None
                if file.exists() or file.is_symlink():
                    # Do not invent technical failure if checkpoint write
                    # succeeded before an exception.
                    raise IsolationHold("CHECKPOINT_WRITTEN_BEFORE_ERROR_HOLD") from None
                create_failure(output / failure_name(pos),
                               position=pos, worker=worker, row=rows[pos - 1],
                               model=model, revision=revision, reason=reason)
                validate_failure(output / failure_name(pos), pos, worker,
                                 rows[pos - 1], model, revision)
                failures += 1
                # QuoteValidationError inherits ReviewError and uses the
                # identical error string. Distinguish the exact exception
                # class without exposing quotes or exception arguments.
                kind = (
                    "QUOTE_VALIDATION" if (
                        hasattr(worker, "QuoteValidationError")
                        and isinstance(exc, worker.QuoteValidationError)
                    ) else "DIRECT_REVIEW_ERROR" if type(exc) is worker.ReviewError
                    else "REVIEW_ERROR_SUBCLASS"
                )
                emit("CASE_TECHNICAL_FAILURE", position=pos,
                     reason_code=reason, exception_kind=kind)
            else:
                if worker.read_checkpoint(file, pos, rows[pos - 1],
                                          model, revision) is None:
                    raise IsolationHold("MISSING_VALID_CHECKPOINT_HOLD")
                successes += 1
                emit("CASE_VERIFIED", position=pos)
            # Fail before attempting a second paid case if the opt-in
            # observer never saw the real validator's first case.
            if attempt_diagnostic_guard is not None:
                attempt_diagnostic_guard(pos)
            attempted += 1
            if attempted % batch_size == 0 or attempted == limit:
                emit("BATCH_COMPLETE", attempted=attempted,
                     verified=successes, technical_failures=failures,
                     engine_init_count=engine_count)
        done = attempted == limit
        if done:
            emit("ALL_CASES_ATTEMPTED", attempted=attempted,
                 verified=successes, technical_failures=failures,
                 engine_init_count=engine_count)
            if failures == 0:
                emit("CONTINUOUS_REVIEW_COMPLETE", completed=successes,
                     engine_init_count=engine_count)
        return {"attempted": attempted, "verified": successes,
                "technical_failures": failures, "all_attempted": done,
                "all_verified": done and failures == 0}
    finally:
        hf_tokenizer.from_pretrained = staticmethod(original_tokenizer)
        vllm.LLM = original_llm

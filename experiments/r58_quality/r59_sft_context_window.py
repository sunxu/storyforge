""""Rebuild an R59 preview with a complete recent history suffix under 16K.

This is an engineering-only adapter: the approved System Prompt and original
final target remain byte-identical; only a leading prefix of history messages
may be removed, and trimming starts at a User-message boundary.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

MODEL = "Qwen/Qwen3.8-27B"
MODEL_REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
MODEL_LENGTH = 16384
MEASUREMENT_LENGTH = 131072
READ_LIMIT = 160 * 1024 * 1024
SCHEMA = "storyforge-r59-context-window-safe-v1"
POLICY = "R59_RECENT_COMPLETE_USER_TURN_SUFFIX_V1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _input_messages_digest(messages: list[dict]) -> str:
    serialized = [
        {"role": message["role"], "content": message["content"]}
        for message in messages[:-1]
    ]
    return hashlib.sha256(_canonical(serialized)).hexdigest()


def rebuild_preview_rows(rows, measure_tokens, *, max_length: int = MODEL_LENGTH,
                         validate_row=None):
    """Return rebuilt rows and a SAFE summary; never mutate input rows.

    `measure_tokens` must return the real, untruncated template input_ids length.
    `validate_row` is the existing R59 preview contract validator.
    """
    if (not isinstance(rows, list) or not rows or type(max_length) is not int
            or not 0 < max_length <= MODEL_LENGTH or not callable(measure_tokens)):
        raise ValueError("INPUT_OR_BUDGET_INVALID")
    if validate_row is None:
        from r59_sft_collator_cpu import validate_preview_row
        validate_row = validate_preview_row

    rebuilt, row_stats = [], []
    total_dropped = 0
    unfit = 0
    for ordinal, source in enumerate(rows, 1):
        validate_row(source)
        original_messages = source["messages"]
        history = original_messages[1:-1]
        # Candidate 1 preserves the complete history (including assistant-first).
        # Every later candidate begins at a complete User turn boundary.
        starts = [1] + [
            index for index, message in enumerate(original_messages[1:-1], 1)
            if message["role"] == "user" and index != 1
        ]
        best = None
        for start in starts:
            candidate = copy.deepcopy(source)
            candidate_messages = (
                [copy.deepcopy(original_messages[0])]
                + copy.deepcopy(original_messages[start:-1])
                + [copy.deepcopy(original_messages[-1])]
            )
            candidate["messages"] = candidate_messages
            token_count = measure_tokens(candidate)
            if type(token_count) is not int or token_count <= 0:
                raise ValueError("TOKEN_LENGTH_INVALID")
            retained_count = len(candidate_messages) - 2
            if token_count <= max_length and (
                best is None or retained_count > best[0]
            ):
                best = (retained_count, start, token_count, candidate)

        if best is None:
            unfit += 1
            row_stats.append({
                "row": ordinal,
                "status": "CURRENT_USER_AND_TARGET_OR_SUFFIX_UNFIT",
                "original_history_messages": len(history),
            })
            continue

        retained_count, start, token_count, candidate = best
        dropped_count = start - 1
        metadata = candidate["metadata"]
        original_digest = metadata["input_messages_sha256"]
        metadata["source_input_messages_sha256"] = original_digest
        metadata["input_messages_sha256"] = _input_messages_digest(
            candidate["messages"]
        )
        metadata["context_window_policy"] = POLICY
        metadata["context_window_max_length"] = MODEL_LENGTH
        metadata["retained_history_start_message_index"] = start
        metadata["dropped_history_messages"] = dropped_count
        metadata["retained_history_messages"] = retained_count
        validate_row(candidate)
        if (candidate["messages"][0]["content"] != original_messages[0]["content"]
                or candidate["messages"][-1]["content"]
                != original_messages[-1]["content"]
                or candidate["messages"][-1]["role"] != "assistant"
                or candidate["messages"][-1]["loss"] is not True
                or candidate["messages"][-2]["role"] != "user"
                or any(message["loss"] is not False
                       for message in candidate["messages"][:-1])):
            raise ValueError("MESSAGE_OR_LOSS_INVARIANT")
        rebuilt.append(candidate)
        total_dropped += dropped_count
        row_stats.append({
            "row": ordinal,
            "status": "FITS_16K",
            "original_history_messages": len(history),
            "retained_history_messages": retained_count,
            "dropped_history_messages": dropped_count,
            "token_length": token_count,
        })

    status = (
        "R59_CONTEXT_WINDOW_REBUILT__NOT_ADMITTED"
        if not unfit else "R59_CONTEXT_WINDOW_HOLD"
    )
    safe = {
        "schema": SCHEMA,
        "status": status,
        "policy": POLICY,
        "rows": len(rows),
        "rows_rebuilt": len(rebuilt) if not unfit else 0,
        "rows_unfit": unfit,
        "messages_dropped": total_dropped,
        "max_length": MODEL_LENGTH,
        "system_prompt_preserved": True,
        "final_user_preserved": True,
        "target_assistant_preserved": True,
        "historical_loss_false": True,
        "complete_message_boundaries_only": True,
        "row_results": row_stats,
        "quality_v1_admitted": 0,
        "dataset_frozen": False,
        "training_authorized": False,
        "gpu_started": False,
        "training_performed": False,
        "private_values_emitted": False,
    }
    return (rebuilt if not unfit else []), safe


def _extract_token_count(encoded, messages) -> int:
    try:
        from storyforge_dataset.token_preflight import extract_input_ids
    except ModuleNotFoundError:
        # HF Job bundles the exact shared module as token_core.py beside this adapter.
        from token_core import extract_input_ids
    prompt_chars = sum(len(message["content"]) for message in messages)
    return len(extract_input_ids(encoded["input_ids"], prompt_chars=prompt_chars))


def _write_create_only(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(private_input: Path, output_dir: Path):
    if (not private_input.is_absolute() or private_input.is_symlink()
            or not private_input.is_file()):
        raise ValueError("PRIVATE_INPUT_INVALID")
    info = private_input.stat()
    if (stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or not 0 < info.st_size <= READ_LIMIT):
        raise ValueError("PRIVATE_INPUT_PERMISSIONS_OR_SIZE_INVALID")
    if (output_dir.exists() or output_dir.is_symlink()
            or not output_dir.is_absolute() or not output_dir.parent.is_dir()
            or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700
            or output_dir.resolve().is_relative_to(Path.cwd().resolve())):
        raise ValueError("OUTPUT_DIRECTORY_INVALID")

    try:
        rows = [
            json.loads(line)
            for line in private_input.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (ValueError, UnicodeError):
        raise ValueError("PRIVATE_INPUT_JSONL_INVALID") from None
    if not 1 <= len(rows) <= 192:
        raise ValueError("PRIVATE_INPUT_ROW_COUNT_INVALID")

    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["USE_HF"] = "true"
    from swift import get_processor, get_template
    from r59_sft_collator_cpu import run as run_actual_collator

    processor = get_processor(MODEL, revision=MODEL_REVISION)
    template = get_template(
        processor, loss_scale="last_round", max_length=MEASUREMENT_LENGTH + 1,
        add_non_thinking_prefix=False,
    )
    template.set_mode("train")

    def measure(candidate):
        return _extract_token_count(
            template.encode(candidate), candidate["messages"]
        )

    rebuilt, safe = rebuild_preview_rows(rows, measure)
    if not rebuilt:
        return safe

    with tempfile.TemporaryDirectory(prefix="r59-context-window-") as temp_dir:
        staged = Path(temp_dir) / "candidate.jsonl"
        payload = b"".join(_canonical(row) + b"\n" for row in rebuilt)
        _write_create_only(staged, payload)
        collator_report = run_actual_collator(staged)

    if (collator_report.get("status") != "R59_ACTUAL_SWIFT_COLLATOR_PASS__NOT_ADMITTED"
            or collator_report.get("checked") != len(rebuilt)
            or collator_report.get("passed") != len(rebuilt)):
        safe["status"] = "R59_CONTEXT_WINDOW_COLLATOR_HOLD"
        safe["actual_collator_status"] = "HOLD"
        return safe

    output_dir.mkdir(mode=0o700)
    safe["actual_collator"] = collator_report
    safe["status"] = "R59_CONTEXT_WINDOW_AND_COLLATOR_PASS__NOT_ADMITTED"
    try:
        _write_create_only(
            output_dir / "R59_SFT_CONTEXT_WINDOW_PRIVATE.jsonl", payload
        )
        _write_create_only(
            output_dir / "R59_SFT_CONTEXT_WINDOW_SAFE.json",
            _canonical(safe) + b"\n",
        )
    except BaseException:
        for item in output_dir.iterdir():
            item.unlink()
        output_dir.rmdir()
        raise
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.private_input, args.output_dir)
        code = 0 if report["status"] in {
            "R59_CONTEXT_WINDOW_REBUILT__NOT_ADMITTED",
            "R59_CONTEXT_WINDOW_AND_COLLATOR_PASS__NOT_ADMITTED",
        } else 42
    except Exception:  # noqa: BLE001 - do not emit private paths, text or token IDs
        report = {
            "schema": SCHEMA,
            "status": "R59_CONTEXT_WINDOW_HOLD",
            "reason_code": "PRIVATE_INPUT_OR_TOKENIZER_OR_COLLATOR_ERROR",
            "quality_v1_admitted": 0,
            "dataset_frozen": False,
            "training_authorized": False,
            "gpu_started": False,
            "training_performed": False,
            "private_values_emitted": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())

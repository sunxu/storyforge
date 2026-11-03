"""Build a private, non-admitted R59 SFT message-shape preview.

Reuses the R52-approved R27 generic no-card input design by exact System
Prompt bytes. Preserves every staged visible-history message in order and
appends the original target as the sole loss=True Assistant message.

This is engineering-only: no quality admission, dataset freeze, HF job,
inference, training, GPU, R50, database, or source mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from gold_source_context_stage import _private_file, _read_rows
from quality_v1 import canonical, sha

SCHEMA = "storyforge-r59-sft-shape-preview-safe-v1"
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
R27_SYSTEM_SHA256 = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
MAX_BYTES = 160 * 1024 * 1024
ROLES = {"user", "assistant"}


class PreviewHold(ValueError):
    pass


def _validate_history(messages):
    if not isinstance(messages, list) or len(messages) < 2:
        raise PreviewHold("HISTORY_INVALID")
    if (not isinstance(messages[0], dict)
            or messages[0].get("role") != "system"
            or set(messages[0]) != {"role", "content"}
            or not isinstance(messages[0].get("content"), str)
            or not messages[0]["content"].strip()
            or sha(messages[0]["content"].encode("utf-8")) != R27_SYSTEM_SHA256):
        raise PreviewHold("APPROVED_GENERIC_SYSTEM_PIN_MISMATCH")
    history = messages[1:]
    if (not history or not isinstance(history[-1], dict)\n            or history[-1].get("role") != "user"):
        raise PreviewHold("CURRENT_USER_MISSING")
    previous = None
    for message in history:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message.get("role") not in ROLES
                or not isinstance(message.get("content"), str)
                or not message["content"].strip()
                or message["role"] == previous):
            raise PreviewHold("HISTORY_STRUCTURE_INVALID")
        previous = message["role"]
    return history


def build_preview(staged_rows):
    if not isinstance(staged_rows, list) or not staged_rows:
        raise PreviewHold("STAGED_ROWS_INVALID")
    output = []
    seen_cases, seen_targets = set(), set()
    assistant_first = 0
    history_messages = 0
    for row in staged_rows:
        if not isinstance(row, dict):
            raise PreviewHold("STAGED_ROW_INVALID")
        if (row.get("schema") != STAGE_SCHEMA
                or row.get("status") != STAGE_STATUS):
            continue
        case_id, target = row.get("case_id"), row.get("target_text")
        target_sha = row.get("target_sha256")
        if (not isinstance(case_id, str) or not case_id or case_id in seen_cases
                or not isinstance(target, str) or not target.strip()
                or not isinstance(target_sha, str)
                or hashlib.sha256(target.encode("utf-8")).hexdigest() != target_sha
                or target_sha in seen_targets):
            raise PreviewHold("TARGET_IDENTITY_INVALID")
        messages = row.get("messages")
        history = _validate_history(messages)
        if history[0]["role"] == "assistant":
            assistant_first += 1
        history_messages += len(history)

        # Copy the original message sequence exactly. Only add loss=False to
        # historical assistant messages and append the original target.
        packed = []
        for message in messages:
            packed.append({
                "role": message["role"],
                "content": message["content"],
                "loss": False,
            })
        packed.append({"role": "assistant", "content": target, "loss": True})
        if (packed[-2]["role"] != "user"
                or sum(message["loss"] is True for message in packed) != 1
                or packed[-1]["role"] != "assistant"
                or packed[-1]["content"] != target):
            raise PreviewHold("LAST_ASSISTANT_LOSS_MASK_INVALID")
        seen_cases.add(case_id)
        seen_targets.add(target_sha)
        output.append({
            "messages": packed,
            "metadata": {
                "source_target_sha256": target_sha,
                "input_messages_sha256": row.get("input_messages_sha256"),
                "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
            },
        })
    if not output:
        raise PreviewHold("NO_READY_STAGED_ROWS")
    return output, {
        "schema": SCHEMA,
        "status": "R59_SFT_SHAPE_PREVIEW_BUILT__NOT_ADMITTED",
        "preview_rows": len(output),
        "historical_messages_preserved": history_messages,
        "assistant_first_histories": assistant_first,
        "all_history_preserved_in_order": True,
        "last_assistant_only_loss_true": True,
        "approved_generic_system_sha256": R27_SYSTEM_SHA256,
        "system_prompt_bytes_verified": True,
        "world_card_inserted": False,
        "quality_v1_admitted": 0,
        "dataset_frozen": False,
        "tokenizer_collator_checked": False,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "source_modified": False,
        "private_values_emitted": False,
    }


def _create_only(path: Path, payload: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(staged_path: Path, receipt_path: Path, output_dir: Path):
    staged_raw = _private_file(staged_path, MAX_BYTES)
    receipt_raw = _private_file(receipt_path, 1024 * 1024)
    try:
        receipt = json.loads(receipt_raw)
    except (ValueError, UnicodeError):
        raise PreviewHold("STAGING_RECEIPT_INVALID") from None
    if (receipt.get("schema") != "storyforge-gold-quality-supabase-source-stage-safe-v1"
            or receipt.get("staged_file_sha256") != sha(staged_raw)
            or receipt.get("system_prompt_sha256") != R27_SYSTEM_SHA256):
        raise PreviewHold("STAGING_RECEIPT_OR_SYSTEM_PIN_MISMATCH")
    rows, safe = build_preview(_read_rows(staged_raw))
    if output_dir.exists() or output_dir.is_symlink():
        raise PreviewHold("OUTPUT_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise PreviewHold("OUTPUT_INSIDE_REPO")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise PreviewHold("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        payload = b"".join(canonical(row) + b"\\n" for row in rows)
        _create_only(output_dir / "R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl", payload)
        _create_only(
            output_dir / "R59_SFT_SHAPE_PREVIEW_SAFE.json",
            json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\\n",
        )
    except BaseException:
        for item in output_dir.iterdir():
            item.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-jsonl", type=Path, required=True)
    parser.add_argument("--staging-safe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.staged_jsonl, args.staging_safe, args.output_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except PreviewHold as exc:
        reason = str(exc)
    except OSError:
        reason = "INPUT_OR_OUTPUT_IO_HOLD"
    except Exception:  # noqa: BLE001 - never expose private exception values
        reason = "INTERNAL_HOLD"
    print(json.dumps({
        "schema": SCHEMA, "status": "R59_SFT_SHAPE_PREVIEW_HOLD",
        "reason_code": reason, "quality_v1_admitted": 0,
        "training_authorized": False, "gpu_started": False,
        "r50_accessed": False, "private_values_emitted": False,
    }, sort_keys=True))
    return 42


if __name__ == "__main__":
    raise SystemExit(main())

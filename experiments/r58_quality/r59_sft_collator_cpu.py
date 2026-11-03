"""Actual CPU-only Qwen/ms-swift tokenizer + collator check for R59 preview.

Accepts only the R59 no-card engineering preview. Never performs inference,
training, admission, dataset freeze, R50 access, or GPU execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

MODEL = "Qwen/Qwen3.8-27B"
MODEL_REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
MODEL_LENGTH = 16384
R27_SYSTEM_SHA256 = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
READ_LIMIT = 160 * 1024 * 1024


def _array(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().tolist()
    elif hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    return value


def validate_preview_row(row):
    if not isinstance(row, dict) or not isinstance(row.get("messages"), list):
        raise TypeError("row format")
    messages = row["messages"]
    if len(messages) < 4:
        raise ValueError("message count")
    if (messages[0].get("role") != "system"
            or hashlib.sha256(messages[0].get("content", "").encode("utf-8")).hexdigest()
            != R27_SYSTEM_SHA256):
        raise ValueError("approved system prompt pin")
    if messages[-1].get("role") != "assistant" or messages[-1].get("loss") is not True:
        raise ValueError("target position or loss")
    if messages[-2].get("role") != "user":
        raise ValueError("current user position")
    if any(not isinstance(message, dict)
           or set(message) != {"role", "content", "loss"}
           or message.get("role") not in ("system", "user", "assistant")
           or not isinstance(message.get("content"), str)
           or not message["content"].strip()
           or type(message.get("loss")) is not bool
           for message in messages):
        raise ValueError("message schema")
    if any(message["loss"] is not False for message in messages[:-1]):
        raise ValueError("historical loss flag")
    previous = None
    for message in messages[1:]:
        role = message["role"]
        if role == previous:
            raise ValueError("history role alternation")
        previous = role
    metadata = row.get("metadata")
    if (not isinstance(metadata, dict)
            or metadata.get("status") != "ENGINEERING_PREVIEW_NOT_ADMITTED"):
        raise ValueError("preview metadata")
    target_sha = metadata.get("source_target_sha256")
    actual_sha = hashlib.sha256(messages[-1]["content"].encode("utf-8")).hexdigest()
    if target_sha != actual_sha:
        raise ValueError("target hash")
    original_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in messages[:-1]
    ]
    input_digest = hashlib.sha256(json.dumps(
        original_messages, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if metadata.get("input_messages_sha256") != input_digest:
        raise ValueError("input message hash")
    return len(messages)


def run(private_input: Path, model: str = MODEL):
    if (not private_input.is_absolute() or private_input.is_symlink()
            or not private_input.is_file()):
        raise ValueError("input file")
    info = private_input.stat()
    if (stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or not 0 < info.st_size <= READ_LIMIT):
        raise ValueError("input permissions or size")
    raw = private_input.read_bytes()
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise ValueError("input jsonl") from None
    if not 1 <= len(rows) <= 192 or model != MODEL:
        raise ValueError("input count or model")
    message_counts = [validate_preview_row(row) for row in rows]

    # Force CPU before importing the model stack. No model weights are loaded.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    from swift import get_processor, get_template

    template = get_template(
        get_processor(model, revision=MODEL_REVISION),
        loss_scale="last_round",
        max_length=MODEL_LENGTH + 1,
        add_non_thinking_prefix=False,
    )
    template.set_mode("train")
    if getattr(template.loss_scale, "base_strategy", None) != "last_round":
        raise ValueError("loss strategy")
    lengths, supervised, passed = [], [], 0
    for row in rows:
        encoded = template.encode(row)
        actual = template.data_collator([encoded])
        ids = _array(actual["input_ids"])
        labels = _array(actual["labels"])
        encoded_ids = _array(encoded["input_ids"])
        encoded_labels = _array(encoded["labels"])
        if ids != encoded_ids or labels != encoded_labels:
            raise ValueError("collator mutation")
        if (not isinstance(ids, list) or not isinstance(labels, list)
                or len(ids) != len(labels) or not 0 < len(ids) < MODEL_LENGTH + 1):
            raise ValueError("token length or shape")
        positions = [index for index, label in enumerate(labels) if label != -100]
        if not positions or any(labels[index] != ids[index] for index in positions):
            raise ValueError("supervision labels")
        lengths.append(len(ids))
        supervised.append(len(positions))
        passed += 1

    ordered = sorted(lengths)
    supervised.sort()
    return {
        "schema": "storyforge-r59-actual-swift-collator-safe-v1",
        "status": "R59_ACTUAL_SWIFT_COLLATOR_PASS__NOT_ADMITTED",
        "checked": len(rows),
        "passed": passed,
        "model": model,
        "model_revision": MODEL_REVISION,
        "model_revision_pinned": True,
        "loss_scale": "last_round",
        "max_length": MODEL_LENGTH,
        "token_min": ordered[0],
        "token_median": ordered[len(ordered) // 2],
        "token_p95": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))],
        "token_max": ordered[-1],
        "messages_min": min(message_counts),
        "messages_max": max(message_counts),
        "supervised_tokens_min": min(supervised),
        "supervised_tokens_max": max(supervised),
        "training_performed": False,
        "gpu_used": False,
        "quality_v1_admitted": 0,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-input", type=Path, required=True)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    try:
        report = run(args.private_input, args.model)
        code = 0
    except Exception:  # noqa: BLE001 - never emit private paths, text or token IDs
        report = {
            "schema": "storyforge-r59-actual-swift-collator-safe-v1",
            "status": "R59_ACTUAL_SWIFT_COLLATOR_HOLD",
            "gpu_used": False,
            "training_performed": False,
            "quality_v1_admitted": 0,
            "r50_accessed": False,
            "private_values_emitted": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())

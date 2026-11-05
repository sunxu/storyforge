#!/usr/bin/env python3
"""R58 CPU-only actual ms-swift Collator verification for PRIVATE 132 probe.

This does not run model weights, inference, training, nor grant quality admission.
Use only with private probe created by r58_assistant_first_sft_probe.py.
No private text or token IDs should appear on stdout.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

MODEL = "Qwen/Qwen3.8-27B"
MODEL_LENGTH = 16384


def array(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().tolist()
    elif hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    return value


def run(private_input, model=MODEL):
    if (not private_input.is_absolute() or not private_input.is_file()
            or private_input.is_symlink()
            or private_input.stat().st_size <= 0
            or private_input.stat().st_size > 120 * 1024 * 1024):
        raise ValueError("invalid private probe input")
    rows = [json.loads(x) for x in private_input.read_bytes().splitlines() if x.strip()]
    if len(rows) != 132:
        raise ValueError("expected 132 probe rows")
    if model != MODEL:
        raise ValueError("model mismatch")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    from swift import get_processor, get_template
    template = get_template(get_processor(model), loss_scale="last_round",
                            max_length=MODEL_LENGTH,
                            add_non_thinking_prefix=False)
    template.set_mode("train")
    if getattr(template.loss_scale, "base_strategy", None) != "last_round":
        raise ValueError("loss strategy mismatch")
    lengths, supervised = [], []
    for row in rows:
        messages = row["messages"]
        if (not isinstance(messages, list) or len(messages) < 4
                or messages[0].get("role") != "system"
                or messages[1].get("role") != "assistant"
                or messages[-2].get("role") != "user"
                or messages[-1].get("role") != "assistant"
                or messages[-1].get("loss") is not True
                or any(x.get("loss") is not False for x in messages[:-1])):
            raise ValueError("message order or loss flags invalid")
        encoded = template.encode(row)
        actual = template.data_collator([encoded])
        ids, labels = array(actual["input_ids"]), array(actual["labels"])
        if ids != array(encoded["input_ids"]) or labels != array(encoded["labels"]):
            raise ValueError("collator changed token ids or labels")
        if (not isinstance(ids, list) or not isinstance(labels, list)
                or len(ids) != len(labels) or not 0 < len(ids) < MODEL_LENGTH):
            raise ValueError("invalid encoded sequence length")
        positions = [p for p, label in enumerate(labels) if label != -100]
        if not positions or any(labels[p] != ids[p] for p in positions):
            raise ValueError("invalid supervision labels")
        lengths.append(len(ids))
        supervised.append(len(positions))
    lengths.sort()
    supervised.sort()
    return {
        "schema": "r58_actual_swift_collator_132_safe_v1",
        "status": "R58_ACTUAL_SWIFT_DATA_COLLATOR_132_132_PASS__NOT_ADMITTED",
        "checked": 132, "passed": 132, "model": model,
        "model_revision_pinned": False,
        "loss_scale": "last_round", "max_length": MODEL_LENGTH,
        "token_min": lengths[0], "token_median": lengths[65],
        "token_p95": lengths[125], "token_max": lengths[-1],
        "supervised_tokens_min": supervised[0],
        "supervised_tokens_max": supervised[-1],
        "training_performed": False, "gpu_used": False,
        "quality_v1_admitted": 0, "r50_accessed": False,
        "private_text_emitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-input", type=Path, required=True)
    p.add_argument("--model", default=MODEL)
    args = p.parse_args()
    try:
        report = run(args.private_input, args.model)
        code = 0
    except Exception:
        report = {
            "schema": "r58_actual_swift_collator_132_safe_v1",
            "status": "R58_ACTUAL_SWIFT_COLLATOR_INVALID__HOLD",
            "gpu_used": False, "training_performed": False,
            "quality_v1_admitted": 0, "private_text_emitted": False,
        }
        code = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())

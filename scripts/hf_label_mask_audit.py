#!/usr/bin/env python3
"""Audit actual ms-swift labels for last-answer-only supervision, without GPU."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--model", default="Qwen/Qwen3.8-27B")
    p.add_argument("--samples", type=int, default=3)
    args = p.parse_args()

    from swift import get_processor, get_template

    processor = get_processor(args.model)
    template = get_template(processor, loss_scale="default", max_length=16384)
    template.set_mode("train")
    audited = 0
    with args.dataset.open(encoding="utf-8") as stream:
        for raw in stream:
            if not raw.strip():
                continue
            row = json.loads(raw)
            messages = row["messages"]
            if messages[-1].get("loss") is not True:
                raise ValueError("target is not marked loss=true")
            encoded = template.encode(row)
            labels = encoded["labels"]
            ids = encoded["input_ids"]
            if len(ids) != len(labels):
                raise ValueError("input_ids and labels length mismatch")
            supervised = [x for x in labels if x != -100]
            if not supervised:
                raise ValueError("zero supervised tokens")
            # Compare against a counterfactual sample with the gold answer masked.
            masked = {"messages": [dict(m) for m in messages]}
            masked["messages"][-1]["loss"] = False
            encoded_masked = template.encode(masked)
            masked_labels = encoded_masked["labels"]
            leaked = sum(x != -100 for x in masked_labels)
            if leaked:
                raise ValueError(f"history/system leakage: {leaked} supervised tokens")
            # A counterfactual fully masked target should preserve input segmentation.
            if list(encoded_masked["input_ids"]) != list(ids):
                raise ValueError("mask audit changed input token IDs")
            print(json.dumps({
                "sample": audited + 1,
                "tokens": len(ids),
                "supervised_tokens": len(supervised),
                "counterfactual_supervised_tokens": leaked,
                "status": "PASS",
            }))
            audited += 1
            if audited >= args.samples:
                break
    if audited != args.samples:
        raise ValueError(f"requested {args.samples} samples, got {audited}")
    print(f"LABEL_MASK_AUDIT_PASS {audited}/{audited}")

if __name__ == "__main__":
    main()

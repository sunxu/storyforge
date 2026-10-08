"""Audit labels produced by the installed ms-swift template."""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any


def _list_ints(value: Any) -> list[int]:
    if value is None:
        return []
    if hasattr(value, "detach"):
        value = value.detach().cpu().tolist()
    elif hasattr(value, "tolist"):
        value = value.tolist()
    return [int(x) for x in value]


class _LossScaleCapture:
    def __init__(self, wrapped: Any) -> None:
        self.wrapped = wrapped
        self.calls: list[dict[str, Any]] = []

    def __call__(self, context_list, context_types, messages, **kwargs):
        self.calls.append({"contexts": copy.deepcopy(context_list),
                           "context_types": list(context_types),
                           "messages": copy.deepcopy(messages), "kwargs": kwargs})
        return self.wrapped(context_list, context_types, messages, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.wrapped, name)


def _encode_with_capture(template: Any, row: dict[str, Any]):
    old_cache = template._loss_scale_cache
    old_swift_encode = template._swift_encode
    strategy = template.loss_scale
    capture = _LossScaleCapture(strategy)
    holder: dict[str, Any] = {}

    def wrapped(inputs, *args, **kwargs):
        holder["inputs"] = copy.deepcopy(inputs)
        return old_swift_encode(inputs, *args, **kwargs)

    try:
        template._loss_scale_cache = dict(old_cache)
        template._loss_scale_cache[template._loss_scale] = capture
        template._swift_encode = wrapped
        return template.encode(row), capture, holder
    finally:
        template._loss_scale_cache = old_cache
        template._swift_encode = old_swift_encode


def _type_name(value: Any) -> str:
    # ms-swift 4.5.3 exposes ContextType members as lowercase strings
    # ("response"/"suffix"/"other"), while older builds may expose enum names.
    name = getattr(value, "name", value)
    return str(name).split(".")[-1].upper()


def _semantic_labels(template: Any, capture: _LossScaleCapture, inputs: Any,
                     input_ids: list[int]):
    if len(capture.calls) != 1:
        raise ValueError(f"expected one loss_scale call, got {len(capture.calls)}")
    call = capture.calls[0]
    contexts, types = call["contexts"], call["context_types"]
    if len(contexts) != len(types):
        raise ValueError("loss_scale contexts/context_types length mismatch")
    responses = [i for i, t in enumerate(types) if _type_name(t) == "RESPONSE"]
    if not responses:
        raise ValueError("no final assistant RESPONSE segment")
    final_response = responses[-1]
    weights = []
    for i, t in enumerate(types):
        name = _type_name(t)
        if name == "RESPONSE" and i == final_response:
            weights.append(1.0)
        elif name == "SUFFIX" and i > final_response:
            weights.append(2.0)
        else:
            weights.append(0.0)
    native_inputs = copy.deepcopy(inputs)
    simplified, simplified_weights = template._simplify_context_list(
        contexts, weights, native_inputs)
    expected_ids, expected_labels, _expected_loss_scale = template._encode_context_list(
        simplified, simplified_weights)
    if expected_ids != input_ids:
        raise ValueError("semantic context encoding does not match actual input_ids")
    if expected_labels:
        expected_labels[0] = -100
    final: set[int] = set()
    pos = 0
    for context, weight in zip(simplified, simplified_weights):
        tokens = context if not isinstance(context, str) else template._tokenize(context)
        if weight == 1.0:
            final.update(range(pos, pos + len(tokens)))
        pos += len(tokens)
    # Template.encode intentionally masks the first token for causal-LM
    # shifting, even when it belongs to the final response.
    final.discard(0)
    suffix: set[int] = set()
    pos = 0
    for context, weight in zip(simplified, simplified_weights):
        tokens = context if not isinstance(context, str) else template._tokenize(context)
        if weight == 2.0:
            suffix.update(range(pos, pos + len(tokens)))
        pos += len(tokens)
    forbidden = set(range(len(expected_labels))) - final - suffix
    if len(expected_labels) != len(input_ids):
        raise ValueError("semantic labels/input_ids length mismatch")
    return expected_labels, forbidden, final, suffix


def _print_leak(template: Any, input_ids: list[int], labels: list[int], positions: set[int],
                segment: str, final_start: int, suffix: set[int]) -> None:
    for idx in sorted(positions):
        lo, hi = max(0, idx - 12), min(len(input_ids), idx + 13)
        print("LEAK POS:", idx)
        print("TOKEN ID:", input_ids[idx])
        print("TOKEN:", repr(template.safe_decode([input_ids[idx]])))
        print("CONTEXT IDS:", input_ids[lo:hi])
        print("CONTEXT:", repr(template.safe_decode(input_ids[lo:hi])))
        print("LABEL:", labels[idx])
        print("SEGMENT:", segment)
        print("AFTER_FINAL:", idx > final_start)
        print("TEMPLATE_SUFFIX:", idx in suffix)


def audit_row(template: Any, row: dict[str, Any], sample_no: int, verbose_labels: bool = False) -> None:
    messages = row["messages"]
    gold_content = copy.deepcopy(messages[-1]["content"]) if messages else None
    if (len(messages) < 2 or messages[-1].get("role") != "assistant"
            or messages[-2].get("role") != "user"):
        raise ValueError("final messages must be user followed by assistant")
    if messages[-1].get("loss") is not True:
        raise ValueError("target is not marked loss=true")
    for message in messages[:-1]:
        if message.get("role") == "assistant" and message.get("loss") is True:
            raise ValueError("historical assistant must have loss=false")
    encoded, capture, prepared = _encode_with_capture(template, row)
    print("ACTUAL_ENCODE_TYPE:", type(encoded).__name__)
    print("ACTUAL_ENCODE_KEYS:", list(encoded.keys()))
    ids, labels = _list_ints(encoded["input_ids"]), _list_ints(encoded["labels"])
    if len(ids) != len(labels):
        raise ValueError("input_ids and labels length mismatch")
    if not capture.calls or "inputs" not in prepared:
        raise ValueError("ms-swift did not expose _swift_encode inputs")
    if capture.calls[0]["messages"][-1]["content"] != gold_content:
        raise ValueError("template changed final Gold content (e.g. added a thinking prefix)")
    _, forbidden, final, suffix = _semantic_labels(template, capture, prepared["inputs"], ids)
    actual_supervised = {i for i, x in enumerate(labels) if x != -100}
    wrong_labels = {i for i in actual_supervised if labels[i] != ids[i]}
    if wrong_labels:
        _print_leak(template, ids, labels, wrong_labels, "supervised-label-mismatch",
                    min(final) if final else 0, suffix)
        raise ValueError("supervised label does not equal input_id")
    if not final or not (actual_supervised & final):
        raise ValueError("missing final assistant supervision")
    leaks = actual_supervised & forbidden
    if leaks:
        _print_leak(template, ids, labels, leaks, "forbidden", min(final), suffix)
        raise ValueError(f"history/system leakage: {len(leaks)} supervised tokens")
    missing = final - actual_supervised
    if missing:
        raise ValueError(f"final assistant content not supervised: {len(missing)} tokens")
    masked = {"messages": [dict(m) for m in messages]}
    masked["messages"][-1]["loss"] = False
    encoded_masked, masked_capture, masked_prepared = _encode_with_capture(template, masked)
    masked_ids, masked_labels = (_list_ints(encoded_masked["input_ids"]),
                                 _list_ints(encoded_masked["labels"]))
    if masked_ids != ids:
        raise ValueError("mask audit changed input token IDs")
    _, masked_forbidden, _, masked_suffix = _semantic_labels(
        template, masked_capture, masked_prepared["inputs"], masked_ids)
    residual = {i for i, x in enumerate(masked_labels) if x != -100}
    wrong_residual = {i for i in residual if masked_labels[i] != masked_ids[i]}
    if wrong_residual:
        _print_leak(template, masked_ids, masked_labels, wrong_residual,
                    "counterfactual-label-mismatch", min(final) if final else 0, masked_suffix)
        raise ValueError("counterfactual supervised label does not equal input_id")
    forbidden_residual = residual & masked_forbidden
    if forbidden_residual:
        _print_leak(template, masked_ids, masked_labels, forbidden_residual,
                    "counterfactual-forbidden", min(final), masked_suffix)
        raise ValueError(f"history/system leakage: {len(forbidden_residual)} supervised tokens")
    if residual - masked_suffix:
        _print_leak(template, masked_ids, masked_labels, residual - masked_suffix,
                    "counterfactual-residual", min(final), masked_suffix)
        raise ValueError("counterfactual supervision outside template suffix")
    if residual:
        _print_leak(template, masked_ids, masked_labels, residual,
                    "counterfactual-suffix", max(final) if final else 0, masked_suffix)
    print("TEMPLATE_STRATEGY:", getattr(template.loss_scale, "base_strategy", None))
    if verbose_labels:
        try:
            safe = template.safe_decode(labels)
        except (TypeError, ValueError, IndexError) as exc:
            safe = f"<safe_decode failed: {exc}>"
        print("SAFE_DECODE_LABELS:", repr(safe))
    print(json.dumps({"sample": sample_no, "tokens": len(ids),
                      "supervised_tokens": len(actual_supervised),
                      "historical_assistant_supervised_tokens": 0,
                      "system_supervised_tokens": 0, "user_supervised_tokens": 0,
                      "final_assistant_content_tokens": len(final),
                      "final_assistant_template_suffix_tokens": len(suffix),
                      "counterfactual_supervised_tokens": len(residual), "status": "PASS"}))


def _check_config(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*loss_scale\s*:\s*([^#\s]+)", text)
    if not match or match.group(1).strip("'\"") != "last_round":
        raise ValueError(f"config does not set loss_scale: last_round: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B")
    parser.add_argument("--samples", type=int, default=0, help="0 means all samples")
    parser.add_argument("--config", type=Path, action="append", default=[])
    parser.add_argument("--verbose-labels", action="store_true")
    args = parser.parse_args()
    if "test.jsonl" in str(args.dataset):
        raise ValueError("held-out test.jsonl is forbidden for label-mask audit")
    for config in args.config:
        _check_config(config)
    from swift import get_processor, get_template
    processor = get_processor(args.model)
    template = get_template(processor, loss_scale="last_round", max_length=16384,
                            add_non_thinking_prefix=False)
    template.set_mode("train")
    if getattr(template.loss_scale, "base_strategy", None) != "last_round":
        raise ValueError("actual ms-swift template strategy is not last_round")
    audited = 0
    with args.dataset.open(encoding="utf-8") as stream:
        for raw in stream:
            if not raw.strip():
                continue
            audit_row(template, json.loads(raw), audited + 1, args.verbose_labels)
            audited += 1
            if args.samples and audited >= args.samples:
                break
    if args.samples and audited != args.samples:
        raise ValueError(f"requested {args.samples} samples, got {audited}")
    if not audited:
        raise ValueError("no samples audited")
    print(f"LABEL_MASK_AUDIT_PASS {audited}/{audited}")


if __name__ == "__main__":
    main()

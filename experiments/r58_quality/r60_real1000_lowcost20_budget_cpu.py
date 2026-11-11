"""Offline frozen Pilot20 cost envelope for low-cost dual-review experiments.

No network, no private text output, no model calls. Prices are caller supplied
to avoid stale assumptions. Character counts are NOT tokenizer measurements.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import r60_real1000_pilot20_local_review as review
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_lowcost20_budget_safe_v1"


class Hold(ValueError):
    pass


def calculate(packets: list[dict], *, input_ratio: float,
              input_price_a: float, output_price_a: float,
              input_price_b: float, output_price_b: float,
              max_output_tokens: int) -> dict:
    if (len(packets) != 20 or not 1 <= input_ratio <= 4
            or not 128 <= max_output_tokens <= 4096
            or any(not math.isfinite(p) or p < 0 for p in (
                input_price_a, output_price_a, input_price_b,
                output_price_b))):
        raise Hold("BUDGET_ARGS_HOLD")
    lengths = []
    for row in packets:
        case = {"history_messages": row["history_messages"],
                "target_text": row["assistant_target"]}
        prompt = ai.REVIEW_INSTRUCTIONS + "\n" + ai.prompt_for_case(case)
        lengths.append(len(prompt))
    total_char = sum(lengths)
    input_token_upper = math.ceil(total_char * input_ratio)
    output_token_upper = len(packets) * max_output_tokens
    a = (input_token_upper * input_price_a
         + output_token_upper * output_price_a) / 1_000_000
    b = (input_token_upper * input_price_b
         + output_token_upper * output_price_b) / 1_000_000
    return {
        "schema": SCHEMA,
        "status": "LOWCOST20_CHARACTER_ENVELOPE_READY__TOKENIZER_AND_AUTH_HOLD",
        "pilot_cases": len(packets),
        "total_prompt_characters": total_char,
        "max_prompt_characters": max(lengths),
        "input_token_upper_assumed": input_token_upper,
        "output_token_upper_assumed_per_model": output_token_upper,
        "assumed_tokens_per_character": input_ratio,
        "max_output_tokens_per_case": max_output_tokens,
        "estimated_model_a_cost_in_caller_currency": round(a, 8),
        "estimated_model_b_cost_in_caller_currency": round(b, 8),
        "estimated_total_cost_in_caller_currency": round(a + b, 8),
        "pricing_currency_must_match": True,
        "actual_tokenizer_measurement": False,
        "input_price_cached_discount_included": False,
        "model_inference_calls": 0,
        "private_data_emitted": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_job_started": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--tokens-per-character", type=float, default=2.0)
    p.add_argument("--max-output-tokens", type=int, default=1024)
    p.add_argument("--a-input-price-per-million", type=float, required=True)
    p.add_argument("--a-output-price-per-million", type=float, required=True)
    p.add_argument("--b-input-price-per-million", type=float, required=True)
    p.add_argument("--b-output-price-per-million", type=float, required=True)
    args = p.parse_args()
    try:
        _config, packets, progress = review.get_state(args.review_dir)
        if progress["processed"] != 20:
            raise Hold("PILOT20_INCOMPLETE_HOLD")
        report = calculate(
            packets["packets"],
            input_ratio=args.tokens_per_character,
            input_price_a=args.a_input_price_per_million,
            output_price_a=args.a_output_price_per_million,
            input_price_b=args.b_input_price_per_million,
            output_price_b=args.b_output_price_per_million,
            max_output_tokens=args.max_output_tokens)
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - do not disclose private inputs
        code = str(exc) if isinstance(exc, Hold) else "LOWCOST20_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "LOWCOST20_BUDGET_HOLD",
            "reason_code": code,
            "model_inference_calls": 0,
            "private_data_emitted": False,
            "quality_v1_admitted": 0, "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

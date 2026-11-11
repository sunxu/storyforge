"""Owner Mac real API pilot: Qwen + DeepSeek on the SAME frozen Pilot20.

One create-only private receipt per model/case; resumable, no reruns of success.
API keys from environment; no case content or credentials on stdout/stderr.
Actual network charges/data egress happen ONLY with the explicit 'run' command.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot
import r60_real_ai_dual_review as ai
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_qwen_deepseek20_live_safe_v1"
CONFIG_SCHEMA = "storyforge_r60_real1000_qwen_deepseek20_config_v1"
RECEIPT_SCHEMA = "storyforge_r60_real1000_qwen_deepseek20_receipt_v1"
CONFIG_NAME = "R60_QWEN_DEEPSEEK20_CONFIG_PRIVATE.json"
MAX_RECEIPT_BYTES = 6000
MODELS = ("qwen", "deepseek")
DEFAULT_URLS = {
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com",
}
DEFAULT_MODELS = {
    "qwen": "qwen3.7-flash",
    "deepseek": "deepseek-flash",
}
KEY_ENV = {"qwen": "DASHSCOPE_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}


class Hold(ValueError):
    pass


def receipt_name(position: int, model: str) -> str:
    return f"R60_QD20_{position:02d}_{model.upper()}_PRIVATE.json"


def config_payload(packet_hash: str, qwen_url: str, qwen_model: str,
                   deepseek_url: str, deepseek_model: str) -> dict:
    configs = {
        "qwen": {"endpoint": ai.validate_endpoint(qwen_url, True),
                 "model": qwen_model},
        "deepseek": {"endpoint": ai.validate_endpoint(deepseek_url, True),
                     "model": deepseek_model},
    }
    qhost = urllib.parse.urlsplit(configs["qwen"]["endpoint"]).hostname
    dhost = urllib.parse.urlsplit(configs["deepseek"]["endpoint"]).hostname
    if (not qwen_model.startswith("qwen")
            or not deepseek_model.startswith("deepseek-")
            or qwen_model.casefold() == deepseek_model.casefold()
            or qhost not in {"dashscope.aliyuncs.com"}
            and not (qhost and qhost.endswith(".maas.aliyuncs.com"))
            or dhost != "api.deepseek.com"):
        raise Hold("MODEL_OR_ENDPOINT_HOLD")
    return {
        "schema": CONFIG_SCHEMA,
        "packets_sha256": packet_hash,
        "reviewer_configs": configs,
        "review_policy": "R60_FROZEN_SIX_DIMENSIONS_V1",
        "independence": "TWO_SEPARATE_OFFICIAL_PROVIDERS",
        "quality_v1_admitted": 0,
        "train_admitted": 0,
    }


def load_input(review_dir: Path) -> tuple[dict, dict, dict]:
    config, packets, progress = pilot.get_state(review_dir)
    if (progress["processed"] != 20 or len(packets["packets"]) != 20):
        raise Hold("PILOT20_SOURCE_NOT_FROZEN_HOLD")
    return config, packets, progress


def read_receipts(out: Path, cfg: dict) -> tuple[dict, Counter]:
    receipts = {}
    decisions = Counter()
    for pos in range(1, 21):
        for model in MODELS:
            path = out / receipt_name(pos, model)
            if not path.exists():
                continue
            row = json.loads(private.read_private(path, MAX_RECEIPT_BYTES))
            if (not isinstance(row, dict)
                    or set(row) != {"schema", "packets_sha256", "position",
                                    "provider", "model", "result", "sha256"}
                    or row["schema"] != RECEIPT_SCHEMA
                    or row["packets_sha256"] != cfg["packets_sha256"]
                    or row["position"] != pos or row["provider"] != model
                    or row["model"] != cfg["reviewer_configs"][model]["model"]
                    or row["sha256"] != pilot.sha(pilot.canonical({
                        k: v for k, v in row.items() if k != "sha256"}))):
                raise Hold("RECEIPT_BINDING_HOLD")
            ai.parse_model_response(row["result"])
            receipts[(pos, model)] = row
            decisions[(model, row["result"]["decision"])] += 1
    return receipts, decisions


def inspect(out: Path, source: dict) -> dict:
    private.private_dir(out, create=False)
    config = json.loads(private.read_private(out / CONFIG_NAME, 12000))
    if config != source:
        raise Hold("SOURCE_OR_CONFIG_MISMATCH_HOLD")
    receipts, counts = read_receipts(out, config)
    pairs = sum(all((p, m) in receipts for m in MODELS)
                for p in range(1, 21))
    pending = 40 - len(receipts)
    return {
        "schema": SCHEMA,
        "status": ("QD20_TWO_PROVIDER_COMPLETED__QUALITY_COMPARISON_PENDING"
                   if pending == 0 else "QD20_PARTIAL__RETRY_PENDING"),
        "cases": 20,
        "complete_provider_reviews": len(receipts),
        "complete_two_provider_pairs": pairs,
        "remaining_provider_reviews": pending,
        "decisions_by_provider": {
            model: {d: counts[(model, d)] for d in ("PASS", "HOLD", "REJECT")}
            for model in MODELS
        },
        "double_pass_on_completed_pairs": sum(
            receipts[(p, "qwen")]["result"]["decision"] == "PASS"
            and receipts[(p, "deepseek")]["result"]["decision"] == "PASS"
            for p in range(1, 21)
            if all((p, m) in receipts for m in MODELS)
        ),
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "private_values_emitted": False,
        "gpu_job_started": False,
        "database_accessed": False,
    }


def call_provider(endpoint: str, model: str, provider: str,
                  key: str, prompt: str, timeout: int,
                  json_mode: bool) -> dict:
    """Single stateless call, with DeepSeek V4.1 thinking explicitly disabled."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": ai.REVIEW_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1600,
        "stream": False,
    }
    if provider == "deepseek":
        body["thinking"] = {"type": "disabled"}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key},
        method="POST",
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), ai.NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(ai.MAX_REPLY_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError,
            TimeoutError, OSError, ValueError) as exc:
        raise ai.Hold("MODEL_TRANSPORT_HOLD") from exc
    if len(raw) > ai.MAX_REPLY_BYTES:
        raise ai.Hold("MODEL_REPLY_OVERSIZE")
    try:
        payload = json.loads(raw)
        message = payload["choices"][0]["message"]
        content = message["content"]
        if not isinstance(content, str):
            raise TypeError("empty content")
        result = json.loads(content)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise ai.Hold("MODEL_JSON_INVALID") from exc
    return ai.parse_model_response(result)


def execute(args: argparse.Namespace) -> dict:
    source, packets, _ = load_input(args.review_dir)
    cfg = config_payload(
        source["packets_sha256"], args.qwen_url, args.qwen_model,
        args.deepseek_url, args.deepseek_model)
    if args.command == "init":
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise Hold("OUTPUT_ALREADY_EXISTS_HOLD")
        private.private_dir(args.output_dir, create=True)
        private.write_new(args.output_dir / CONFIG_NAME, pilot.canonical(cfg))
        return {**inspect(args.output_dir, cfg), "status": "QD20_INITIALIZED__NO_API_REQUESTS",
                "model_inference_calls_this_run": 0}
    if args.command == "inspect":
        return {**inspect(args.output_dir, cfg), "model_inference_calls_this_run": 0}
    if args.command != "run":
        raise Hold("COMMAND_HOLD")
    if not args.authorize_remote_private_review:
        raise Hold("REMOTE_PRIVATE_REVIEW_NOT_AUTHORIZED_HOLD")
    if not 1 <= args.max_calls <= 40:
        raise Hold("MAX_CALLS_HOLD")
    private.private_dir(args.output_dir, create=False)
    saved = json.loads(private.read_private(args.output_dir / CONFIG_NAME, 12000))
    if saved != cfg:
        raise Hold("SOURCE_OR_CONFIG_MISMATCH_HOLD")
    for model in MODELS:
        if not os.environ.get(KEY_ENV[model]):
            raise Hold("MISSING_API_KEY_HOLD")
    # Verify all existing receipts before any network call.
    receipts, _ = read_receipts(args.output_dir, saved)
    attempts = 0
    completed = 0
    failed = Counter()
    for pos, packet in enumerate(packets["packets"], 1):
        prompt = ai.prompt_for_case({
            "history_messages": packet["history_messages"],
            "target_text": packet["assistant_target"],
        })
        for model in MODELS:
            if (pos, model) in receipts:
                continue
            if attempts >= args.max_calls:
                break
            attempts += 1
            conf = cfg["reviewer_configs"][model]
            try:
                answer = call_provider(
                    conf["endpoint"], conf["model"], model,
                    os.environ[KEY_ENV[model]], prompt,
                    args.timeout, args.json_mode)
            except ai.Hold as exc:
                failed[str(exc)] += 1
                continue
            row = {
                "schema": RECEIPT_SCHEMA,
                "packets_sha256": cfg["packets_sha256"],
                "position": pos,
                "provider": model,
                "model": conf["model"],
                "result": answer,
            }
            row["sha256"] = pilot.sha(pilot.canonical(row))
            private.write_new(args.output_dir / receipt_name(pos, model),
                              pilot.canonical(row))
            completed += 1
        if attempts >= args.max_calls:
            break
    safe = inspect(args.output_dir, cfg)
    safe.update({
        "model_inference_calls_this_run": attempts,
        "valid_receipts_created_this_run": completed,
        "technical_failure_counts": dict(sorted(failed.items())),
    })
    return safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init", "run", "inspect"))
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--qwen-url", default=DEFAULT_URLS["qwen"])
    parser.add_argument("--qwen-model", default=DEFAULT_MODELS["qwen"])
    parser.add_argument("--deepseek-url", default=DEFAULT_URLS["deepseek"])
    parser.add_argument("--deepseek-model", default=DEFAULT_MODELS["deepseek"])
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-calls", type=int, default=40)
    parser.add_argument("--json-mode", action="store_true")
    parser.add_argument("--authorize-remote-private-review", action="store_true")
    args = parser.parse_args()
    try:
        if not 10 <= args.timeout <= 300:
            raise Hold("TIMEOUT_HOLD")
        print(json.dumps(execute(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never expose private input or keys
        reason = str(exc) if isinstance(exc, Hold) else "LIVE_REVIEW_TECHNICAL_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "QD20_RUN_HOLD",
            "reason_code": reason,
            "private_values_emitted": False,
            "train_admitted": 0,
            "quality_v1_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

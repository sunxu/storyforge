"""R60 REAL: resumable, Owner-private AI dual quality review of frozen 1000 cases.

All candidate text and model judgments stay under 0700/0600 Mac-private files.
No database writes or reads, no R50 content, no train admission, no GPU jobs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
from collections import Counter
from pathlib import Path

import r60_real_ai_dual_review as ai
import r60_real_expand_private as expand
import r60_real_private_batch as g1

SCHEMA = "storyforge_r60_quality_batch_private_v1"
CASE_SCHEMA = "storyforge_r60_quality_case_review_private_v1"
SAFE_SCHEMA = "storyforge_r60_quality_batch_safe_v1"
CONFIG_FILE = "R60_QUALITY_BATCH_CONFIG_PRIVATE.json"
CASE_PREFIX = "R60_QUALITY_CASE_"
CASE_SUFFIX = "_PRIVATE.json"
EXPECTED_CASES = 1000
MAX_CONFIG_BYTES = 16000
MAX_CASE_BYTES = 24000
MAX_CASES_PER_CALL = 25


class Hold(ValueError):
    pass


def receipt_name(index: int) -> str:
    return f"{CASE_PREFIX}{index:04d}{CASE_SUFFIX}"


def safe_error(exc: Exception) -> str:
    if isinstance(exc, (Hold, ai.Hold, expand.Hold, g1.Hold)):
        return str(exc)
    if isinstance(exc, FileNotFoundError):
        return "PRIVATE_FILE_NOT_FOUND"
    return type(exc).__name__


def frozen_pool(source: Path) -> tuple[list[dict], str]:
    """Validate every sealed expansion page before any model sees its text."""
    g1.private_dir(source, create=False)
    with expand.locked(source):
        config, seeds = expand.validate_config(source)
        progress = expand.reconstruct(source, config, seeds)
        effective_target = expand.extension_target(source, config, progress)
        if (effective_target != EXPECTED_CASES or
                progress["total"] != EXPECTED_CASES or progress["pages"] < 1):
            raise Hold("EXACT_1000_FROZEN_POOL_REQUIRED")
        raw_paths = [
            source / expand.CONFIG_NAME,
            Path(config["seed_capture_file"]),
            source / expand.EXTENSION_NAME,
        ]
        raw_paths.extend(source / expand.page_name(i)
                         for i in range(1, progress["pages"] + 1))
        hasher = hashlib.sha256()
        cases = list(seeds)
        for path in raw_paths:
            size = (g1.MAX_CAPTURE_BYTES if path.name ==
                    "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
                    else expand.MAX_BATCH_BYTES if path.name.startswith(
                        expand.PAGE_PREFIX) else expand.MAX_CONFIG_BYTES)
            raw = g1.read_private(path, size)
            hasher.update(len(raw).to_bytes(8, "big"))
            hasher.update(raw)
            if path.name.startswith(expand.PAGE_PREFIX):
                page = json.loads(raw)
                cases.extend(page["cases"])
        if len(cases) != EXPECTED_CASES:
            raise Hold("POOL_CASE_COUNT_HOLD")
        for case in cases:
            expand.check_case(case)
            # Prevent malformed/future-containing message structure from
            # bypassing the bound review prompt.
            ai.prompt_for_case(case)
        return cases, hasher.hexdigest()


def create_config(folder: Path, source: Path, endpoint_a: str,
                  model_a: str, endpoint_b: str, model_b: str,
                  allow_remote: bool, attest: bool, json_mode: bool,
                  timeout: int, protocol_a: str = "openai-chat",
                  protocol_b: str = "openai-chat") -> dict:
    try:
        ai.transport.require_profile(protocol_a)
        ai.transport.require_profile(protocol_b)
    except ValueError as exc:
        raise Hold("REVIEW_PROTOCOL_UNSUPPORTED") from exc
    if (protocol_a == "claude-proxy-top-system" or
            protocol_b == "claude-proxy-top-system") and json_mode:
        raise Hold("CLAUDE_PROXY_JSON_MODE_UNSUPPORTED")
    if folder.exists():
        raise Hold("QUALITY_OUTPUT_EXISTS_HOLD")
    if type(timeout) is not int or not 10 <= timeout <= 300:
        raise Hold("TIMEOUT_BOUNDS_HOLD")
    if (not model_a.strip() or not model_b.strip()
            or model_a.strip().casefold() == model_b.strip().casefold()):
        raise Hold("DISTINCT_MODELS_REQUIRED")
    endpoint_a = ai.validate_endpoint(endpoint_a, allow_remote)
    endpoint_b = ai.validate_endpoint(endpoint_b, allow_remote)
    cases, pool_hash = frozen_pool(source)
    g1.private_dir(folder, create=True)
    config = {
        "schema": SCHEMA, "source": str(source),
        "pool_sha256": pool_hash, "expected_cases": len(cases),
        "endpoint_a": endpoint_a, "endpoint_b": endpoint_b,
        "model_a": model_a, "model_b": model_b,
        "allow_remote": bool(allow_remote),
        "owner_attested_independent_ai": bool(attest),
        "json_mode": bool(json_mode), "timeout": timeout,
        "protocol_a": protocol_a, "protocol_b": protocol_b,
    }
    g1.write_new(folder / CONFIG_FILE, expand.private_bytes(config))
    return {
        "schema": SAFE_SCHEMA, "status": "QUALITY_BATCH_INITIALIZED__NO_REVIEWS",
        "candidate_total": len(cases), "cases_reviewed": 0,
        "train_admitted": 0, "quality_pass": 0,
        "database_modified": False, "gpu_started": False,
        "r50_body_accessed": False, "private_values_emitted": False,
    }


def validate_config(folder: Path) -> dict:
    if not folder.is_dir():
        raise Hold("QUALITY_BATCH_NOT_INITIALIZED")
    g1.private_dir(folder, create=False)
    try:
        config = json.loads(g1.read_private(folder / CONFIG_FILE, MAX_CONFIG_BYTES))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Hold("QUALITY_CONFIG_FORMAT_HOLD") from exc
    if (not isinstance(config, dict) or config.get("schema") != SCHEMA
            or config.get("expected_cases") != EXPECTED_CASES
            or type(config.get("timeout")) is not int
            or not 10 <= config["timeout"] <= 300
            or any(type(config.get(k)) is not bool for k in
                   ("allow_remote", "owner_attested_independent_ai", "json_mode"))
            or any(not isinstance(config.get(k), str) or not config[k] for k in
                   ("source", "pool_sha256", "endpoint_a", "endpoint_b",
                    "model_a", "model_b"))
            or config["model_a"].casefold() == config["model_b"].casefold()):
        raise Hold("QUALITY_CONFIG_INTEGRITY_HOLD")
    for part in ("a", "b"):
        try:
            ai.transport.require_profile(config.get("protocol_" + part, "openai-chat"))
        except ValueError as exc:
            raise Hold("REVIEW_PROTOCOL_UNSUPPORTED") from exc
        if (config.get("protocol_" + part) == "claude-proxy-top-system"
                and config["json_mode"]):
            raise Hold("CLAUDE_PROXY_JSON_MODE_UNSUPPORTED")
        endpoint = config["endpoint_" + part]
        # validator only accepts a base URL, and the frozen URL is already a
        # completions endpoint. Remove the exact suffix before revalidation.
        suffix = "/chat/completions"
        if not endpoint.endswith(suffix):
            raise Hold("QUALITY_ENDPOINT_INTEGRITY_HOLD")
        base = endpoint[:-len(suffix)]
        if ai.validate_endpoint(base, config["allow_remote"]) != endpoint:
            raise Hold("QUALITY_ENDPOINT_INTEGRITY_HOLD")
    if Path(config["source"]).parent != expand.BASE:
        raise Hold("QUALITY_SOURCE_PATH_HOLD")
    return config


def case_receipt(case: dict, index: int, pool_hash: str,
                 config: dict) -> dict:
    reviews = []
    attempt_holds = []
    prompt = ai.prompt_for_case(case)
    for side in ("a", "b"):
        model = config["model_" + side]
        key = os.getenv("R60_REVIEW_" + side.upper() + "_KEY", "")
        try:
            profile = config.get("protocol_" + side, "openai-chat")
            if profile == "openai-chat":
                # Retain historical positional interface for existing batches.
                answer = ai.model_request(config["endpoint_" + side], model, key,
                                          prompt, config["timeout"],
                                          config["json_mode"])
            else:
                answer = ai.model_request(config["endpoint_" + side], model, key,
                                          prompt, config["timeout"],
                                          config["json_mode"], protocol=profile)
        except ai.Hold as exc:
            attempt_holds.append(str(exc))
            continue
        reviews.append({
            "reviewer_key": "ai-model-" + side,
            "model_id": model,
            "method": "ISOLATED_STATELESS_MODEL_REQUEST",
            "decision": answer["decision"], "scores": answer["scores"],
            "severe_flags": answer["severe_flags"],
            "private_evidence_ref": "r60-private-batch-" +
                                    case["case_key"] + "-" + side,
            "reason_cn": answer["reason_cn"],
        })
    # If neither model can be reached, assume a configuration/service outage,
    # not 1000 examples of poor literary quality. Fail before committing a case.
    if not reviews and attempt_holds and all(
            reason == "MODEL_TRANSPORT_HOLD" for reason in attempt_holds):
        raise Hold("BOTH_REVIEW_MODELS_UNAVAILABLE")
    record = {
        "schema": CASE_SCHEMA, "position": index,
        "pool_sha256": pool_hash,
        "review_schema": g1.REVIEW_SCHEMA,
        "case_key": case["case_key"],
        "assistant_target_sha256": case["assistant_target_sha256"],
        "history_messages_sha256": case["history_messages_sha256"],
        "reviewers_independent_owner_attested":
            config["owner_attested_independent_ai"],
        "reviews": reviews, "attempt_holds": attempt_holds,
    }
    decision, reason = g1.validated_review(
        {**record, "schema": g1.REVIEW_SCHEMA}, case)
    record["quality_decision"] = decision
    record["quality_reason_code"] = reason
    record["receipt_sha256"] = g1.digest(record)
    return record


def inspected_records(folder: Path, config: dict, cases: list[dict],
                      pool_hash: str) -> dict:
    rows = sorted(folder.glob(CASE_PREFIX + "*" + CASE_SUFFIX))
    counts, reasons, failures = Counter(), Counter(), Counter()
    for n, path in enumerate(rows, 1):
        if n > len(cases) or path.name != receipt_name(n):
            raise Hold("QUALITY_CASE_SEQUENCE_HOLD")
        try:
            record = json.loads(g1.read_private(path, MAX_CASE_BYTES))
        except (ValueError, TypeError, UnicodeError) as exc:
            raise Hold("QUALITY_CASE_FILE_FORMAT_HOLD") from exc
        case = cases[n - 1]
        if not isinstance(record, dict):
            raise Hold("QUALITY_CASE_FILE_FORMAT_HOLD")
        signed = {k: v for k, v in record.items() if k != "receipt_sha256"}
        if (record.get("receipt_sha256") != g1.digest(signed)
                or record.get("schema") != CASE_SCHEMA
                or record.get("position") != n
                or record.get("pool_sha256") != pool_hash
                or record.get("case_key") != case["case_key"]
                or record.get("history_messages_sha256") !=
                case["history_messages_sha256"]
                or record.get("assistant_target_sha256") !=
                case["assistant_target_sha256"]
                or record.get("reviewers_independent_owner_attested") is not
                config["owner_attested_independent_ai"]
                or not isinstance(record.get("reviews"), list)
                or not isinstance(record.get("attempt_holds"), list)
                or len(record["reviews"]) + len(record["attempt_holds"]) != 2
                or len(record["reviews"]) > 2):
            raise Hold("QUALITY_SOURCE_OR_RECEIPT_TAMPER_HOLD")
        if any(not isinstance(x, dict) for x in record["reviews"]):
            raise Hold("QUALITY_REVIEW_FORMAT_HOLD")
        if len({x.get("reviewer_key") for x in record["reviews"]}) != len(
                record["reviews"]):
            raise Hold("QUALITY_DUPLICATE_REVIEWER_HOLD")
        expected_model_sides = ("a", "b")
        for entry in record["reviews"]:
            side = entry.get("reviewer_key", "").removeprefix("ai-model-")
            if side not in expected_model_sides or entry.get("model_id") != config[
                    "model_" + side] or entry.get("method") != (
                    "ISOLATED_STATELESS_MODEL_REQUEST"):
                raise Hold("QUALITY_REVIEW_MODEL_MISMATCH_HOLD")
        if any(not isinstance(x, str) or x not in (
                "MODEL_TRANSPORT_HOLD", "MODEL_JSON_INVALID",
                "MODEL_REPLY_OVERSIZE", "SEVERE_FLAG_DECISION_INCONSISTENT",
                "QUALITY_FLOOR_DECISION_INCONSISTENT") for x in
               record["attempt_holds"]):
            raise Hold("QUALITY_ATTEMPT_ERROR_CODE_HOLD")
        status, reason = g1.validated_review(
            {**record, "schema": g1.REVIEW_SCHEMA}, case)
        if (record.get("quality_decision") != status
                or record.get("quality_reason_code") != reason):
            raise Hold("QUALITY_DECISION_TAMPER_HOLD")
        counts[status] += 1
        if status != "PASS":
            reasons[reason] += 1
        failures.update(record["attempt_holds"])
    completed = len(rows)
    return {
        "schema": SAFE_SCHEMA,
        "status": ("QUALITY_BATCH_REVIEWED__TRAIN_ADMISSION_HOLD"
                   if completed == len(cases) else
                   "QUALITY_BATCH_IN_PROGRESS__TRAIN_ADMISSION_HOLD"),
        "candidate_total": len(cases), "cases_reviewed": completed,
        "remaining_cases": len(cases) - completed,
        "quality_decisions": {
            key: counts[key] for key in ("PASS", "HOLD", "REJECT")},
        "quality_pass": counts["PASS"],
        "hold_reject_codes": dict(sorted(reasons.items())),
        "model_attempt_hold_counts": dict(sorted(failures.items())),
        "reviewer_independence_attested_by_owner":
            config["owner_attested_independent_ai"],
        "reviewer_independence_independently_proven_by_script": False,
        "world_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "train_admitted": 0, "database_modified": False,
        "r50_body_accessed": False, "gpu_started": False,
        "private_values_emitted": False,
    }


def atomic_case_file(folder: Path, index: int, record: dict) -> None:
    """fsync a new receipt and link it without overwriting an existing one."""
    data = expand.private_bytes(record)
    if len(data) > MAX_CASE_BYTES:
        raise Hold("QUALITY_RECEIPT_TOO_LARGE_HOLD")
    target = folder / receipt_name(index)
    temp = folder / (".r60-review-" + secrets.token_hex(12) + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(temp, target, follow_symlinks=False)
        except FileExistsError as exc:
            raise Hold("QUALITY_RECEIPT_ALREADY_EXISTS") from exc
        dir_fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if temp.exists():
            temp.unlink()


def inspect(folder: Path) -> dict:
    if not folder.is_dir():
        raise Hold("QUALITY_BATCH_NOT_INITIALIZED")
    with expand.locked(folder):
        config = validate_config(folder)
        cases, pool_hash = frozen_pool(Path(config["source"]))
        if pool_hash != config["pool_sha256"]:
            raise Hold("FROZEN_POOL_CHANGED_HOLD")
        return inspected_records(folder, config, cases, pool_hash)


def advance(folder: Path, max_cases: int) -> dict:
    if type(max_cases) is not int or not 1 <= max_cases <= MAX_CASES_PER_CALL:
        raise Hold("MAX_CASES_PER_CALL_HOLD")
    if not folder.is_dir():
        raise Hold("QUALITY_BATCH_NOT_INITIALIZED")
    with expand.locked(folder):
        config = validate_config(folder)
        cases, pool_hash = frozen_pool(Path(config["source"]))
        if pool_hash != config["pool_sha256"]:
            raise Hold("FROZEN_POOL_CHANGED_HOLD")
        progress = inspected_records(folder, config, cases, pool_hash)
        start = progress["cases_reviewed"]
        for index in range(start, min(start + max_cases, len(cases))):
            record = case_receipt(cases[index], index + 1, pool_hash, config)
            atomic_case_file(folder, index + 1, record)
        return inspected_records(folder, config, cases, pool_hash)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="mode", required=True)
    init = subs.add_parser("init")
    init.add_argument("--expand-dir", type=Path, required=True)
    init.add_argument("--output-dir", type=Path, required=True)
    init.add_argument("--endpoint-a", required=True)
    init.add_argument("--model-a", required=True)
    init.add_argument("--endpoint-b", required=True)
    init.add_argument("--model-b", required=True)
    init.add_argument("--allow-remote-review", action="store_true")
    init.add_argument("--owner-attest-independent-ai", action="store_true")
    init.add_argument("--json-mode", action="store_true")
    init.add_argument("--protocol-a", default="openai-chat",
                      choices=sorted(ai.transport.PROFILES))
    init.add_argument("--protocol-b", default="openai-chat",
                      choices=sorted(ai.transport.PROFILES))
    init.add_argument("--timeout", type=int, default=180)
    run = subs.add_parser("advance")
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--max-cases", type=int, default=5)
    view = subs.add_parser("inspect")
    view.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "init":
            safe = create_config(
                args.output_dir, args.expand_dir,
                args.endpoint_a, args.model_a, args.endpoint_b, args.model_b,
                args.allow_remote_review, args.owner_attest_independent_ai,
                args.json_mode, args.timeout,
                args.protocol_a, args.protocol_b)
        elif args.mode == "advance":
            safe = advance(args.output_dir, args.max_cases)
        else:
            safe = inspect(args.output_dir)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never print private text/ID/paths
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "QUALITY_BATCH_HOLD",
            "reason_code": safe_error(exc), "quality_pass": 0,
            "train_admitted": 0, "database_modified": False,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

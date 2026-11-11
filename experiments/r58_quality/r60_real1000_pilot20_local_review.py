"""R60 REAL pilot20: bounded 4Router Claude quality pilot.

Reuses the existing literary rubric and validated Claude proxy system format.
Create-only private receipts. Model verdicts remain advisory; no training.
An explicit execution and private-egress opt-in is required for API requests.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_packets_cpu as pilot
import r60_real_ai_dual_review as reviewer
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_pilot20_local_review_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_pilot20_local_review_safe_v1"
CONFIG = "R60_PILOT20_REVIEW_CONFIG_PRIVATE.json"
MAX_PACKETS_BYTES = 200000
MAX_RECEIPT_BYTES = 16000
MAX_CASES_PER_CALL = 5
MAX_REPLY_BYTES = 120000
MODEL_DEFAULT = "claude-opus-5-5"
API_KEY_ENV = "CLI_PROXY_API_KEY"
# A 1600-token budget caused a real 4Router response to finish with length.
# Keep this request-only change separate from the frozen review contract.
REVIEW_MAX_TOKENS = 8192


class Hold(ValueError):
    """Reject a missing or inconsistent local review artifact."""


def canonical(data: object) -> bytes:
    return (json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ) + "\n").encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_packets(directory: Path) -> tuple[dict, str]:
    private.private_dir(directory, create=False)
    raw = private.read_private(directory / pilot.FILENAME, MAX_PACKETS_BYTES)
    data = json.loads(raw)
    if (
        not isinstance(data, dict)
        or data.get("schema") != pilot.SCHEMA
        or data.get("status") != "PILOT20_PACKETS_PRIVATE__NOT_REVIEWED"
        or data.get("sample100_binding") != "RECOMPUTED_EXACT"
        or not isinstance(data.get("packets"), list)
        or len(data["packets"]) != 20
        or data.get("quality_review_performed") is not False
        or data.get("train_admitted") != 0
    ):
        raise Hold("PACKETS_SCHEMA_HOLD")
    bins = Counter()
    for i, packet in enumerate(data["packets"], 1):
        if (
            not isinstance(packet, dict)
            or packet.get("pilot_position") != i
            or packet.get("human_reference_status") != "NOT_ADJUDICATED"
            or packet.get("model_quality_status") != "NOT_REVIEWED"
            or type(packet.get("sample100_position")) is not int
            or not 1 <= packet["sample100_position"] <= 1000
            or packet.get("target_char_bin") not in pilot.SAMPLE_QUOTAS
        ):
            raise Hold("PACKET_ENTRY_HOLD")
        payload = {
            "history_messages": packet.get("history_messages"),
            "target_text": packet.get("assistant_target"),
        }
        reviewer.prompt_for_case(payload)
        bins[packet["target_char_bin"]] += 1
    if bins != Counter(pilot.SAMPLE_QUOTAS):
        raise Hold("PACKETS_QUOTA_HOLD")
    if len({p["sample100_position"] for p in data["packets"]}) != 20:
        raise Hold("PACKET_POSITION_DUPLICATE_HOLD")
    return data, sha(raw)


def conflict_name(i: int) -> str:
    if not 1 <= i <= 20:
        raise Hold("POSITION_HOLD")
    return f"R60_PILOT20_CONFLICT_{i:04d}_PRIVATE.json"


def receipt_name(i: int) -> str:
    if not 1 <= i <= 20:
        raise Hold("POSITION_HOLD")
    return f"R60_PILOT20_REVIEW_{i:04d}_PRIVATE.json"


def proxy_endpoint(base: str) -> str:
    """Only HTTPS 4router.ai or a subdomain, no redirects or URL secrets."""
    if not isinstance(base, str):
        raise Hold("PROXY_ENDPOINT_HOLD")
    try:
        parsed = urllib.parse.urlsplit(base)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise Hold("PROXY_ENDPOINT_HOLD") from exc
    if (
        parsed.scheme != "https"
        or not hostname
        or (hostname != "4router.ai" and not hostname.endswith(".4router.ai"))
        or port not in (None, 443)
        or parsed.username or parsed.password
        or parsed.query or parsed.fragment
    ):
        raise Hold("PROXY_ENDPOINT_HOLD")
    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        pass
    elif path.endswith("/v1"):
        path += "/chat/completions"
    elif not path:
        path = "/v1/chat/completions"
    else:
        raise Hold("PROXY_ENDPOINT_HOLD")
    return urllib.parse.urlunsplit(("https", parsed.netloc, path, "", ""))


def claude_payload(model: str, prompt: str) -> dict:
    """Match prior successful R60 4Router contract: top-level system, no temp."""
    return {
        "model": model,
        "system": reviewer.REVIEW_INSTRUCTIONS,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": REVIEW_MAX_TOKENS,
        "stream": False,
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Do not emit provider messages or arbitrary error strings. Only known
# diagnostic categories (or numeric HTTP statuses) may enter SAFE output.
HTTP_PROVIDER_CATEGORIES = {
    "authentication_error": "AUTH",
    "authorization_error": "AUTH",
    "permission_error": "PERMISSION",
    "invalid_request_error": "INVALID_REQUEST",
    "rate_limit_error": "RATE_LIMIT",
    "overloaded_error": "OVERLOADED",
    "not_found_error": "NOT_FOUND",
    "insufficient_quota": "QUOTA",
    "billing_error": "BILLING",
    "model_not_found": "MODEL_NOT_FOUND",
}


def safe_http_code(exc: urllib.error.HTTPError) -> str:
    status = exc.code
    if type(status) is not int or not 300 <= status <= 599:
        return "PROXY_HTTP_UNKNOWN_HOLD"
    category = None
    # Reading capped bytes only for fixed-enum diagnostics; never print
    # provider bodies, error messages, URLs or arbitrary values.
    try:
        payload = json.loads(exc.read(8193))
        detail = payload.get("error", payload)
        if isinstance(detail, dict):
            for field in ("type", "code"):
                value = detail.get(field)
                if type(value) is str and value in HTTP_PROVIDER_CATEGORIES:
                    category = HTTP_PROVIDER_CATEGORIES[value]
                    break
    except (ValueError, TypeError, AttributeError, OSError):
        pass
    return (f"PROXY_HTTP_{status}_{category}_HOLD" if category
            else f"PROXY_HTTP_{status}_HOLD")


def safe_transport_code(exc: Exception) -> str:
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    # Traverse only exception objects, never stringify them: transport
    # exception text can contain private hostnames or other identifiers.
    seen = set()
    while isinstance(reason, BaseException) and id(reason) not in seen:
        seen.add(id(reason))
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return "PROXY_TIMEOUT_HOLD"
        if isinstance(reason, ssl.SSLCertVerificationError):
            return "PROXY_TLS_CERT_VERIFY_HOLD"
        if isinstance(reason, ssl.SSLError):
            return "PROXY_TLS_HANDSHAKE_HOLD"
        if isinstance(reason, socket.gaierror):
            return "PROXY_DNS_HOLD"
        if isinstance(reason, ConnectionRefusedError):
            return "PROXY_CONNECTION_REFUSED_HOLD"
        if isinstance(reason, ConnectionResetError):
            return "PROXY_CONNECTION_RESET_HOLD"
        if isinstance(reason, BrokenPipeError):
            return "PROXY_CONNECTION_BROKEN_PIPE_HOLD"
        if isinstance(reason, OSError):
            code = reason.errno
            if code in (errno.ENETUNREACH, errno.EHOSTUNREACH):
                return "PROXY_NETWORK_UNREACHABLE_HOLD"
            if code == errno.ECONNREFUSED:
                return "PROXY_CONNECTION_REFUSED_HOLD"
            if code == errno.ECONNRESET:
                return "PROXY_CONNECTION_RESET_HOLD"
            if code == errno.ETIMEDOUT:
                return "PROXY_TIMEOUT_HOLD"
        reason = reason.__cause__ or reason.__context__
    return "PROXY_CONNECTION_OTHER_HOLD"


def decoded_model_json(raw: bytes) -> object:
    """Decode only a complete model JSON object, including exact JSON fences."""
    try:
        envelope = json.loads(raw)
        content = envelope["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise Hold("PROXY_CONTENT_STRUCTURE_HOLD")
        stripped = content.strip()
        if stripped.startswith("```"):
            match = re.fullmatch(r"```(?:json|JSON)\r?\n([\s\S]*?)\r?\n```", stripped)
            if not match:
                raise Hold("PROXY_MODEL_JSON_HOLD")
            content = match.group(1)
        return json.loads(content)
    except Hold:
        raise
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise Hold("PROXY_MODEL_JSON_HOLD") from None


def parse_proxy_response(raw: bytes) -> dict:
    """Strict response parser; never expose remote text in exceptions."""
    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeError):
        raise Hold("PROXY_ENVELOPE_JSON_HOLD") from None
    if not isinstance(envelope, dict):
        raise Hold("PROXY_ENVELOPE_STRUCTURE_HOLD")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise Hold("PROXY_ENVELOPE_STRUCTURE_HOLD")
    choice = choices[0]
    if choice.get("finish_reason") == "length":
        raise Hold("PROXY_TRUNCATED_HOLD")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise Hold("PROXY_ENVELOPE_STRUCTURE_HOLD")
    content = message.get("content")
    if isinstance(content, list):
        if not all(isinstance(x, dict) and isinstance(x.get("text"), str)
                   for x in content):
            raise Hold("PROXY_CONTENT_STRUCTURE_HOLD")
        content = "".join(x["text"] for x in content)
    if not isinstance(content, str):
        raise Hold("PROXY_CONTENT_STRUCTURE_HOLD")
    if not content.strip():
        raise Hold("PROXY_EMPTY_HOLD")
    # Only a complete standalone JSON fence is normalized.
    # Never extract arbitrary braces or accept text outside that fence.
    stripped = content.strip()
    if stripped.startswith("```"):
        match = re.fullmatch(r"```(?:json|JSON)\r?\n([\s\S]*?)\r?\n```", stripped)
        if not match:
            raise Hold("PROXY_MODEL_JSON_HOLD")
        content = match.group(1)
    try:
        model_json = json.loads(content)
    except (ValueError, TypeError):
        raise Hold("PROXY_MODEL_JSON_HOLD") from None
    try:
        return reviewer.parse_model_response(model_json)
    except reviewer.Hold as exc:
        if str(exc) == "QUALITY_FLOOR_DECISION_INCONSISTENT":
            raise Hold("PROXY_PASS_BELOW_FLOOR_HOLD") from None
        if str(exc) == "SEVERE_FLAG_DECISION_INCONSISTENT":
            raise Hold("PROXY_SEVERE_FLAG_CONFLICT_HOLD") from None
        raise Hold("PROXY_RUBRIC_SCHEMA_HOLD") from None
    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
        raise Hold("PROXY_RUBRIC_SCHEMA_HOLD") from None


def save_failed_response(output_dir: Path, position: int, raw: bytes) -> None:
    """Preserve private raw model reply for offline replay. No stdout content."""
    if not 1 <= position <= 20:
        raise Hold("POSITION_HOLD")
    diagnostics = output_dir.parent / (output_dir.name + "-response-diagnostics-v1")
    if diagnostics.exists():
        private.private_dir(diagnostics, create=False)
    else:
        private.private_dir(diagnostics, create=True)
    path = diagnostics / f"R60_PILOT20_FAILED_{position:04d}_PRIVATE.json"
    if path.exists() or path.is_symlink():
        # Never overwrite the first evidence snapshot.
        return
    private.write_new(path, raw)


def quarantine_private_conflict(output_dir: Path, *, position: int,
                                confirm_provenance: bool = False) -> dict:
    """CPU-only: preserve model verdict without wrongly promoting it to PASS."""
    if not confirm_provenance:
        raise Hold("SNAPSHOT_PROVENANCE_CONFIRMATION_REQUIRED")
    config, _packets, current = get_state(output_dir)
    if type(position) is not int or position != current["processed"] + 1:
        raise Hold("REPLAY_POSITION_HOLD")
    diagnostics = output_dir.parent / (output_dir.name + "-response-diagnostics-v1")
    private.private_dir(diagnostics, create=False)
    raw = private.read_private(
        diagnostics / f"R60_PILOT20_FAILED_{position:04d}_PRIVATE.json",
        MAX_REPLY_BYTES,
    )
    try:
        envelope = json.loads(raw)
        if (not isinstance(envelope, dict)
                or envelope.get("model") != config["model_id"]
                or not isinstance(envelope.get("id"), str)
                or not envelope["id"].strip()
                or envelope["choices"][0].get("finish_reason") != "stop"):
            raise Hold("SNAPSHOT_MODEL_BINDING_HOLD")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise Hold("SNAPSHOT_MODEL_BINDING_HOLD") from None
    model_value = decoded_model_json(raw)
    if not isinstance(model_value, dict):
        raise Hold("PROXY_RUBRIC_SCHEMA_HOLD")
    try:
        reviewer.parse_model_response(model_value)
    except reviewer.Hold as exc:
        if str(exc) != "QUALITY_FLOOR_DECISION_INCONSISTENT":
            raise Hold("PROXY_RUBRIC_SCHEMA_HOLD") from None
    else:
        raise Hold("NOT_A_QUALITY_CONFLICT_HOLD")
    if model_value.get("decision") != "PASS":
        raise Hold("PROXY_RUBRIC_SCHEMA_HOLD")
    record = {
        "schema": SCHEMA,
        "position": position,
        "packets_sha256": config["packets_sha256"],
        "model_id": config["model_id"],
        "conflict_code": "PROXY_PASS_BELOW_FLOOR_HOLD",
        "original_decision": model_value["decision"],
        "scores": model_value["scores"],
        "severe_flags": model_value["severe_flags"],
        "reason_cn": model_value["reason_cn"],
    }
    record["receipt_sha256"] = sha(canonical(record))
    private.write_new(output_dir / conflict_name(position), canonical(record))
    return get_state(output_dir)[2]


def replay_private_snapshot(output_dir: Path, *, position: int,
                            confirm_provenance: bool = False) -> dict:
    """CPU-only recovery of one already generated review, never model inference.

    Raw failed snapshots do not contain a cryptographic input-packet binding.
    Explicit operator provenance confirmation is therefore required.
    """
    if not confirm_provenance:
        raise Hold("SNAPSHOT_PROVENANCE_CONFIRMATION_REQUIRED")
    if type(position) is not int or not 1 <= position <= 20:
        raise Hold("POSITION_HOLD")
    config, _packets, current = get_state(output_dir)
    if position != current["processed"] + 1:
        raise Hold("REPLAY_POSITION_HOLD")
    diagnostics = output_dir.parent / (output_dir.name + "-response-diagnostics-v1")
    private.private_dir(diagnostics, create=False)
    snapshot = diagnostics / f"R60_PILOT20_FAILED_{position:04d}_PRIVATE.json"
    raw = private.read_private(snapshot, MAX_REPLY_BYTES)
    try:
        envelope = json.loads(raw)
        if (not isinstance(envelope, dict)
                or envelope.get("model") != config["model_id"]
                or not isinstance(envelope.get("id"), str)
                or not envelope["id"].strip()):
            raise Hold("SNAPSHOT_MODEL_BINDING_HOLD")
    except (ValueError, TypeError, AttributeError):
        raise Hold("SNAPSHOT_MODEL_BINDING_HOLD") from None
    answer = parse_proxy_response(raw)
    receipt = {
        "schema": SCHEMA,
        "position": position,
        "packets_sha256": config["packets_sha256"],
        "model_id": config["model_id"],
        **answer,
    }
    receipt["receipt_sha256"] = sha(canonical(receipt))
    private.write_new(output_dir / receipt_name(position), canonical(receipt))
    return get_state(output_dir)[2]


def proxy_request(endpoint: str, model: str, prompt: str, timeout: int,
                  output_dir: Path | None = None, position: int | None = None) -> dict:
    key = os.environ.get(API_KEY_ENV)
    if not key:
        raise Hold("PROXY_API_KEY_REQUIRED")
    body = claude_payload(model, prompt)
    request = urllib.request.Request(
        endpoint, data=canonical(body), method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect,
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_REPLY_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise Hold(safe_http_code(exc)) from None
    except (urllib.error.URLError, TimeoutError, OSError,
            ValueError) as exc:
        raise Hold(safe_transport_code(exc)) from None
    if len(raw) > MAX_REPLY_BYTES:
        raise Hold("PROXY_RESPONSE_OVERSIZE_HOLD")
    try:
        return parse_proxy_response(raw)
    except Hold:
        if output_dir is not None and position is not None:
            save_failed_response(output_dir, position, raw)
        raise

def validate_config(folder: Path) -> dict:
    private.private_dir(folder, create=False)
    config = json.loads(private.read_private(folder / CONFIG, MAX_RECEIPT_BYTES))
    if (
        not isinstance(config, dict)
        or set(config) != {"schema", "packet_dir", "packets_sha256", "model_id",
                           "endpoint", "provider", "timeout"}
        or config["schema"] != SCHEMA
        or type(config["packet_dir"]) is not str
        or type(config["packets_sha256"]) is not str
        or len(config["packets_sha256"]) != 64
        or type(config["model_id"]) is not str
        or not config["model_id"].strip()
        or config["provider"] != "4router_claude_top_level_system"
        or type(config["timeout"]) is not int
        or not 10 <= config["timeout"] <= 300
        or proxy_endpoint(config["endpoint"]) != config["endpoint"]
    ):
        raise Hold("CONFIG_HOLD")
    return config


def read_progress(folder: Path, config: dict, packets: dict) -> dict:
    entries = sorted(folder.iterdir())
    allowed = {CONFIG} | {receipt_name(i) for i in range(1, 21)} | {
        conflict_name(i) for i in range(1, 21)}
    if any(item.is_symlink() or not item.is_file() or item.name not in allowed
           for item in entries):
        raise Hold("FOREIGN_FILE_HOLD")
    names = {item.name for item in entries if item.name != CONFIG}
    decisions = Counter()
    flags = Counter()
    conflicts = Counter()
    processed = 0
    for i in range(1, 21):
        receipt = folder / receipt_name(i)
        conflict = folder / conflict_name(i)
        has_receipt = receipt.name in names
        has_conflict = conflict.name in names
        if has_receipt and has_conflict:
            raise Hold("DUPLICATE_REVIEW_POSITION_HOLD")
        if not has_receipt and not has_conflict:
            if any(receipt_name(j) in names or conflict_name(j) in names
                   for j in range(i + 1, 21)):
                raise Hold("NONCONTIGUOUS_HOLD")
            break
        processed += 1
        row = json.loads(private.read_private(
            receipt if has_receipt else conflict, MAX_RECEIPT_BYTES))
        if not isinstance(row, dict):
            raise Hold("RECEIPT_SCHEMA_HOLD")
        checksum = row.get("receipt_sha256")
        source = {key: value for key, value in row.items()
                  if key != "receipt_sha256"}
        common = (
            row.get("schema") == SCHEMA
            and row.get("position") == i
            and row.get("packets_sha256") == config["packets_sha256"]
            and row.get("model_id") == config["model_id"]
            and checksum == sha(canonical(source))
        )
        if not common:
            raise Hold("RECEIPT_BINDING_HOLD")
        if has_receipt:
            if set(row) != {"schema", "position", "packets_sha256",
                            "model_id", "decision", "scores",
                            "severe_flags", "reason_cn", "receipt_sha256"}:
                raise Hold("RECEIPT_SCHEMA_HOLD")
            answer = {k: row[k] for k in
                      ("decision", "scores", "severe_flags", "reason_cn")}
            reviewer.parse_model_response(answer)
            decisions[answer["decision"]] += 1
            flags.update({k: 1 for k, v in answer["severe_flags"].items() if v})
        else:
            if set(row) != {"schema", "position", "packets_sha256",
                            "model_id", "conflict_code", "original_decision",
                            "scores", "severe_flags", "reason_cn",
                            "receipt_sha256"}:
                raise Hold("RECEIPT_SCHEMA_HOLD")
            if (row["conflict_code"] != "PROXY_PASS_BELOW_FLOOR_HOLD"
                    or row["original_decision"] != "PASS"):
                raise Hold("RECEIPT_SCHEMA_HOLD")
            original = {"decision": row["original_decision"],
                        "scores": row["scores"],
                        "severe_flags": row["severe_flags"],
                        "reason_cn": row["reason_cn"]}
            try:
                reviewer.parse_model_response(original)
            except reviewer.Hold as exc:
                if str(exc) != "QUALITY_FLOOR_DECISION_INCONSISTENT":
                    raise Hold("RECEIPT_SCHEMA_HOLD") from None
            else:
                raise Hold("RECEIPT_SCHEMA_HOLD")
            conflicts["PASS_BELOW_FLOOR"] += 1
    return {
        "schema": SAFE_SCHEMA,
        "status": "PILOT20_LOCAL_REVIEW_COMPLETE__OWNER_ADJUDICATION_PENDING"
        if processed == 20 else
        "PILOT20_LOCAL_REVIEW_PARTIAL__OWNER_ADJUDICATION_PENDING",
        "total_cases": len(packets["packets"]),
        "model_reviewed": sum(decisions.values()),
        "processed": processed,
        "conflict_pending": sum(conflicts.values()),
        "remaining": 20 - processed,
        "model_decisions_advisory": {name: decisions[name] for name in
                                    ("PASS", "HOLD", "REJECT")},
        "model_severe_flag_counts_advisory": {
            name: flags[name] for name in private.SEVERE
        },
        "independent_reference_reviews": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_data_egress": bool(processed),
        "private_values_emitted": False,
    }


def initialize(packets_dir: Path, output_dir: Path, endpoint: str,
               model: str, timeout: int) -> dict:
    if output_dir.exists() or output_dir.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    packets, digest = load_packets(packets_dir)
    if not model.strip() or not 10 <= timeout <= 300:
        raise Hold("CONFIG_ARGS_HOLD")
    remote_endpoint = proxy_endpoint(endpoint)
    private.private_dir(output_dir, create=True)
    config = {
        "schema": SCHEMA, "packet_dir": str(packets_dir),
        "packets_sha256": digest, "model_id": model,
        "endpoint": remote_endpoint,
        "provider": "4router_claude_top_level_system", "timeout": timeout,
    }
    private.write_new(output_dir / CONFIG, canonical(config))
    return read_progress(output_dir, config, packets)


def get_state(output_dir: Path) -> tuple[dict, dict, dict]:
    config = validate_config(output_dir)
    packets, digest = load_packets(Path(config["packet_dir"]))
    if config["packets_sha256"] != digest:
        raise Hold("PACKETS_MODIFIED_HOLD")
    return config, packets, read_progress(output_dir, config, packets)


def advance(output_dir: Path, max_cases: int, *,
            execute: bool = False, allow_private_data_egress: bool = False) -> dict:
    if type(max_cases) is not int or not 1 <= max_cases <= MAX_CASES_PER_CALL:
        raise Hold("MAX_CASES_HOLD")
    if not execute or not allow_private_data_egress:
        raise Hold("EXPLICIT_EGRESS_APPROVAL_REQUIRED")
    if not os.environ.get(API_KEY_ENV):
        raise Hold("PROXY_API_KEY_REQUIRED")
    config, packets, current = get_state(output_dir)
    start = current["processed"]
    for i in range(start, min(start + max_cases, 20)):
        packet = packets["packets"][i]
        prompt = reviewer.prompt_for_case({
            "history_messages": packet["history_messages"],
            "target_text": packet["assistant_target"],
        })
        answer = proxy_request(
            config["endpoint"], config["model_id"], prompt, config["timeout"],
            output_dir, i + 1,
        )
        receipt = {
            "schema": SCHEMA,
            "position": i + 1,
            "packets_sha256": config["packets_sha256"],
            "model_id": config["model_id"],
            **answer,
        }
        receipt["receipt_sha256"] = sha(canonical(receipt))
        private.write_new(output_dir / receipt_name(i + 1), canonical(receipt))
    return get_state(output_dir)[2]


# Exact allowlist: never echo arbitrary exception strings from private I/O or APIs.
SAFE_REASON_CODES = frozenset({
    "PACKETS_SCHEMA_HOLD", "PACKET_ENTRY_HOLD", "PACKETS_QUOTA_HOLD",
    "PACKET_POSITION_DUPLICATE_HOLD", "PROXY_ENDPOINT_HOLD",
    "PROXY_API_KEY_REQUIRED", "PROXY_TRANSPORT_OR_HTTP_HOLD",
    "PROXY_HTTP_UNKNOWN_HOLD", "PROXY_CONNECTION_OR_TLS_HOLD",
    "PROXY_TIMEOUT_HOLD", "PROXY_TLS_CERT_VERIFY_HOLD",
    "PROXY_TLS_HANDSHAKE_HOLD", "PROXY_DNS_HOLD",
    "PROXY_CONNECTION_REFUSED_HOLD", "PROXY_CONNECTION_RESET_HOLD",
    "PROXY_CONNECTION_BROKEN_PIPE_HOLD", "PROXY_NETWORK_UNREACHABLE_HOLD",
    "PROXY_CONNECTION_OTHER_HOLD",
    "PROXY_RESPONSE_OVERSIZE_HOLD", "PROXY_TRUNCATED_HOLD",
    "PROXY_EMPTY_HOLD", "PROXY_RESPONSE_SCHEMA_HOLD",
    "PROXY_ENVELOPE_JSON_HOLD", "PROXY_ENVELOPE_STRUCTURE_HOLD",
    "PROXY_CONTENT_STRUCTURE_HOLD", "PROXY_MODEL_JSON_HOLD",
    "PROXY_RUBRIC_SCHEMA_HOLD", "PROXY_PASS_BELOW_FLOOR_HOLD",
    "PROXY_SEVERE_FLAG_CONFLICT_HOLD",
    "SNAPSHOT_PROVENANCE_CONFIRMATION_REQUIRED", "REPLAY_POSITION_HOLD",
    "SNAPSHOT_MODEL_BINDING_HOLD", "NOT_A_QUALITY_CONFLICT_HOLD",
    "DUPLICATE_REVIEW_POSITION_HOLD",
    "CONFIG_HOLD", "FOREIGN_FILE_HOLD", "NONCONTIGUOUS_HOLD",
    "RECEIPT_SCHEMA_HOLD", "RECEIPT_BINDING_HOLD", "PACKETS_MODIFIED_HOLD",
    "OUTPUT_EXISTS_HOLD", "CONFIG_ARGS_HOLD", "MAX_CASES_HOLD",
    "EXPLICIT_EGRESS_APPROVAL_REQUIRED", "POSITION_HOLD",
    "HISTORY_BOUNDARY_HOLD", "PROMPT_TOO_LARGE_HOLD",
    "MODEL_JSON_INVALID", "SEVERE_FLAG_DECISION_INCONSISTENT",
    "QUALITY_FLOOR_DECISION_INCONSISTENT",
})


def safe_reason_code(exc: Exception) -> str:
    if isinstance(exc, (Hold, reviewer.Hold)):
        code = str(exc)
        if re.fullmatch(
            r"PROXY_HTTP_[345][0-9]{2}(?:_(?:AUTH|PERMISSION|INVALID_REQUEST|"
            r"RATE_LIMIT|OVERLOADED|NOT_FOUND|QUOTA|BILLING|MODEL_NOT_FOUND))?_HOLD",
            code,
        ):
            return code
        return code if code in SAFE_REASON_CODES else "REVIEW_CONTRACT_HOLD"
    if isinstance(exc, FileNotFoundError):
        return "PRIVATE_FILE_MISSING_HOLD"
    if isinstance(exc, PermissionError):
        return "PRIVATE_FILE_PERMISSION_HOLD"
    if isinstance(exc, FileExistsError):
        return "PRIVATE_OUTPUT_EXISTS_HOLD"
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)):
        return "PRIVATE_JSON_INVALID_HOLD"
    if isinstance(exc, (OSError, ValueError, TypeError, KeyError)):
        return "PRIVATE_INPUT_OR_IO_HOLD"
    return "UNEXPECTED_TECHNICAL_HOLD"


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    init = sub.add_parser("init")
    init.add_argument("--packets-dir", type=Path, required=True)
    init.add_argument("--output-dir", type=Path, required=True)
    init.add_argument("--base-url", default=os.environ.get("CLI_PROXY_BASE_URL"))
    init.add_argument("--model", default=os.environ.get("CLI_PROXY_MODEL", MODEL_DEFAULT))
    init.add_argument("--timeout", type=int, default=180)
    run = sub.add_parser("advance")
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--max-cases", type=int, default=5)
    run.add_argument("--execute", action="store_true")
    run.add_argument("--allow-private-data-egress", action="store_true")
    quarantine = sub.add_parser("quarantine-snapshot")
    quarantine.add_argument("--output-dir", type=Path, required=True)
    quarantine.add_argument("--position", type=int, required=True)
    quarantine.add_argument("--confirm-snapshot-provenance", action="store_true")
    replay = sub.add_parser("replay-snapshot")
    replay.add_argument("--output-dir", type=Path, required=True)
    replay.add_argument("--position", type=int, required=True)
    replay.add_argument("--confirm-snapshot-provenance", action="store_true")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "init":
            result = initialize(args.packets_dir, args.output_dir, args.base_url,
                                args.model, args.timeout)
        elif args.mode == "quarantine-snapshot":
            result = quarantine_private_conflict(
                args.output_dir, position=args.position,
                confirm_provenance=args.confirm_snapshot_provenance,
            )
        elif args.mode == "replay-snapshot":
            result = replay_private_snapshot(
                args.output_dir, position=args.position,
                confirm_provenance=args.confirm_snapshot_provenance,
            )
        elif args.mode == "advance":
            result = advance(
                args.output_dir, args.max_cases, execute=args.execute,
                allow_private_data_egress=args.allow_private_data_egress,
            )
        else:
            result = get_state(args.output_dir)[2]
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never expose private error text
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "PILOT20_LOCAL_REVIEW_HOLD",
            "reason_code": safe_reason_code(exc),
            "stage": args.mode.upper(),
            "database_accessed": False, "gpu_job_started": False,
            "private_values_emitted": False, "quality_v1_admitted": 0,
            "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

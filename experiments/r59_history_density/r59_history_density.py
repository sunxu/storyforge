#!/usr/bin/env python3
"""Build a privacy-safe aggregate history-density report for frozen R59 Pilot8 prompts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path
from statistics import median
from typing import Any

SCHEMA = "storyforge-r59-semantic-review-prompt-private-v1"
REPORT_SCHEMA = "storyforge-r59-pilot8-history-density-report-v1"
TOKEN_SCHEMA = "storyforge-r59-pilot8-hf-cpu-review-token-safe-v1"
MAX_INPUT_BYTES = 160 * 1024 * 1024
EXPECTED_CASES = 8


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular_nofollow(path: Path, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("INPUT_FILE_TYPE_OR_LINK_COUNT_INVALID")
        if info.st_size <= 0 or info.st_size > max_bytes:
            raise ValueError("INPUT_SIZE_LIMIT_EXCEEDED")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) != info.st_size or len(raw) > max_bytes:
            raise ValueError("INPUT_CHANGED_OR_SIZE_INVALID")
        after = os.fstat(fd)
        before_identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if before_identity != after_identity:
            raise ValueError("INPUT_CHANGED_DURING_READ")
        return raw
    finally:
        os.close(fd)


def _percentile(values: list[int], p: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * p + 0.999999999)))
    return ordered[index]


def _nonnegative_int(value: Any, field: str, index: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"HISTORY_COVERAGE_FIELD_INVALID_{field.upper()}_CASE_{index}")
    return value


def load_rows(raw: bytes, expected_sha256: str, expected_fingerprint: str) -> list[dict[str, Any]]:
    if _sha256(raw) != expected_sha256:
        raise ValueError("SOURCE_SHA256_MISMATCH")
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("INPUT_JSONL_INVALID") from None
    if len(rows) != EXPECTED_CASES:
        raise ValueError("INPUT_CASE_COUNT_INVALID")
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("schema") != SCHEMA:
            raise ValueError(f"PROMPT_SCHEMA_INVALID_CASE_{index}")
        if row.get("pilot_index") != index or row.get("prompt_fingerprint") != expected_fingerprint:
            raise ValueError(f"PROMPT_IDENTITY_INVALID_CASE_{index}")
        if row.get("review_decision") is not None or row.get("gpu_started") is not False:
            raise ValueError(f"PROMPT_STATE_INVALID_CASE_{index}")
        if row.get("quality_v1_admitted") is not False:
            raise ValueError(f"PROMPT_ADMISSION_STATE_INVALID_CASE_{index}")
        messages = row.get("messages")
        if (
            not isinstance(messages, list)
            or len(messages) != 2
            or [m.get("role") for m in messages if isinstance(m, dict)] != ["system", "user"]
            or any(
                not isinstance(m, dict)
                or not isinstance(m.get("content"), str)
                or not m["content"].strip()
                for m in messages
            )
        ):
            raise ValueError(f"PROMPT_MESSAGES_INVALID_CASE_{index}")
        coverage = row.get("history_coverage")
        if not isinstance(coverage, dict) or coverage.get("scope") != "FULL_STAGED_SUFFIX_ONLY":
            raise ValueError(f"HISTORY_COVERAGE_SCOPE_INVALID_CASE_{index}")
        _nonnegative_int(
            coverage.get("retained_history_messages"), "retained_history_messages", index
        )
        _nonnegative_int(
            coverage.get("removed_upstream_prefix_messages"),
            "removed_upstream_prefix_messages",
            index,
        )
        flags = (
            "context_semantically_verified",
            "historical_world_card_approved",
            "history_origin_verified_from_database",
        )
        for flag in flags:
            if type(coverage.get(flag)) is not bool:
                raise ValueError(f"HISTORY_COVERAGE_FLAG_INVALID_{flag.upper()}_CASE_{index}")
    return rows


def load_token_summary(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    raw = _read_regular_nofollow(path, max_bytes=1024 * 1024)
    try:
        item = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("TOKEN_SAFE_JSON_INVALID") from None
    if (
        not isinstance(item, dict)
        or item.get("schema") != TOKEN_SCHEMA
        or item.get("cases_checked") != EXPECTED_CASES
    ):
        raise ValueError("TOKEN_SAFE_SCHEMA_OR_COUNT_INVALID")
    allowed = (
        "status",
        "cases_checked",
        "prompt_tokens_min",
        "prompt_tokens_median",
        "prompt_tokens_p95",
        "prompt_tokens_max",
        "over_budget_count",
        "max_model_len",
        "reserved_output_tokens",
        "max_total_tokens",
    )
    return {key: item.get(key) for key in allowed}


def build_report(
    rows: list[dict[str, Any]],
    input_sha256: str,
    token_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        messages = row["messages"]
        coverage = row["history_coverage"]
        retained = coverage["retained_history_messages"]
        removed = coverage["removed_upstream_prefix_messages"]
        user_chars = len(messages[1]["content"])
        system_chars = len(messages[0]["content"])
        total = retained + removed
        cases.append(
            {
                "pilot_index": index,
                "system_prompt_chars": system_chars,
                "serialized_user_prompt_chars": user_chars,
                "retained_history_messages": retained,
                "removed_upstream_prefix_messages": removed,
                "staged_source_history_messages": total,
                "retained_message_share": round(retained / total, 6) if total else None,
                "serialized_chars_per_retained_message": (
                    round(user_chars / retained, 2) if retained else None
                ),
                "context_semantically_verified": coverage["context_semantically_verified"],
                "historical_world_card_approved": coverage["historical_world_card_approved"],
                "history_origin_verified_from_database": (
                    coverage["history_origin_verified_from_database"]
                ),
            }
        )
    retained_values = [case["retained_history_messages"] for case in cases]
    removed_values = [case["removed_upstream_prefix_messages"] for case in cases]
    source_values = [case["staged_source_history_messages"] for case in cases]
    char_values = [case["serialized_user_prompt_chars"] for case in cases]
    return {
        "schema": REPORT_SCHEMA,
        "status": "R59_HISTORY_DENSITY_REPORT_READY",
        "source": {
            "input_sha256": input_sha256,
            "case_count": EXPECTED_CASES,
            "prompt_schema": SCHEMA,
            "history_scope": "FULL_STAGED_SUFFIX_ONLY",
            "private_text_included": False,
        },
        "aggregate": {
            "retained_history_messages_total": sum(retained_values),
            "removed_upstream_prefix_messages_total": sum(removed_values),
            "staged_source_history_messages_total": sum(source_values),
            "retained_history_messages_min": min(retained_values),
            "retained_history_messages_median": median(retained_values),
            "retained_history_messages_p95": _percentile(retained_values, 0.95),
            "retained_history_messages_max": max(retained_values),
            "removed_upstream_prefix_messages_min": min(removed_values),
            "removed_upstream_prefix_messages_median": median(removed_values),
            "removed_upstream_prefix_messages_p95": _percentile(removed_values, 0.95),
            "removed_upstream_prefix_messages_max": max(removed_values),
            "serialized_user_prompt_chars_total": sum(char_values),
            "serialized_user_prompt_chars_min": min(char_values),
            "serialized_user_prompt_chars_median": median(char_values),
            "serialized_user_prompt_chars_p95": _percentile(char_values, 0.95),
            "serialized_user_prompt_chars_max": max(char_values),
        },
        "tokenizer_summary": token_summary,
        "cases": cases,
        "interpretation_limits": [
            "The input stores each serialized conversation prompt as one system message and one user message; these wrapper roles are not the historical dialogue role distribution.",
            "Removed upstream-prefix message bodies are not present in this staged input; only their declared counts can be reported.",
            "This report measures staged-history volume and coverage metadata; it does not judge semantic necessity, quality, or training eligibility.",
            "No prompt text, character names, source identifiers, target text, or per-message content is emitted.",
        ],
        "gpu_started": False,
        "training_performed": False,
        "quality_v1_admitted": 0,
        "private_values_emitted": False,
    }


def _write_create_only(path: Path, raw: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temporary, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("OUTPUT_WRITE_INCOMPLETE")
            view = view[written:]
        os.fsync(fd)
        if stat.S_IMODE(os.fstat(fd).st_mode) & 0o077:
            raise OSError("OUTPUT_MODE_NOT_PRIVATE")
    except BaseException:
        os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    published = False
    try:
        os.link(temporary, path, follow_symlinks=False)
        published = True
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        if published:
            path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def render_markdown(report: dict[str, Any]) -> str:
    agg = report["aggregate"]
    lines = [
        "# R59 Pilot8 历史密度报告",
        "",
        f"状态：{report['status']}",
        f"样本数：{report['source']['case_count']}",
        "",
        "## 聚合统计",
        "",
        "| 指标 | 总计 | 最小 | 中位数 | P95 | 最大 |",
        "|---|---:|---:|---:|---:|---:|",
        f"| 保留历史消息 | {agg['retained_history_messages_total']} | {agg['retained_history_messages_min']} | {agg['retained_history_messages_median']} | {agg['retained_history_messages_p95']} | {agg['retained_history_messages_max']} |",
        f"| 上游移除前缀消息 | {agg['removed_upstream_prefix_messages_total']} | {agg['removed_upstream_prefix_messages_min']} | {agg['removed_upstream_prefix_messages_median']} | {agg['removed_upstream_prefix_messages_p95']} | {agg['removed_upstream_prefix_messages_max']} |",
        f"| 序列化 User Prompt 字符 | {agg['serialized_user_prompt_chars_total']} | {agg['serialized_user_prompt_chars_min']} | {agg['serialized_user_prompt_chars_median']} | {agg['serialized_user_prompt_chars_p95']} | {agg['serialized_user_prompt_chars_max']} |",
        "",
        "## 逐案聚合（仅索引，不含文本）",
        "",
        "| Pilot | User 字符 | 保留历史消息 | 上游移除消息 | 来源历史消息合计 | 保留比例 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        share = (
            "N/A"
            if case["retained_message_share"] is None
            else f"{case['retained_message_share']:.1%}"
        )
        lines.append(
            f"| {case['pilot_index']} | {case['serialized_user_prompt_chars']} | "
            f"{case['retained_history_messages']} | "
            f"{case['removed_upstream_prefix_messages']} | "
            f"{case['staged_source_history_messages']} | {share} |"
        )
    lines.extend(["", "## Tokenizer 聚合", ""])
    token = report.get("tokenizer_summary")
    if token is None:
        lines.append("未提供 Token SAFE；本报告不推算 Token 数。")
    else:
        lines.append(f"- 业务状态：`{token.get('status')}`")
        lines.append(
            "- Token min / median / P95 / max："
            f"{token.get('prompt_tokens_min')} / {token.get('prompt_tokens_median')} / "
            f"{token.get('prompt_tokens_p95')} / {token.get('prompt_tokens_max')}"
        )
        lines.append(f"- 超预算：{token.get('over_budget_count')} / {token.get('cases_checked')}")
    lines.extend(["", "## 解释限制", ""])
    lines.extend(f"- {item}" for item in report["interpretation_limits"])
    lines.extend(["", "本报告仅用于历史规模分析，不构成训练候选准入或训练授权。", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-fingerprint", required=True)
    parser.add_argument("--token-safe", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if (
        re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", args.expected_fingerprint) is None
    ):
        parser.error("SHA256 and fingerprint must be 64 lowercase hexadecimal characters")
    raw = _read_regular_nofollow(args.input, max_bytes=MAX_INPUT_BYTES)
    rows = load_rows(raw, args.expected_sha256, args.expected_fingerprint)
    token_summary = load_token_summary(args.token_safe)
    report = build_report(rows, args.expected_sha256, token_summary)
    output_dir = args.output_dir
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    if stat.S_IMODE(output_dir.stat().st_mode) & 0o077:
        raise ValueError("OUTPUT_DIRECTORY_NOT_PRIVATE")
    _write_create_only(
        output_dir / "R59_PILOT8_HISTORY_DENSITY_SAFE.json",
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode(),
    )
    _write_create_only(
        output_dir / "R59_PILOT8_HISTORY_DENSITY_REPORT.md",
        render_markdown(report).encode(),
    )
    print(
        json.dumps(
            {
                "schema": REPORT_SCHEMA,
                "status": "R59_HISTORY_DENSITY_REPORT_WRITTEN",
                "cases": EXPECTED_CASES,
                "gpu_started": False,
                "training_performed": False,
                "private_values_emitted": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "FILESYSTEM_OPERATION_FAILED"
        print(f"R59_HISTORY_DENSITY_HOLD: {type(exc).__name__}:{reason}", file=sys.stderr)
        raise SystemExit(2)

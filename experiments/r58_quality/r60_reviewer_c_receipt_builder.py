"""Owner-local, fail-closed receipt builder for the frozen R60 Gold72 C disagreement review.

No model execution, network, admission, training, or private case output.
Only interactive, individually answered Owner attestations can authorize a
final EXECUTION_COMPLETE receipt. All hashes cover original file bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from . import r60_reviewer_c_audit as audit
except ImportError:  # direct invocation via an absolute script path
    import r60_reviewer_c_audit as audit

SAFE_SCHEMA = "r60_gold72_reviewer_c_receipt_builder_safe_v1"
PACKAGE_SCHEMA = "r60_gold72_reviewer_c_disagreement_package_safe_v1"
PACKAGE_STATUS = "REVIEWER_C_DISAGREEMENT_PACKAGE_BUILT__AWAITING_INDEPENDENT_REVIEW"
MODES = {"STATELESS_API", "CHATGPT_TEMPORARY_CHAT"}
SENTINEL = "NOT_EXPOSED_BY_PROVIDER"
LIMITS = {
    "package_safe": 256 * 1024,
    "receipt_template": 2 * 1024 * 1024,
    "blind_input": 160 * 1024 * 1024,
    "instructions": 128 * 1024,
    "owner_map": 8 * 1024 * 1024,
    "result": 16 * 1024 * 1024,
    "execution_record": 32 * 1024 * 1024,
}
ATTESTATION_PROMPTS = {
    "reviewer_a_materials_not_provided": "Reviewer C 未获得 Reviewer A 的任何材料",
    "reviewer_b2_materials_not_provided": "Reviewer C 未获得 Reviewer B2 的任何材料",
    "owner_id_map_not_provided": "Reviewer C 未获得 Owner ID Map 或原始案例身份",
    "prior_conversations_or_memory_not_used": "独立执行未使用任何旧会话、记忆或历史上下文",
    "tools_and_connectors_not_used": "独立执行未使用任何工具、连接器、搜索或仓库",
    "all_40_cases_reviewed_independently": "全部 40 条均在所声明的独立环境中完成审核",
}
OWNER_PROMPTS = {
    "input_hashes_rechecked": "已复核工具重新计算的 Blind Input / Instructions 哈希及 SAFE pins",
    "execution_record_inspected": "已亲自打开检查真实完整的执行转录/提供方记录及其限制",
    "result_hash_rechecked": "已复核工具重新计算的 Results 原始字节 SHA256",
    "case_binding_rechecked": "已复核工具报告的 Blind ↔ Owner Map ↔ Results 40/40 逐案绑定",
}


class ReceiptHold(ValueError):
    """A fixed, non-sensitive reason code."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, limit: int) -> bytes:
    """Read a stable, nonempty regular file without following the final symlink."""
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
            raise ReceiptHold("INPUT_NOT_REGULAR_OR_SIZE_INVALID")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise ReceiptHold("INPUT_CHANGED_DURING_OPEN")
            if not stat.S_ISREG(opened.st_mode) or not 0 < opened.st_size <= limit:
                raise ReceiptHold("INPUT_NOT_REGULAR_OR_SIZE_INVALID")
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        if not 0 < len(data) <= limit or (after.st_size, after.st_mtime_ns) != (
            opened.st_size, opened.st_mtime_ns
        ):
            raise ReceiptHold("INPUT_CHANGED_OR_SIZE_INVALID")
        return data
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        raise ReceiptHold("INPUT_NOT_REGULAR_OR_SIZE_INVALID") from None


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    return audit._json(raw, reason)


def _validate_binding(blind: bytes, mapping: bytes, results: bytes) -> dict[str, int]:
    """Match the existing Audit structural contract *without* assuming attestations."""
    packets = audit._jsonl(blind, "C_BLIND_INPUT_INVALID")
    if any(p.get("schema") != audit.BLIND_SCHEMA or p.get("reviewer") != "C" for p in packets):
        raise ReceiptHold("C_BLIND_PACKET_SCHEMA_INVALID")
    cases = []
    for packet in packets:
        rows = packet.get("cases")
        if not isinstance(rows, list) or not rows or any(not isinstance(x, dict) for x in rows):
            raise ReceiptHold("C_BLIND_PACKET_CASES_INVALID")
        cases.extend(rows)
    if len(cases) != 40:
        raise ReceiptHold("C_BLIND_CASE_COUNT_INVALID")
    blind_ids = audit._unique(cases, "blind_case_id", "C_BLIND_ID_DUPLICATE")
    blind_sha = audit._unique(cases, "target_sha256", "C_BLIND_TARGET_SHA_DUPLICATE")

    owner = _json(mapping, "C_OWNER_MAP_INVALID")
    owners = owner.get("mapping")
    if owner.get("schema") != audit.MAP_SCHEMA or owner.get("reviewer") != "C":
        raise ReceiptHold("C_OWNER_MAP_SCHEMA_INVALID")
    if not isinstance(owners, list) or len(owners) != 40 or any(not isinstance(x, dict) for x in owners):
        raise ReceiptHold("C_OWNER_MAP_COUNT_INVALID")
    owner_ids = audit._unique(owners, "blind_case_id", "C_OWNER_MAP_BLIND_ID_INVALID")
    owner_sha = audit._unique(owners, "target_sha256", "C_OWNER_MAP_TARGET_SHA_INVALID")
    if set(blind_ids) != set(owner_ids) or set(blind_sha) != set(owner_sha):
        raise ReceiptHold("C_BLIND_OWNER_MAP_SET_MISMATCH")
    for key, row in owner_ids.items():
        if (row.get("target_sha256") != blind_ids[key].get("target_sha256")
            or not isinstance(row.get("original_case_id"), str)
            or not row["original_case_id"]
            or not isinstance(row.get("original_story_uuid"), str)
            or not row["original_story_uuid"]):
            raise ReceiptHold("C_OWNER_MAP_CASE_BINDING_INVALID")

    result = _json(results, "C_RESULT_JSON_INVALID")
    if (result.get("schema") != audit.RESULT_SCHEMA or result.get("reviewer") != "C"
        or result.get("status") != "REVIEW_COMPLETE"):
        raise ReceiptHold("C_RESULT_SCHEMA_INVALID")
    rows = result.get("cases")
    if not isinstance(rows, list) or len(rows) != 40 or any(not isinstance(x, dict) for x in rows):
        raise ReceiptHold("C_RESULT_CASE_COUNT_INVALID")
    result_ids = audit._unique(rows, "blind_case_id", "C_RESULT_BLIND_ID_INVALID")
    result_sha = audit._unique(rows, "target_sha256", "C_RESULT_TARGET_SHA_INVALID")
    if set(result_ids) != set(owner_ids) or set(result_sha) != set(owner_sha):
        raise ReceiptHold("C_RESULT_OWNER_MAP_SET_MISMATCH")
    decisions: Counter[str] = Counter()
    for key, row in result_ids.items():
        if row.get("target_sha256") != owner_ids[key].get("target_sha256"):
            raise ReceiptHold("C_RESULT_TARGET_SHA_MISMATCH")
        decision, scores = row.get("decision"), row.get("scores_1_to_5")
        if decision not in {"PASS", "HOLD", "REJECT"}:
            raise ReceiptHold("C_RESULT_DECISION_INVALID")
        if not audit._scores_valid(scores):
            raise ReceiptHold("C_RESULT_SCORES_INVALID")
        flags, evidence = row.get("severe_flags"), row.get("evidence_summary")
        if not isinstance(flags, list) or any(not isinstance(f, str) for f in flags):
            raise ReceiptHold("C_RESULT_SEVERE_FLAGS_INVALID")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ReceiptHold("C_RESULT_EVIDENCE_SUMMARY_MISSING")
        if decision == "PASS" and (flags or any(scores[k] < v for k, v in audit.SCORE_FLOORS.items())):
            raise ReceiptHold("C_PASS_GATE_VIOLATION")
        decisions[decision] += 1
    counts = {key: decisions.get(key, 0) for key in ("PASS", "HOLD", "REJECT")}
    if result.get("counts") != counts or sum(counts.values()) != 40:
        raise ReceiptHold("C_RESULT_COUNTS_INVALID")
    return counts


def _validate_package(safe_raw: bytes, template_raw: bytes, raw: dict[str, bytes]) -> dict:
    safe = _json(safe_raw, "C_PACKAGE_SAFE_INVALID")
    template = _json(template_raw, "C_RECEIPT_TEMPLATE_INVALID")
    if (safe.get("schema") != PACKAGE_SCHEMA or safe.get("status") != PACKAGE_STATUS
        or type(safe.get("candidate_count")) is not int or safe["candidate_count"] != 40):
        raise ReceiptHold("C_PACKAGE_SAFE_INVALID")
    for key in ("blind_input", "instructions", "owner_map"):
        if safe.get(key + "_sha256") != _sha(raw[key]):
            raise ReceiptHold("C_PACKAGE_PIN_MISMATCH")
    if safe.get("execution_receipt_template_sha256") != _sha(template_raw):
        raise ReceiptHold("C_PACKAGE_PIN_MISMATCH")
    if (template.get("schema") != audit.EXECUTION_SCHEMA or template.get("reviewer") != "C"
        or template.get("status") != "PENDING_INDEPENDENT_REVIEW_EXECUTION"
        or template.get("blind_input_sha256") != _sha(raw["blind_input"])
        or template.get("instructions_sha256") != _sha(raw["instructions"])
        or set(template.get("attestations", {})) != audit.ATTESTATIONS
        or set(template.get("owner_verification", {})) != audit.OWNER_VERIFICATION):
        raise ReceiptHold("C_RECEIPT_TEMPLATE_INVALID")
    if any(value is not None for value in template["attestations"].values()) or any(
        value is not False for value in template["owner_verification"].values()
    ):
        raise ReceiptHold("C_RECEIPT_TEMPLATE_PRECONFIRMED")
    return template


def _utc(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _ask(prompt: str) -> str:
    print(prompt, file=sys.stderr, flush=True)
    return sys.stdin.readline().strip()


def _confirm(key: str, meaning: str) -> bool | None:
    response = _ask(f"[{key}] {meaning}。逐项回答 YES / NO / UNKNOWN：").upper()
    return {"YES": True, "NO": False, "UNKNOWN": None}.get(response)


def _output_check(path: Path, repo: Path) -> None:
    if not path.is_absolute() or path.is_symlink() or path.exists():
        raise ReceiptHold("C_OUTPUT_PATH_INVALID_OR_EXISTS")
    parent = path.parent
    if (not parent.is_dir() or parent.is_symlink()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
        or parent.resolve().is_relative_to(repo.resolve())):
        raise ReceiptHold("C_OUTPUT_LOCATION_INVALID")


def _create_only(path: Path, value: dict[str, Any]) -> None:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    if len(data) > 2 * 1024 * 1024:
        raise ReceiptHold("C_RECEIPT_SIZE_INVALID")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo_root.resolve()
    _output_check(args.output, repo)
    if args.draft_output is not None:
        _output_check(args.draft_output, repo)
        if args.output == args.draft_output:
            raise ReceiptHold("C_OUTPUT_PATHS_IDENTICAL")
    raw = {key: _read(getattr(args, key), limit) for key, limit in LIMITS.items()}
    template = _validate_package(raw["package_safe"], raw["receipt_template"], raw)
    counts = _validate_binding(raw["blind_input"], raw["owner_map"], raw["result"])
    if raw["execution_record"] == raw["result"]:
        raise ReceiptHold("C_EXECUTION_RECORD_EQUALS_RESULT")
    hashes = {
        "blind_input_sha256": _sha(raw["blind_input"]),
        "instructions_sha256": _sha(raw["instructions"]),
        "result_sha256": _sha(raw["result"]),
        "transcript_or_provider_record_sha256": _sha(raw["execution_record"]),
    }
    safe = {
        "schema": SAFE_SCHEMA, "candidate_count": 40, "case_bindings_valid": 40,
        "decision_counts": counts, "raw_sha256": hashes,
        "quality_v1_admitted": 0, "training_authorized": False,
        "gpu_started": False, "r50_accessed": False, "private_values_emitted": False,
    }
    if args.validate_only:
        return {**safe, "status": "C_RECEIPT_INPUTS_VALID__OWNER_CONFIRMATION_PENDING"}
    for key, digest in hashes.items():
        print(f"Recomputed {key}: {digest}", file=sys.stderr)
    print("Structural binding: 40/40; this does NOT prove reviewer independence.", file=sys.stderr)
    receipt = dict(template)
    receipt.update(hashes)
    receipt["execution_mode"] = _ask("实际执行模式：STATELESS_API / CHATGPT_TEMPORARY_CHAT")
    for field, label in (
        ("provider", "真实 provider"), ("model_id", "真实 model ID / 可见 UI model label（勿编造）"),
        ("model_version", "实际可见 model version（未知时可留空）"),
        ("session_or_request_id", f"实际 session / request ID（Temporary Chat 未公开时填 {SENTINEL}）"),
        ("started_at_utc", "实际开始时间（带时区 ISO8601，不可使用脚本当前时间）"),
        ("completed_at_utc", "实际结束时间（带时区 ISO8601）"),
    ):
        receipt[field] = _ask(label) or None
    limitations = template.get("limitations", [])
    if not isinstance(limitations, list) or any(not isinstance(x, str) for x in limitations):
        raise ReceiptHold("C_RECEIPT_TEMPLATE_INVALID")
    receipt["limitations"] = list(limitations)
    if receipt["session_or_request_id"] == SENTINEL:
        receipt["limitations"].append("Provider did not expose a session ID; sentinel is not a real ID.")
    if isinstance(receipt["model_id"], str) and "backend model ID unavailable" in receipt["model_id"]:
        receipt["limitations"].append("Backend model ID unavailable; only UI label recorded.")
    start = _utc(receipt["started_at_utc"] or "")
    end = _utc(receipt["completed_at_utc"] or "")
    timestamps_valid = start is not None and end is not None and end >= start
    if timestamps_valid:
        receipt["started_at_utc"] = start.isoformat().replace("+00:00", "Z")
        receipt["completed_at_utc"] = end.isoformat().replace("+00:00", "Z")
    print("六项执行独立性声明：仅根据真实独立执行事实回答；无法证明时选 UNKNOWN。", file=sys.stderr)
    receipt["attestations"] = {
        key: _confirm(key, meaning) for key, meaning in ATTESTATION_PROMPTS.items()
    }
    print("四项 Owner 验证：须亲自检查执行记录真实性并逐项回答。", file=sys.stderr)
    receipt["owner_verification"] = {
        key: _confirm(key, meaning) for key, meaning in OWNER_PROMPTS.items()
    }
    metadata_valid = (
        receipt["execution_mode"] in MODES
        and all(isinstance(receipt[k], str) and receipt[k].strip() for k in ("provider", "model_id", "session_or_request_id"))
        and (receipt["session_or_request_id"] != SENTINEL or receipt["execution_mode"] == "CHATGPT_TEMPORARY_CHAT")
        and timestamps_valid
    )
    complete = (metadata_valid
                and all(v is True for v in receipt["attestations"].values())
                and all(v is True for v in receipt["owner_verification"].values()))
    # Re-read every input immediately before any write, rejecting mid-run mutations.
    if any(_read(getattr(args, key), LIMITS[key]) != data for key, data in raw.items()):
        raise ReceiptHold("INPUT_CHANGED_DURING_CONFIRMATION")
    if not complete:
        receipt["status"] = "PENDING_OWNER_CONFIRMATION"
        if args.draft_output is not None:
            _create_only(args.draft_output, receipt)
        return {**safe, "status": "C_RECEIPT_HOLD", "reason_code": "OWNER_CONFIRMATION_INCOMPLETE",
                "draft_created": args.draft_output is not None}
    receipt["status"] = "EXECUTION_COMPLETE"
    final_raw = json.dumps(receipt, ensure_ascii=False).encode()
    audit.audit(raw["blind_input"], raw["instructions"], raw["owner_map"], raw["result"],
                final_raw, raw["execution_record"])
    _create_only(args.output, receipt)
    return {**safe, "status": "C_EXECUTION_RECEIPT_CREATED__SELF_ATTESTED_NOT_PROVEN"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in LIMITS:
        parser.add_argument("--" + key.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draft-output", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        safe = run(args)
        print(json.dumps(safe, sort_keys=True, ensure_ascii=False))
        return 42 if safe["status"] == "C_RECEIPT_HOLD" else 0
    except (ReceiptHold, audit.AuditHold, OSError, ValueError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, (ReceiptHold, audit.AuditHold)) else "INPUT_OR_IO_ERROR"
        print(json.dumps({"schema": SAFE_SCHEMA, "status": "C_RECEIPT_HOLD", "reason_code": reason,
                          "quality_v1_admitted": 0, "training_authorized": False,
                          "gpu_started": False, "r50_accessed": False,
                          "private_values_emitted": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

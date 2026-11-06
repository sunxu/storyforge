"""Owner-only audit of R60 Gold72 Reviewer B2 result and execution receipt.

Verifies exact input/instruction/result/transcript hashes and all 72 blind-ID
to target-SHA joins against the private Owner map. Execution declarations are
reported as attestations, never upgraded to cryptographic proof of independence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

BLIND_SCHEMA = "r60_gold72_reviewer_b2_blind_story_packet_v1"
MAP_SCHEMA = "r60_gold72_reviewer_b2_private_id_map_v1"
EXECUTION_SCHEMA = "r60_gold72_reviewer_b2_execution_receipt_v1"
RESULT_SCHEMA = "r60_gold72_reviewer_b2_results_v1"
SAFE_SCHEMA = "r60_gold72_reviewer_b2_audit_safe_v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCORE_FLOORS = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 3,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}
ATTESTATIONS = {
    "reviewer_a_materials_not_provided",
    "reviewer_b1_materials_not_provided",
    "owner_id_map_not_provided",
    "prior_conversations_or_memory_not_used",
    "tools_and_connectors_not_used",
    "all_72_cases_reviewed_independently",
}


class AuditHold(ValueError):
    """Fixed fail-closed reason code."""


def _read(path: Path, limit: int = 160 * 1024 * 1024) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AuditHold("INPUT_NOT_REGULAR_FILE")
    raw = path.read_bytes()
    if not 0 < len(raw) <= limit:
        raise AuditHold("INPUT_SIZE_INVALID")
    return raw


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise AuditHold(reason) from None
    if not isinstance(value, dict):
        raise AuditHold(reason)
    return value


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise AuditHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise AuditHold(reason)
    return rows


def _unique(rows: list[dict[str, Any]], key: str, reason: str):
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise AuditHold(reason)
        result[value] = row
    return result


def _scores_valid(scores: Any) -> bool:
    return (
        isinstance(scores, dict)
        and set(scores) == set(SCORE_FLOORS)
        and all(type(value) is int and 1 <= value <= 5 for value in scores.values())
    )


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def audit(
    blind_raw: bytes,
    instructions_raw: bytes,
    map_raw: bytes,
    result_raw: bytes,
    receipt_raw: bytes,
    execution_record_raw: bytes,
):
    blind_packets = _jsonl(blind_raw, "B2_BLIND_INPUT_INVALID")
    if any(packet.get("schema") != BLIND_SCHEMA or packet.get("reviewer") != "B2"
           for packet in blind_packets):
        raise AuditHold("B2_BLIND_PACKET_SCHEMA_INVALID")
    blind_rows = []
    for packet in blind_packets:
        cases = packet.get("cases")
        if not isinstance(cases, list) or not cases:
            raise AuditHold("B2_BLIND_PACKET_CASES_INVALID")
        for case in cases:
            if not isinstance(case, dict):
                raise AuditHold("B2_BLIND_CASE_INVALID")
            blind_rows.append(case)
    if len(blind_rows) != 72:
        raise AuditHold("B2_BLIND_CASE_COUNT_INVALID")
    blind_idx = _unique(blind_rows, "blind_case_id", "B2_BLIND_ID_DUPLICATE")
    blind_sha_idx = _unique(blind_rows, "target_sha256", "B2_BLIND_TARGET_SHA_DUPLICATE")

    owner_map = _json(map_raw, "B2_OWNER_MAP_INVALID")
    if owner_map.get("schema") != MAP_SCHEMA or owner_map.get("reviewer") != "B2":
        raise AuditHold("B2_OWNER_MAP_SCHEMA_INVALID")
    mapping = owner_map.get("mapping")
    if not isinstance(mapping, list) or len(mapping) != 72:
        raise AuditHold("B2_OWNER_MAP_COUNT_INVALID")
    map_idx = _unique(mapping, "blind_case_id", "B2_OWNER_MAP_BLIND_ID_INVALID")
    map_sha_idx = _unique(mapping, "target_sha256", "B2_OWNER_MAP_TARGET_SHA_INVALID")
    if set(map_idx) != set(blind_idx) or set(map_sha_idx) != set(blind_sha_idx):
        raise AuditHold("B2_BLIND_OWNER_MAP_SET_MISMATCH")
    for blind_id, owner in map_idx.items():
        case = blind_idx[blind_id]
        if (
            owner.get("target_sha256") != case.get("target_sha256")
            or not isinstance(owner.get("original_case_id"), str)
            or not owner.get("original_case_id")
            or not isinstance(owner.get("original_story_uuid"), str)
            or not owner.get("original_story_uuid")
        ):
            raise AuditHold("B2_OWNER_MAP_CASE_BINDING_INVALID")

    result = _json(result_raw, "B2_RESULT_JSON_INVALID")
    if (
        result.get("schema") != RESULT_SCHEMA
        or result.get("reviewer") != "B2"
        or result.get("status") != "REVIEW_COMPLETE"
    ):
        raise AuditHold("B2_RESULT_SCHEMA_INVALID")
    result_rows = result.get("cases")
    if not isinstance(result_rows, list) or len(result_rows) != 72:
        raise AuditHold("B2_RESULT_CASE_COUNT_INVALID")
    result_idx = _unique(result_rows, "blind_case_id", "B2_RESULT_BLIND_ID_INVALID")
    result_sha_idx = _unique(result_rows, "target_sha256", "B2_RESULT_TARGET_SHA_INVALID")
    if set(result_idx) != set(map_idx) or set(result_sha_idx) != set(map_sha_idx):
        raise AuditHold("B2_RESULT_OWNER_MAP_SET_MISMATCH")

    decisions = Counter()
    complete_scores = 0
    pass_gate_violations = 0
    for blind_id, row in result_idx.items():
        owner = map_idx[blind_id]
        if row.get("target_sha256") != owner.get("target_sha256"):
            raise AuditHold("B2_RESULT_TARGET_SHA_MISMATCH")
        decision = row.get("decision")
        if decision not in {"PASS", "HOLD", "REJECT"}:
            raise AuditHold("B2_RESULT_DECISION_INVALID")
        decisions[decision] += 1
        scores = row.get("scores_1_to_5")
        if not _scores_valid(scores):
            raise AuditHold("B2_RESULT_SCORES_INVALID")
        complete_scores += 1
        severe = row.get("severe_flags")
        summary = row.get("evidence_summary")
        if not isinstance(severe, list) or any(not isinstance(flag, str) for flag in severe):
            raise AuditHold("B2_RESULT_SEVERE_FLAGS_INVALID")
        if not isinstance(summary, str) or not summary.strip():
            raise AuditHold("B2_RESULT_EVIDENCE_SUMMARY_MISSING")
        if decision == "PASS" and (
            severe or any(scores[key] < floor for key, floor in SCORE_FLOORS.items())
        ):
            pass_gate_violations += 1
    expected_counts = {key: decisions.get(key, 0) for key in ("PASS", "HOLD", "REJECT")}
    if result.get("counts") != expected_counts or sum(expected_counts.values()) != 72:
        raise AuditHold("B2_RESULT_COUNTS_INVALID")
    if pass_gate_violations:
        raise AuditHold("B2_PASS_GATE_VIOLATION")

    receipt = _json(receipt_raw, "B2_EXECUTION_RECEIPT_INVALID")
    if receipt.get("schema") != EXECUTION_SCHEMA or receipt.get("reviewer") != "B2":
        raise AuditHold("B2_EXECUTION_RECEIPT_SCHEMA_INVALID")
    if (
        receipt.get("blind_input_sha256") != _sha(blind_raw)
        or receipt.get("instructions_sha256") != _sha(instructions_raw)
        or receipt.get("result_sha256") != _sha(result_raw)
        or receipt.get("transcript_or_provider_record_sha256") != _sha(execution_record_raw)
    ):
        raise AuditHold("B2_EXECUTION_HASH_BINDING_MISMATCH")
    if receipt.get("execution_mode") not in {"STATELESS_API", "CHATGPT_TEMPORARY_CHAT"}:
        raise AuditHold("B2_EXECUTION_MODE_INVALID")
    for field in ("provider", "model_id", "session_or_request_id"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise AuditHold("B2_EXECUTION_METADATA_MISSING")
    if not _aware_timestamp(receipt.get("started_at_utc")) or not _aware_timestamp(
        receipt.get("completed_at_utc")
    ):
        raise AuditHold("B2_EXECUTION_TIMESTAMPS_INVALID")
    attestations = receipt.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != ATTESTATIONS:
        raise AuditHold("B2_EXECUTION_ATTESTATIONS_INVALID")
    if any(attestations.get(key) is not True for key in ATTESTATIONS):
        raise AuditHold("B2_EXECUTION_ATTESTATIONS_INCOMPLETE")

    return {
        "schema": SAFE_SCHEMA,
        "status": "B2_RESULT_BINDING_VALID__EXECUTION_ATTESTATION_PRESENT_NOT_PROVEN",
        "candidate_count": 72,
        "blind_input_cases": len(blind_idx),
        "owner_map_cases": len(map_idx),
        "result_cases": len(result_idx),
        "blind_input_to_owner_map_matches": 72,
        "owner_map_to_result_matches": 72,
        "scores_complete": complete_scores,
        "decision_counts": dict(sorted(expected_counts.items())),
        "pass_gate_violations": pass_gate_violations,
        "blind_input_sha256": _sha(blind_raw),
        "instructions_sha256": _sha(instructions_raw),
        "owner_map_sha256": _sha(map_raw),
        "result_sha256": _sha(result_raw),
        "execution_record_sha256": _sha(execution_record_raw),
        "execution_mode": receipt["execution_mode"],
        "execution_attestations_complete": True,
        "execution_attestation_is_self_reported": True,
        "cryptographic_independence_proven": False,
        "reviewer_b2_independence_verified": False,
        "owner_manual_execution_record_inspection_required": True,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "blind-input", "instructions", "owner-map", "result",
        "execution-receipt", "execution-record",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--safe-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        values = [
            _read(args.blind_input),
            _read(args.instructions, 128 * 1024),
            _read(args.owner_map, 8 * 1024 * 1024),
            _read(args.result, 16 * 1024 * 1024),
            _read(args.execution_receipt, 2 * 1024 * 1024),
            _read(args.execution_record, 32 * 1024 * 1024),
        ]
        safe = audit(*values)
        if args.safe_output.exists() or args.safe_output.is_symlink():
            raise AuditHold("B2_SAFE_OUTPUT_ALREADY_EXISTS")
        raw = json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
        fd = args.safe_output.open("xb")
        with fd:
            fd.write(raw)
        args.safe_output.chmod(0o600)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (AuditHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, AuditHold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "B2_AUDIT_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())

"""Owner-only crosswalk of frozen Gold72 Reviewer A V3 and independent B2 results.

The tool revalidates the B2 receipt/audit inputs, joins both reviews to the
same frozen Gold72 target identities, and emits aggregate SAFE statistics.
It never emits case identifiers or private review text and never admits data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from . import r60_reviewer_ab_canonical_crosswalk as canonical
from . import r60_reviewer_b2_audit as b2_audit

SAFE_SCHEMA = "r60_gold72_reviewer_a_b2_crosswalk_safe_v1"
SAFE_STATUS = "A_B2_CROSSWALK_COMPLETE__ADMISSION_HOLD"
B2_SAFE_SCHEMA = "r60_gold72_reviewer_b2_audit_safe_v1"
B2_SAFE_STATUS = "B2_RESULT_BINDING_VALID__EXECUTION_ATTESTATION_PRESENT_NOT_PROVEN"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCORE_FIELDS = canonical.SCORE_FIELDS


class CrosswalkHold(ValueError):
    """Fixed, non-sensitive reason code."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, limit: int = 160 * 1024 * 1024) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CrosswalkHold("INPUT_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    if not 0 < len(raw) <= limit:
        raise CrosswalkHold("INPUT_SIZE_INVALID")
    return raw


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise CrosswalkHold(reason) from None
    if not isinstance(value, dict):
        raise CrosswalkHold(reason)
    return value


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line)
            for line in raw.decode("utf-8").splitlines()
            if line.strip()
        ]
    except (ValueError, UnicodeError):
        raise CrosswalkHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise CrosswalkHold(reason)
    return rows


def _unique(rows: list[dict[str, Any]], key: str, reason: str):
    indexed = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in indexed:
            raise CrosswalkHold(reason)
        indexed[value] = row
    return indexed


def _a_decision(row: dict[str, Any]) -> str | None:
    value = row.get("decision_for_strict_ab_decision_comparison")
    if value is None:
        return None
    mapping = {"PASS_ONLY": "PASS", "HOLD": "HOLD", "REJECT": "REJECT"}
    if value not in mapping:
        raise CrosswalkHold("A_DECISION_LABEL_INVALID")
    return mapping[value]


def _validate_staging(
    staged_raw: bytes,
    staging_safe: dict[str, Any],
    owner_rows: list[dict[str, Any]],
):
    staged_rows = _jsonl(staged_raw, "STAGED_JSONL_INVALID")
    if len(staged_rows) != 72:
        raise CrosswalkHold("STAGED_CASE_COUNT_INVALID")
    staged_sha = _sha(staged_raw)
    source_sha = staging_safe.get("source_context_file_sha256")
    if (
        staging_safe.get("schema") != canonical.RECEIPT_SCHEMA
        or staging_safe.get("status") != canonical.RECEIPT_STATUS
        or staging_safe.get("staged_file_sha256") != staged_sha
        or staging_safe.get("source_rows") != 72
        or staging_safe.get("context_staged") != 72
        or staging_safe.get("context_structure_hold") != 0
        or staging_safe.get("source_histories_mutated") is not False
        or staging_safe.get("original_staging_mutated") is not False
        or staging_safe.get("quality_v1_admitted") != 0
        or staging_safe.get("training_authorized") is not False
        or not isinstance(source_sha, str)
        or not HEX64.fullmatch(source_sha)
    ):
        raise CrosswalkHold("STAGING_RECEIPT_INVALID")
    staged_idx = {}
    for row in staged_rows:
        digest = row.get("target_sha256")
        if (
            row.get("schema") != canonical.STAGE_SCHEMA
            or row.get("status") != canonical.STAGE_STATUS
            or not isinstance(row.get("case_id"), str)
            or not row["case_id"]
            or not isinstance(digest, str)
            or not HEX64.fullmatch(digest)
            or digest in staged_idx
        ):
            raise CrosswalkHold("STAGED_ROW_INVALID")
        staged_idx[digest] = row

    owner_idx = _unique(owner_rows, "target_sha256", "OWNER_TARGET_IDENTITY_INVALID")
    if len(owner_idx) != 72 or set(owner_idx) != set(staged_idx):
        raise CrosswalkHold("OWNER_STAGED_TARGET_SET_MISMATCH")
    for digest, owner in owner_idx.items():
        staged = staged_idx[digest]
        if (
            owner.get("case_id") != staged.get("case_id")
            or owner.get("staged_file_sha256") != staged_sha
            or owner.get("source_context_file_sha256") != source_sha
        ):
            raise CrosswalkHold("OWNER_STAGING_IDENTITY_OR_PIN_MISMATCH")
    return staged_idx, owner_idx, staged_sha, source_sha


def _validate_b2_safe(
    safe: dict[str, Any],
    fresh: dict[str, Any],
):
    if (
        safe.get("schema") != B2_SAFE_SCHEMA
        or safe.get("status") != B2_SAFE_STATUS
        or safe.get("candidate_count") != 72
        or safe.get("blind_input_cases") != 72
        or safe.get("owner_map_cases") != 72
        or safe.get("result_cases") != 72
        or safe.get("blind_input_to_owner_map_matches") != 72
        or safe.get("owner_map_to_result_matches") != 72
        or safe.get("scores_complete") != 72
        or safe.get("decision_counts") != fresh.get("decision_counts")
        or safe.get("blind_input_sha256") != fresh.get("blind_input_sha256")
        or safe.get("instructions_sha256") != fresh.get("instructions_sha256")
        or safe.get("owner_map_sha256") != fresh.get("owner_map_sha256")
        or safe.get("result_sha256") != fresh.get("result_sha256")
        or safe.get("execution_record_sha256") != fresh.get("execution_record_sha256")
        or safe.get("execution_attestations_complete") is not True
        or safe.get("owner_verification_complete") is not True
        or safe.get("cryptographic_independence_proven") is not False
        or safe.get("reviewer_b2_independence_verified") is not False
        or safe.get("quality_v1_admitted") != 0
        or safe.get("training_authorized") is not False
        or safe.get("gpu_started") is not False
        or safe.get("r50_accessed") is not False
        or safe.get("private_values_emitted") is not False
    ):
        raise CrosswalkHold("B2_AUDIT_SAFE_INVALID_OR_STALE")


def audit(
    staged_raw: bytes,
    staging_safe_raw: bytes,
    owner_raw: bytes,
    a_raw: bytes,
    blind_raw: bytes,
    instructions_raw: bytes,
    map_raw: bytes,
    result_raw: bytes,
    execution_receipt_raw: bytes,
    execution_record_raw: bytes,
    b2_safe_raw: bytes,
) -> dict[str, Any]:
    staging_safe = _json(staging_safe_raw, "STAGING_SAFE_JSON_INVALID")
    owner_rows = _jsonl(owner_raw, "OWNER_EVIDENCE_JSONL_INVALID")
    staged_idx, owner_idx, staged_sha, source_sha = _validate_staging(
        staged_raw, staging_safe, owner_rows
    )

    if _sha(a_raw) != canonical.A_REPORT_SHA256:
        raise CrosswalkHold("REVIEWER_A_V3_REPORT_PIN_MISMATCH")
    a_report = _json(a_raw, "REVIEWER_A_V3_JSON_INVALID")
    if (
        a_report.get("schema") != canonical.A_SCHEMA
        or a_report.get("status") != canonical.A_STATUS
        or a_report.get("source_pins") != canonical.A_SOURCE_PINS
        or not isinstance(a_report.get("records"), list)
        or len(a_report["records"]) != 192
    ):
        raise CrosswalkHold("CANONICAL_REVIEWER_A_V3_REQUIRED")
    a_idx = _unique(
        a_report["records"], "target_sha256", "A_TARGET_IDENTITY_INVALID"
    )
    if len(a_idx) != 192:
        raise CrosswalkHold("A_CASE_COUNT_INVALID")

    b2_safe = _json(b2_safe_raw, "B2_AUDIT_SAFE_JSON_INVALID")
    b2_result = b2_audit.audit(
        blind_raw,
        instructions_raw,
        map_raw,
        result_raw,
        execution_receipt_raw,
        execution_record_raw,
    )
    _validate_b2_safe(b2_safe, b2_result)

    blind_packets = _jsonl(blind_raw, "B2_BLIND_INPUT_INVALID")
    blind_rows = []
    for packet in blind_packets:
        if (
            packet.get("schema") != b2_audit.BLIND_SCHEMA
            or packet.get("reviewer") != "B2"
            or not isinstance(packet.get("cases"), list)
        ):
            raise CrosswalkHold("B2_BLIND_PACKET_SCHEMA_INVALID")
        blind_rows.extend(packet["cases"])
    blind_idx = _unique(blind_rows, "blind_case_id", "B2_BLIND_ID_INVALID")

    owner_map = _json(map_raw, "B2_OWNER_MAP_INVALID")
    mapping = owner_map.get("mapping")
    if (
        owner_map.get("schema") != b2_audit.MAP_SCHEMA
        or owner_map.get("reviewer") != "B2"
        or not isinstance(mapping, list)
    ):
        raise CrosswalkHold("B2_OWNER_MAP_SCHEMA_INVALID")
    map_idx = _unique(mapping, "blind_case_id", "B2_OWNER_MAP_ID_INVALID")

    result = _json(result_raw, "B2_RESULT_JSON_INVALID")
    result_idx = _unique(
        result.get("cases", []), "blind_case_id", "B2_RESULT_ID_INVALID"
    )
    if (
        len(blind_idx) != 72
        or len(map_idx) != 72
        or len(result_idx) != 72
        or set(blind_idx) != set(map_idx)
        or set(map_idx) != set(result_idx)
    ):
        raise CrosswalkHold("B2_CASE_ID_SET_MISMATCH")

    a_classes: Counter[str] = Counter()
    b2_decisions: Counter[str] = Counter()
    pairs: Counter[str] = Counter()
    disagreements = 0
    comparable = 0
    score_exact = Counter()
    score_abs_delta = Counter()
    score_comparable = 0
    case_level_a_b2_pass = 0
    explicit_nonpass_b2_pass = 0
    aggregate_only_b2_pass = 0

    for blind_id, b2_row in result_idx.items():
        owner_map_row = map_idx[blind_id]
        blind_row = blind_idx[blind_id]
        digest = b2_row.get("target_sha256")
        if (
            digest != blind_row.get("target_sha256")
            or digest != owner_map_row.get("target_sha256")
            or owner_map_row.get("original_case_id") != staged_idx.get(digest, {}).get("case_id")
            or digest not in staged_idx
            or digest not in owner_idx
            or digest not in a_idx
        ):
            raise CrosswalkHold("B2_TO_GOLD72_TARGET_BINDING_MISMATCH")
        if owner_idx[digest].get("case_id") != owner_map_row.get("original_case_id"):
            raise CrosswalkHold("B2_OWNER_MAP_CASE_ID_MISMATCH")

        a_row = a_idx[digest]
        a_class = canonical._a_class(a_row)
        a_classes[a_class] += 1
        b_decision = b2_row.get("decision")
        if b_decision not in {"PASS", "HOLD", "REJECT"}:
            raise CrosswalkHold("B2_DECISION_INVALID")
        b2_decisions[b_decision] += 1
        pairs[f"{a_class}__B2_{b_decision}"] += 1

        a_decision = _a_decision(a_row)
        if a_decision is not None:
            comparable += 1
            if a_decision != b_decision:
                disagreements += 1

        severe = b2_row.get("severe_flags")
        if a_class == "CASE_LEVEL_SCORED_PASS" and b_decision == "PASS" and severe == []:
            case_level_a_b2_pass += 1
        elif a_class == "AGGREGATE_COMPLEMENT_PASS_ONLY" and b_decision == "PASS" and severe == []:
            aggregate_only_b2_pass += 1
        elif a_class in {"EXPLICIT_HOLD", "EXPLICIT_REJECT"} and b_decision == "PASS":
            explicit_nonpass_b2_pass += 1

        a_scores = a_row.get("scores_1_to_5")
        b_scores = b2_row.get("scores_1_to_5")
        if canonical._scores_valid(a_scores) and b2_audit._scores_valid(b_scores):
            score_comparable += 1
            for field in sorted(SCORE_FIELDS):
                delta = abs(a_scores[field] - b_scores[field])
                score_abs_delta[field] += delta
                if delta == 0:
                    score_exact[field] += 1

    score_metrics = {
        field: {
            "exact_matches": score_exact[field],
            "mean_absolute_difference": round(
                score_abs_delta[field] / score_comparable, 4
            ) if score_comparable else None,
            "comparable_cases": score_comparable,
        }
        for field in sorted(SCORE_FIELDS)
    }
    return {
        "schema": SAFE_SCHEMA,
        "status": SAFE_STATUS,
        "candidate_count": 72,
        "staging_sha256": staged_sha,
        "source_context_sha256": source_sha,
        "reviewer_a_v3_report_sha256": _sha(a_raw),
        "reviewer_b2_blind_input_sha256": b2_result["blind_input_sha256"],
        "reviewer_b2_instructions_sha256": b2_result["instructions_sha256"],
        "reviewer_b2_owner_map_sha256": b2_result["owner_map_sha256"],
        "reviewer_b2_result_sha256": b2_result["result_sha256"],
        "reviewer_b2_execution_record_sha256": b2_result["execution_record_sha256"],
        "reviewer_a_evidence_granularity": dict(sorted(a_classes.items())),
        "reviewer_b2_decisions": dict(sorted(b2_decisions.items())),
        "a_b2_pair_counts": dict(sorted(pairs.items())),
        "a_b2_comparable_decision_cases": comparable,
        "a_b2_semantic_decision_disagreements": disagreements,
        "a_b2_semantic_decision_agreements": comparable - disagreements,
        "a_case_level_scored_pass_and_b2_pass_no_severe_flags": case_level_a_b2_pass,
        "a_aggregate_only_pass_and_b2_pass_no_severe_flags": aggregate_only_b2_pass,
        "a_explicit_nonpass_b2_pass": explicit_nonpass_b2_pass,
        "score_comparable_cases": score_comparable,
        "score_comparison_by_dimension": score_metrics,
        "reviewer_a_two_independent_blinded_reviews_met": False,
        "reviewer_b2_execution_attestation_self_reported": True,
        "reviewer_b2_independence_verified": False,
        "cryptographic_independence_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Owner-only canonical Reviewer A V3 / B2 Gold72 crosswalk"
    )
    for flag in (
        "staged-jsonl", "staging-safe", "owner-evidence-jsonl",
        "reviewer-a-v3-json", "b2-blind-jsonl", "b2-instructions",
        "b2-owner-map-json", "b2-results-json", "b2-execution-receipt",
        "b2-execution-record", "b2-audit-safe",
    ):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--safe-output", required=True, type=Path)
    args = parser.parse_args()
    try:
        inputs = {
            "staged": _read(args.staged_jsonl),
            "staging_safe": _read(args.staging_safe, 2 * 1024 * 1024),
            "owner": _read(args.owner_evidence_jsonl),
            "a": _read(args.reviewer_a_v3_json),
            "blind": _read(args.b2_blind_jsonl),
            "instructions": _read(args.b2_instructions, 128 * 1024),
            "map": _read(args.b2_owner_map_json, 8 * 1024 * 1024),
            "result": _read(args.b2_results_json, 16 * 1024 * 1024),
            "receipt": _read(args.b2_execution_receipt, 2 * 1024 * 1024),
            "record": _read(args.b2_execution_record, 32 * 1024 * 1024),
            "b2_safe": _read(args.b2_audit_safe, 2 * 1024 * 1024),
        }
        safe = audit(
            inputs["staged"], inputs["staging_safe"], inputs["owner"],
            inputs["a"], inputs["blind"], inputs["instructions"],
            inputs["map"], inputs["result"], inputs["receipt"],
            inputs["record"], inputs["b2_safe"],
        )
        path = args.safe_output
        if path.exists() or path.is_symlink() or not path.is_absolute():
            raise CrosswalkHold("SAFE_OUTPUT_INVALID_OR_EXISTS")
        parent = path.parent
        if (
            not parent.is_dir()
            or parent.is_symlink()
            or parent.stat().st_mode & 0o777 != 0o700
        ):
            raise CrosswalkHold("SAFE_OUTPUT_PARENT_INVALID")
        raw = json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
        fd = path.open("xb")
        with fd:
            fd.write(raw)
        path.chmod(0o600)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (CrosswalkHold, b2_audit.AuditHold, canonical.AuditHold,
            OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, (CrosswalkHold, b2_audit.AuditHold,
                                              canonical.AuditHold)) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "A_B2_CROSSWALK_HOLD",
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

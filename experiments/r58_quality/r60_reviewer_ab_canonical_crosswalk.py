"""Canonical V3 Reviewer A / Reviewer B crosswalk for the frozen Gold72 stage.

Reads only owner-local private files and emits aggregate SAFE statistics.
It never treats the superseded R59 A pairing artifact as canonical evidence,
never infers reviewer independence, and never admits Quality-v1 records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

A_SCHEMA = "r58_gold192_reviewer_a_results_v3_reconciled_private_v1"
A_STATUS = "V3_SOURCES_NORMALIZED__192_IDENTITIES_VERIFIED__EVIDENCE_GRANULARITY_EXPLICIT"
A_REPORT_SHA256 = "b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8"
B_SCHEMA = "r58_gold192_reviewer_b_results_v1"
B_SHA256 = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
A_SOURCE_PINS = {
    "safe_v3": "e9009984fb5c223dd179b9f9920ff0fb083e26f7241bda4b2c3b0f16de6ae2ac",
    "cases31": "734ae5ccfc5ce06ff8c5fec3a98798273c1b75b2496289173bf212203de3deaf",
    "supplement_v3": "84ea6170aa13532093ebb611b3541c73d28f6add3271ab0c7c8ad22a0ee2af02",
    "packets": "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e",
    "reviewer_b": B_SHA256,
}
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
RECEIPT_SCHEMA = "storyforge-r59-contiguous-suffix-stage-safe-v1"
RECEIPT_STATUS = "CONTIGUOUS_SUFFIX_SOURCE_STAGE_BUILT__NOT_QUALITY_ADMITTED"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCORE_FIELDS = {
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
}


class AuditHold(ValueError):
    """Fail-closed input or provenance error."""


def _read(path: Path, limit: int = 160 * 1024 * 1024) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AuditHold("INPUT_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    if len(raw) > limit:
        raise AuditHold("INPUT_SIZE_LIMIT")
    return raw


def _json(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise AuditHold("JSON_OBJECT_REQUIRED")
    return value


def _jsonl(raw: bytes) -> list[dict[str, Any]]:
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise AuditHold("JSONL_OBJECT_REQUIRED")
        rows.append(value)
    return rows


def _unique_index(rows: list[dict[str, Any]], key: str, reason: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not HEX64.fullmatch(value) or value in indexed:
            raise AuditHold(reason)
        indexed[value] = row
    return indexed


def _scores_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == SCORE_FIELDS
        and all(type(score) is int and 1 <= score <= 5 for score in value.values())
    )


def _a_decision_for_comparison(row: dict[str, Any]) -> str:
    decision = row.get("reported_final_decision")
    mapping = {"PASS_ONLY": "PASS", "HOLD": "HOLD", "REJECT": "REJECT"}
    if decision not in mapping:
        raise AuditHold("A_DECISION_LABEL_INVALID")
    return mapping[decision]


def _a_class(row: dict[str, Any]) -> str:
    granularity = row.get("evidence_granularity")
    decision = row.get("reported_final_decision")
    strict = row.get("decision_for_strict_ab_decision_comparison")
    scored = row.get("case_level_scored_review_present")
    aggregate = row.get("aggregate_complement_only")
    scores = row.get("scores_1_to_5")

    if granularity == "CASE_LEVEL_SCORED_REVIEW":
        if (decision != "PASS_ONLY" or strict != "PASS_ONLY" or scored is not True
                or aggregate is not False or not _scores_valid(scores)):
            raise AuditHold("A_CASE_LEVEL_RECORD_INVALID")
        return "CASE_LEVEL_SCORED_PASS"
    if granularity == "AGGREGATE_COMPLEMENT_ONLY":
        if (decision != "PASS_ONLY" or strict is not None or scored is not False
                or aggregate is not True or scores is not None):
            raise AuditHold("A_AGGREGATE_ONLY_RECORD_INVALID")
        return "AGGREGATE_COMPLEMENT_PASS_ONLY"
    if granularity == "CASE_ID_IN_EXPLICIT_HOLD_GROUP":
        if decision != "HOLD" or strict != "HOLD" or scored is not False or scores is not None:
            raise AuditHold("A_EXPLICIT_HOLD_RECORD_INVALID")
        return "EXPLICIT_HOLD"
    if granularity == "CASE_ID_IN_EXPLICIT_REJECT_GROUP":
        if decision != "REJECT" or strict != "REJECT" or scored is not False or scores is not None:
            raise AuditHold("A_EXPLICIT_REJECT_RECORD_INVALID")
        return "EXPLICIT_REJECT"
    raise AuditHold("A_EVIDENCE_GRANULARITY_UNKNOWN")


def audit(staged_raw: bytes, receipt: dict[str, Any], owner_rows: list[dict[str, Any]],
          a_report: dict[str, Any], a_raw: bytes, b_report: dict[str, Any],
          b_raw: bytes) -> dict[str, Any]:
    staged_sha = hashlib.sha256(staged_raw).hexdigest()
    source_sha = receipt.get("source_context_file_sha256")
    if (receipt.get("schema") != RECEIPT_SCHEMA
            or receipt.get("status") != RECEIPT_STATUS
            or receipt.get("staged_file_sha256") != staged_sha
            or receipt.get("source_rows") != 72
            or receipt.get("context_staged") != 72
            or receipt.get("context_structure_hold") != 0
            or receipt.get("source_histories_mutated") is not False
            or receipt.get("original_staging_mutated") is not False
            or receipt.get("quality_v1_admitted") != 0
            or receipt.get("training_authorized") is not False
            or not isinstance(source_sha, str) or not HEX64.fullmatch(source_sha)):
        raise AuditHold("STAGING_RECEIPT_INVALID")
    if hashlib.sha256(a_raw).hexdigest() != A_REPORT_SHA256:
        raise AuditHold("REVIEWER_A_V3_REPORT_PIN_MISMATCH")
    if hashlib.sha256(b_raw).hexdigest() != B_SHA256:
        raise AuditHold("REVIEWER_B_SOURCE_PIN_MISMATCH")
    if (a_report.get("schema") != A_SCHEMA or a_report.get("status") != A_STATUS
            or a_report.get("source_pins") != A_SOURCE_PINS
            or len(a_report.get("records", [])) != 192):
        raise AuditHold("CANONICAL_REVIEWER_A_V3_REQUIRED")
    if (b_report.get("schema") != B_SCHEMA
            or len(b_report.get("cases", [])) != 192
            or b_report.get("counts") != {"PASS": 178, "HOLD": 12, "REJECT": 2}):
        raise AuditHold("CANONICAL_REVIEWER_B_REQUIRED")

    staged_rows = _jsonl(staged_raw)
    if len(staged_rows) != 72:
        raise AuditHold("STAGED_CASE_COUNT_INVALID")
    staged_idx: dict[str, dict[str, Any]] = {}
    for row in staged_rows:
        if (row.get("schema") != STAGE_SCHEMA or row.get("status") != STAGE_STATUS
                or not isinstance(row.get("case_id"), str) or not row["case_id"]):
            raise AuditHold("STAGED_ROW_INVALID")
        digest = row.get("target_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest) or digest in staged_idx:
            raise AuditHold("STAGED_TARGET_IDENTITY_INVALID")
        staged_idx[digest] = row

    owner_idx = _unique_index(owner_rows, "target_sha256", "OWNER_TARGET_IDENTITY_INVALID")
    if len(owner_idx) != 72 or set(owner_idx) != set(staged_idx):
        raise AuditHold("OWNER_STAGED_TARGET_SET_MISMATCH")
    for digest, owner in owner_idx.items():
        staged = staged_idx[digest]
        if (owner.get("case_id") != staged.get("case_id")
                or owner.get("staged_file_sha256") != staged_sha
                or owner.get("source_context_file_sha256") != source_sha):
            raise AuditHold("OWNER_STAGING_IDENTITY_OR_PIN_MISMATCH")

    a_rows = a_report["records"]
    b_rows = b_report["cases"]
    a_idx = _unique_index(a_rows, "target_sha256", "A_TARGET_IDENTITY_INVALID")
    b_idx = _unique_index(b_rows, "target_sha256", "B_TARGET_IDENTITY_INVALID")
    if len(a_idx) != 192 or len(b_idx) != 192 or set(a_idx) != set(b_idx):
        raise AuditHold("A_B_CANONICAL_TARGET_SET_MISMATCH")

    a_counts: Counter[str] = Counter()
    b_counts: Counter[str] = Counter()
    pair_counts: Counter[str] = Counter()
    b_blind_ids: list[str] = []
    b_score_count = 0
    b_empty_severe_count = 0
    a_b_disagreement_count = 0
    a_b_raw_token_inequality_count = 0
    a_case_level_b_pass = 0
    a_aggregate_b_pass = 0
    a_nonpass_b_pass = 0

    for digest, staged in staged_idx.items():
        owner = owner_idx[digest]
        a = a_idx[digest]
        b = b_idx[digest]
        if a.get("case_id") != staged.get("case_id") or owner.get("case_id") != staged.get("case_id"):
            raise AuditHold("CASE_ID_TARGET_SHA_MISMATCH")
        a_class = _a_class(a)
        a_counts[a_class] += 1

        b_decision = b.get("decision")
        if b_decision not in {"PASS", "HOLD", "REJECT"}:
            raise AuditHold("B_DECISION_INVALID")
        b_counts[b_decision] += 1
        blind_id = b.get("blind_case_id")
        if isinstance(blind_id, str) and blind_id:
            b_blind_ids.append(blind_id)
        if _scores_valid(b.get("scores_1_to_5")):
            b_score_count += 1
        severe = b.get("severe_flags")
        if severe == []:
            b_empty_severe_count += 1

        a_decision = a.get("reported_final_decision")
        if a.get("decision_for_strict_ab_decision_comparison") is not None:
            if a_decision != b_decision:
                a_b_raw_token_inequality_count += 1
            if _a_decision_for_comparison(a) != b_decision:
                a_b_disagreement_count += 1
        if a_class == "CASE_LEVEL_SCORED_PASS" and b_decision == "PASS" and severe == []:
            a_case_level_b_pass += 1
        elif a_class == "AGGREGATE_COMPLEMENT_PASS_ONLY" and b_decision == "PASS" and severe == []:
            a_aggregate_b_pass += 1
        elif a_class in {"EXPLICIT_HOLD", "EXPLICIT_REJECT"} and b_decision == "PASS":
            a_nonpass_b_pass += 1

        pair_counts[f"{a_class}__B_{b_decision}"] += 1

    if len(b_blind_ids) != 72 or len(set(b_blind_ids)) != 72:
        raise AuditHold("B_BLIND_CASE_ID_MISSING_OR_DUPLICATE")

    owner_attestation = Counter(
        "TRUE" if (isinstance(row.get("evidence"), dict)
                   and row["evidence"].get("reviewers_blinded_and_independent_attested") is True)
        else "FALSE" if (isinstance(row.get("evidence"), dict)
                         and row["evidence"].get("reviewers_blinded_and_independent_attested") is False)
        else "MISSING"
        for row in owner_rows
    )
    return {
        "schema": "r60_reviewer_ab_canonical_crosswalk_safe_v1",
        "status": "CANONICAL_CROSSWALK_COMPLETE__ADMISSION_HOLD",
        "candidate_count": 72,
        "staging_sha256": staged_sha,
        "source_context_sha256": source_sha,
        "reviewer_a_source_contract": "VERIFIED_V3_NORMALIZED_REPORT",
        "reviewer_b_source_sha256": B_SHA256,
        "reviewer_a_evidence_granularity": dict(sorted(a_counts.items())),
        "reviewer_b_decisions": dict(sorted(b_counts.items())),
        "reviewer_b_blind_case_ids_present_unique": len(b_blind_ids) == 72,
        "reviewer_b_scores_complete": b_score_count,
        "reviewer_b_empty_severe_flags": b_empty_severe_count,
        "a_b_decision_disagreements_on_comparable_rows": a_b_disagreement_count,
        "a_b_raw_decision_token_inequalities": a_b_raw_token_inequality_count,
        "a_b_decision_label_normalization": {"PASS_ONLY": "PASS"},
        "reviewer_a_two_independent_blinded_reviews_met": False,
        "reviewer_b_independent_semantic_recheck_completed": False,
        "reviewer_b_case_to_gold192_scope_binding_verified": False,
        "reviewer_b_independence_verified": False,
        "a_case_level_scored_pass_and_b_pass_no_severe_flags": a_case_level_b_pass,
        "a_aggregate_only_pass_and_b_pass_no_severe_flags": a_aggregate_b_pass,
        "a_explicit_nonpass_b_pass": a_nonpass_b_pass,
        "pair_counts": dict(sorted(pair_counts.items())),
        "owner_independent_blind_attestation": dict(sorted(owner_attestation.items())),
        "reviewer_independence_proven": False,
        "reviewer_independence_reason": "EXISTING_CANONICAL_SAFE_RECORDS_DO_NOT_PROVE_INDEPENDENCE",
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Gold72 against canonical V3 A and canonical B")
    for flag in ("staged-jsonl", "staging-safe", "owner-evidence-jsonl",
                 "reviewer-a-v3-json", "reviewer-b-json"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args()
    try:
        staged_raw = _read(args.staged_jsonl)
        receipt = _json(_read(args.staging_safe, 2 * 1024 * 1024))
        owner_rows = _jsonl(_read(args.owner_evidence_jsonl))
        a_raw = _read(args.reviewer_a_v3_json)
        a_report = _json(a_raw)
        b_raw = _read(args.reviewer_b_json)
        b_report = _json(b_raw)
        result = audit(staged_raw, receipt, owner_rows, a_report, a_raw, b_report, b_raw)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (AuditHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, AuditHold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "r60_reviewer_ab_canonical_crosswalk_safe_v1",
            "status": "CANONICAL_CROSSWALK_HOLD",
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

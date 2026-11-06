"""Import batch-level review reconciliation receipts into the shared private ledger.

This is a generic append-only evidence adapter. It accepts only allowlisted,
aggregate SAFE schemas; it never imports case rows or turns agreement into admission.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .manifest import ManifestError, append_events, load_events, make_event

SAFE_SCHEMA = "r60_gold72_reviewer_a_b2_crosswalk_safe_v1"
SAFE_STATUS = "A_B2_CROSSWALK_COMPLETE__ADMISSION_HOLD"
RECONCILIATION_KIND = "reviewer-a-b2-gold72"
RECONCILIATION_TYPE = "REVIEWER_A_B2_CROSSWALK"
EVENT_TYPE = "REVIEW_RECONCILIATION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCORE_FIELDS = {
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
}
A_CLASSES = {
    "CASE_LEVEL_SCORED_PASS", "AGGREGATE_COMPLEMENT_PASS_ONLY",
    "EXPLICIT_HOLD", "EXPLICIT_REJECT",
}
SOURCE_PIN_FIELDS = (
    "staging_sha256", "source_context_sha256", "reviewer_a_v3_report_sha256",
    "reviewer_b2_blind_input_sha256", "reviewer_b2_instructions_sha256",
    "reviewer_b2_owner_map_sha256", "reviewer_b2_result_sha256",
    "reviewer_b2_execution_record_sha256",
)
COUNT_FIELDS = (
    "a_b2_comparable_decision_cases", "a_b2_semantic_decision_disagreements",
    "a_b2_semantic_decision_agreements",
    "a_case_level_scored_pass_and_b2_pass_no_severe_flags",
    "a_aggregate_only_pass_and_b2_pass_no_severe_flags",
    "a_explicit_nonpass_b2_pass", "score_comparable_cases",
)
SAFE_FIELDS = {
    "schema", "status", "candidate_count", *SOURCE_PIN_FIELDS,
    "reviewer_a_evidence_granularity", "reviewer_b2_decisions", "a_b2_pair_counts",
    *COUNT_FIELDS, "score_comparison_by_dimension",
    "reviewer_a_two_independent_blinded_reviews_met",
    "reviewer_b2_execution_attestation_self_reported",
    "reviewer_b2_independence_verified", "cryptographic_independence_proven",
    "quality_v1_admitted", "training_authorized", "gpu_started", "r50_accessed",
    "private_values_emitted",
}


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("RECONCILIATION_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _count_map(value: Any, allowed: set[str], reason: str) -> dict[str, int]:
    if not isinstance(value, dict) or not value or not set(value).issubset(allowed):
        raise ManifestError(reason)
    if any(type(count) is not int or not 0 < count <= 72 for count in value.values()):
        raise ManifestError(reason)
    return dict(value)


def _validate_safe(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != SAFE_FIELDS:
        raise ManifestError("RECONCILIATION_SAFE_FIELDS_INVALID")
    if data.get("schema") != SAFE_SCHEMA or data.get("status") != SAFE_STATUS:
        raise ManifestError("RECONCILIATION_SAFE_SCHEMA_OR_STATUS_INVALID")
    if type(data.get("candidate_count")) is not int or data["candidate_count"] != 72:
        raise ManifestError("RECONCILIATION_CANDIDATE_COUNT_INVALID")

    for field in SOURCE_PIN_FIELDS:
        if not isinstance(data.get(field), str) or not HEX64.fullmatch(data[field]):
            raise ManifestError("RECONCILIATION_SOURCE_PIN_INVALID")

    a_classes = _count_map(
        data.get("reviewer_a_evidence_granularity"), A_CLASSES,
        "RECONCILIATION_A_GRANULARITY_INVALID",
    )
    b2_decisions = _count_map(
        data.get("reviewer_b2_decisions"), {"PASS", "HOLD", "REJECT"},
        "RECONCILIATION_B2_DECISIONS_INVALID",
    )
    pair_allowed = {
        f"{a_class}__B2_{decision}"
        for a_class in A_CLASSES for decision in ("PASS", "HOLD", "REJECT")
    }
    pair_counts = _count_map(
        data.get("a_b2_pair_counts"), pair_allowed,
        "RECONCILIATION_PAIR_COUNTS_INVALID",
    )
    if sum(a_classes.values()) != 72 or sum(b2_decisions.values()) != 72:
        raise ManifestError("RECONCILIATION_ROW_TOTAL_INVALID")
    if sum(pair_counts.values()) != 72:
        raise ManifestError("RECONCILIATION_PAIR_TOTAL_INVALID")

    for field in COUNT_FIELDS:
        value = data.get(field)
        if type(value) is not int or not 0 <= value <= 72:
            raise ManifestError("RECONCILIATION_COUNT_INVALID")
    comparable = data["a_b2_comparable_decision_cases"]
    disagreements = data["a_b2_semantic_decision_disagreements"]
    agreements = data["a_b2_semantic_decision_agreements"]
    if disagreements + agreements != comparable or comparable > 72:
        raise ManifestError("RECONCILIATION_AGREEMENT_TOTAL_INVALID")
    strict_pair_total = sum(
        count for key, count in pair_counts.items()
        if not key.startswith("AGGREGATE_COMPLEMENT_PASS_ONLY__")
    )
    if strict_pair_total != comparable:
        raise ManifestError("RECONCILIATION_COMPARABLE_PAIR_TOTAL_INVALID")
    if data["score_comparable_cases"] > 72:
        raise ManifestError("RECONCILIATION_SCORE_TOTAL_INVALID")

    score_metrics = data.get("score_comparison_by_dimension")
    if not isinstance(score_metrics, dict) or set(score_metrics) != SCORE_FIELDS:
        raise ManifestError("RECONCILIATION_SCORE_DIMENSIONS_INVALID")
    for field, metric in score_metrics.items():
        if not isinstance(metric, dict) or set(metric) != {
            "exact_matches", "mean_absolute_difference", "comparable_cases"
        }:
            raise ManifestError("RECONCILIATION_SCORE_METRIC_INVALID")
        exact = metric["exact_matches"]
        cases = metric["comparable_cases"]
        mean = metric["mean_absolute_difference"]
        if (type(exact) is not int or type(cases) is not int
                or cases != data["score_comparable_cases"]
                or not 0 <= exact <= cases):
            raise ManifestError("RECONCILIATION_SCORE_METRIC_INVALID")
        if cases == 0:
            if mean is not None:
                raise ManifestError("RECONCILIATION_SCORE_MEAN_INVALID")
        elif (isinstance(mean, bool) or not isinstance(mean, (int, float))
              or not 0 <= mean <= 4):
            raise ManifestError("RECONCILIATION_SCORE_MEAN_INVALID")

    required_flags = {
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
    if any(data.get(key) is not expected for key, expected in required_flags.items()):
        raise ManifestError("RECONCILIATION_NON_ADMISSION_FLAGS_INVALID")
    return data


def _safe_result(status: str, data: dict[str, Any], *, appended: int) -> dict[str, Any]:
    return {
        "schema": "storyforge_gold_quality_review_reconciliation_import_safe_v1",
        "status": status,
        "reconciliation_type": RECONCILIATION_TYPE,
        "candidate_count": data["candidate_count"],
        "reviewer_a_evidence_granularity": data["reviewer_a_evidence_granularity"],
        "reviewer_b2_decisions": data["reviewer_b2_decisions"],
        "a_b2_pair_counts": data["a_b2_pair_counts"],
        "comparable_decision_cases": data["a_b2_comparable_decision_cases"],
        "decision_agreements": data["a_b2_semantic_decision_agreements"],
        "decision_disagreements": data["a_b2_semantic_decision_disagreements"],
        "score_comparable_cases": data["score_comparable_cases"],
        "events_appended": appended,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def import_review_reconciliation(args) -> dict[str, Any]:
    """Import one allowlisted Gold72 A/B2 SAFE receipt as a batch-level event."""
    if args.batch != "gold72" or args.kind != RECONCILIATION_KIND:
        raise ManifestError("RECONCILIATION_KIND_NOT_ALLOWLISTED")

    path: Path = args.input
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ManifestError("RECONCILIATION_INPUT_NOT_REGULAR_FILE")
    repo = args.repo_root.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise ManifestError("RECONCILIATION_INPUT_MUST_BE_PRIVATE")
    parent_mode = path.parent.stat().st_mode & 0o777
    if parent_mode != 0o700:
        raise ManifestError("RECONCILIATION_INPUT_PARENT_PERMISSIONS_INVALID")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise ManifestError("RECONCILIATION_INPUT_NOT_REGULAR_FILE") from None
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o777 != 0o600
                or info.st_nlink != 1):
            raise ManifestError("RECONCILIATION_INPUT_PERMISSIONS_INVALID")
        raw = b""
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            raw += chunk
    finally:
        os.close(fd)
    if not 0 < len(raw) <= 2 * 1024 * 1024:
        raise ManifestError("RECONCILIATION_INPUT_SIZE_INVALID")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise ManifestError("RECONCILIATION_SAFE_JSON_INVALID") from None
    data = _validate_safe(data)
    receipt_sha = _sha(raw)

    existing = load_events(args.manifest) if args.manifest.exists() else []
    prior = [
        event for event in existing
        if event["batch_id"] == args.batch
        and event["event_type"] == EVENT_TYPE
        and event["payload"].get("reconciliation_type") == RECONCILIATION_TYPE
    ]
    if len(prior) > 1:
        raise ManifestError("RECONCILIATION_DUPLICATE_CANONICAL_EVENTS")
    if prior:
        if prior[0]["payload"].get("source_receipt_sha256") == receipt_sha:
            return _safe_result("CANONICAL_RECONCILIATION_ALREADY_IMPORTED", data, appended=0)
        raise ManifestError("RECONCILIATION_SOURCE_ALREADY_PINNED")

    source_pins = {field: data[field] for field in SOURCE_PIN_FIELDS}
    payload = {
        "reconciliation_type": RECONCILIATION_TYPE,
        "source_receipt_sha256": receipt_sha,
        "source_pins": source_pins,
        "candidate_count": 72,
        "reviewer_a_evidence_granularity": data["reviewer_a_evidence_granularity"],
        "reviewer_b2_decisions": data["reviewer_b2_decisions"],
        "a_b2_pair_counts": data["a_b2_pair_counts"],
        "comparable_decision_cases": data["a_b2_comparable_decision_cases"],
        "decision_agreements": data["a_b2_semantic_decision_agreements"],
        "decision_disagreements": data["a_b2_semantic_decision_disagreements"],
        "case_level_scored_pass_and_b2_pass_no_severe_flags":
            data["a_case_level_scored_pass_and_b2_pass_no_severe_flags"],
        "aggregate_only_pass_and_b2_pass_no_severe_flags":
            data["a_aggregate_only_pass_and_b2_pass_no_severe_flags"],
        "explicit_nonpass_b2_pass": data["a_explicit_nonpass_b2_pass"],
        "score_comparable_cases": data["score_comparable_cases"],
        "score_comparison_by_dimension": data["score_comparison_by_dimension"],
        "reviewer_a_two_independent_blinded_reviews_met": False,
        "reviewer_b2_execution_attestation_self_reported": True,
        "reviewer_b2_independence_verified": False,
        "cryptographic_independence_proven": False,
        "evidence_tier": "OWNER_RETURNED_SAFE_AGGREGATE",
        "quality_v1_admitted": False,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }
    event = make_event(args.batch, EVENT_TYPE, payload, _now())
    appended = append_events(args.manifest, [event], args.repo_root)
    return _safe_result("CANONICAL_RECONCILIATION_APPENDED", data, appended=appended)


def reconciliation_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Count-only summary; source pins and receipt digests never leave the ledger."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event["event_type"] == EVENT_TYPE:
            grouped.setdefault(event["batch_id"], []).append(event["payload"])
    summary = {}
    for batch, payloads in sorted(grouped.items()):
        summary[batch] = {
            "receipt_count": len(payloads),
            "candidate_count": sum(item["candidate_count"] for item in payloads),
            "comparable_decision_cases": sum(item["comparable_decision_cases"] for item in payloads),
            "decision_agreements": sum(item["decision_agreements"] for item in payloads),
            "decision_disagreements": sum(item["decision_disagreements"] for item in payloads),
            "score_comparable_cases": sum(item["score_comparable_cases"] for item in payloads),
            "reviewer_independence_verified": all(
                item["reviewer_b2_independence_verified"] for item in payloads
            ),
            "quality_v1_admitted": 0,
            "training_authorized": False,
        }
    return summary

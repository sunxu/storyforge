"""Canonical, frozen Reviewer A V3 source contract for Gold192.

This module is the single source of truth for the V3 report pin and evidence
granularity semantics. Aggregate-complement PASS rows are never case-level
review evidence and are never eligible for strict A/B candidate selection.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

A_SHA = "b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8"
A_REPORT_SHA256 = A_SHA
A_SCHEMA = "r58_gold192_reviewer_a_results_v3_reconciled_private_v1"
A_STATUS = "V3_SOURCES_NORMALIZED__192_IDENTITIES_VERIFIED__EVIDENCE_GRANULARITY_EXPLICIT"

B_SHA = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
B_SCHEMA = "r58_gold192_reviewer_b_results_v1"
B_COUNTS = {"PASS": 178, "HOLD": 12, "REJECT": 2}
EX_SHA = "9ca99432e08b680cb67b1f89d172a337cb91c9bd02af70b68356938c6c04ed"
PACKETS_SHA = "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e"

A_SOURCE_PINS = {
    "safe_v3": "e9009984fb5c223dd179b9f9920ff0fb083e26f7241bda4b2c3b0f16de6ae2ac",
    "cases31": "734ae5ccfc5ce06ff8c5fec3a98798273c1b75b2496289173bf212203de3deaf",
    "supplement_v3": "84ea6170aa13532093ebb611b3541c73d28f6add3271ab0c7c8ad22a0ee2af02",
    "packets": PACKETS_SHA,
    "reviewer_b": B_SHA,
}

SCORE_FIELDS = frozenset({
    "chinese_prose",
    "character_consistency",
    "npc_initiative",
    "player_agency",
    "narrative_continuity",
    "rule_fidelity",
})
EXPECTED_GRANULARITY_COUNTS = {
    "CASE_LEVEL_SCORED_REVIEW": 31,
    "CASE_ID_IN_EXPLICIT_HOLD_GROUP": 51,
    "CASE_ID_IN_EXPLICIT_REJECT_GROUP": 1,
    "AGGREGATE_COMPLEMENT_ONLY": 109,
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CanonicalReviewerAHold(ValueError):
    """Fail-closed canonical Reviewer A V3 contract error."""


def scores_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == SCORE_FIELDS
        and all(type(score) is int and 1 <= score <= 5 for score in value.values())
    )


def validate_reviewer_a_v3(report: Any) -> dict[str, dict[str, Any]]:
    """Validate the frozen V3 report and return its unique target-SHA index."""
    if not isinstance(report, dict):
        raise CanonicalReviewerAHold("CANONICAL_A_REPORT_OBJECT_INVALID")
    if report.get("schema") != A_SCHEMA or report.get("status") != A_STATUS:
        raise CanonicalReviewerAHold("CANONICAL_A_V3_REQUIRED")
    if report.get("source_pins") != A_SOURCE_PINS:
        raise CanonicalReviewerAHold("CANONICAL_A_SOURCE_PINS_INVALID")

    records = report.get("records")
    if not isinstance(records, list) or len(records) != 192:
        raise CanonicalReviewerAHold("CANONICAL_A_RECORD_COUNT_INVALID")

    indexed: dict[str, dict[str, Any]] = {}
    case_ids: set[str] = set()
    granularity_counts: Counter[str] = Counter()

    for row in records:
        if not isinstance(row, dict):
            raise CanonicalReviewerAHold("CANONICAL_A_RECORD_INVALID")
        case_id = row.get("case_id")
        target = row.get("target_sha256")
        if (not isinstance(case_id, str) or not case_id
                or case_id in case_ids
                or not isinstance(target, str) or not HEX64.fullmatch(target)
                or target in indexed):
            raise CanonicalReviewerAHold("CANONICAL_A_IDENTITY_INVALID")
        case_ids.add(case_id)
        indexed[target] = row

        granularity = row.get("evidence_granularity")
        decision = row.get("reported_final_decision")
        strict_decision = row.get("decision_for_strict_ab_decision_comparison")
        scored = row.get("case_level_scored_review_present")
        aggregate = row.get("aggregate_complement_only")
        scores = row.get("scores_1_to_5")

        if granularity == "CASE_LEVEL_SCORED_REVIEW":
            valid = (
                decision == "PASS_ONLY"
                and strict_decision == "PASS_ONLY"
                and scored is True
                and aggregate is False
                and scores_valid(scores)
            )
        elif granularity == "AGGREGATE_COMPLEMENT_ONLY":
            valid = (
                decision == "PASS_ONLY"
                and strict_decision is None
                and scored is False
                and aggregate is True
                and scores is None
            )
        elif granularity == "CASE_ID_IN_EXPLICIT_HOLD_GROUP":
            valid = (
                decision == "HOLD"
                and strict_decision == "HOLD"
                and scored is False
                and scores is None
            )
        elif granularity == "CASE_ID_IN_EXPLICIT_REJECT_GROUP":
            valid = (
                decision == "REJECT"
                and strict_decision == "REJECT"
                and scored is False
                and scores is None
            )
        else:
            raise CanonicalReviewerAHold("CANONICAL_A_GRANULARITY_UNKNOWN")

        if not valid:
            raise CanonicalReviewerAHold("CANONICAL_A_GRANULARITY_RECORD_INVALID")
        granularity_counts[granularity] += 1

    if dict(granularity_counts) != EXPECTED_GRANULARITY_COUNTS:
        raise CanonicalReviewerAHold("CANONICAL_A_GRANULARITY_COUNTS_INVALID")
    return indexed

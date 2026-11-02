"""Private Gold192 review reconciliation with count-only SAFE output.

Never converts an AI review PASS into quality admission. Reviewer disagreement
and any REJECT remain visible in the private event history, not overwritten.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .manifest import ManifestError, validate_manifest

DECISIONS = {"PASS", "PASS_ONLY", "HOLD", "REJECT"}
ROLES = {"REVIEWER_A", "REVIEWER_B", "AI_REVIEWER", "OWNER_ARBITER"}
REVIEW_EVENTS = {"INCREMENTAL_REVIEW", "BLIND_REVIEW", "ADJUDICATION"}
SCORE_FIELDS = {
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
}
EXPECTED = 192
CANONICAL_REVIEWER_B_SHA256 = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"


def reconcile_gold192(events: list[dict], *, expected: int = EXPECTED) -> dict:
    """Return count-only audit; no raw IDs, hashes, quotes or scores."""
    validate_manifest(events)
    if type(expected) is not int or not 1 <= expected <= 195:
        raise ManifestError("GOLD192_EXPECTED_COUNT_INVALID")
    cases: dict[str, dict] = defaultdict(lambda: {"reviews": {}, "historical_a_reject": False, "excluded": False})
    seen_exclusions = set()
    counts = Counter()
    for event in events:
        if event["batch_id"] != "gold192":
            continue
        kind, payload = event["event_type"], event["payload"]
        if kind not in REVIEW_EVENTS | {"EXCLUSION", "HISTORICAL_REJECT_EVIDENCE"}:
            continue
        case = payload.get("case_id")
        digest = payload.get("target_sha256")
        if not isinstance(case, str) or not case:
            raise ManifestError("GOLD192_CASE_IDENTITY_INVALID")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ManifestError("GOLD192_CASE_IDENTITY_INVALID")
        if kind == "EXCLUSION":
            state = cases[digest]
            if case in seen_exclusions:
                raise ManifestError("GOLD192_DUPLICATE_EXCLUSION")
            seen_exclusions.add(case)
            if payload.get("reason_code") != "WORLD_IDENTITY_UNRESOLVED":
                raise ManifestError("GOLD192_EXCLUSION_INVALID")
            state["excluded"] = True
            continue
        if kind == "HISTORICAL_REJECT_EVIDENCE":
            if (payload.get("reviewer_role") != "REVIEWER_A" or
                    payload.get("reviewer_source") != "r58_reviewer_a_recovered_v6_20261102" or
                    payload.get("decision") != "REJECT" or
                    payload.get("score_state") != "UNAVAILABLE_NOT_SYNTHESIZED" or
                    "scores" in payload or cases[digest]["historical_a_reject"]):
                raise ManifestError("GOLD192_HISTORICAL_REJECT_EVIDENCE_INVALID")
            cases[digest]["historical_a_reject"] = True
            continue
        role = payload.get("reviewer_role")
        if role == "REVIEWER_B" and payload.get("reviewer_source_sha256") != CANONICAL_REVIEWER_B_SHA256:
            counts["superseded_or_unpinned_reviewer_b_events_ignored"] += 1
            continue
        state = cases[digest]
        decision = payload.get("decision")
        scores = payload.get("scores")
        if role not in ROLES or decision not in DECISIONS:
            raise ManifestError("GOLD192_REVIEW_INVALID")
        if (not isinstance(scores, dict) or set(scores) != SCORE_FIELDS
                or any(type(v) is not int or not 1 <= v <= 5 for v in scores.values())):
            raise ManifestError("GOLD192_SCORES_INVALID")
        if kind == "ADJUDICATION" and role != "OWNER_ARBITER":
            raise ManifestError("GOLD192_ARBITER_ROLE_INVALID")
        if kind != "ADJUDICATION" and role == "OWNER_ARBITER":
            raise ManifestError("GOLD192_ARBITER_ROLE_INVALID")
        # Retain all review attempts in the Manifest; a repeated role remains
        # ambiguous until explicitly bound to a review round.
        state["reviews"].setdefault(role, []).append(decision)

    # The 192 review-scope candidates and three world-identity exclusions\n    # can be recorded together under the gold192 batch (195 total).\n    # No source index was loaded here. The caller must independently bind
    # these case identifiers to frozen Gold192 scope before any promotion.
    for state in cases.values():
        if state["excluded"]:
            counts["excluded_world_identity_hold"] += 1
            if state["reviews"]:
                counts["excluded_with_review_events"] += 1
            continue
        roles = state["reviews"]
        a = roles.get("REVIEWER_A", [])
        b = roles.get("REVIEWER_B", [])
        if len(a) > 1 or len(b) > 1:
            counts["multiple_review_rounds_need_binding"] += 1
        if not a:
            counts["missing_reviewer_a"] += 1
        if not b:
            counts["missing_reviewer_b"] += 1
        historical_reject = state["historical_a_reject"]
        if historical_reject:
            counts["historical_a_reject_without_scores"] += 1
            if b:
                counts["historical_a_reject_b_review_present"] += 1
                if len(b) == 1 and b[0] in {"PASS", "PASS_ONLY"}:
                    counts["historical_a_reject_b_pass_disagreement"] += 1
            if a:
                counts["historical_a_reject_and_scored_a_collision"] += 1
        if historical_reject or any("REJECT" in values for values in roles.values()):
            counts["any_reject_hold_for_arbitration"] += 1
        if a and b:
            counts["paired_case_count"] += 1
            if len(a) == len(b) == 1:
                if a[0] == "REJECT" and b[0] in {"PASS", "PASS_ONLY"}:
                    counts["reviewer_a_reject_b_pass_disagreement"] += 1
                elif b[0] == "REJECT" and a[0] in {"PASS", "PASS_ONLY"}:
                    counts["reviewer_b_reject_a_pass_disagreement"] += 1
                elif a[0] in {"PASS", "PASS_ONLY"} and b[0] in {"PASS", "PASS_ONLY"}:
                    counts["declared_both_pass_not_admitted"] += 1
                elif a[0] != b[0]:
                    counts["other_review_disagreement"] += 1
        if roles.get("OWNER_ARBITER"):
            counts["owner_arbitration_events_present"] += 1
    eligible = len(cases) - counts["excluded_world_identity_hold"]
    if eligible > expected or counts["excluded_world_identity_hold"] > 3:
        raise ManifestError("GOLD192_SCOPE_COUNTS_EXCEED_EXPECTED")
    return {
        "schema": "storyforge_gold192_review_reconciliation_safe_v1",
        "status": "REVIEW_EVIDENCE_SUMMARIZED__SCOPE_AND_SEMANTIC_CLEARANCE_HOLD",
        "expected_review_scope": expected,
        "case_events_observed": len(cases),
        "nonexcluded_cases_observed": eligible,
        "coverage_unknown_or_missing": max(0, expected - eligible),
        "counts": {key: counts[key] for key in sorted(counts)},
        "reviewer_independence_verified": False,
        "semantic_world_clearance_verified": False,
        "case_identity_scope_verified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }

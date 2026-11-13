"""Pure, source-agnostic screening status policy for StoryForge R60 1000 pool.

No IO, network, model calls, source material, or admission mutations.
A caller must first bind reviewer evidence to its frozen source and use
the existing six-dimensional rubric validator. This policy never changes
a reviewer response or silently repairs a contradictory decision.
"""
from __future__ import annotations

from collections import Counter

DECISIONS = frozenset({"PASS", "HOLD", "REJECT"})
STATES = (
    "SOURCE_HOLD", "TECHNICAL_HOLD", "AWAITING_DUAL_REVIEW",
    "SEMANTIC_REVIEW_REQUIRED", "SEMANTIC_HOLD",
    "CONTENT_REJECT", "QUALITY_CANDIDATE_NOT_ADMITTED",
)
SAFE_SCHEMA = "storyforge_r60_real1000_screening_policy_safe_v1"


def classify(*, source_verified: bool, reviewer_decisions: tuple[str, ...],
             technical_failures: int, semantic_decision: str | None,
             semantic_evidence_verified: bool) -> str:
    """Classify a single evidence-bound case; never authorize admission.

    reviewer_decisions includes only valid, independently stored reviews
    (never a failed model attempt). A semantic decision is an additional
    explicit evidence assessment, not inferred by voting on reviewers.
    """
    if type(source_verified) is not bool:
        raise ValueError("SOURCE_VERIFICATION_TYPE_HOLD")
    if (type(reviewer_decisions) is not tuple
            or len(reviewer_decisions) > 2
            or any(x not in DECISIONS for x in reviewer_decisions)
            or type(technical_failures) is not int
            or not 0 <= technical_failures <= 2
            or len(reviewer_decisions) + technical_failures > 2
            or semantic_decision not in (*DECISIONS, None)
            or type(semantic_evidence_verified) is not bool):
        raise ValueError("SCREENING_INPUT_HOLD")
    if semantic_decision is not None and not semantic_evidence_verified:
        raise ValueError("UNVERIFIED_SEMANTIC_DECISION_HOLD")
    if not source_verified:
        return "SOURCE_HOLD"
    # A separately evidenced, source-bound content exclusion is allowed
    # even when a reviewer request failed. This is *not* a vote or repair.
    if semantic_decision == "REJECT":
        return "CONTENT_REJECT"
    if semantic_decision == "HOLD":
        return "SEMANTIC_HOLD"
    if technical_failures:
        return "TECHNICAL_HOLD"
    if len(reviewer_decisions) != 2:
        return "AWAITING_DUAL_REVIEW"
    # Explicit semantic PASS does not cure a review REJECT, conflict, or HOLD.
    if (semantic_decision is None or
            reviewer_decisions != ("PASS", "PASS")):
        return "SEMANTIC_REVIEW_REQUIRED"
    # A candidate is never automatically admitted to Gold or training.
    return "QUALITY_CANDIDATE_NOT_ADMITTED"


def summarize(states: list[str], *, expected_total: int = 1000) -> dict:
    """Public aggregate-only SAFE, after caller has verified all source rows."""
    if (type(expected_total) is not int or expected_total != 1000
            or type(states) is not list
            or len(states) > expected_total
            or any(s not in STATES for s in states)):
        raise ValueError("SCREENING_AGGREGATE_HOLD")
    counts = Counter(states)
    return {
        "schema": SAFE_SCHEMA,
        "status": "REAL1000_SCREENING_PARTIAL__NO_ADMISSION"
        if len(states) != expected_total
        else "REAL1000_SCREENING_CLASSIFIED__NO_ADMISSION",
        "expected_total": expected_total,
        "classified": len(states),
        "unclassified": expected_total - len(states),
        "states": {s: counts[s] for s in STATES},
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "gpu_started": False,
        "model_requests": 0,
        "database_modified": False,
        "private_values_emitted": False,
    }

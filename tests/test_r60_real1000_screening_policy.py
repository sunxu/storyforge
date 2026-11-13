"""Synthetic-only tests: generic 1000-row classification, never model IO."""
from __future__ import annotations

import pytest

from storyforge_gold_quality.real1000_screening_policy import (
    classify,
    summarize,
)


def case(decisions=(), failures=0, semantic=None, verified=False, source=True):
    return classify(
        source_verified=source, reviewer_decisions=decisions,
        technical_failures=failures, semantic_decision=semantic,
        semantic_evidence_verified=verified,
    )


def test_dual_pass_is_only_candidate_not_admission():
    s = case(("PASS", "PASS"), semantic="PASS", verified=True)
    assert s == "QUALITY_CANDIDATE_NOT_ADMITTED"
    safe = summarize([s] * 1000)
    assert safe["quality_v1_admitted"] == safe["train_admitted"] == 0
    assert safe["classified"] == 1000


def test_failure_is_not_content_reject_or_review_vote():
    assert case(("PASS",), failures=1) == "TECHNICAL_HOLD"
    assert case((), failures=2) == "TECHNICAL_HOLD"
    assert case(("HOLD", "PASS")) == "SEMANTIC_REVIEW_REQUIRED"


def test_independently_supported_reject_does_not_need_rerun():
    assert case(("PASS",), failures=1, semantic="REJECT", verified=True) == (
        "CONTENT_REJECT"
    )
    assert case((), failures=2, semantic="HOLD", verified=True) == "SEMANTIC_HOLD"


def test_source_and_independence_evidence_never_inferred():
    assert case(("PASS", "PASS"), semantic="PASS",
                verified=True, source=False) == "SOURCE_HOLD"
    assert case(("PASS", "PASS")) == "SEMANTIC_REVIEW_REQUIRED"
    assert case(("PASS",), failures=0) == "AWAITING_DUAL_REVIEW"


def test_invalid_and_unverified_inputs_fail_closed():
    with pytest.raises(ValueError):
        case(("PASS", "PASS"), semantic="REJECT")
    with pytest.raises(ValueError):
        case(("PASS", "INVALID"))
    with pytest.raises(ValueError):
        case(("PASS", "PASS"), failures=1)
    with pytest.raises(ValueError):
        summarize(["UNKNOWN"])
    with pytest.raises(ValueError):
        summarize([], expected_total=25)


def test_partial_batch_is_not_global_completion():
    safe = summarize(["TECHNICAL_HOLD"] * 25)
    assert safe["status"] == "REAL1000_SCREENING_PARTIAL__NO_ADMISSION"
    assert safe["unclassified"] == 975
    assert safe["model_requests"] == 0

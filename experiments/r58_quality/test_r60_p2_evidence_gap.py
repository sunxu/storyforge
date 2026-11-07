"""Synthetic fail-closed tests for R60 P2 gap-only queue."""
from __future__ import annotations

import pytest

from experiments.r58_quality import r60_p2_evidence_gap as p2
from experiments.r58_quality.r60_p1_case_triage import Hold


def test_build_rejects_first_pass_out_of_bounds():
    with pytest.raises(Hold, match="LIMIT_INVALID"):
        p2.build({}, limit=0)


def test_stage_receipt_rejects_bad_pin():
    with pytest.raises((Hold, ValueError, TypeError, KeyError, ImportError)):
        p2.validated_stage(b'{"case_id":"test"}\n', b'{"status":"invalid"}')


def test_prohibited_auto_promotion_not_present():
    assert "A" not in p2.SCORES
    assert set(p2.FLOORS) == set(p2.SCORES)
    assert p2.STAGE_READY == "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"

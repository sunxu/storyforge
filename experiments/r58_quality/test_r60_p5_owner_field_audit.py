"""Synthetic-only P5 Owner field audit safeguards."""
from __future__ import annotations

import pytest

from experiments.r58_quality import r60_p5_owner_field_audit as p5
from experiments.r58_quality.r60_p3_stage_pair_probe import Hold


def test_p5_requires_exactly_three_unique_cases():
    with pytest.raises(Hold, match="P4_THREE_UNIQUE_CASES_REQUIRED"):
        p5.inspect([], lambda *_: b"")
    with pytest.raises(Hold, match="P4_THREE_UNIQUE_CASES_REQUIRED"):
        p5.inspect([{"case_id": "duplicate"}] * 3, lambda *_: b"")


def test_p5_does_not_promote_metadata_to_attestation():
    assert "owner_quality_approved" in p5.REQUIRED_TRUE
    assert "known_protected_overlap" in p5.REQUIRED_FALSE
    assert "sent_payload_sha256" in p5.SENT_FIELDS
    assert p5.SCHEMA == "storyforge_r60_p5_owner_field_audit_safe_v1"

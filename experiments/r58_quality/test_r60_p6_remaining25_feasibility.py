"""Synthetic safeguards for R60 P6 remaining 25 candidate feasibility."""
from __future__ import annotations

import pytest

from experiments.r58_quality import r60_p6_remaining25_feasibility as p6
from experiments.r58_quality.r60_p3_stage_pair_probe import Hold


def synthetic_inputs():
    queue = [{"case_id": f"synthetic-{i}",
              "target_sha256": f"synthetic-sha-{i}",
              "p2_priority_rank": i + 1} for i in range(28)]
    prior = [dict(queue[i]) for i in range(3)]
    inventory = {"schema": "r60_p3_local_artifact_inventory_private_v1",
                 "records": []}
    return queue, prior, inventory


def test_no_owner_files_means_unknown_not_d():
    queue, prior, inventory = synthetic_inputs()
    private, safe = p6.assess(queue, prior, inventory, lambda *_: b"")
    assert len(private) == 25
    assert safe["owner_metadata_found_cases"] == 0
    assert safe["exact_sent_payload_verified_count"] == 0
    assert all(x["input_evidence_class"] == "UNKNOWN_NOT_REVIEWED" for x in private)


def test_prior_three_must_match_target_pin():
    queue, prior, inventory = synthetic_inputs()
    prior[0]["target_sha256"] = "wrong"
    with pytest.raises(Hold, match="PRIOR_THREE_PIN_MISMATCH"):
        p6.assess(queue, prior, inventory, lambda *_: b"")


def test_exactly_28_unique_candidates_required():
    queue, prior, inventory = synthetic_inputs()
    with pytest.raises(Hold, match="P2_FROZEN_QUEUE_INVALID"):
        p6.assess(queue[:27], prior, inventory, lambda *_: b"")

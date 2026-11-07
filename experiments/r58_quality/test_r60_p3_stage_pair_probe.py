"""Synthetic-only tests for bounded R60 P3 Stage receipt matching."""
from __future__ import annotations

import pytest

from experiments.r58_quality import r60_p3_stage_pair_probe as p3


def test_inventory_rejects_untrusted_directory():
    inventory = {"schema": "r60_p3_local_artifact_inventory_private_v1",
                 "records": [{"private_path": "/tmp/unsafe.json", "categories": ["STAGE"]}]}
    with pytest.raises(p3.Hold, match="INVENTORY_SCOPE_INVALID"):
        p3.investigate(inventory, [{"case_id": str(i)} for i in range(28)], lambda *_: b"")


def test_p2_requires_exactly_28_distinct_candidates():
    inventory = {"schema": "r60_p3_local_artifact_inventory_private_v1", "records": []}
    with pytest.raises(p3.Hold, match="P2_QUEUE_INVALID"):
        p3.investigate(inventory, [{"case_id": "duplicate"}] * 28, lambda *_: b"")


def test_empty_verified_inventory_reports_unproven_strict_and_input():
    inventory = {"schema": "r60_p3_local_artifact_inventory_private_v1", "records": []}
    rows, safe = p3.investigate(
        inventory, [{"case_id": f"synthetic-{i}"} for i in range(28)], lambda *_: b""
    )
    assert rows == []
    assert safe["validated_stage_receipt_pairs"] == 0
    assert safe["old_strict_structural_ready_5_recomputed"] is False
    assert safe["actual_input_A_or_B_proven"] is False
    assert safe["quality_v1_admitted"] == 0

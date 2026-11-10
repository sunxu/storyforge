"""P4 synthetic safeguards: identity-based joins and no evidence promotion."""
from __future__ import annotations

import pytest

from experiments.r58_quality import r60_p4_owner_locator_probe as p4
from experiments.r58_quality.r60_p3_stage_pair_probe import Hold


def test_p4_bad_inventory_fails_closed():
    with pytest.raises(Hold, match="INVENTORY_SCHEMA_INVALID"):
        p4.inspect({}, [], [], lambda *_: b"")


def test_p4_requires_28_unique_cases():
    inventory = {"schema": "r60_p3_local_artifact_inventory_private_v1",
                 "records": []}
    with pytest.raises(Hold, match="P2_QUEUE_INVALID"):
        p4.inspect(inventory, [], [{"case_id": "x"}] * 28, lambda *_: b"")


def test_p4_does_not_infer_from_empty_stage_pairs():
    inventory = {"schema": "r60_p3_local_artifact_inventory_private_v1",
                 "records": []}
    queue = [{"case_id": f"fake-{i}", "target_sha256": f"hash-{i}"}
             for i in range(28)]
    with pytest.raises(Hold, match="STAGE_AB_INTERSECTION_INVALID"):
        p4.inspect(inventory, [], queue, lambda *_: b"")


def test_parse_owner_accepts_array_and_jsonl():
    assert p4.parse_owner(b'[{"case_id":"a"}]') == [{"case_id": "a"}]
    assert p4.parse_owner(b'{"case_id":"a"}\n{"case_id":"b"}\n') == [
        {"case_id": "a"}, {"case_id": "b"},
    ]
    assert p4.parse_owner(b"not json") is None

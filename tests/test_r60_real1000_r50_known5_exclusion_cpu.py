"""Synthetic checks for explicitly partial known R50 source-story exclusion."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
import r60_real1000_r50_known5_exclusion_cpu as gate


def fixture():
    cases = [{
        "source": {"story_id": f"unrelated-story-{i}"},
        "history_messages": [{"role": "user", "content": str(i)}],
        "target_text": f"target-{i}",
    } for i in range(1000)]
    packets = [{
        "sample100_position": i + 1,
        "history_messages": cases[i]["history_messages"],
        "assistant_target": cases[i]["target_text"],
    } for i in range(20)]
    manifest = {
        "schema": gate.double.PRIVATE_SCHEMA,
        "status": "DOUBLE_PASS_TRAIN_CANDIDATES__NOT_ADMITTED",
        "train_admitted": 0, "quality_v1_admitted": 0,
        "candidates": [
            {"pilot_position": pos,
             "status": "TRAIN_CANDIDATE__NOT_ADMITTED"}
            for pos in (1, 2, 3)
        ],
    }
    return cases, packets, manifest


def test_no_known5_overlap_remains_full_exclusion_hold():
    safe = gate.check(*fixture())
    assert safe["status"] == "R50_KNOWN5_PARTIAL_CHECK_PASS__FULL_EXCLUSION_HOLD"
    assert safe["known5_story_overlap_count"] == 0
    assert safe["r50_complete_exclusion_verified"] is False
    assert safe["train_admitted"] == 0


def test_known5_overlap_is_detected():
    cases, packets, manifest = fixture()
    cases[0]["source"]["story_id"] = min(gate.KNOWN_R50_STORIES)
    safe = gate.check(cases, packets, manifest)
    assert safe["status"] == "R50_KNOWN5_OVERLAP_FOUND__TRAIN_ADMISSION_HOLD"
    assert safe["known5_story_overlap_count"] == 1
    assert safe["train_admitted"] == 0


def test_changed_candidate_binding_is_rejected():
    cases, packets, manifest = fixture()
    packets[1]["assistant_target"] = "tampered"
    try:
        gate.check(cases, packets, manifest)
    except gate.Hold as exc:
        assert str(exc) == "SOURCE_BINDING_HOLD"
    else:
        raise AssertionError("must reject source tampering")


def test_duplicate_position_is_rejected():
    cases, packets, manifest = fixture()
    manifest["candidates"][2]["pilot_position"] = 2
    try:
        gate.check(cases, packets, manifest)
    except gate.Hold as exc:
        assert str(exc) == "CANDIDATE_POSITION_HOLD"
    else:
        raise AssertionError("must reject duplicate candidate")

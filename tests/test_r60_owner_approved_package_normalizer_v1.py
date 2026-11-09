from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/r60_owner_approved_package_normalizer_v1.py"
SPEC = importlib.util.spec_from_file_location("r60_owner_approved_package_normalizer_v1", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _packet():
    return {
        "calibration_id": "a" * 32,
        "visible_history": [{"role": "user", "content": "I refuse."}],
    }


def _assessment(verdict="NOT_SUPPORTED", history_complete=False):
    return {
        "verdict": verdict,
        "context_coverage": {
            "history_complete": history_complete,
            "target_complete": True,
            "relevant_context_complete": True,
        },
        "missing_context": [],
        "evidence": [
            {
                "source": "target",
                "message_index": -1,
                "component_ref": "legacy-target",
                "quote": "target quote",
            },
            {
                "source": "history",
                "message_index": 0,
                "component_ref": "legacy-history",
                "quote": "history quote",
            },
        ],
    }


def test_normalize_results_changes_only_approved_coverage_and_locator_fields():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_id = "a" * 32
    result = {
        "case_ref": case_id,
        "assessments": {dimension: _assessment() for dimension in dimensions},
    }
    original = __import__("copy").deepcopy(result)

    normalized, counts = MODULE.normalize_results(
        [result], [_packet()], {(case_id, "player_agency")}, dimensions
    )

    assert counts == {
        "history_completeness_confirmed": 1,
        "target_locators_normalized": 3,
        "history_locators_normalized": 3,
    }
    assert result == original  # source object is not mutated
    assert normalized[0]["assessments"]["player_agency"]["context_coverage"]["history_complete"] is True
    assert normalized[0]["assessments"]["hard_rule"]["context_coverage"]["history_complete"] is False
    for assessment in normalized[0]["assessments"].values():
        target, history = assessment["evidence"]
        assert (target["message_index"], target["component_ref"]) == (0, "")
        assert (history["message_index"], history["component_ref"]) == (0, "")


def test_normalize_results_rejects_approved_non_negative_verdict():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_id = "a" * 32
    result = {
        "case_ref": case_id,
        "assessments": {dimension: _assessment() for dimension in dimensions},
    }
    result["assessments"]["player_agency"]["verdict"] = "SUPPORTED"

    with pytest.raises(SystemExit):
        MODULE.normalize_results(
            [result], [_packet()], {(case_id, "player_agency")}, dimensions
        )


def test_normalize_results_rejects_unexpected_target_locator():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_id = "a" * 32
    result = {
        "case_ref": case_id,
        "assessments": {dimension: _assessment() for dimension in dimensions},
    }
    result["assessments"]["safety"]["evidence"][0]["message_index"] = 0

    with pytest.raises(SystemExit):
        MODULE.normalize_results(
            [result], [_packet()], set(), dimensions
        )

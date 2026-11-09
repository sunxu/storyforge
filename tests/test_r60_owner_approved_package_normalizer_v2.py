from __future__ import annotations

from scripts import r60_owner_approved_package_normalizer_v2 as MODULE


def _packet():
    return {
        "calibration_id": "a" * 32,
        "visible_history": [{"role": "user", "content": "I refuse."}],
    }


def _assessment(verdict, history_complete=False):
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


def test_normalize_results_accepts_exact_approved_supported_and_negative_pairs():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_id = "a" * 32
    result = {
        "case_ref": case_id,
        "assessments": {
            "player_agency": _assessment("SUPPORTED"),
            "hard_rule": _assessment("NOT_SUPPORTED"),
            "safety": _assessment("NOT_SUPPORTED"),
        },
    }
    import copy
    original = copy.deepcopy(result)

    normalized, counts = MODULE.normalize_results(
        [result],
        [_packet()],
        {
            (case_id, "player_agency"): "SUPPORTED",
            (case_id, "hard_rule"): "NOT_SUPPORTED",
            (case_id, "safety"): "NOT_SUPPORTED",
        },
        dimensions,
    )

    assert result == original
    assert counts == {
        "history_completeness_confirmed": 3,
        "target_locators_normalized": 3,
        "history_locators_normalized": 3,
    }
    assert all(
        item["context_coverage"]["history_complete"] is True
        for item in normalized[0]["assessments"].values()
    )
    assert normalized[0]["assessments"]["player_agency"]["verdict"] == "SUPPORTED"


def test_normalize_results_rejects_approved_verdict_mismatch():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_id = "a" * 32
    result = {
        "case_ref": case_id,
        "assessments": {
            dimension: _assessment("NOT_SUPPORTED") for dimension in dimensions
        },
    }
    try:
        MODULE.normalize_results(
            [result], [_packet()], {(case_id, "player_agency"): "SUPPORTED"}, dimensions
        )
    except SystemExit:
        pass
    else:
        raise AssertionError("mismatched approved verdict was accepted")


def test_normalize_results_rejects_target_locator_shape_mismatch():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_id = "a" * 32
    result = {
        "case_ref": case_id,
        "assessments": {
            dimension: _assessment("NOT_SUPPORTED") for dimension in dimensions
        },
    }
    result["assessments"]["safety"]["evidence"][0]["message_index"] = 0
    try:
        MODULE.normalize_results([result], [_packet()], {}, dimensions)
    except SystemExit:
        pass
    else:
        raise AssertionError("unexpected target locator was accepted")

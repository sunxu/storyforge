from __future__ import annotations

import copy

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


def test_owner_approved_basis_type_normalization_changes_only_four_derived_pairs():
    dimensions = ("player_agency", "hard_rule", "safety")
    case_ids = ["a" * 32, "b" * 32, "c" * 32, "d" * 32]
    results = []
    for case_id in case_ids:
        result = {
            "case_ref": case_id,
            "assessments": {
                "player_agency": _assessment("SUPPORTED"),
                "hard_rule": _assessment("NOT_SUPPORTED"),
                "safety": _assessment("NOT_SUPPORTED"),
            },
        }
        result["assessments"]["player_agency"]["rule_basis"] = [{
            "source": "interaction_contract",
            "basis_type": "player_agency",
            "rule_id": "boundary",
            "rule_version": "v1",
            "scope": "player boundary",
            "applicability": "APPLIES",
            "coverage_complete": True,
        }]
        results.append(result)

    original = copy.deepcopy(results)
    derived = copy.deepcopy(results)
    approvals = {(case_id, "player_agency"): "SUPPORTED" for case_id in case_ids}
    normalized_count = MODULE.normalize_owner_approved_basis_types(derived, approvals)

    assert normalized_count == 4
    assert results == original
    for result in derived:
        basis = result["assessments"]["player_agency"]["rule_basis"][0]
        assert basis["basis_type"] == "player_agency_boundary"
        assert basis["rule_id"] == "boundary"
        assert basis["rule_version"] == "v1"
        assert basis["scope"] == "player boundary"
        assert basis["applicability"] == "APPLIES"
        assert basis["coverage_complete"] is True
        assert result["assessments"]["player_agency"]["verdict"] == "SUPPORTED"
    MODULE.validate_supported_basis_types(derived, dimensions)


def test_basis_type_normalization_rejects_approval_scope_other_than_four():
    try:
        MODULE.normalize_owner_approved_basis_types([], {})
    except SystemExit:
        pass
    else:
        raise AssertionError("basis type normalization accepted an unapproved scope")


def test_supported_basis_type_accepts_exact_rubric_v21_label():
    dimensions = ("player_agency", "hard_rule", "safety")
    result = {
        "case_ref": "a" * 32,
        "assessments": {
            "player_agency": _assessment("SUPPORTED"),
            "hard_rule": _assessment("NOT_SUPPORTED"),
            "safety": _assessment("NOT_SUPPORTED"),
        },
    }
    result["assessments"]["player_agency"]["rule_basis"] = [{
        "basis_type": "player_agency_boundary",
    }]
    MODULE.validate_supported_basis_types([result], dimensions)

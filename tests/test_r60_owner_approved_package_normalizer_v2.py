from __future__ import annotations

import copy
import json

from scripts import r60_owner_approved_package_normalizer_v2 as MODULE
from scripts import r60_p2a_second_model_cross_review as CROSS_REVIEW
from scripts import r60_p2a_semantic_check_keyset_diagnostic as KEYSET_DIAG
from storyforge_gold_quality import hf_owner_adjudication_v2 as ADJUDICATION
from storyforge_gold_quality import hf_severity_evidence_v2 as SEVERITY


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


def test_owner_semantic_reviewer_binding_rejects_ai_generated_checks_without_owner_review():
    checks = [
        {
            "calibration_id": f"{i:032x}",
            "dimension": ("player_agency", "hard_rule", "safety")[i % 3],
            "reviewed_at_utc": "2026-11-09T05:00:00Z",
            "check": {
                "schema": "storyforge_severity_semantic_entailment_check_v2",
                "rubric_version": "r60_severity_rubric_v2_1",
                "conclusion": "SUPPORTS_VERDICT",
                "reviewed_evidence_indexes": [0],
                "reasoning_summary": "AI advisory reviewed the cited evidence against the recorded verdict.",
            },
        }
        for i in range(60)
    ]
    original = copy.deepcopy(checks)
    try:
        MODULE.normalize_owner_semantic_reviewer_binding(checks)
    except SystemExit:
        pass
    else:
        raise AssertionError("AI-generated semantic checks were promoted to Owner review")
    assert checks == original


def test_owner_semantic_reviewer_binding_accepts_only_explicit_owner_metadata():
    checks = [
        {
            "calibration_id": f"{i:032x}",
            "dimension": ("player_agency", "hard_rule", "safety")[i % 3],
            "reviewed_at_utc": "2026-11-09T05:00:00Z",
            "check": {
                "schema": "storyforge_severity_semantic_entailment_check_v2",
                "rubric_version": "r60_severity_rubric_v2_1",
                "reviewer_role": "OWNER_INDEPENDENT",
                "reviewer_ref": "owner-reviewed-r60-p2a",
                "conclusion": "SUPPORTS_VERDICT",
                "reviewed_evidence_indexes": [0],
                "reasoning_summary": "Owner independently reviewed the complete cited evidence.",
            },
        }
        for i in range(60)
    ]
    derived, count = MODULE.normalize_owner_semantic_reviewer_binding(checks)
    assert count == 0
    assert derived == checks


def test_owner_semantic_reviewer_binding_rejects_conflicting_identity():
    checks = [
        {
            "calibration_id": f"{i:032x}",
            "dimension": ("player_agency", "hard_rule", "safety")[i % 3],
            "reviewed_at_utc": "2026-11-09T05:00:00Z",
            "check": {},
        }
        for i in range(60)
    ]
    checks[7]["check"]["reviewer_ref"] = "another-reviewer-ref"
    try:
        MODULE.normalize_owner_semantic_reviewer_binding(checks)
    except SystemExit:
        pass
    else:
        raise AssertionError("conflicting reviewer identity was silently overwritten")


def test_owner_semantic_reviewer_binding_rejects_wrong_cardinality():
    try:
        MODULE.normalize_owner_semantic_reviewer_binding([])
    except SystemExit:
        pass
    else:
        raise AssertionError("semantic reviewer binding accepted wrong cardinality")



def test_semantic_hold_reason_exposes_only_allowlisted_safe_code():
    exc = SEVERITY.SemanticEntailmentHold("SEMANTIC_ENTAILMENT_CHECK_HOLD")
    assert ADJUDICATION.semantic_entailment_hold_reason(exc) == (
        "OWNER_SEMANTIC_CHECK_INVALID:SEMANTIC_ENTAILMENT_CHECK_HOLD"
    )


def test_semantic_hold_reason_preserves_non_established_verdict_hold():
    exc = SEVERITY.SemanticEntailmentHold("SEMANTIC_ENTAILMENT_NOT_ESTABLISHED")
    assert ADJUDICATION.semantic_entailment_hold_reason(exc) == (
        "SEMANTIC_ENTAILMENT_NOT_ESTABLISHED_HOLD"
    )


def test_semantic_hold_reason_never_echoes_untrusted_exception_text():
    exc = SEVERITY.SemanticEntailmentHold("private payload must not leak")
    assert ADJUDICATION.semantic_entailment_hold_reason(exc) == (
        "OWNER_SEMANTIC_CHECK_INVALID:UNCLASSIFIED"
    )


def test_official_verifier_reason_reports_allowlisted_adjudication_hold():
    exc = ADJUDICATION.AdjudicationHold(
        "OWNER_SEMANTIC_CHECK_INVALID:SEMANTIC_ENTAILMENT_CHECK_HOLD"
    )
    assert MODULE.official_verifier_reason(
        exc, ADJUDICATION.AdjudicationHold, SEVERITY.EvidenceHold
    ) == (
        "OFFICIAL_VERIFIER_OWNER_SEMANTIC_CHECK_INVALID:"
        "SEMANTIC_ENTAILMENT_CHECK_HOLD"
    )


def test_official_verifier_reason_does_not_echo_unknown_adjudication_hold():
    exc = ADJUDICATION.AdjudicationHold("private input fragment")
    assert MODULE.official_verifier_reason(
        exc, ADJUDICATION.AdjudicationHold, SEVERITY.EvidenceHold
    ) == "OFFICIAL_VERIFIER_ADJUDICATION_HOLD"


def test_official_verifier_reason_does_not_echo_evidence_exception():
    exc = SEVERITY.EvidenceHold("private evidence fragment")
    assert MODULE.official_verifier_reason(
        exc, ADJUDICATION.AdjudicationHold, SEVERITY.EvidenceHold
    ) == "OFFICIAL_VERIFIER_EVIDENCE_HOLD"


def _valid_semantic_check():
    return {
        "schema": SEVERITY.SEMANTIC_CHECK_SCHEMA,
        "rubric_version": SEVERITY.RUBRIC_VERSION,
        "reviewer_role": "OWNER_INDEPENDENT",
        "reviewer_ref": "owner-independent-r60-p2a-dev20-20261109",
        "conclusion": "SUPPORTS_VERDICT",
        "reviewed_evidence_indexes": [0],
        "reasoning_summary": "Reviewed the complete cited evidence against the recorded verdict.",
    }


def test_semantic_check_contract_diagnostic_accepts_valid_contract():
    assert SEVERITY.semantic_check_contract_reason(_valid_semantic_check()) is None


def test_semantic_check_contract_diagnostic_identifies_keyset_mismatch():
    check = _valid_semantic_check()
    check["unexpected"] = "not emitted"
    assert SEVERITY.semantic_check_contract_reason(check) == "CHECK_KEYSET_MISMATCH"


def test_semantic_check_contract_diagnostic_identifies_rubric_mismatch():
    check = _valid_semantic_check()
    check["rubric_version"] = "wrong"
    assert SEVERITY.semantic_check_contract_reason(check) == "RUBRIC_VERSION_MISMATCH"


def test_semantic_check_contract_diagnostic_identifies_index_shape_and_duplicates():
    check = _valid_semantic_check()
    check["reviewed_evidence_indexes"] = ["0"]
    assert SEVERITY.semantic_check_contract_reason(check) == "EVIDENCE_INDEX_TYPE_INVALID"
    check["reviewed_evidence_indexes"] = [0, 0]
    assert SEVERITY.semantic_check_contract_reason(check) == "EVIDENCE_INDEX_DUPLICATE"


def test_official_verifier_reason_reports_semantic_row_and_timestamp_holds():
    row_exc = ADJUDICATION.AdjudicationHold("OWNER_SEMANTIC_CHECK_ROW_SHAPE_HOLD")
    timestamp_exc = ADJUDICATION.AdjudicationHold("OWNER_SEMANTIC_CHECK_TIMESTAMP_HOLD")
    assert MODULE.official_verifier_reason(
        row_exc, ADJUDICATION.AdjudicationHold, SEVERITY.EvidenceHold
    ) == "OFFICIAL_VERIFIER_OWNER_SEMANTIC_CHECK_ROW_SHAPE_HOLD"
    assert MODULE.official_verifier_reason(
        timestamp_exc, ADJUDICATION.AdjudicationHold, SEVERITY.EvidenceHold
    ) == "OFFICIAL_VERIFIER_OWNER_SEMANTIC_CHECK_TIMESTAMP_HOLD"


def test_official_verifier_reason_reports_semantic_duplicate_hold():
    exc = ADJUDICATION.AdjudicationHold("OWNER_SEMANTIC_CHECK_DUPLICATE")
    assert MODULE.official_verifier_reason(
        exc, ADJUDICATION.AdjudicationHold, SEVERITY.EvidenceHold
    ) == "OFFICIAL_VERIFIER_OWNER_SEMANTIC_CHECK_DUPLICATE"



def test_keyset_diagnostic_reports_only_missing_and_extra_field_names():
    expected = KEYSET_DIAG.EXPECTED_CHECK_KEYS
    check = {key: "x" for key in expected}
    del check["reviewer_ref"]
    check["legacy_reviewer_id"] = "secret-value"
    raw = (json.dumps({"calibration_id": "PRIVATE-ID", "check": check}) + "\n").encode()
    report = KEYSET_DIAG.diagnose(raw)
    assert report["keyset_mismatch_count"] == 1
    assert report["row_diagnostics"] == [{
        "line": 1,
        "missing_keys": ["reviewer_ref"],
        "extra_keys": ["legacy_reviewer_id"],
        "keyset_match": False,
    }]
    assert "PRIVATE-ID" not in json.dumps(report)
    assert "secret-value" not in json.dumps(report)


def test_keyset_diagnostic_handles_invalid_json_without_echoing_input():
    raw = b'{"private":"do-not-echo"}\nnot-json\n'
    report = KEYSET_DIAG.diagnose(raw)
    assert report["status"] == "DIAGNOSTIC_INPUT_HOLD"
    assert report["input_errors"] == [{"line": 2, "reason": "INVALID_JSON"}]
    assert "do-not-echo" not in json.dumps(report)


def _cross_review_inputs():
    packets = []
    results = []
    for i in range(20):
        case_id = f"{i:032x}"
        packets.append({
            "schema": "storyforge_r60_owner_adjudication_packet_v2",
            "calibration_id": case_id,
            "visible_history": [{"role": "user", "content": "A player chooses whether to leave."}],
            "target_text": "The character responds to the player's choice.",
            "verified_world_components": [],
        })
        results.append({
            "schema": "storyforge_severity_evidence_review_v2",
            "rubric_version": "r60_severity_rubric_v2_1",
            "case_ref": case_id,
            "assessments": {
                dimension: {
                    "verdict": "NOT_SUPPORTED",
                    "evidence": [{"quote": "The player chooses whether to leave."}],
                    "rule_basis": [],
                    "context_coverage": {"history_complete": True},
                }
                for dimension in CROSS_REVIEW.DIMENSIONS
            },
        })
    return packets, results


def test_second_model_cross_review_builder_creates_fresh_blind_advisory_only_packets():
    packets, results = _cross_review_inputs()
    counter = iter(f"{i:032x}" for i in range(100, 120))
    output, id_map, safe = CROSS_REVIEW.build(
        packets, results, b"rubric",
        token_factory=lambda _n: next(counter),
    )
    assert len(output) == 20
    assert len(id_map["mapping"]) == 20
    assert all(set(row) == {
        "schema", "blind_id", "visible_history", "target_text",
        "verified_world_components", "review_targets",
    } for row in output)
    assert all(set(row["review_targets"]) == set(CROSS_REVIEW.DIMENSIONS) for row in output)
    assert all("calibration_id" not in row for row in output)
    assert safe["prior_ai_semantic_checks_read"] is False
    assert safe["prior_ai_advisory_files_read"] is False
    assert safe["reviewer_identity_attested"] is False
    assert safe["owner_review_completed"] is False


def test_second_model_cross_review_builder_rejects_packet_result_mismatch():
    packets, results = _cross_review_inputs()
    results.pop()
    try:
        CROSS_REVIEW.build(packets, results, b"rubric")
    except CROSS_REVIEW.Hold as exc:
        assert str(exc) == "P2A_INPUT_CARDINALITY_HOLD"
    else:
        raise AssertionError("mismatched packet/result set was accepted")

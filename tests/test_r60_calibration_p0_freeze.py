from __future__ import annotations

from scripts.r60_calibration_p0_freeze import (
    build_inventory_safe,
    case_fingerprints,
    compare_crosssets,
    stratify_gold72,
)


def _gold_rows():
    quotas = {
        "EXPLICIT_HOLD__B2_PASS": 15,
        "EXPLICIT_HOLD__B2_REJECT": 2,
        "CASE_LEVEL_SCORED_PASS__B2_REJECT": 1,
        "CASE_LEVEL_SCORED_PASS__B2_HOLD": 2,
    }
    totals = {
        "EXPLICIT_HOLD__B2_PASS": 30,
        "EXPLICIT_HOLD__B2_REJECT": 3,
        "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
        "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
    }
    rows = []
    n = 1
    for stratum, development_count in quotas.items():
        for index in range(totals[stratum]):
            if index < development_count:
                story = f"story-{(index % 5) + 1}"
            else:
                story = f"story-{((index - development_count) % 6) + 1}"
            rows.append({
                "target_sha256": f"{n:064x}",
                "original_story_uuid": story,
                "disagreement_type": stratum,
            })
            n += 1
    return rows


def test_gold72_stratification_is_deterministic_20_20_and_story_crossing():
    development, locked, summary = stratify_gold72(_gold_rows())
    development_again, locked_again, summary_again = stratify_gold72(_gold_rows())

    assert [row["target_sha256"] for row in development] == [
        row["target_sha256"] for row in development_again
    ]
    assert [row["target_sha256"] for row in locked] == [
        row["target_sha256"] for row in locked_again
    ]
    assert len(development) == 20
    assert len(locked) == 20
    assert summary == summary_again
    assert summary["development_story_count"] == 5
    assert summary["locked_regression_story_count"] == 6
    assert summary["shared_story_count"] == 5
    assert summary["story_disjoint"] is False


def test_gold72_stratification_fails_closed_on_changed_stratum_counts():
    rows = _gold_rows()[:-1]
    try:
        stratify_gold72(rows)
    except ValueError as exc:
        assert str(exc) == "GOLD72_CASE_COUNT_INVALID"
    else:
        raise AssertionError("expected fail-closed case-count validation")


def test_exact_crossset_dedup_detects_same_full_case():
    messages = [{"role": "user", "content": "continue"}]
    gold_fp = case_fingerprints(messages, "the target")
    pilot_fp = case_fingerprints(messages, "the target")

    result = compare_crosssets(
        [{"private_case_ref": "gold-private", **gold_fp}],
        [{"private_case_ref": "pilot-private", **pilot_fp}],
    )

    assert result["status"] == "CROSSSET_EXACT_OVERLAP_HOLD"
    assert result["exact_history_overlap_count"] == 1
    assert result["exact_target_overlap_count"] == 1
    assert result["exact_full_history_target_overlap_count"] == 1
    assert len(result["overlap_pairs"]) == 1


def test_exact_crossset_dedup_counts_each_dimension_independently():
    gold_fp = case_fingerprints(
        [{"role": "user", "content": "history-a"}], "same target"
    )
    pilot_fp = case_fingerprints(
        [{"role": "user", "content": "history-b"}], "same target"
    )

    result = compare_crosssets(
        [{"private_case_ref": "gold-private", **gold_fp}],
        [{"private_case_ref": "pilot-private", **pilot_fp}],
    )

    assert result["status"] == "CROSSSET_EXACT_OVERLAP_HOLD"
    assert result["exact_history_overlap_count"] == 0
    assert result["exact_target_overlap_count"] == 1
    assert result["exact_full_history_target_overlap_count"] == 0
    assert result["overlap_pairs"] == []


def test_inventory_safe_is_aggregate_only_and_preserves_story_overlap():
    summary = {
        "development_story_count": 5,
        "locked_regression_story_count": 6,
        "shared_story_count": 5,
    }
    pilot = {}
    dedup = {
        "exact_history_overlap_count": 0,
        "exact_target_overlap_count": 0,
        "exact_full_history_target_overlap_count": 0,
    }

    safe = build_inventory_safe(summary, pilot, dedup, written=True)

    assert safe["status"] == "CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD"
    assert safe["gold72_development_cases"] == 20
    assert safe["gold72_locked_regression_cases"] == 20
    assert safe["gold72_story_disjoint"] is False
    assert safe["gold72_shared_story_count"] == 5
    assert safe["private_values_emitted"] is False
    assert not any("sha256" in key.lower() or "blind_id" in key.lower()
                   for key in safe)


def test_failure_diagnostics_expose_location_without_exception_payload():
    from scripts.r60_calibration_p0_freeze import _safe_diagnostic

    try:
        raise KeyError("private owner evidence value")
    except KeyError as exc:
        diagnostic = _safe_diagnostic(exc)

    assert diagnostic["exception_type"] == "KeyError"
    assert isinstance(diagnostic["source_line"], int)
    assert "private owner evidence value" not in str(diagnostic)

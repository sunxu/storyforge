"""Synthetic, no-private-data tests for GLM Owner Gold calibration."""
import importlib.util
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "experiments/r58_quality/r60_glm_gold_calibration_cpu.py"
)
spec = importlib.util.spec_from_file_location("gold_cpu_probe", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def model():
    return {
        "schema": mod.MODEL_SCHEMA,
        "status": "GLM_RAW_DECISION_DIAGNOSTIC",
        "counts": {"REJECT": 25},
        "positions": {"PASS": [], "HOLD": [], "REJECT": list(range(1, 26)), "OTHER": []},
        "gpu_started": False,
        "private_values_emitted": False,
        "quality_v1_admitted": 0,
    }


def gold():
    return {
        "schema": mod.GOLD_SCHEMA,
        "rubric_version": "v2.1",
        "owner_attests_independent": True,
        "cases": [
            {
                "original_position": i,
                "gold_decision": "PASS" if i <= 3 else "HOLD" if i <= 5 else "REJECT",
                "finalized": True,
            }
            for i in range(1, 26)
        ],
    }


def test_owner_attested_counts_not_training_admission():
    result = mod.summarize(model(), gold())
    assert result["candidate_false_rejections_vs_gold_pass"] == 3
    assert result["model_reject_vs_gold_hold"] == 2
    assert result["model_reject_vs_gold_reject_agreement"] == 20
    assert result["independence_proven"] is False
    assert result["quality_v1_admitted"] == 0


def test_missing_gold_row_holds():
    labels = gold()
    labels["cases"].pop()
    try:
        mod.summarize(model(), labels)
    except mod.CalibrationHold:
        return
    raise AssertionError("expected HOLD")


def test_duplicate_position_holds():
    labels = gold()
    labels["cases"][1]["original_position"] = 1
    try:
        mod.summarize(model(), labels)
    except mod.CalibrationHold:
        return
    raise AssertionError("expected HOLD")


def test_nonindependent_labels_hold():
    labels = gold()
    labels["owner_attests_independent"] = False
    try:
        mod.summarize(model(), labels)
    except mod.CalibrationHold:
        return
    raise AssertionError("expected HOLD")


def test_tampered_model_inventory_holds():
    report = model()
    report["positions"]["REJECT"].pop()
    try:
        mod.summarize(report, gold())
    except mod.CalibrationHold:
        return
    raise AssertionError("expected HOLD")

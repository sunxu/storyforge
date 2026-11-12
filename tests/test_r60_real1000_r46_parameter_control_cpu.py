"""Static synthetic drift tests; no private inputs, model downloads or GPU."""
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("r60_param_control", ROOT / "scripts/r60_real1000_r46_parameter_control_cpu.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def sources(tmp_path):
    original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
    config = tmp_path / "policy.json"
    config.write_text(json.dumps(original), encoding="utf-8")
    baseline = tmp_path / "base.yaml"
    baseline.write_text(m.BASELINE.read_text(encoding="utf-8"), encoding="utf-8")
    return config, baseline, original


def test_repo_proposal_matches_baseline_but_never_admits():
    result = m.inspect()
    assert result["status"] == "R60_R46_PROPOSED_HYPERPARAMETER_CONTROL_PASS__SYSTEM_TEMPLATE_ADMISSION_HOLD"
    assert result["hyperparameters_checked"] == len(m.EXPECTED_FIXED)
    assert result["r46_system_prompt_equivalence_verified"] is False
    assert result["r46_runtime_template_equivalence_verified"] is False
    assert result["train_admitted"] == 0
    assert result["gpu_started"] is False


def test_parameter_change_not_silently_accepted(tmp_path):
    p,b,config = sources(tmp_path)
    config["frozen_hyperparameters"]["learning_rate"] = 0.0001
    p.write_text(json.dumps(config))
    result = m.inspect(p,b)
    assert result["reason_code"] == "HYPERPARAMETER_DRIFT_HOLD"
    assert result["train_admitted"] == 0


def test_baseline_change_is_detected(tmp_path):
    p,b,config = sources(tmp_path)
    original = b.read_text()
    b.write_text(original.replace("gradient_accumulation_steps: 8", "gradient_accumulation_steps: 4"))
    assert m.inspect(p,b)["reason_code"] == "REFERENCE_BASELINE_MISMATCH_HOLD"


def test_attempted_training_authorization_rejected(tmp_path):
    p,b,config = sources(tmp_path)
    config["train_admitted"] = 2
    config["gpu_authorized"] = True
    p.write_text(json.dumps(config))
    result = m.inspect(p,b)
    assert result["reason_code"] == "POLICY_CONTRACT_HOLD"
    assert result["train_admitted"] == 0


def test_false_template_parity_rejected(tmp_path):
    p,b,config = sources(tmp_path)
    config["r46_actual_template_equivalence"] = "VERIFIED"
    p.write_text(json.dumps(config))
    result = m.inspect(p,b)
    assert result["reason_code"] == "POLICY_CONTRACT_HOLD"
    assert result["r46_runtime_template_equivalence_verified"] is False


def test_unknown_private_runtime_error_is_never_reflected(tmp_path):
    p,b,config = sources(tmp_path)
    p.write_text("{secret-private-data")
    result = m.inspect(p,b)
    assert result["reason_code"] == "INPUT_OR_RUNTIME_HOLD"
    assert "secret-private-data" not in json.dumps(result)


def test_duplicate_yaml_key_rejected(tmp_path):
    p,b,config = sources(tmp_path)
    b.write_text(b.read_text() + "\nlearning_rate: 0.00005\n")
    assert m.inspect(p,b)["reason_code"] == "DUPLICATE_REFERENCE_KEY_HOLD"

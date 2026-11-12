"""Synthetic receipt only. Never read or print real Common2 private results."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "scripts/r60_common2_cpu2_receipt_verify.py"
spec = importlib.util.spec_from_file_location("r60_receipt_verify", SRC)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def payload():
    return {
        "schema": "storyforge_r60_common2_sft_cpu_template_audit_safe_v1",
        "status": "COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD",
        "cases": 2,
        "tokenizer_verified": True,
        "collator_verified": True,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "model_inference_calls": 0,
        "model_weights_loaded": False,
        "native_template_token_parity_verified": False,
        "gpu_started": False,
        "private_values_emitted": False,
        "database_accessed": False,
        "tokenizer_input_token_counts": [48, 63],
        "real_collator_token_counts": [45, 60],
        "supervised_token_counts": [9, 11],
    }


def stage(tmp_path, value=None):
    f = tmp_path / "R60_COMMON2_CPU2_SAFE_RECEIPT.json"
    f.write_text(json.dumps(payload() if value is None else value))
    os.chmod(f, 0o600)
    return f


def test_verifies_synthetic_2_case_receipt(tmp_path):
    r = module.inspect(stage(tmp_path))
    assert r["status"] == "CPU2_SAFE_RECEIPT_VERIFIED__R50_TRAIN_HOLD"
    assert r["tokenizer_token_counts"] == [48, 63]
    assert r["train_admitted"] == 0
    assert r["native_template_token_parity_verified"] is False


@pytest.mark.parametrize("field,value", [
    ("train_admitted", 1),
    ("r50_complete_exclusion_verified", True),
    ("native_template_token_parity_verified", True),
    ("collator_verified", False),
    ("model_weights_loaded", True),
    ("cases", True),
    ("status", "NOT_PASS"),
    ("supervised_token_counts", [1000, 2]),
    ("real_collator_token_counts", [2, 2]),
    ("tokenizer_input_token_counts", [True, 63]),
    ("tokenizer_input_token_counts", [0, 63]),
    ("tokenizer_input_token_counts", [16400, 63]),
])
def test_fail_closed_bad_contract(tmp_path, field, value):
    data = payload()
    data[field] = value
    r = module.inspect(stage(tmp_path, data))
    assert r["status"] == "CPU2_SAFE_RECEIPT_HOLD"
    assert "secret" not in json.dumps(r)


def test_mode_name_and_symlink_fail_closed(tmp_path):
    file = stage(tmp_path)
    os.chmod(file, 0o644)
    assert module.inspect(file)["status"] == "CPU2_SAFE_RECEIPT_HOLD"
    os.chmod(file, 0o600)
    link = tmp_path / "alias"
    link.symlink_to(file)
    assert module.inspect(link)["status"] == "CPU2_SAFE_RECEIPT_HOLD"

"""Fully synthetic Common2 readiness tests, no real story or HF inputs."""
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "r60_common2_training_readiness_cpu",
    ROOT / "scripts" / "r60_common2_training_readiness_cpu.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def make(tmp_path):
    folder = tmp_path / "private"
    folder.mkdir(mode=0o700)
    messages = [{"role": "user" if i % 2 == 0 else "assistant",
                 "content": f"fictional {i}"} for i in range(11)]
    item = {
        "schema": "storyforge_r60_source_bound_experimental_sft_v1",
        "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
        "supervision_scope": "FINAL_ASSISTANT_ONLY",
        "messages": messages + [{"role": "assistant", "content": "synthetic completion"}],
        "system_prompt": None, "world_card": None, "train_admitted": False,
    }
    raw = (json.dumps(item, sort_keys=True) + "\n").encode() * 2
    (folder / m.sft.DATA_NAME).write_bytes(raw)
    manifest = {
        "schema": "storyforge_r60_common2_sft_experimental_manifest_private_v1",
        "status": "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED",
        "examples": 2, "window": 11, "train_admitted": 0,
        "r50_complete_exclusion_verified": False,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
    }
    (folder / m.sft.MANIFEST_NAME).write_text(json.dumps(manifest))
    rec = {
        "schema": m.receipt.SCHEMA,
        "status": m.receipt.SUCCESS,
        "cases": 2, "tokenizer_verified": True, "collator_verified": True,
        "r50_complete_exclusion_verified": False, "train_admitted": 0,
        "model_inference_calls": 0, "model_weights_loaded": False,
        "native_template_token_parity_verified": False,
        "gpu_started": False, "private_values_emitted": False,
        "database_accessed": False,
        "tokenizer_input_token_counts": [2552, 4048],
        "real_collator_token_counts": [2486, 3982],
        "supervised_token_counts": [282, 305],
    }
    path = tmp_path / m.receipt.EXPECTED_NAME
    path.write_text(json.dumps(rec))
    for p in folder.iterdir():
        os.chmod(p, 0o600)
    os.chmod(path, 0o600)
    return folder, path


def test_synthetic_success_still_never_admits(tmp_path):
    folder, receipt = make(tmp_path)
    out = m.inspect(folder, receipt)
    assert out["status"] == "COMMON2_INPUT_AND_CPU2_INDEPENDENT_CHECKS_PASS__ADMISSION_HOLD"
    assert out["cases_verified"] == 2
    assert out["payload_sha_verified"] is True
    assert out["cpu2_existing_receipt_verified"] is True
    assert out["train_admitted"] == 0
    assert out["train_deploy_template_policy_approved"] is False
    assert out["semantic_world_alias_isolation_verified"] is False
    assert "fictional" not in json.dumps(out)


def test_tamper_payload_hash_holds(tmp_path):
    folder, receipt = make(tmp_path)
    payload = folder / m.sft.DATA_NAME
    payload.write_bytes(payload.read_bytes() + b" ")
    out = m.inspect(folder, receipt)
    assert out["cases_verified"] == 0
    assert out["derived_input_contract_verified"] is False
    assert out["train_admitted"] == 0


def test_receipt_wrong_status_holds(tmp_path):
    folder, path = make(tmp_path)
    doc = json.loads(path.read_text())
    doc["status"] = "fake-success"
    path.write_text(json.dumps(doc))
    out = m.inspect(folder, path)
    assert out["stage"] == "CPU2_RECEIPT"
    assert out["reason_code"] == "CPU2_RECEIPT_CONTRACT_HOLD"
    assert out["train_admitted"] == 0


def test_symlink_private_input_holds(tmp_path):
    folder, path = make(tmp_path)
    payload = folder / m.sft.DATA_NAME
    copy = folder / "source-copy"
    copy.write_bytes(payload.read_bytes())
    payload.unlink()
    payload.symlink_to(copy)
    out = m.inspect(folder, path)
    assert out["reason_code"] == "PRIVATE_INPUT_LINK_HOLD"
    assert out["train_admitted"] == 0


def test_world_card_injected_rejected(tmp_path):
    folder, path = make(tmp_path)
    payload = folder / m.sft.DATA_NAME
    rows = [json.loads(x) for x in payload.read_text().splitlines()]
    rows[0]["world_card"] = "fabricated"
    raw = b"".join((json.dumps(x) + "\n").encode() for x in rows)
    payload.write_bytes(raw)
    manifest = folder / m.sft.MANIFEST_NAME
    doc = json.loads(manifest.read_text())
    doc["data_sha256"] = hashlib.sha256(raw).hexdigest()
    manifest.write_text(json.dumps(doc))
    out = m.inspect(folder, path)
    assert out["reason_code"] == "EXPERIMENT_MESSAGE_SEQUENCE_HOLD"
    assert "fabricated" not in json.dumps(out)


def test_receipt_open_permissions_holds(tmp_path):
    folder, path = make(tmp_path)
    os.chmod(path, 0o644)
    out = m.inspect(folder, path)
    assert out["reason_code"] == "CPU2_RECEIPT_CONTRACT_HOLD"
    assert out["train_admitted"] == 0


def test_hold_subclass_reason_code_remains_allowlisted(tmp_path, monkeypatch):
    folder, path = make(tmp_path)
    monkeypatch.setattr(
        m.audit, "validate_payload",
        lambda *args: (_ for _ in ()).throw(
            m.audit.Hold("PRIVATE_EXPERIMENT_CONTRACT_HOLD")
        ),
    )
    out = m.inspect(folder, path)
    assert out["reason_code"] == "PRIVATE_EXPERIMENT_CONTRACT_HOLD"
    assert out["train_admitted"] == 0
    assert "PRIVATE_INPUT_OR_RUNTIME_HOLD" not in json.dumps(out)


def test_unknown_hold_reason_cannot_leak_private_text(tmp_path, monkeypatch):
    folder, path = make(tmp_path)
    monkeypatch.setattr(
        m.audit, "validate_payload",
        lambda *args: (_ for _ in ()).throw(m.audit.Hold("secret narrative")),
    )
    out = m.inspect(folder, path)
    assert out["reason_code"] == "PRIVATE_INPUT_OR_RUNTIME_HOLD"
    assert "secret narrative" not in json.dumps(out)

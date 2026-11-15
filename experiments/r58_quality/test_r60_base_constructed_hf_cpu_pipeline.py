"""Synthetic-only immutable HF CPU3 stage/worker checks, no HF request."""
import hashlib
import json
from types import SimpleNamespace

import pytest
import r60_base_constructed_hf_cpu_stage as stage
import r60_base_constructed_hf_cpu_worker as worker


def test_stage_verify_accepts_hf_mounted_path(monkeypatch, tmp_path):
    key = "r60-constructcpu-20261115T100000Z-aabbccddeeff"
    actual = tmp_path / "common2"
    actual.mkdir(mode=0o700)
    source = actual / "synthetic.txt"
    source.write_text("synthetic-only")
    source.chmod(0o600)
    data = source.read_bytes()
    record = {
        "schema": stage.SCHEMA, "run_key": key,
        "status": "SYNTHETIC_STAGE_ONLY__NO_JOB",
        "synthetic_cases": 3, "train_admitted": 0,
        "files": {"synthetic.txt": hashlib.sha256(data).hexdigest()},
    }
    (actual / "SHA256_MANIFEST_PRIVATE.json").write_text(json.dumps(record))
    monkeypatch.setattr(stage, "ENTRY", [])
    result = stage.verify(actual, key)
    assert result["status"] == "BASE_CONSTRUCTED_HF_CPU_STAGE_VERIFIED__NO_JOB"
    assert result["train_admitted"] == 0


def test_stage_manifest_drift_fails_closed(monkeypatch, tmp_path):
    key = "r60-constructcpu-20261115T100000Z-aabbccddeeff"
    target = tmp_path / key
    target.mkdir()
    (target / "SHA256_MANIFEST_PRIVATE.json").write_text(json.dumps({
        "schema": stage.SCHEMA,
        "run_key": key, "status": "SYNTHETIC_STAGE_ONLY__NO_JOB",
        "synthetic_cases": 3, "train_admitted": 0,
        "files": {"fake": "0" * 64},
    }))
    monkeypatch.setattr(stage, "ENTRY", [])
    with pytest.raises(ValueError, match="STAGE_FILESET_HOLD"):
        stage.verify(target, key)


def test_worker_no_dependencies_does_not_claim_success(monkeypatch, tmp_path):
    key = "r60-constructcpu-20261115T100000Z-aabbccddeeff"
    monkeypatch.setattr(worker.RuntimeContext, "detect",
                        lambda **_: SimpleNamespace(operating_system="linux"))
    monkeypatch.setattr(worker.ResourceGuard, "check_cpu_only",
                        lambda: SimpleNamespace(status="PASS"))
    monkeypatch.setattr(worker.stage_tool, "verify", lambda *_: {})
    monkeypatch.setattr(worker, "version", lambda name: "incompatible")
    result = worker.run(tmp_path, key)
    assert result["status"] == "BASE_CONSTRUCTED_HF_CPU_HOLD"
    assert result["reason_code"] == "DEPENDENCIES_HOLD"
    assert result["train_admitted"] == 0
    assert result["gpu_started"] is False


def test_stage_empty_create_only(monkeypatch, tmp_path):
    key = "r60-constructcpu-20261115T100000Z-aabbccddeeff"
    target = tmp_path / key
    target.mkdir()
    with pytest.raises(ValueError, match="CREATE_ONLY_HOLD"):
        stage.prepare(target, key)


def test_stage_run_key_rejected():
    assert stage.RUN_RE.fullmatch("r60-base-cpu336-20261115T100000Z-aabbccddeeff") is None


def test_stage_code_source_dependencies_exist():
    assert stage.SCHEMA
    assert "scripts/r60_base_constructed_hf_cpu_worker.sh" in stage.ENTRY
    assert "experiments/r58_quality/r60_base_constructed_sft_cpu_smoke.py" in stage.ENTRY


def test_synthetic_stage_does_not_contain_private_story_inputs():
    assert not any("PRIVATE.jsonl" in name for name in stage.ENTRY)
    assert not any(name.startswith("private/") for name in stage.ENTRY)


def test_dependency_closure_includes_audited_collator_and_r18():
    files = stage.dependencies()
    assert "scripts/hf_label_mask_audit.py" in files
    assert "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py" in files
    assert "experiments/r58_quality/r60_base_constructed_sft_cpu_smoke.py" in files
    assert len(files) == len(set(files))

"""No HF, model weights, private story files or paid actions in these tests."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import r60_common2_wrapped_hf_stage as stage
import r60_common2_wrapped_hf_cli as cli
import r60_common2_wrapped_hf_receipt_verify as receipt


KEY = "r60-common2-wrapcpu-20261112T120000Z-abc123456789"


def synthetic_stage(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    for name in (stage.DATA, stage.MANIFEST):
        (source / name).write_text("synthetic-only", encoding="utf-8")
        (source / name).chmod(0o600)
    from r60_common2_generic_system_wrapper_preview_cpu import preview
    import r60_common2_generic_system_wrapper_preview_cpu as wrapper
    monkeypatch.setattr(wrapper, "preview", lambda path: {
        "status": "COMMON2_GENERIC_SYSTEM_IN_MEMORY_WRAPPER_PREVIEW_PASS__TRAIN_HOLD",
    })
    # Use real project code dependencies to confirm stage import closure.
    output = tmp_path / KEY
    result = stage.prepare(source, output, KEY)
    assert result["status"] == "WRAPPED_CPU_STAGE_VERIFIED__NO_JOB"
    return output


def test_stage_is_create_only_sha_bound_and_never_submits(tmp_path, monkeypatch):
    path = synthetic_stage(tmp_path, monkeypatch)
    assert path.joinpath("src/storyforge_dataset/token_preflight.py").is_file()
    assert path.joinpath("scripts/r60_common2_wrapped_hf_worker.sh").is_file()
    with pytest.raises(ValueError, match="STAGE_ALREADY_EXISTS_HOLD"):
        stage.prepare(tmp_path / "source", path, KEY)
    assert stage.verify(path, KEY)["hf_jobs_submitted"] == 0


def test_tampered_stage_or_added_file_fails(tmp_path, monkeypatch):
    path = synthetic_stage(tmp_path, monkeypatch)
    target = path / ("private/" + stage.DATA)
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        stage.verify(path, KEY)


def test_extra_stage_file_fails_closed(tmp_path, monkeypatch):
    path = synthetic_stage(tmp_path, monkeypatch)
    (path / "new.bin").write_bytes(b"unknown")
    with pytest.raises(ValueError, match="STAGE_FILES_HOLD"):
        stage.verify(path, KEY)


def test_job_cli_keeps_cpu_ro_rw_fixed_and_correct_image_position():
    help_text = ("--namespace --name --flavor --timeout --attempts "
                 "--detach --volume --dry-run")
    argv = cli.job_command(KEY, help_text)
    assert "--namespace" in argv and argv[argv.index("--namespace") + 1] == "adradar"
    assert "--flavor" in argv and argv[argv.index("--flavor") + 1] == "cpu-upgrade"
    assert "--attempts" in argv and argv[argv.index("--attempts") + 1] == "1"
    assert ":/input/common2:ro" in " ".join(argv)
    assert ":/output:rw" in " ".join(argv)
    assert cli.IMAGE in argv
    assert argv[argv.index(cli.IMAGE) + 1] == "bash"
    assert "--" not in argv[argv.index(cli.IMAGE) + 1:]


def test_empty_run_key_never_matches():
    assert stage.RUN_RE.fullmatch(KEY)
    assert not stage.RUN_RE.fullmatch("../foo")
    assert not stage.RUN_RE.fullmatch("r60-common2-cpu2-20261112T073854Z-e076f53c8eae")


def safe_receipt(tmp_path):
    output = {
        "schema": receipt.SCHEMA, "run_key": KEY,
        "status": receipt.SUCCESS, "reason_code": "WRAPPED_ACTUAL_SWIFT_ONLY",
        "stage": "AUDIT_COMPLETE", "model": "Qwen/Qwen3.8-27B",
        "model_revision": receipt.PIN, "stage_sha_verified": True,
        "system_text_pin_verified": True, "original_input_sha_verified": True,
        "source_examples": 2, "wrapped_examples": 2, "tokenizer_verified": True,
        "actual_swift_collator_verified": True,
        "last_assistant_label_mask_verified": True,
        "deployment_template_compatibility_verified": False,
        "semantic_world_isolation_verified": False,
        "r60_input_design_approved": False,
        "train_admitted": 0, "quality_v1_admitted": 0,
        "model_weights_loaded": False, "model_inference_calls": 0,
        "gpu_started": False, "hf_jobs_submitted": 0,
        "private_values_emitted": False,
        "training_dataset_files_written": 0,
        "safe_receipt_publication_expected": True,
        "system_origin": "R27_R52_FROZEN_SYNTHETIC_NOT_HISTORICAL_SENT",
        "tokenizer_token_counts": [2600, 4050],
        "real_collator_token_counts": [2550, 4000],
        "supervised_token_counts": [280, 305],
    }
    p = tmp_path / receipt.EXPECTED_NAME
    p.write_text(json.dumps(output))
    return p, output


def test_receipt_acceptance_requires_verified_audit(tmp_path):
    path, _ = safe_receipt(tmp_path)
    result = receipt.inspect(path, KEY)
    assert result["status"] == "WRAPPED_CPU_RECEIPT_ACCEPTED__TRAIN_HOLD"
    assert result["cases_verified"] == 2
    assert result["train_admitted"] == 0


def test_receipt_rejects_collator_false_or_admitted_data(tmp_path):
    path, data = safe_receipt(tmp_path)
    data["actual_swift_collator_verified"] = False
    data["train_admitted"] = 2
    path.write_text(json.dumps(data))
    result = receipt.inspect(path, KEY)
    assert result["status"] == "WRAPPED_CPU_RECEIPT_HOLD"
    assert result["reason_code"] == "RECEIPT_CONTRACT_HOLD"


def test_receipt_count_tamper_and_expected_sha_fail(tmp_path):
    path, data = safe_receipt(tmp_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert receipt.inspect(path, KEY, digest)["cases_verified"] == 2
    data["supervised_token_counts"] = [9999, 305]
    path.write_text(json.dumps(data))
    assert receipt.inspect(path, KEY, digest)["status"] == "WRAPPED_CPU_RECEIPT_HOLD"
    assert receipt.inspect(path, KEY)["reason_code"] == "RECEIPT_COUNT_RANGE_HOLD"


def test_no_secret_exception_leaks(tmp_path):
    result = receipt.inspect(tmp_path / "SECRET_PATH" / receipt.EXPECTED_NAME, KEY)
    assert "SECRET_PATH" not in json.dumps(result)
    assert result["train_admitted"] == 0

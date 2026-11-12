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
import r60_common2_wrapped_hf_cli as cli
import r60_common2_wrapped_hf_receipt_verify as receipt
import r60_common2_wrapped_hf_stage as stage

KEY = "r60-common2-wrapcpu-20261112T120000Z-abc123456789"


def synthetic_stage(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    for name in (stage.DATA, stage.MANIFEST):
        (source / name).write_text("synthetic-only", encoding="utf-8")
        (source / name).chmod(0o600)
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


def test_sync_uploads_manifest_last_and_never_submits(tmp_path, monkeypatch):
    """Synthetic remote never reaches Hugging Face; verify upload order."""
    import types
    stage_dir = tmp_path / KEY
    stage_dir.mkdir()
    targets = ["scripts/a.py", "private/sample.jsonl", "SHA256_MANIFEST_PRIVATE.json"]
    for name in targets:
        p = stage_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("synthetic")
    monkeypatch.setattr(cli, "expected", lambda *args: set(targets))
    monkeypatch.setattr(cli, "remote_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "output_is_empty", lambda *args, **kwargs: None)
    mock_hf = types.ModuleType("huggingface_hub")
    mock_hf.HfApi = lambda: object()
    monkeypatch.setitem(sys.modules, "huggingface_hub", mock_hf)
    uploads = []

    def fake_run(argv, **kwargs):
        assert argv[:3] == ["hf", "buckets", "cp"]
        uploads.append(argv[-1])
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    out = cli.execute("sync", stage_dir, KEY, False)
    assert out["status"] == "WRAPPED_CPU_REMOTE_STAGE_READY__NO_JOB"
    assert uploads[-1].endswith("SHA256_MANIFEST_PRIVATE.json")
    assert len(uploads) == len(targets)
    assert out["job_submission_calls"] == 0


def test_submit_creates_marker_before_single_cli_call_and_replay_holds(
        tmp_path, monkeypatch):
    import types
    stage_dir = tmp_path / KEY
    stage_dir.mkdir()
    monkeypatch.setattr(cli, "expected", lambda *args: {"fake"})
    monkeypatch.setattr(cli, "remote_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "output_is_empty", lambda *args, **kwargs: None)
    mock_hf = types.ModuleType("huggingface_hub")
    mock_hf.HfApi = lambda: object()
    monkeypatch.setitem(sys.modules, "huggingface_hub", mock_hf)
    import r60_common2_hf_cpu_final_read_only as historical
    monkeypatch.setattr(historical, "walk_job_history", lambda *args: (2, 0))
    marker = tmp_path / (KEY + ".wrapped-cpu-attempted")
    seen_job_calls = []

    def fake_run(argv, **kwargs):
        if argv[:4] == ["hf", "jobs", "run", "--help"]:
            return types.SimpleNamespace(
                returncode=0, stdout="--namespace --name --flavor --timeout "
                                    "--attempts --detach --volume --dry-run",
                stderr="")
        if argv[:3] == ["hf", "auth", "whoami"]:
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if "--dry-run" in argv:
            return types.SimpleNamespace(returncode=0, stdout="Dry run OK", stderr="")
        seen_job_calls.append(argv)
        assert marker.exists(), "create-only marker must precede HF API call"
        return types.SimpleNamespace(
            returncode=0, stdout="Job started with ID: 6af570089737d9a9e093d501",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    out = cli.execute("submit", stage_dir, KEY, True)
    assert out["status"] == "WRAPPED_CPU_JOB_SUBMITTED__TRAIN_HOLD"
    assert out["job_submission_calls"] == 1
    assert len(seen_job_calls) == 1
    assert marker.exists()
    try:
        cli.execute("submit", stage_dir, KEY, True)
        assert False, "replay must fail before any second submission"
    except ValueError as exc:
        assert str(exc) == "JOB_ATTEMPT_ALREADY_RECORDED_HOLD"
    assert len(seen_job_calls) == 1


def test_diagnose_is_read_only_and_reports_empty_or_partial(tmp_path, monkeypatch):
    import types

    folder = tmp_path / KEY
    folder.mkdir()
    expected_files = {"private/data.jsonl", "SHA256_MANIFEST_PRIVATE.json"}
    monkeypatch.setattr(cli, "expected", lambda *args: expected_files)
    mock_hf = types.ModuleType("huggingface_hub")
    mock_hf.HfApi = lambda: object()
    monkeypatch.setitem(sys.modules, "huggingface_hub", mock_hf)
    prefixes = []

    def fake_remote_set(api, prefix):
        prefixes.append(prefix)
        return {"private/data.jsonl"} if "/runs/" in prefix else set()

    monkeypatch.setattr(cli, "remote_set", fake_remote_set)
    monkeypatch.setattr(
        cli.subprocess, "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("diagnose must never call hf CLI")
        ),
    )
    result = cli.diagnose(folder, KEY)
    assert result["status"] == "WRAPPED_CPU_REMOTE_DIAGNOSTIC_PASS__NO_JOB"
    assert result["remote_input"] == "PARTIAL_OR_MISMATCH"
    assert result["remote_output"] == "EMPTY"
    assert result["submit_marker"] == "ABSENT"
    assert result["job_submission_calls"] == 0
    assert len(prefixes) == 2


def test_diagnose_reports_sdk_category_without_exception_leak(tmp_path, monkeypatch):
    import types

    folder = tmp_path / KEY
    folder.mkdir()
    monkeypatch.setattr(cli, "expected", lambda *args: {"a"})
    mock_hf = types.ModuleType("huggingface_hub")
    mock_hf.HfApi = lambda: object()
    monkeypatch.setitem(sys.modules, "huggingface_hub", mock_hf)

    def broken_remote_set(*args):
        raise AttributeError("PRIVATE HF AUTH TOKEN OR USER DATA")

    monkeypatch.setattr(cli, "remote_set", broken_remote_set)
    result = cli.diagnose(folder, KEY)
    assert result["status"] == "WRAPPED_CPU_REMOTE_DIAGNOSTIC_HOLD"
    assert result["phase"] == "REMOTE_INPUT_LIST"
    assert result["reason_code"] == "SDK_API_UNAVAILABLE"
    assert "PRIVATE HF AUTH TOKEN" not in json.dumps(result)
    assert result["job_submission_calls"] == 0


def test_remote_listing_rejects_unexpected_path_without_leaking(tmp_path):
    import types

    api = types.SimpleNamespace(
        list_bucket_tree=lambda *args, **kwargs: [
            types.SimpleNamespace(path="unexpected/private/id", type="file"),
        ]
    )
    with pytest.raises(ValueError, match="REMOTE_PATH_HOLD"):
        cli.remote_set(api, "preflight/r60/common2/wrapped-cpu/runs/key/")
    assert cli.classify_safe_failure(ValueError("REMOTE_PATH_HOLD")) == "REMOTE_PATH_HOLD"

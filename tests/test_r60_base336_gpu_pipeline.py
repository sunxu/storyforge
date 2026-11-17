"""Network-free R60 Base336 GPU pipeline tests; no CUDA, HF Hub or Jobs calls."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "scripts"),
    str(ROOT / "src"),
    str(ROOT / "experiments/r58_quality"),
]

import r60_base336_gpu_cli as cli
import r60_base336_gpu_contract as contract
import r60_base336_gpu_stage as stage
import r60_base336_gpu_worker as worker

KEY = "r60-base336-gpu-20261117T040000Z-abcdef123456"


def proof_value() -> dict:
    return {
        "schema": contract.PROOF_SCHEMA,
        "status": contract.PROOF_STATUS,
        "train_rows": 293,
        "validation_rows": 43,
        "source_cpu_audited_rows": 336,
        "source_cpu_receipt_accepted": True,
        "all_final_rows_byte_identical_to_audited_rows": True,
        "actual_final_collator_verified": True,
        "collator_executed_in_this_run": False,
        "input_contract": contract.INPUT_CONTRACT,
        "formal_source_admission_verified": False,
        "train_admitted": 0,
        "gpu_stage_prepared": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def write_private(path: Path, raw: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o600)


def test_optimizer_steps_are_derived_from_actual_shape():
    assert contract.optimizer_steps() == 37
    assert contract.optimizer_steps(17, per_device_batch_size=2,
                                    gradient_accumulation_steps=4) == 3
    with pytest.raises(ValueError, match="TRAINING_SHAPE_HOLD"):
        contract.optimizer_steps(293, world_size=0)


def test_render_config_binds_mount_paths_and_preserves_training_contract():
    template = (ROOT / "configs/r60_base336_exploratory_293_43.yaml").read_bytes()
    rendered = contract.render_config(template).decode()
    assert "/input/r60-base336/private/release/train.jsonl" in rendered
    assert "/input/r60-base336/private/release/validation.jsonl" in rendered
    assert "output_dir: /output/training" in rendered
    assert "REPLACE_RUN_KEY" not in rendered
    assert "eval_steps: 37" in rendered and "save_steps: 37" in rendered


def test_render_config_rejects_step_drift():
    template = (ROOT / "configs/r60_base336_exploratory_293_43.yaml").read_bytes()
    with pytest.raises(ValueError, match="TRAINING_CONFIG_CONTRACT_HOLD"):
        contract.render_config(template.replace(b"save_steps: 37", b"save_steps: 16"))


def test_collator_proof_acceptance_requires_all_transfer_invariants(tmp_path):
    path = tmp_path / "proof.json"
    write_private(path, json.dumps(proof_value()).encode())
    assert contract.verify_proof_receipt(path)["actual_final_collator_verified"] is True
    changed = proof_value()
    changed["collator_executed_in_this_run"] = True
    write_private(path, json.dumps(changed).encode())
    with pytest.raises(ValueError, match="COLLATOR_TRANSFER_PROOF_HOLD"):
        contract.verify_proof_receipt(path)


def _synthetic_stage(tmp_path: Path, monkeypatch) -> Path:
    folder = tmp_path / KEY
    folder.mkdir(mode=0o700)
    files: dict[str, str] = {}

    def add(name: str, raw: bytes) -> None:
        path = folder / name
        write_private(path, raw)
        files[name] = hashlib.sha256(raw).hexdigest()

    template = (ROOT / "configs/r60_base336_exploratory_293_43.yaml").read_bytes()
    add("config/template.yaml", template)
    add(contract.CONFIG_NAME, contract.render_config(template))
    add("requirements/r60-base336-gpu.in", b"ms-swift==4.5.3\n")
    add("scripts/r60_base336_gpu_worker.py", b"synthetic worker\n")
    add("scripts/r60_base336_gpu_worker.sh", b"#!/bin/sh\n")
    add("scripts/r60_base336_gpu_contract.py", b"synthetic contract\n")
    add("scripts/hf_job_runner.py", b"synthetic shared helper\n")
    add("scripts/hf_smoke_guard.py", b"synthetic custom guard\n")
    add("src/storyforge_dataset/__init__.py", b"")
    add("src/storyforge_dataset/hf_runtime/__init__.py", b"")
    add("src/storyforge_dataset/hf_runtime/inputs.py", b"")
    add("src/storyforge_dataset/hf_runtime/outputs.py", b"")
    add("private/release/train.jsonl", b'{"messages":[]}\n')
    add("private/release/validation.jsonl", b'{"messages":[]}\n')
    release_manifest = {
        "schema": "synthetic",
        "statistics": {
            "rows": {"train": 293, "validation": 43},
            "input_contract": contract.INPUT_CONTRACT,
            "semantic_world_isolation_verified": False,
            "r50_semantic_isolation_verified": False,
            "reviewer_execution_independence_verified": False,
        },
    }
    add("private/release/" + contract.RELEASE_MANIFEST,
        json.dumps(release_manifest).encode())
    add("private/proof/" + contract.PROOF_NAME,
        json.dumps(proof_value()).encode())

    manifest = {
        "schema": contract.STAGE_SCHEMA,
        "status": "STAGED_NOT_SUBMITTED",
        "run_key": KEY,
        "git_commit": "a" * 40,
        "files": files,
        "model": contract.MODEL,
        "model_revision": contract.REVISION,
        "hf_namespace": contract.HF_NAMESPACE,
        "hf_bucket": contract.HF_BUCKET,
        "hf_stage_prefix": contract.HF_STAGE_PREFIX,
        "hf_result_prefix": contract.HF_RESULT_PREFIX,
        "hf_flavor": contract.HF_FLAVOR,
        "hf_timeout_minutes": contract.HF_TIMEOUT_MINUTES,
        "hf_image": contract.HF_IMAGE,
        "train_rows": 293,
        "validation_rows": 43,
        "optimizer_steps": 37,
        "input_contract": contract.INPUT_CONTRACT,
        "collator_transfer_status": contract.PROOF_STATUS,
        "collator_executed_in_this_run": False,
        "source_cpu_receipt_accepted": True,
        "private_data_contains_r50": False,
        "r50_semantic_isolation_verified": False,
        "semantic_world_isolation_verified": False,
        "reviewer_execution_independence_verified": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "model_weights_in_stage": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }
    write_private(
        folder / "SHA256_MANIFEST_PRIVATE.json",
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
    )
    monkeypatch.setattr(contract, "verify_release", lambda _path, **_kwargs: {
        "status": "BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD",
        "train_rows": 293,
        "validation_rows": 43,
        "sha256_verified": True,
        "train_admitted": 0,
        "gpu_started": False,
    })
    return folder


def test_stage_verifies_manifest_proof_and_shared_runtime(tmp_path, monkeypatch):
    folder = _synthetic_stage(tmp_path, monkeypatch)
    result = contract.verify_stage(folder, KEY)
    assert result["status"] == "BASE336_GPU_STAGE_VERIFIED__NO_JOB"
    assert result["files_verified"] >= 15
    assert result["train_admitted"] == 0
    assert result["gpu_started"] is False


def test_stage_rejects_changed_file_bytes(tmp_path, monkeypatch):
    folder = _synthetic_stage(tmp_path, monkeypatch)
    target = folder / "scripts/hf_job_runner.py"
    target.write_bytes(b"tampered\n")
    with pytest.raises(ValueError, match="INPUT_SHA256_MISMATCH"):
        contract.verify_stage(folder, KEY)


def test_stage_rejects_extra_files(tmp_path, monkeypatch):
    folder = _synthetic_stage(tmp_path, monkeypatch)
    (folder / "unexpected.txt").write_text("extra")
    with pytest.raises(ValueError, match="STAGE_FILESET_HOLD"):
        contract.verify_stage(folder, KEY)


def test_stage_reuses_existing_dependency_closure_without_r54_or_token_preflight():
    dependencies = stage.shared_stage.local_dependencies(
        entries=stage.ENTRY, extras=stage.EXTRA
    )
    assert len(dependencies) <= stage.shared_stage.MAX_CODE_FILES
    assert {
        "scripts/r60_base336_gpu_worker.py",
        "scripts/r60_base336_gpu_worker.sh",
        "scripts/r60_base336_gpu_contract.py",
        "scripts/hf_job_runner.py",
        "scripts/hf_smoke_guard.py",
        "experiments/r58_quality/r60_base336_exploratory_release_verify.py",
        "experiments/r58_quality/r60_real_private_batch.py",
        "src/storyforge_dataset/hf_runtime/inputs.py",
        "src/storyforge_dataset/hf_runtime/outputs.py",
    }.issubset(dependencies)
    assert "scripts/v03_r54_gpu_runner.py" not in dependencies
    assert "src/storyforge_dataset/token_preflight.py" not in dependencies


def test_stage_create_only_write_uses_private_mode(tmp_path):
    root = tmp_path / KEY
    root.mkdir(mode=0o700)
    digest = stage._copy_new(root, "private/item.json", b"safe")
    assert digest == hashlib.sha256(b"safe").hexdigest()
    assert (root / "private/item.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="STAGE_CREATE_ONLY_HOLD"):
        stage._copy_new(root, "private/item.json", b"overwrite")


def test_gpu_cli_command_is_a100_ro_rw_and_dry_run_only(monkeypatch):
    monkeypatch.setattr(cli.shared_cli, "missing_job_cli_flags", lambda _text: [])
    monkeypatch.setattr(cli.shared_cli, "use_documented_default_attempts", lambda _text: False)
    monkeypatch.setattr(
        cli.hf_job_guard, "validate_spec",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("CPU policy must not be called")),
    )
    argv = cli.job_command(
        KEY, "--namespace --name --flavor --timeout --attempts --detach -v --env --dry-run"
    )
    assert "--dry-run" in argv
    assert argv[argv.index("--flavor") + 1] == "a100-large"
    assert argv[argv.index("--timeout") + 1] == "120m"
    volumes = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "-v"]
    assert len(volumes) == 2
    assert volumes[0].endswith(":/input/r60-base336:ro")
    assert volumes[1].endswith(":/output:rw")
    assert cli.IMAGE in argv and "@sha256:" in cli.IMAGE
    assert argv[argv.index(cli.IMAGE) + 1] == "bash"
    assert argv[:3] == ["hf", "jobs", "run"]
    assert "STORYFORGE_R60_BASE336_GPU_SCOPE=DRY_RUN_NOT_AUTHORIZED" in argv


def test_cli_local_preflight_requires_exact_clean_stage_git_head(tmp_path, monkeypatch):
    folder = _synthetic_stage(tmp_path, monkeypatch)
    monkeypatch.setattr(stage, "_git_commit", lambda: "a" * 40)
    files = cli._local_files(folder, KEY)
    assert "SHA256_MANIFEST_PRIVATE.json" in files
    monkeypatch.setattr(stage, "_git_commit", lambda: "b" * 40)
    with pytest.raises(ValueError, match="STAGE_GIT_HEAD_DRIFT_HOLD"):
        cli._local_files(folder, KEY)


def test_cli_sync_uploads_manifest_last_and_never_submits(tmp_path, monkeypatch):
    stage_dir = tmp_path / KEY
    stage_dir.mkdir()
    for name in ("code/a.py", "SHA256_MANIFEST_PRIVATE.json"):
        path = stage_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic")
    expected = {
        "code/a.py": "a" * 64,
        "SHA256_MANIFEST_PRIVATE.json": "b" * 64,
    }
    monkeypatch.setattr(cli, "_check_remote_set", lambda *args, **kwargs: expected)
    monkeypatch.setattr(cli, "_prefix_empty", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_check_job_history", lambda *args, **kwargs: {
        "visible_jobs": 0, "matching_jobs": 0, "exhaustive": True,
    })
    monkeypatch.setattr(cli, "_verify_remote_sha", lambda *args, **kwargs: None)
    uploads = []

    def fake_run(argv, **kwargs):
        uploads.append(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    report = cli.sync(stage_dir, KEY, object())
    assert report["status"] == "BASE336_GPU_REMOTE_STAGE_READY__NO_JOB"
    assert uploads[-1][-1].endswith("/SHA256_MANIFEST_PRIVATE.json")
    assert len(uploads) == 2
    assert all(argv[:3] == ["hf", "buckets", "cp"] for argv in uploads)
    assert report["job_submission_calls"] == 0
    assert report["job_history_exhaustive"] is True
    assert report["matching_jobs"] == 0


def test_cli_ready_runs_only_dry_run_and_exhaustive_history(tmp_path, monkeypatch):
    stage_dir = tmp_path / KEY
    stage_dir.mkdir()
    monkeypatch.setattr(cli, "_check_remote_set", lambda *args, **kwargs: {"a": "b"})
    monkeypatch.setattr(cli, "_verify_remote_sha", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_prefix_empty", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "_check_job_history", lambda *args, **kwargs: {
        "visible_jobs": 4, "matching_jobs": 0, "exhaustive": True,
    })
    monkeypatch.setattr(cli, "job_command", lambda *_args: ["hf", "jobs", "run", "--dry-run"])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[-1] == "--help":
            return SimpleNamespace(returncode=0, stdout="help", stderr="")
        return SimpleNamespace(returncode=0, stdout="Dry run OK", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    report = cli.ready(stage_dir, KEY, object())
    assert report["status"] == "BASE336_GPU_REMOTE_AND_CLI_READY__NO_JOB"
    assert report["job_history_exhaustive"] is True
    assert report["matching_jobs"] == 0
    assert calls[-1] == ["hf", "jobs", "run", "--dry-run"]
    assert len(calls) == 2
    assert report["job_submission_calls"] == 0


def test_worker_preflight_does_not_start_gpu_or_training(monkeypatch):
    monkeypatch.setattr(contract, "verify_stage", lambda *_args: {
        "status": "BASE336_GPU_STAGE_VERIFIED__NO_JOB",
    })
    report = worker.run(Path("/input/r60-base336"), Path("/output"), KEY, "preflight")
    assert report["status"] == "BASE336_GPU_STAGE_VERIFIED__NO_GPU"
    assert report["collator_transfer_verified"] is True
    assert report["gpu_started"] is False
    assert report["training_started"] is False
    assert report["train_admitted"] == 0


def _training_output(tmp_path: Path, step: int = 37, rank: int = 64) -> Path:
    output = tmp_path / "training"
    checkpoint = output / "v0-20261117-040000" / f"checkpoint-{step}"
    checkpoint.mkdir(parents=True)
    state = {
        "global_step": step,
        "epoch": 1.0,
        "log_history": [
            {"step": step, "loss": 0.1, "eval_loss": 0.2},
        ],
    }
    write_private(checkpoint / "trainer_state.json", json.dumps(state).encode())
    write_private(checkpoint / "adapter_model.safetensors", b"adapter")
    write_private(checkpoint / "adapter_config.json", json.dumps({
        "peft_type": "LORA", "r": rank, "lora_alpha": 128,
    }).encode())
    return output


def test_terminal_checkpoint_requires_step_37_and_lora_contract(tmp_path):
    output = _training_output(tmp_path)
    report, path = worker._terminal_checkpoint(output, 37)
    assert report["global_step"] == 37
    assert report["adapter_rank"] == 64
    assert path.name == "checkpoint-37"


def test_terminal_checkpoint_rejects_r54_step_16(tmp_path):
    output = _training_output(tmp_path, step=16)
    with pytest.raises(ValueError, match="TERMINAL_OPTIMIZER_STEP_HOLD"):
        worker._terminal_checkpoint(output, 37)


def test_terminal_checkpoint_rejects_adapter_rank_drift(tmp_path):
    output = _training_output(tmp_path, rank=32)
    with pytest.raises(ValueError, match="FINAL_ADAPTER_CONFIG_HOLD"):
        worker._terminal_checkpoint(output, 37)


def test_cli_has_no_submit_action_or_billable_submission_call():
    source = (ROOT / "scripts/r60_base336_gpu_cli.py").read_text()
    assert 'choices=("preflight", "sync", "ready", "diagnose", "cli-flags")' in source
    assert "action == \"submit\"" not in source
    assert "argv.remove(\"--dry-run\")" not in source

"""Synthetic tests for the public HF Jobs Runtime; no network or private data."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from storyforge_dataset.hf_runtime import (
    DiagnosticReporter,
    InputManager,
    OutputManager,
    PathResolver,
    ReceiptValidator,
    ResourceGuard,
    RuntimeContext,
)


def valid_receipt() -> dict[str, object]:
    return {
        "schema": "storyforge-hf-runtime-diagnostic-v1",
        "runtime_version": "0.1.0",
        "profile": "cpu",
        "status": "PASS",
        "phase": "COMPLETION",
        "error_code": None,
        "checks": {"synthetic_check": "PASS"},
        "environment": {"runtime": "TEST", "python_version": "3.11"},
        "private_values_emitted": False,
        "gpu_started": False,
        "training_performed": False,
    }


def test_context_does_not_emit_environment_values() -> None:
    context = RuntimeContext.detect(environ={"HF_JOB_ID": "private-job-id", "SECRET": "never"})
    safe = context.to_safe_dict()
    assert safe["hf_job_hint"] is True
    assert "SECRET" not in safe
    assert "private-job-id" not in json.dumps(safe)


@pytest.mark.parametrize("raw", ["relative/file", "/safe/../escape"])
def test_path_resolver_rejects_ambiguous_or_traversal(raw: str) -> None:
    with pytest.raises(ValueError):
        PathResolver.resolve(raw, kind="host")


def test_path_resolver_separates_host_and_container() -> None:
    host = PathResolver.resolve("/tmp/input", kind="host")
    container = PathResolver.resolve("/job/input", kind="container")
    assert host.kind == "host"
    assert container.kind == "container"
    assert str(container.value) == "/job/input"
    with pytest.raises(ValueError, match="PATH_KIND_AMBIGUOUS"):
        PathResolver.resolve("/job/input", kind="auto")


def test_runner_module_bootstrap_uses_explicit_source_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "mounted-data"
    package = source_root / "storyforge_dataset"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""synthetic package"""\n', encoding="utf-8")
    monkeypatch.setattr(sys, "path", list(sys.path))
    resolved = PathResolver.bootstrap_module_root(source_root)
    assert resolved == source_root
    assert sys.path[0] == str(source_root)


def test_path_root_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="PATH_SYMLINK_REJECTED"):
        PathResolver.validate_input_root(link)


def test_input_manager_reads_and_hashes_synthetic_file(tmp_path: Path) -> None:
    source = tmp_path / "input.jsonl"
    data = b'{"synthetic":true}\n'
    source.write_bytes(data)
    result = InputManager.open_verified(
        source, max_bytes=1024, expected_sha256=hashlib.sha256(data).hexdigest()
    )
    assert result.read_bytes() == data
    assert result.size_bytes == len(data)
    assert result.to_safe_dict()["sha256"] == hashlib.sha256(data).hexdigest()


def test_input_manager_rejects_digest_mismatch_and_size(tmp_path: Path) -> None:
    source = tmp_path / "input.jsonl"
    source.write_text("synthetic", encoding="utf-8")
    with pytest.raises(ValueError, match="INPUT_SHA256_MISMATCH"):
        InputManager.open_verified(source, max_bytes=100, expected_sha256="0" * 64)
    with pytest.raises(ValueError, match="INPUT_SIZE_LIMIT_EXCEEDED"):
        InputManager.open_verified(source, max_bytes=2)


@pytest.mark.parametrize("mode", [0o600, 0o644, 0o444])
def test_input_permissions_are_not_mistaken_for_content_integrity(
    tmp_path: Path, mode: int
) -> None:
    source = tmp_path / f"mode-{mode:o}.jsonl"
    source.write_bytes(b'{"ok":true}\n')
    source.chmod(mode)
    result = InputManager.open_verified(source, max_bytes=100)
    assert result.read_bytes() == b'{"ok":true}\n'


def test_input_manager_accepts_multiple_hardlinks_with_verified_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    alias = tmp_path / "alias.jsonl"
    source.write_bytes(b'{"synthetic":1}\n')
    os.link(source, alias)
    assert source.stat().st_nlink == 2
    result = InputManager.open_verified(alias, max_bytes=100)
    assert result.read_bytes() == source.read_bytes()


def test_input_manager_validates_json_and_jsonl_structure() -> None:
    assert InputManager.validate_json(b'{"x":1}') == {"x": 1}
    rows = InputManager.validate_jsonl(b'{"x":1}\n{"x":2}\n', max_records=2)
    assert rows == [{"x": 1}, {"x": 2}]
    with pytest.raises(ValueError, match="INPUT_JSON_INVALID"):
        InputManager.validate_json(b'{')
    with pytest.raises(ValueError, match="INPUT_JSONL_INVALID"):
        InputManager.validate_jsonl(b'{"x":1}\nnot-json\n', max_records=5)
    with pytest.raises(ValueError, match="INPUT_SIZE_LIMIT_EXCEEDED"):
        InputManager.validate_jsonl(b'{"x":1}\n{"x":2}\n', max_records=1)


def test_input_manager_rejects_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("synthetic", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(ValueError, match="INPUT_SYMLINK_REJECTED"):
        InputManager.open_verified(link, max_bytes=100)


def test_output_probe_and_atomic_create_only_write(tmp_path: Path) -> None:
    capability = OutputManager.probe(tmp_path)
    assert capability.writable is True
    assert capability.probe_cleaned is True
    target = tmp_path / "safe.json"
    receipt = OutputManager.write_safe(target, {"status": "PASS", "synthetic": True})
    assert target.is_file()
    assert receipt.sha256 == hashlib.sha256(target.read_bytes()).hexdigest()
    assert receipt.mode == 0o600
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        OutputManager.write_safe(target, {"status": "FAIL"})


def test_output_manager_rejects_symlink_and_non_private_mode(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.write_text("existing", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="OUTPUT_SYMLINK_REJECTED"):
        OutputManager.write_safe(link, {"status": "PASS"})
    with pytest.raises(ValueError, match="OUTPUT_VERIFY_FAILED"):
        OutputManager.write_safe(tmp_path / "public.json", {"status": "PASS"}, mode=0o644)


def test_diagnostic_reporter_redacts_unapproved_environment_fields() -> None:
    reporter = DiagnosticReporter()
    reporter.environment = {
        "runtime": "TEST",
        "python_version": "3.11",
        "secret": "never-emit",
        "path": "/private/path",
    }
    reporter.start_phase("INPUT_READ")
    value = reporter.to_safe_dict()
    assert value.phase == "INPUT_READ"
    assert "secret" not in value.environment
    assert "path" not in value.environment
    assert "never-emit" not in json.dumps(value.environment)


def test_receipt_validator_accepts_only_safe_contract() -> None:
    assert ReceiptValidator.validate_runtime_receipt(valid_receipt()).value["status"] == "PASS"
    invalid = valid_receipt()
    invalid["environment"] = {"private_path": "/private"}
    with pytest.raises(ValueError, match="RECEIPT_FIELD_INVALID"):
        ReceiptValidator.validate_runtime_receipt(invalid)
    invalid = valid_receipt()
    invalid["gpu_started"] = True
    with pytest.raises(ValueError, match="RECEIPT_INVARIANT_FAILED"):
        ReceiptValidator.validate_runtime_receipt(invalid)


def test_receipt_file_verification_is_bounded_and_no_follow(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(valid_receipt()), encoding="utf-8")
    result = ReceiptValidator.verify_file(
        path, expected_schema="storyforge-hf-runtime-diagnostic-v1"
    )
    assert result.value["status"] == "PASS"
    with pytest.raises(ValueError, match="RECEIPT_SIZE_LIMIT_EXCEEDED"):
        ReceiptValidator.verify_file(
            path, expected_schema="storyforge-hf-runtime-diagnostic-v1", max_bytes=4
        )


def test_resource_guard_denies_visible_gpu() -> None:
    report = ResourceGuard.check_cpu_only(environ={"CUDA_VISIBLE_DEVICES": "0"})
    assert report.status == "FAIL"
    assert report.error_code == "CPU_PROFILE_GPU_VISIBLE"
    assert report.gpu_started is False
    assert report.training_performed is False


def test_resource_guard_rejects_gpu_accelerator_even_without_device_nodes() -> None:
    report = ResourceGuard.check_cpu_only(environ={"ACCELERATOR": "a100x4"})
    assert report.status == "FAIL"
    assert report.error_code == "CPU_PROFILE_GPU_VISIBLE"
    assert report.checks["accelerator_profile"] == "FAIL"


def test_resource_guard_accepts_explicit_cpu_accelerator() -> None:
    report = ResourceGuard.check_cpu_only(environ={"ACCELERATOR": "none"})
    assert report.status == "PASS"
    assert report.checks["accelerator_profile"] == "PASS"


def test_doctor_json_is_machine_readable_and_side_effect_bounded() -> None:
    env = dict(os.environ)
    env.pop("CUDA_VISIBLE_DEVICES", None)
    env.pop("NVIDIA_VISIBLE_DEVICES", None)
    env["STORYFORGE_RUNTIME_TEST"] = "1"
    source_root = str(Path(__file__).parents[1] / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_root if not existing_pythonpath else f"{source_root}{os.pathsep}{existing_pythonpath}"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "storyforge_dataset.hf_runtime",
            "doctor",
            "--profile",
            "cpu",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, (
        "doctor subprocess failed without exposing private input; "
        f"stderr={result.stderr!r}"
    )
    payload = json.loads(result.stdout)
    assert payload["schema"] == "storyforge-hf-runtime-diagnostic-v1"
    assert payload["private_values_emitted"] is False
    assert payload["gpu_started"] is False
    assert payload["training_performed"] is False
    assert payload["environment"]["runtime"] == "TEST"


def test_runtime_source_has_no_network_or_training_imports() -> None:
    root = Path(__file__).parents[1] / "src" / "storyforge_dataset" / "hf_runtime"
    forbidden = ("requests", "httpx", "transformers", "ms_swift", "huggingface_hub", "torch")
    for source in root.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        for token in forbidden:
            assert f"import {token}" not in text
            assert f"from {token}" not in text

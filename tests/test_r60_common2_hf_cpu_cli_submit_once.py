"""Synthetic-only regressions for the one-attempt HF CLI launcher."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts import r60_common2_hf_cpu_cli_submit_once as submit


KEY = "r60-common2-cpu2-20261112T054440Z-d5ad72dc667c"
JOB = "6af55450ab34849891aed739"


def test_no_execute_never_calls_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(submit.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("subprocess")))
    r = submit.submit(tmp_path / KEY, KEY)
    assert r["reason_code"] == "EXPLICIT_EXECUTE_REQUIRED"
    assert not (tmp_path / (KEY + ".cpu-submit-v2-attempted")).exists()


def install_mock(monkeypatch, stage: Path, *, job_exit: int = 0):
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(HfApi=lambda: object()))
    monkeypatch.setattr(submit.gate, "check", lambda api, s, k: {
        "status": "CPU2_HISTORY_PAGINATED_PASS__NO_JOB",
        "history_exhaustive": True, "matching_jobs": 0,
        "submit_marker": "ABSENT", "remote_output": "EMPTY_PASS",
    })
    argv = ["hf", "jobs", "run", "--attempts", "1", "--detach",
            "--name", "r60-cpu2-" + KEY, "--dry-run", submit.dry.IMAGE,
            "bash", "/input/common2/code/scripts/r60_common2_hf_cpu_worker_v2.sh"]
    monkeypatch.setattr(submit.dry, "prepare", lambda s, k, help_text: argv.copy())
    calls = []
    def run(args, **kwargs):
        calls.append(list(args))
        if args[:4] == ["hf", "jobs", "run", "--help"]:
            return SimpleNamespace(returncode=0, stdout="all flags", stderr="")
        if args[:3] == ["hf", "auth", "whoami"]:
            return SimpleNamespace(returncode=0, stdout="owner", stderr="")
        if "--dry-run" in args:
            return SimpleNamespace(returncode=0, stdout="Dry run successful", stderr="")
        assert "--attempts" in args and "--dry-run" not in args
        assert (stage.parent / (KEY + ".cpu-submit-v2-attempted")).exists()
        return SimpleNamespace(returncode=job_exit,
                               stdout=f"Job started with ID: {JOB}" if not job_exit else "",
                               stderr="FAIL" if job_exit else "")
    monkeypatch.setattr(submit.subprocess, "run", run)
    return calls


def test_submit_once_then_marker_blocks(monkeypatch, tmp_path):
    stage = tmp_path / KEY
    stage.mkdir()
    calls = install_mock(monkeypatch, stage)
    first = submit.submit(stage, KEY, execute=True)
    assert first["status"] == "CPU2_JOB_SUBMITTED__TRAIN_HOLD"
    assert first["job_id"] == JOB
    assert len(calls) == 4
    second = submit.submit(stage, KEY, execute=True)
    assert second["reason_code"] == "ATTEMPT_MARKER_PRESENT"
    assert len(calls) == 4


def test_failed_submission_keeps_marker_and_holds(monkeypatch, tmp_path):
    stage = tmp_path / KEY
    stage.mkdir()
    calls = install_mock(monkeypatch, stage, job_exit=1)
    first = submit.submit(stage, KEY, execute=True)
    assert first["status"] == "CPU2_SUBMISSION_UNCONFIRMED_HOLD"
    assert len(calls) == 4
    assert (tmp_path / (KEY + ".cpu-submit-v2-attempted")).exists()
    second = submit.submit(stage, KEY, execute=True)
    assert second["reason_code"] == "ATTEMPT_MARKER_PRESENT"
    assert len(calls) == 4


def test_final_gate_hold_cannot_mark_or_submit(monkeypatch, tmp_path):
    stage = tmp_path / KEY
    stage.mkdir()
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(HfApi=lambda: object()))
    monkeypatch.setattr(submit.gate, "check", lambda *a: {
        "status": "CPU2_FINAL_READ_ONLY_HOLD", "history_exhaustive": False,
    })
    monkeypatch.setattr(submit.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected")))
    r = submit.submit(stage, KEY, execute=True)
    assert r["reason_code"] == "FINAL_GATE_FAILED"
    assert not (tmp_path / (KEY + ".cpu-submit-v2-attempted")).exists()


def test_prepare_exception_has_safe_phase_and_no_marker(monkeypatch, tmp_path):
    stage = tmp_path / KEY
    stage.mkdir()
    install_mock(monkeypatch, stage)
    monkeypatch.setattr(submit.dry, "prepare", lambda *a: (_ for _ in ()).throw(ValueError("secret private body")))
    r = submit.submit(stage, KEY, execute=True)
    assert r["reason_code"] == "PRE_MARKER_CLI_PREPARE_VALUE_ERROR_HOLD"
    assert "secret" not in str(r)
    assert not (tmp_path / (KEY + ".cpu-submit-v2-attempted")).exists()


def test_post_marker_unknown_error_fails_closed(monkeypatch, tmp_path):
    stage = tmp_path / KEY
    stage.mkdir()
    install_mock(monkeypatch, stage)
    call = submit.subprocess.run
    def broken(args, **kwargs):
        if (args[:3] == ["hf", "jobs", "run"]
                and "--dry-run" not in args and "--help" not in args):
            raise RuntimeError("private confidential")
        return call(args, **kwargs)
    monkeypatch.setattr(submit.subprocess, "run", broken)
    r = submit.submit(stage, KEY, execute=True)
    assert r["status"] == "CPU2_SUBMISSION_UNCONFIRMED_HOLD"
    assert r["reason_code"] == "POST_MARKER_SUBMISSION_CALL_HOLD"
    assert "confidential" not in str(r)
    assert (tmp_path / (KEY + ".cpu-submit-v2-attempted")).exists()


def test_known_prepare_error_exposes_only_safe_code(monkeypatch, tmp_path):
    stage = tmp_path / KEY
    stage.mkdir()
    install_mock(monkeypatch, stage)
    monkeypatch.setattr(submit.dry, "prepare", lambda *a: (_ for _ in ()).throw(ValueError("HF_CLI_FLAGS_HOLD")))
    r = submit.submit(stage, KEY, execute=True)
    assert r["reason_code"] == "CLI_PREPARE_HF_CLI_FLAGS_HOLD"
    assert not (tmp_path / (KEY + ".cpu-submit-v2-attempted")).exists()

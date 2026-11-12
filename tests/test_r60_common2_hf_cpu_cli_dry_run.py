"""Synthetic HF CLI 2.4.0 dry-run tests: no network and no submission."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import r60_common2_hf_cpu_stage as staging
from scripts import r60_common2_hf_cpu_stage_v2 as v2
from scripts import r60_common2_hf_cpu_image_retry as retry
from scripts import r60_common2_hf_cpu_cli_dry_run as cli
from tests.test_r60_common2_hf_cpu_stage import fixture

KEY = "r60-common2-cpu2-20261112T090000Z-bbbbbbbbbbbb"
HELP = " ".join([*cli.NEEDED_OPTIONS, "--env", "IMAGE COMMAND..."])


def new_stage(tmp_path):
    inp = fixture(tmp_path)
    original = tmp_path / retry.RUN_KEY
    staging.stage(inp, original, retry.RUN_KEY)
    new = tmp_path / KEY
    v2.build(original, new, KEY)
    return original, new


def test_reuse_guard_and_cli_flags_without_submission(tmp_path):
    original, stage = new_stage(tmp_path)
    original_sha = (original / "SHA256SUMS.txt").read_bytes()
    argv = cli.prepare(stage, KEY, HELP)
    assert argv[:3] == ["hf", "jobs", "run"]
    assert argv.count("-v") == 2
    assert "--dry-run" in argv
    assert argv.index("--dry-run") < argv.index(cli.IMAGE)
    assert argv[argv.index(cli.IMAGE) + 1] == "bash"
    assert "--env" in argv
    assert argv[argv.index("--env") + 1] == f"STORYFORGE_R60_COMMON2_RUN_KEY={KEY}"
    assert "cpu-upgrade" in argv
    assert "--attempts" in argv and argv[argv.index("--attempts")+1] == "1"
    assert argv.count(":ro") == 0
    assert any(x.endswith(":/input/common2:ro") for x in argv)
    assert any(x.endswith(":/output:rw") for x in argv)
    assert (original / "SHA256SUMS.txt").read_bytes() == original_sha


def test_missing_dry_run_flag_fails_closed(tmp_path):
    _, stage = new_stage(tmp_path)
    with pytest.raises(ValueError, match="HF_CLI_FLAGS_HOLD"):
        cli.prepare(stage, KEY, HELP.replace("--dry-run", ""))


def test_old_key_rejected_even_with_valid_stage(tmp_path):
    _, stage = new_stage(tmp_path)
    with pytest.raises(ValueError, match="NEW_KEY_HOLD"):
        cli.prepare(stage, retry.RUN_KEY, HELP)


def test_mock_dry_run_never_sends_plain_job(tmp_path, monkeypatch):
    _, stage = new_stage(tmp_path)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv == ["hf", "jobs", "run", "--help"]:
            return SimpleNamespace(returncode=0, stdout=HELP, stderr="")
        assert "--dry-run" in argv
        assert "--submit" not in argv
        return SimpleNamespace(returncode=0,
                               stdout="Dry run resolved configuration (private synthetic data)",
                               stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = cli.run(stage, KEY, True)
    assert result["status"] == "CLI_DRY_RUN_PASS__NO_JOB"
    assert result["job_submission_calls"] == 0
    assert result["private_values_emitted"] is False
    assert len(calls) == 2


def test_mock_dry_run_failure_never_leaks_source(tmp_path, monkeypatch):
    _, stage = new_stage(tmp_path)
    def fake_run(argv, **kwargs):
        if "--help" in argv:
            return SimpleNamespace(returncode=0, stdout=HELP, stderr="")
        return SimpleNamespace(returncode=1, stdout="private-secret", stderr="private-secret")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = cli.run(stage, KEY, True)
    assert result["status"] == "CLI_PREFLIGHT_HOLD"
    assert result["reason_code"] == "HF_CLI_DRY_RUN_HOLD"
    assert "private-secret" not in repr(result)

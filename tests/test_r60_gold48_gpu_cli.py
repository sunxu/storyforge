"""Gold48 reuses existing HF CLI builder: CPU-only, mock dry-run, no Jobs."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts import r60_gold48_gpu_cli as cli

RUN = "gold48-owner-20261121-static-dryrun-01"
CODE = cli.BUCKET + cli.CODE_PREFIX + "/" + "a" * 40
ADAPTERS = {
    r: cli.BUCKET + f"reviewed-private-source/{r}/checkpoint"
    for r in cli.ROLE_ADAPTERS
}
HELP = "--namespace --name --flavor --timeout --attempts --detach -v --env --dry-run"


def test_gpu_shape_reuses_existing_argv_no_submit(monkeypatch):
    monkeypatch.setattr(cli.shared, "missing_job_cli_flags", lambda _s: [])
    monkeypatch.setattr(cli.shared, "use_documented_default_attempts",
                        lambda _s: False)
    argv = cli.job_dry_run_argv(
        run_id=RUN, role="r46_v02", code=CODE,
        adapters=ADAPTERS, help_text=HELP,
    )
    assert "--dry-run" in argv and "--flavor" in argv
    assert "submit" not in argv
    assert argv[argv.index(cli.IMAGE) + 1] == "bash"
    assert argv[-5:] == [
        "bash", "/input/code/scripts/r60_gold48_gpu_worker.sh",
        "check", RUN, "r46_v02",
    ]
    i = [argv[n + 1] for n, v in enumerate(argv[:-1]) if v == "-v"]
    assert len(i) == 6
    assert all(v.endswith(":ro") for v in i[:-1])
    assert i[-1] == (
        cli.BUCKET + cli.RESULT_PREFIX + "/" + RUN + ":/output:rw"
    )
    assert argv.count("--attempts") == 1


@pytest.mark.parametrize("bad,code", [
    ({**ADAPTERS, "r46_v02": ADAPTERS["r54_v03a"]}, "GOLD48_DUPLICATE_VOLUME_HOLD"),
    ({**ADAPTERS, "r46_v02": cli.BUCKET}, "GOLD48_SOURCE_PREFIX_HOLD"),
    ({**ADAPTERS, "r46_v02": "hf://buckets/other/bucket/path"}, "GOLD48_SOURCE_BUCKET_HOLD"),
    ({**ADAPTERS, "r46_v02": cli.BUCKET + cli.INPUT_PREFIX + "/" + RUN}, "GOLD48_DUPLICATE_VOLUME_HOLD"),
])
def test_gpu_shape_rejects_unreviewed_paths(bad, code):
    with pytest.raises(ValueError, match=code):
        cli._volumes(RUN, "base", CODE, bad)


def test_gpu_shape_rejects_missing_code_digest():
    with pytest.raises(ValueError, match="GOLD48_IMMUTABLE_CODE_PREFIX_HOLD"):
        cli._volumes(RUN, "base", cli.BUCKET + cli.CODE_PREFIX + "/latest", ADAPTERS)


def test_cli_shape_does_not_call_hf_or_gpu(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("NO_HF_CLI_OR_GPU")
    monkeypatch.setattr(cli.subprocess, "run", forbidden)
    rc = cli.main([
        "shape", "--run-id", RUN, "--role", "base",
        "--code-prefix", CODE,
        *[arg for role, value in ADAPTERS.items()
          for arg in ("--adapter-" + role.replace("_", "-"), value)],
    ])
    result = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert result["status"] == "GOLD48_GPU_COMMAND_SHAPE_PASS__NO_JOB"
    assert result["hf_jobs_submitted"] == 0
    assert result["owner_gpu_authorized"] is False


def test_cli_mock_dry_run_only_no_submission(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli.shared, "missing_job_cli_flags", lambda _s: [])
    monkeypatch.setattr(cli.shared, "use_documented_default_attempts",
                        lambda _s: False)
    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if argv == ["hf", "jobs", "run", "--help"]:
            return SimpleNamespace(returncode=0, stdout=HELP, stderr="")
        assert "--dry-run" in argv
        return SimpleNamespace(returncode=0, stdout="dry-run safe", stderr="")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    rc = cli.main([
        "dry-run", "--run-id", RUN, "--role", "r60_base336",
        "--code-prefix", CODE,
        *[arg for role, value in ADAPTERS.items()
          for arg in ("--adapter-" + role.replace("_", "-"), value)],
    ])
    result = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert len(calls) == 2
    assert result["status"] == "GOLD48_GPU_CLI_DRY_RUN_PASS__NO_JOB"
    assert result["private_stage_bytes_verified"] is False


def test_gpu_command_does_not_mount_removed_provider_handoff():
    inputs, output = cli._volumes(RUN, "base", CODE, ADAPTERS)
    assert len(inputs) == 5
    assert all("/input/provider" not in value for value in inputs)
    assert inputs[0].endswith(":/input/gold48:ro")
    assert inputs[1].endswith(":/input/code:ro")
    assert output.endswith(":/output:rw")


def _mock_owner_mac_ready(tmp_path, monkeypatch, *, submit_returncode=0):
    """All HF/remote operations fake. No real Job, GPU, or private source."""
    from pathlib import Path

    import huggingface_hub
    import r60_common2_hf_cpu_final_read_only as history

    parent = tmp_path / "mac-owner"
    parent.mkdir(mode=0o700)
    stage = parent / RUN
    stage.mkdir(mode=0o700)
    monkeypatch.setattr(huggingface_hub, "HfApi", lambda: object())
    monkeypatch.setattr(history, "walk_job_history",
                        lambda _api, _key: (0, 0))
    monkeypatch.setattr(cli, "_local_stage_sha",
                        lambda _stage, _run, _role: {"frozen_profile.json": "a" * 64})
    monkeypatch.setattr(cli, "_remote_file_sha",
                        lambda _api, _prefix, _names: None)
    monkeypatch.setattr(cli.shared, "missing_job_cli_flags", lambda _s: [])
    monkeypatch.setattr(cli.shared, "use_documented_default_attempts",
                        lambda _s: False)

    def remote_set(_api, prefix):
        if prefix.startswith(cli.RESULT_PREFIX):
            return set()
        if prefix.startswith(cli.CODE_PREFIX):
            return set(cli.CORE_CODE_FILES)
        raise AssertionError("unexpected remote listing")
    monkeypatch.setattr(cli.shared, "remote_set", remote_set)

    calls = []
    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        if argv[:3] == ["git", "-C", str(cli.ROOT)]:
            return SimpleNamespace(returncode=0, stdout="a" * 40 + "\n", stderr="")
        if argv[:3] == ["hf", "buckets", "cp"]:
            name = argv[3].split("/" + cli.CODE_PREFIX + "/")[-1]
            assert name.startswith("a" * 40 + "/")
            rel = name[41:]
            Path(argv[4]).write_bytes((cli.ROOT / rel).read_bytes())
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if argv == ["hf", "jobs", "run", "--help"]:
            return SimpleNamespace(returncode=0, stdout=HELP, stderr="")
        if argv == ["hf", "auth", "whoami"]:
            return SimpleNamespace(returncode=0, stdout="safe", stderr="")
        if argv[:3] == ["hf", "jobs", "run"]:
            if "--dry-run" in argv:
                assert "execute" in argv and "--dry-run" in argv
                return SimpleNamespace(returncode=0, stdout="dry-run safe", stderr="")
            return SimpleNamespace(
                returncode=submit_returncode,
                stdout="Job 6b00ca46efaf5e14f4b3f8ca" if submit_returncode == 0 else "",
                stderr="",
            )
        raise AssertionError("unexpected subprocess call")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    return stage, calls


def test_ready_checks_existing_mac_history_and_hashes_no_submit(
    tmp_path, monkeypatch,
):
    stage, calls = _mock_owner_mac_ready(tmp_path, monkeypatch)
    status = cli._ready_or_submit(
        action="ready", run_id=RUN, role="base", code=CODE,
        adapters=ADAPTERS, stage=stage, allow_execute=False,
    )
    assert status["status"] == "GOLD48_GPU_MAC_STAGE_CODE_AND_CLI_READY__NO_JOB"
    assert status["hf_jobs_submitted"] == 0
    assert status["private_stage_bytes_verified"] is True
    assert status["code_bundle_sha_verified"] is True
    assert not list(stage.parent.glob("*.gold48-gpu-submit.private.json"))
    assert all(
        "--dry-run" in call
        for call in calls if call[:3] == ["hf", "jobs", "run"]
    )


def test_submit_must_be_explicit_creates_marker_before_billing_and_no_retry(
    tmp_path, monkeypatch,
):
    stage, calls = _mock_owner_mac_ready(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="GOLD48_EXPLICIT_OWNER_GPU_EXECUTE_REQUIRED_HOLD"):
        cli._ready_or_submit(
            action="submit", run_id=RUN, role="base", code=CODE,
            adapters=ADAPTERS, stage=stage, allow_execute=False,
        )
    assert calls == []
    result = cli._ready_or_submit(
        action="submit", run_id=RUN, role="base", code=CODE,
        adapters=ADAPTERS, stage=stage, allow_execute=True,
    )
    assert result["status"] == "GOLD48_GPU_SUBMITTED__OWNER_DOWNLOAD_AUDIT_PENDING"
    assert result["job_id"] == "6b00ca46efaf5e14f4b3f8ca"
    assert result["hf_jobs_submitted"] == 1
    marker = stage.parent / (RUN + ".gold48-gpu-submit.private.json")
    assert marker.is_file() and marker.stat().st_mode & 0o777 == 0o600
    import json
    assert json.loads(marker.read_text())["status"] == "ATTEMPTED__NO_AUTO_RETRY"
    billed = [call for call in calls
              if call[:3] == ["hf", "jobs", "run"] and "--dry-run" not in call]
    assert len(billed) == 1
    with pytest.raises(ValueError, match="GOLD48_GPU_ALREADY_ATTEMPTED_NO_RETRY_HOLD"):
        cli._ready_or_submit(
            action="submit", run_id=RUN, role="base", code=CODE,
            adapters=ADAPTERS, stage=stage, allow_execute=True,
        )
    assert len([call for call in calls if
                call[:3] == ["hf", "jobs", "run"] and "--dry-run" not in call]) == 1


def test_submit_unconfirmed_keeps_marker_and_never_retries(tmp_path, monkeypatch):
    stage, calls = _mock_owner_mac_ready(
        tmp_path, monkeypatch, submit_returncode=1,
    )
    report = cli._ready_or_submit(
        action="submit", run_id=RUN, role="base", code=CODE,
        adapters=ADAPTERS, stage=stage, allow_execute=True,
    )
    assert report["status"] == "GOLD48_GPU_SUBMISSION_UNCONFIRMED_NO_RETRY"
    assert report["hf_jobs_submitted"] is None
    assert report["gpu_started"] is None
    assert (stage.parent / (RUN + ".gold48-gpu-submit.private.json")).exists()
    assert len([call for call in calls if
                call[:3] == ["hf", "jobs", "run"] and "--dry-run" not in call]) == 1


def test_gpu_bootstrap_is_only_a_hash_locked_preflight_not_another_submitter():
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    shell = root / "scripts/r60_gold48_gpu_worker.sh"
    syntax = subprocess.run(
        ["bash", "-n", str(shell)],
        capture_output=True, text=True, check=False,
    )
    assert syntax.returncode == 0
    text = shell.read_text()
    assert text.index('"$ENTRY" check') < text.index("--require-hashes")
    assert text.index("--require-hashes") < text.index('"$ENTRY" execute')
    assert "pip check" in text
    assert "/input/provider" not in text
    assert "hf jobs run" not in text
    assert "hf buckets cp" not in text

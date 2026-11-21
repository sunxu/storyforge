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

"""Tests of the isolated Gold48 two-Job probe. No HF submission or GPU."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.r60_gold48_ledger_atomic_cpu_probe import (
    ProbeHold, main, run,
)


@pytest.fixture
def isolated_mount(tmp_path, monkeypatch):
    root = tmp_path / "synthetic-bucket-mount"
    root.mkdir(mode=0o700)
    original = Path.is_mount
    monkeypatch.setattr(
        Path, "is_mount",
        lambda self: self == root or original(self),
    )
    original_read = Path.read_text

    def fake_read(self, *args, **kwargs):
        if str(self) == "/proc/self/mountinfo":
            return "9 1 0:12 / " + str(root) + " rw,relatime - fuse.fake fake rw\\n"
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read)
    source = (
        Path(__file__).resolve().parents[1]
        / "src/storyforge_dataset/hf_runtime/outputs.py"
    )
    return root, source


def test_reuses_pinned_outputmanager_then_checks_same_marker_across_phases(
    isolated_mount,
):
    root, source = isolated_mount
    key = "gold48-synthetic-12345678"
    write = run(phase="write", root=root, source=source, probe_id=key)
    assert write["status"] == "ATOMIC_CREATE_ONLY_CPU_PASS__SECOND_JOB_PENDING"
    assert write["cross_job_persistence_verified"] is False
    assert write["gpu_started"] is False
    assert len(list(root.iterdir())) == 1
    verify = run(phase="verify", root=root, source=source, probe_id=key)
    assert verify["status"] == "ATOMIC_CREATE_ONLY_AND_CROSS_JOB_PERSISTENCE_CPU_PASS"
    assert verify["cross_job_persistence_verified"] is True
    assert verify["marker_sha256"] == write["marker_sha256"]
    assert len(list(root.iterdir())) == 1
    with pytest.raises(ProbeHold, match="SYNTHETIC_PROBE_ALREADY_EXISTS_HOLD"):
        run(phase="write", root=root, source=source, probe_id=key)


def test_missing_marker_and_unpinned_source_fail_closed(isolated_mount, tmp_path):
    root, source = isolated_mount
    key = "gold48-synthetic-abcdefgh"
    with pytest.raises(ProbeHold, match="CROSS_JOB_MARKER_MISSING_HOLD"):
        run(phase="verify", root=root, source=source, probe_id=key)
    forged = tmp_path / "outputs.py"
    forged.write_bytes(source.read_bytes() + b"\\n# unreviewed change")
    with pytest.raises(ProbeHold, match="PINNED_OUTPUT_MODULE_SHA_HOLD"):
        run(phase="write", root=root, source=forged, probe_id=key)
    assert list(root.iterdir()) == []


def test_direct_mount_and_permission_are_mandatory(isolated_mount, monkeypatch):
    root, source = isolated_mount
    key = "gold48-synthetic-abcdefgh"
    root.chmod(0o755)
    with pytest.raises(ProbeHold, match="MOUNT_DIRECTORY_MODE_0700_HOLD"):
        run(phase="write", root=root, source=source, probe_id=key)
    root.chmod(0o700)
    monkeypatch.setattr(Path, "is_mount", lambda _self: False)
    with pytest.raises(ProbeHold, match="DIRECT_PERSISTENT_MOUNT_REQUIRED_HOLD"):
        run(phase="write", root=root, source=source, probe_id=key)


def test_safe_cli_holds_on_invalid_probe_id(isolated_mount, capsys):
    root, source = isolated_mount
    rc = main(["--phase", "write", "--root", str(root),
               "--source", str(source), "--probe-id", "../escape"])
    assert rc == 2
    safe = json.loads(capsys.readouterr().out)
    assert safe["reason_code"] == "PROBE_ID_FORMAT_HOLD"
    assert safe["gpu_started"] is False
    assert safe["model_calls"] == 0

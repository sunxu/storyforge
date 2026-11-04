"""Linux/macOS filesystem edge tests using synthetic SAFE receipts only."""

from __future__ import annotations

import errno
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import storyforge_dataset.hf_runtime.outputs as outputs_module
from storyforge_dataset.hf_runtime import OutputManager


def _temporary_outputs(root: Path) -> list[Path]:
    return sorted(root.glob(".storyforge-tmp-*"))


def test_concurrent_create_only_publication_has_exactly_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "concurrent-safe.json"
    barrier = threading.Barrier(2)
    original_link = outputs_module.os.link

    def synchronized_link(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        follow_symlinks: bool = True,
    ) -> None:
        barrier.wait(timeout=5)
        original_link(source, target, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(outputs_module.os, "link", synchronized_link)

    def publish(value: int) -> str:
        try:
            OutputManager.write_safe(destination, {"winner": value})
            return "PASS"
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, (1, 2)))

    assert results.count("PASS") == 1
    assert results.count("OUTPUT_ALREADY_EXISTS") == 1
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["winner"] in {1, 2}
    assert destination.stat().st_mode & 0o777 == 0o600
    assert _temporary_outputs(tmp_path) == []


def test_enospc_during_write_never_publishes_partial_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "enospc-safe.json"
    original_write = outputs_module.os.write
    calls = 0

    def fail_after_partial_write(fd: int, data: bytes | memoryview) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_write(fd, data[: max(1, len(data) // 2)])
        raise OSError(errno.ENOSPC, "synthetic disk full")

    monkeypatch.setattr(outputs_module.os, "write", fail_after_partial_write)
    with pytest.raises(ValueError, match="OUTPUT_WRITE_FAILED"):
        OutputManager.write_safe(destination, {"synthetic": "enospc"})

    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


def test_file_fsync_failure_cleans_temporary_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "file-fsync-safe.json"

    def fail_fsync(_fd: int) -> None:
        raise OSError(errno.EIO, "synthetic fsync failure")

    monkeypatch.setattr(outputs_module.os, "fsync", fail_fsync)
    with pytest.raises(ValueError, match="OUTPUT_FSYNC_FAILED"):
        OutputManager.write_safe(destination, {"synthetic": "file-fsync"})

    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


def test_directory_fsync_failure_removes_uncommitted_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "directory-fsync-safe.json"
    original_fsync = outputs_module.os.fsync
    calls = 0

    def fail_second_fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(errno.EIO, "synthetic directory fsync failure")
        original_fsync(fd)

    monkeypatch.setattr(outputs_module.os, "fsync", fail_second_fsync)
    with pytest.raises(ValueError, match="OUTPUT_FSYNC_FAILED"):
        OutputManager.write_safe(destination, {"synthetic": "directory-fsync"})

    assert calls == 2
    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


def test_hardlink_and_noreplace_rename_unsupported_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "no-atomic-publish-safe.json"

    def unsupported(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EOPNOTSUPP, "synthetic filesystem limitation")

    monkeypatch.setattr(outputs_module.os, "link", unsupported)
    monkeypatch.setattr(outputs_module.OutputManager, "_rename_noreplace", unsupported)
    with pytest.raises(ValueError, match="OUTPUT_ATOMIC_PUBLISH_UNSUPPORTED"):
        OutputManager.write_safe(destination, {"synthetic": "no-atomic-publish"})

    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="renameat2 is Linux-specific")
def test_hardlink_unsupported_falls_back_to_atomic_noreplace_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "renameat2-safe.json"

    def unsupported_link(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EOPNOTSUPP, "synthetic hardlink limitation")

    monkeypatch.setattr(outputs_module.os, "link", unsupported_link)
    receipt = OutputManager.write_safe(destination, {"synthetic": "renameat2"})
    assert destination.is_file()
    assert receipt.sha256
    assert destination.stat().st_mode & 0o777 == 0o600
    assert _temporary_outputs(tmp_path) == []
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        OutputManager.write_safe(destination, {"synthetic": "must-not-overwrite"})


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="renameat2 is Linux-specific")
def test_concurrent_renameat2_publication_has_exactly_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "concurrent-renameat2-safe.json"

    def unsupported_link(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EOPNOTSUPP, "synthetic hardlink limitation")

    monkeypatch.setattr(outputs_module.os, "link", unsupported_link)

    def publish(value: int) -> str:
        try:
            OutputManager.write_safe(destination, {"winner": value})
            return "PASS"
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, (1, 2)))

    assert results.count("PASS") == 1
    assert results.count("OUTPUT_ALREADY_EXISTS") == 1
    assert json.loads(destination.read_text(encoding="utf-8"))["winner"] in {1, 2}
    assert _temporary_outputs(tmp_path) == []


def test_cleanup_failure_is_reported_instead_of_silently_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "cleanup-safe.json"
    original_unlink = Path.unlink

    def fail_write(_fd: int, _data: bytes | memoryview) -> int:
        raise OSError(errno.ENOSPC, "synthetic disk full")

    def fail_temp_cleanup(path: Path, *args: object, **kwargs: object) -> None:
        if path.name.startswith(".storyforge-tmp-"):
            raise OSError(errno.EACCES, "synthetic cleanup denied")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(outputs_module.os, "write", fail_write)
    monkeypatch.setattr(Path, "unlink", fail_temp_cleanup)
    with pytest.raises(ValueError, match="OUTPUT_CLEANUP_FAILED"):
        OutputManager.write_safe(destination, {"synthetic": "cleanup"})

    monkeypatch.setattr(Path, "unlink", original_unlink)
    assert not destination.exists()
    leftovers = _temporary_outputs(tmp_path)
    assert len(leftovers) == 1
    leftovers[0].unlink()

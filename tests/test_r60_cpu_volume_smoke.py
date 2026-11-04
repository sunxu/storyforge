"""Synthetic tests for the owner-invoked R60 HF volume smoke adapter."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.r60_hf_runtime import r60_cpu_smoke as smoke


def _fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    output_root.mkdir()
    data = b"".join(
        json.dumps(
            {"schema": smoke.INPUT_SCHEMA, "case": f"synthetic-{index:03d}"},
            separators=(",", ":"),
        ).encode() + b"\n"
        for index in range(1, 4)
    )
    (input_root / "synthetic.jsonl").write_bytes(data)
    return input_root, output_root, hashlib.sha256(data).hexdigest()


def test_read_only_mount_check_requires_mount_flag_and_denied_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ro"
    root.mkdir()
    monkeypatch.setattr(smoke.os, "statvfs", lambda _path: SimpleNamespace(f_flag=1))
    original_open = smoke.os.open

    def deny_create(path: str | os.PathLike[str], flags: int, mode: int = 0o777) -> int:
        if ".storyforge-r60-ro-probe-" in str(path):
            raise OSError(smoke.errno.EROFS, "synthetic readonly")
        return original_open(path, flags, mode)

    monkeypatch.setattr(smoke.os, "open", deny_create)
    assert smoke._read_only_mount_check(root) == {
        "mount_readonly_flag": "PASS", "create_denied": "PASS"
    }


def test_read_only_mount_check_fails_when_mount_flag_is_rw(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "rw"
    root.mkdir()
    monkeypatch.setattr(smoke.os, "statvfs", lambda _path: SimpleNamespace(f_flag=0))
    original_open = smoke.os.open

    def deny_create(path: str | os.PathLike[str], flags: int, mode: int = 0o777) -> int:
        if ".storyforge-r60-ro-probe-" in str(path):
            raise OSError(smoke.errno.EROFS, "synthetic denied")
        return original_open(path, flags, mode)

    monkeypatch.setattr(smoke.os, "open", deny_create)
    assert smoke._read_only_mount_check(root)["mount_readonly_flag"] == "FAIL"


def test_success_writes_create_only_safe_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root, output_root, digest = _fixture(tmp_path)
    monkeypatch.setattr(
        smoke, "_read_only_mount_check",
        lambda _root: {"mount_readonly_flag": "PASS", "create_denied": "PASS"},
    )
    result = smoke.run_smoke(
        input_root=input_root, input_name="synthetic.jsonl", output_root=output_root,
        expected_sha256=digest, expected_records=3,
    )
    assert result["status"] == "PASS"
    receipt = output_root / smoke.REPORT_NAME
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == smoke.SCHEMA
    assert payload["input"]["sha256"] == digest
    assert payload["input"]["records"] == 3
    assert payload["private_values_emitted"] is False
    assert payload["gpu_started"] is False
    assert payload["training_performed"] is False
    assert result["report_sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest()


def test_existing_report_is_never_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root, output_root, digest = _fixture(tmp_path)
    monkeypatch.setattr(
        smoke, "_read_only_mount_check",
        lambda _root: {"mount_readonly_flag": "PASS", "create_denied": "PASS"},
    )
    target = output_root / smoke.REPORT_NAME
    target.write_text("owner-existing", encoding="utf-8")
    with pytest.raises(smoke.SmokeFailure, match="OUTPUT_ALREADY_EXISTS"):
        smoke.run_smoke(
            input_root=input_root, input_name="synthetic.jsonl", output_root=output_root,
            expected_sha256=digest, expected_records=3,
        )
    assert target.read_text(encoding="utf-8") == "owner-existing"


def test_digest_mismatch_fails_without_emitting_input_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root, output_root, _digest = _fixture(tmp_path)
    monkeypatch.setattr(
        smoke, "_read_only_mount_check",
        lambda _root: {"mount_readonly_flag": "PASS", "create_denied": "PASS"},
    )
    with pytest.raises(smoke.SmokeFailure) as captured:
        smoke.run_smoke(
            input_root=input_root, input_name="synthetic.jsonl", output_root=output_root,
            expected_sha256="0" * 64, expected_records=3,
        )
    assert captured.value.code == "INPUT_SHA256_MISMATCH"
    assert "synthetic-001" not in json.dumps(captured.value.report)


@pytest.mark.parametrize("bad_record", [
    {"schema": smoke.INPUT_SCHEMA, "case": "real-user-value"},
    {"schema": smoke.INPUT_SCHEMA, "case": "synthetic-001", "extra": "no"},
    {"schema": "other", "case": "synthetic-001"},
])
def test_non_synthetic_or_extra_fields_rejected(bad_record: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        smoke._validate_synthetic_records([bad_record], 1)


def test_wrong_record_count_rejected() -> None:
    with pytest.raises(ValueError, match="SMOKE_RECORD_COUNT_MISMATCH"):
        smoke._validate_synthetic_records([], 1)


def test_input_name_and_digest_are_strict(tmp_path: Path) -> None:
    input_root, output_root, digest = _fixture(tmp_path)
    with pytest.raises(ValueError, match="SMOKE_INPUT_NAME_INVALID"):
        smoke.run_smoke(
            input_root=input_root, input_name="../escape", output_root=output_root,
            expected_sha256=digest, expected_records=3,
        )
    with pytest.raises(ValueError, match="SMOKE_EXPECTED_SHA256_INVALID"):
        smoke.run_smoke(
            input_root=input_root, input_name="synthetic.jsonl", output_root=output_root,
            expected_sha256="not-a-digest", expected_records=3,
        )

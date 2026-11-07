"""Synthetic, no-private-data checks for R60 P1 SAFE triage."""
from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from experiments.r58_quality import r60_p1_case_triage as triage


def test_digest_is_deterministic():
    assert triage.digest(b"synthetic") == triage.digest(b"synthetic")
    assert triage.digest(b"synthetic") != triage.digest(b"synthetic-other")


def test_private_read_rejects_relative_path(tmp_path):
    with pytest.raises(triage.Hold, match="PRIVATE_INPUT_PATH_INVALID"):
        triage.read_private(Path(tmp_path.name))


def test_private_read_rejects_relaxed_mode(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    item = private / "fake.json"
    item.write_text("{}")
    item.chmod(0o644)
    with pytest.raises(triage.Hold, match="PRIVATE_INPUT_MODE_OR_SIZE_INVALID"):
        triage.read_private(item)


def test_private_read_accepts_owner_only_mode(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    item = private / "fake.json"
    item.write_text("{}")
    item.chmod(0o600)
    assert triage.read_private(item) == b"{}"


def test_triage_rejects_bad_pin_before_parsing():
    class Pins:
        A_SHA = "x"
        B_SHA = "y"
        EX_SHA = "z"
        PACKETS_SHA = "w"

    data = {key: b"synthetic" for key in (
        "reviewer_a", "reviewer_b", "exclusions", "source_packets",
        "source_locators", "source_safe", "evidence_slots",
    )}
    with pytest.raises(triage.Hold, match="FROZEN_PIN_MISMATCH"):
        triage.triage(data, object(), Pins)


def test_safe_file_serialization(tmp_path):
    target = tmp_path / "receipt.json"
    triage.save_new(target, {"status": "P1_HOLD", "private_values_emitted": False})
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert json.loads(target.read_text())["private_values_emitted"] is False
    with pytest.raises(FileExistsError):
        triage.save_new(target, {})

"""Gold48 Owner scoped freeze: synthetic-only approval, integrity, and no overwrite."""
from __future__ import annotations

import importlib.util
import json
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from r60_p2_gold48_owner_freeze_packet_cpu import SAFE as READY_SCHEMA
from r60_p2_gold48_owner_freeze_packet_cpu import make_packet
from test_r60_p2_gold48_candidate_preflight_cpu import private_file
from test_r60_p2_gold48_owner_freeze_packet_cpu import fixtures

spec = importlib.util.spec_from_file_location(
    "r60_p2_gold48_owner_scoped_freeze_cpu",
    ROOT / "scripts/r60_p2_gold48_owner_scoped_freeze_cpu.py",
)
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


def ready_fixture(private_root):
    inputs = fixtures(private_root)
    packet, receipt = make_packet(*inputs)
    folder = private_root / "readiness"
    folder.mkdir(mode=0o700)
    for name, document in (
        (freeze.PACKET_NAME, packet),
        (freeze.READY_NAME, receipt),
    ):
        target = folder / name
        target.write_bytes(freeze.canonical(document) + b"\n")
        target.chmod(0o600)
    return (*inputs[:5], folder, inputs[5])


def test_owner_explicit_approval_freezes_only_scoped_dataset(tmp_path):
    inputs = ready_fixture(tmp_path)
    frozen, safe = freeze.build_freeze(*inputs, approved=True)
    assert safe["status"] == freeze.SAFE_STATUS
    assert safe["owner_gold48_freeze"] is True
    assert safe["case_count"] == 48
    assert safe["sensitivity_analysis_count"] == 42
    assert safe["excluded_sensitivity_count"] == 6
    assert safe["original_reference_hashes_frozen"] == 48
    assert safe["stage_and_hf_cpu_receipt_frozen_by_sha"] is True
    assert safe["historical_actual_sent_prompt_verified"] is False
    assert safe["full_protected_universe_independence_verified"] is False
    assert safe["model_generation_authorized"] is False
    assert safe["model_generation_profile_frozen"] is False
    assert frozen["original_reference_count"] == 48
    assert frozen["owner_approval"]["kind"] == (
        "EXPLICIT_OWNER_APPROVAL_IN_CURRENT_CONVERSATION"
    )
    assert frozen["status"] == freeze.STATUS
    assert frozen["session_count"] == 48  # synthetic candidate fixture only
    assert len(frozen["cases_PRIVATE"]) == 48
    assert sum(c["exclude_from_42_sensitivity"] for c in frozen["cases_PRIVATE"]) == 6
    raw = json.dumps(frozen)
    assert "synthetic-story" not in raw
    assert "original response" not in raw
    assert "historical assistant" not in raw
    assert READY_SCHEMA not in json.dumps(safe)


def test_missing_explicit_approval_holds_without_freeze(tmp_path):
    inputs = ready_fixture(tmp_path)
    with pytest.raises(freeze.Hold, match="EXPLICIT_OWNER_SCOPED_APPROVAL_REQUIRED_HOLD"):
        freeze.build_freeze(*inputs, approved=False)


def test_changed_readiness_packet_holds(tmp_path):
    inputs = ready_fixture(tmp_path)
    path = inputs[5] / freeze.PACKET_NAME
    data = json.loads(path.read_text())
    data["cases_PRIVATE"][0]["exclude_from_42_sensitivity"] = True
    private_file(path, data)
    with pytest.raises(freeze.Hold, match="OWNER_READINESS_SOURCE_VERSION_DRIFT_HOLD"):
        freeze.build_freeze(*inputs, approved=True)


def test_changed_historical_reply_after_ready_holds(tmp_path):
    inputs = ready_fixture(tmp_path)
    path = inputs[0] / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json"
    obj = json.loads(path.read_text())
    obj["cases_PRIVATE"][0]["original_reply_PRIVATE"] = "different text"
    private_file(path, obj)
    with pytest.raises(ValueError, match="SHA_BINDING"):
        freeze.build_freeze(*inputs, approved=True)


def test_create_only_no_reuse_of_existing_output_directory(tmp_path, monkeypatch):
    home = tmp_path / "home"
    root = home / ".local/share/storyforge/r60/private"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    inputs = ready_fixture(root)
    output = root / "scoped-freeze"
    monkeypatch.setattr(Path, "home", lambda: home)
    args = SimpleNamespace(
        candidate_dir=inputs[0],
        binding_dir=inputs[1],
        draft_dir=inputs[2],
        stage_dir=inputs[3],
        receipt_dir=inputs[4],
        packet_dir=inputs[5],
        run_key=inputs[6],
        output_dir=output,
        owner_approved_scoped_freeze=True,
    )
    receipt = freeze.run(args)
    assert receipt["status"] == freeze.SAFE_STATUS
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    manifest = output / freeze.MANIFEST_NAME
    assert manifest.exists()
    assert stat.S_IMODE(manifest.stat().st_mode) == 0o600
    assert stat.S_IMODE((output / freeze.SAFE_NAME).stat().st_mode) == 0o600
    with pytest.raises(freeze.Hold, match="OWNER_FREEZE_PATH_SCOPE_HOLD"):
        freeze.run(args)


def test_run_without_approval_creates_nothing(tmp_path):
    args = SimpleNamespace(owner_approved_scoped_freeze=False)
    with pytest.raises(freeze.Hold, match="EXPLICIT_OWNER_SCOPED_APPROVAL_REQUIRED_HOLD"):
        freeze.run(args)

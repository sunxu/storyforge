"""Gold48 reviewed GPU thin entry: CPU-only mocked stage and no GPU."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import r60_gold48_gpu_worker_entry as entry
from storyforge_dataset.generation_eval.worker import WorkerError


def stage(tmp_path, monkeypatch):
    root = tmp_path / "gold48"
    root.mkdir()
    monkeypatch.setattr(entry, "RO_STAGE", root)
    original_mount = Path.is_mount
    original_read = Path.read_text
    monkeypatch.setattr(Path, "is_mount",
                        lambda self: self == root or original_mount(self))

    def mountinfo(self, *args, **kwargs):
        if str(self) == "/proc/self/mountinfo":
            return f"1 0 0:2 / {root} ro,relatime - fuse.hf-bucket hf ro\n"
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mountinfo)
    current_frozen = (
        Path(__file__).resolve().parents[1]
        / "experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json"
    )
    input_data = b'{"sample_id":"synthetic","messages":[]}\n'
    input_sha = hashlib.sha256(input_data).hexdigest()
    contents = {
        "frozen_profile.json": current_frozen.read_bytes(),
        "owner_authorization.private.json": json.dumps({
            "schema": entry.APPROVAL_SCHEMA,
            "approval_mode": entry.APPROVAL_MODE,
            "payload": {
            "run_id": "gold48-owner-20261121-test-001",
            "model_role": "base",
            "output_directory": "/tmp/storyforge-gold48-private/outputs/"
                                "gold48-owner-20261121-test-001",
            "output_filename": "base.private.json",
        }}).encode(),
        "input_manifest.private.json": json.dumps({
            "schema": "storyforge_r60_gold48_generation_input_manifest_private_v1",
            "record_count": 48, "sha256": input_sha,
        }).encode(),
        "input.private.jsonl": input_data,
    }
    for name in entry.STAGED:
        if name not in contents:
            contents[name] = b"synthetic-nonempty"
        (root / name).write_bytes(contents[name])
    # This test is about staging shape and order; the runtime lock is verified
    # separately by the already-pinned hash CI, not simulated here.
    monkeypatch.setattr(entry.gate, "FROZEN_RUNTIME_LOCK_SHA256",
                        hashlib.sha256(b"synthetic-nonempty").hexdigest())
    return root


def test_fixed_ro_bundle_no_gpu_with_plain_mac_approval(tmp_path, monkeypatch):
    root = stage(tmp_path, monkeypatch)
    status = entry.run(root, "gold48-owner-20261121-test-001", "base",
                       execute=False)
    assert status["status"] == "GOLD48_FIXED_RO_STAGE_VERIFIED__NO_GPU"
    assert status["model_calls"] == 0
    # Mac-approved check does not need Ed25519 private/public keys.
    assert "owner_public.pem" not in entry.STAGED
    assert "provider_public.pem" not in entry.STAGED
    assert "token_preflight.private.json" not in entry.STAGED
    assert len(entry.STAGED) == 11


def test_extra_stage_file_fails_before_gpu(tmp_path, monkeypatch):
    root = stage(tmp_path, monkeypatch)
    (root / "historical_original_answer.private.json").write_bytes(b"NO")
    with pytest.raises(WorkerError, match="GOLD48_ENTRY_EXACT_INPUT_FILESET_HOLD"):
        entry.run(root, "gold48-owner-20261121-test-001", "base",
                  execute=False)


def test_corrupted_input_sha_fails_before_gpu(tmp_path, monkeypatch):
    root = stage(tmp_path, monkeypatch)
    (root / "input.private.jsonl").write_bytes(b"tamper")
    with pytest.raises(WorkerError):
        entry.run(root, "gold48-owner-20261121-test-001", "base",
                  execute=False)


def test_safe_progress_jsonl_has_no_private_content_or_untrusted_keys(capsys):
    start = entry.time.monotonic()
    entry._safe_progress("r46_v02", start, "case_completed", {
        "case_number": 3,
        "completed": 3,
        "total": 48,
        "percent": 6.25,
        "case_elapsed_seconds": 1.25,
        "eta_seconds": 56.25,
        "finish_reason": "eos",
        "sample_id": "secret-case-id",
        "prompt": "secret-input-text",
        "answer": "secret-model-output",
        "input_sha256": "a" * 64,
    })
    safe = json.loads(capsys.readouterr().out)
    assert safe["schema"] == "storyforge_gold48_gpu_progress_safe_v1"
    assert safe["event"] == "case_completed"
    assert safe["case_number"] == 3
    assert safe["completed"] == 3
    assert safe["total"] == 48
    assert safe["finish_reason"] == "eos"
    assert safe["private_values_emitted"] is False
    assert "timestamp_utc" in safe and "elapsed_seconds" in safe
    assert not (set(safe) & {"sample_id", "prompt", "answer", "input_sha256"})
    with pytest.raises(WorkerError, match="GOLD48_PROGRESS_EVENT_INVALID"):
        entry._safe_progress("r46_v02", start, "private-debug", {
            "answer": "secret-model-output",
        })
    assert capsys.readouterr().out == ""


def test_cli_execute_requires_explicit_scope_and_safe_json(capsys):
    exit_code = entry.main([
        "execute", "--run-id", "gold48-owner-20261121-test-001",
        "--model-role", "base",
    ])
    assert exit_code == 42
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "HOLD"
    assert value["gpu_started"] is None
    assert value["private_values_emitted"] is False


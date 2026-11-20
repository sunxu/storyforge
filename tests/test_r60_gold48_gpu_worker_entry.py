"""Gold48 reviewed GPU thin entry: CPU-only mocked stage and no GPU."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

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
        "owner_authorization.private.json": json.dumps({"payload": {
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
        "token_preflight.private.json": json.dumps({
            "schema": "storyforge_r60_p2_gold48_token_preflight_private_v1",
            "tokenizer_revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
            "chat_template_sha256_PRIVATE": "a" * 64,
        }).encode(),
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


def test_fixed_ro_bundle_no_gpu_without_production_keys(tmp_path, monkeypatch):
    root = stage(tmp_path, monkeypatch)
    status = entry.run(root, "gold48-owner-20261121-test-001", "base",
                       execute=False)
    assert status["status"] == "GOLD48_FIXED_RO_STAGE_VERIFIED__NO_GPU"
    assert status["model_calls"] == 0
    with pytest.raises(WorkerError, match="GOLD48_INDEPENDENT_TRUST_ANCHORS_NOT_PINNED_HOLD"):
        entry.run(root, "gold48-owner-20261121-test-001", "base",
                  execute=True)


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

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


def _provider_handoff(tmp_path, monkeypatch, job_id="6b00ca46efaf5e14f4b3f8ca"):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub = tmp_path / "provider_public.pem"
    pub.write_bytes(public)
    pub.chmod(0o600)
    monkeypatch.setattr(
        entry.gate, "PROVIDER_TRUSTED_PUBLIC_PEM_SHA256",
        hashlib.sha256(public).hexdigest(),
    )
    monkeypatch.setenv("JOB_ID", job_id)
    source = tmp_path / "provider-handoff"
    source.mkdir()
    monkeypatch.setattr(entry, "PROVIDER_MOUNT", source)
    pending = {
        "schema": "storyforge_r60_gold48_provider_handoff_pending_v1",
        "run_id": "gold48-owner-20261121-test-001",
        "model_role": "base",
    }
    (source / entry.PENDING_NAME).write_text(json.dumps(pending))
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    original_mount = Path.is_mount
    original_read = Path.read_text
    monkeypatch.setattr(Path, "is_mount",
                        lambda self: self == source or original_mount(self))

    def read_mountinfo(self, *args, **kwargs):
        if str(self) == "/proc/self/mountinfo":
            return (
                "1 0 0:1 / / rw - overlay overlay rw\n"
                f"2 1 0:2 / {source} ro,relatime - fuse.hf-bucket hf ro\n"
            )
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_mountinfo)
    scope = {
        "run_id": pending["run_id"], "model_role": pending["model_role"],
        "runtime_image_digest": "sha256:" + "a" * 64,
    }

    def publish_signed(current_job_id):
        from storyforge_dataset.generation_eval.gold48_owner_receipt import canonical
        measurement = {
            "schema": entry.gate.MEASUREMENT_SCHEMA,
            "provider_job_id": current_job_id,
            "run_id": scope["run_id"], "model_role": scope["model_role"],
            "image_digest": scope["runtime_image_digest"],
            "measurement_source": "PROVIDER_JOB_INSPECT_IMAGE_DIGEST",
            "inspect_receipt_sha256": "b" * 64,
        }
        payload = {
            "schema": entry.gate.SIGNED_MEASUREMENT_SCHEMA,
            "measurement": measurement,
            "signature_hex": key.sign(canonical(measurement)).hex(),
        }
        (source / entry.ATTESTATION_NAME).write_bytes(
            canonical(payload) + b"\n"
        )
    return source, private, pub, scope, publish_signed


def test_delayed_provider_attestation_arrives_and_verifies_before_gpu(
    tmp_path, monkeypatch,
):
    source, private, pub, scope, publish = _provider_handoff(
        tmp_path, monkeypatch,
    )
    calls = []

    def remote_arrival(_seconds):
        calls.append("poll")
        publish("6b00ca46efaf5e14f4b3f8ca")

    digest = entry.receive_current_provider_attestation(
        mount=source, run_id=scope["run_id"], model_role="base",
        owner_scope=scope, target=private / entry.ATTESTATION_NAME,
        trusted_provider_public_key_path=pub,
        sleep=remote_arrival,
    )
    assert len(calls) == 1
    assert len(digest) == 64
    assert (private / entry.ATTESTATION_NAME).stat().st_mode & 0o777 == 0o600


def test_delayed_provider_attestation_rejects_valid_other_job_signature(
    tmp_path, monkeypatch,
):
    source, private, pub, scope, publish = _provider_handoff(
        tmp_path, monkeypatch,
    )
    publish("6b00c8544fdc5ab3c55c02dd")
    with pytest.raises(WorkerError, match="GOLD48_PROVIDER_MEASUREMENT_SCOPE_HOLD"):
        entry.receive_current_provider_attestation(
            mount=source, run_id=scope["run_id"], model_role="base",
            owner_scope=scope, target=private / entry.ATTESTATION_NAME,
            trusted_provider_public_key_path=pub,
            sleep=lambda _seconds: pytest.fail("must reject without retry"),
        )


def test_delayed_provider_handoff_bounded_timeout_no_gpu(tmp_path, monkeypatch):
    source, private, pub, scope, _publish = _provider_handoff(
        tmp_path, monkeypatch,
    )
    moments = iter([0, 1, 2, 4, 6])
    with pytest.raises(WorkerError, match="GOLD48_PROVIDER_HANDOFF_TIMED_OUT_HOLD"):
        entry.receive_current_provider_attestation(
            mount=source, run_id=scope["run_id"], model_role="base",
            owner_scope=scope, target=private / entry.ATTESTATION_NAME,
            trusted_provider_public_key_path=pub,
            timeout_seconds=1, monotonic=lambda: next(moments),
            sleep=lambda _seconds: None,
        )
    assert not (private / entry.ATTESTATION_NAME).exists()


def test_old_pre_submission_provider_proof_is_rejected_from_frozen_stage(
    tmp_path, monkeypatch,
):
    root = stage(tmp_path, monkeypatch)
    (root / entry.ATTESTATION_NAME).write_text("old proof")
    with pytest.raises(WorkerError, match="GOLD48_ENTRY_EXACT_INPUT_FILESET_HOLD"):
        entry.run(root, "gold48-owner-20261121-test-001", "base", execute=False)

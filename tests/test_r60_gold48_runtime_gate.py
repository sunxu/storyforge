"""No-GPU preflight: signed Owner + provider evidence + one-shot consumption."""
from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_r60_gold48_contract_bridge import (
    fixture,
    source_receipt_files,
    synthetic_signed_owner_receipt,
)

import storyforge_dataset.generation_eval.gold48_runtime_gate as gate
from storyforge_dataset.generation_eval.gold48_owner_receipt import canonical
from storyforge_dataset.generation_eval.worker import WorkerError


def test_pre_gpu_runtime_gate_spends_owner_receipt_before_loader(tmp_path, monkeypatch):
    """No real GPU or model. A receipt cannot be silently retried after a crash."""
    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    role = "r60_base336"
    pack[2].update({
        "status": "OWNER_GOLD48_ADAPTER_BINDINGS_ACCEPTED__MOUNT_PENDING",
        "owner_receipt_verified": True,
        "provider_volume_attestation_verified": False,
        "current_remote_weight_bytes_verified_all_three": False,
    })
    auth, output, _ = synthetic_signed_owner_receipt(
        tmp_path, monkeypatch, pack, role
    )
    persistent_root = tmp_path / "synthetic-shared-authority-ledger"
    persistent_root.mkdir(mode=0o700)
    monkeypatch.setattr(gate, "DURABLE_CONSUMPTION_ROOT", persistent_root)
    # The actual production root must be a distinct durable mount. This
    # isolated fixture replaces ONLY that environmental requirement.
    monkeypatch.setattr(gate, "_validate_durable_ledger_root", lambda: None)
    measured = {"torch": "2.6.0+cu124", "peft": "0.21.2"}
    lock_sha = hashlib.sha256(auth["runtime_lock_path"].read_bytes()).hexdigest()
    monkeypatch.setattr(
        gate, "verify_current_dependency_install",
        lambda **_kwargs: (lock_sha, measured),
    )
    monkeypatch.setattr(
        gate, "verify_provider_image_measurement",
        lambda **_kwargs: "9" * 64,
    )
    kwargs = {
        "frozen": pack[0], "owner_freeze": pack[1],
        "adapter_bindings": pack[2], "input_manifest": pack[3],
        "input_path": pack[4], "output_path": output, "model_role": role,
        "source_evidence_paths": evidence,
        "owner_authorization_receipt_path": auth["owner_authorization_receipt_path"],
        "trusted_owner_public_key_pem_path": auth["trusted_owner_public_key_pem_path"],
        "runtime_lock_path": auth["runtime_lock_path"],
        "runtime_contract_path": tmp_path / "synthetic-not-actually-loaded-contract.json",
        "provider_attestation_path": tmp_path / "synthetic-provider-signature",
        "trusted_provider_public_key_path": tmp_path / "synthetic-provider-public-key",
    }
    permit = gate.authorize_and_consume_before_gpu(**kwargs)
    assert permit.signed_scope["model_role"] == role
    assert stat.S_IMODE(permit.spent_receipt_path.stat().st_mode) == 0o600
    spent = json.loads(permit.spent_receipt_path.read_text())
    assert spent["policy"] == "ONE_SHOT_CONSUME_BEFORE_GPU__NO_AUTOMATIC_RETRY"
    assert spent["max_model_calls"] == 48
    assert not output.exists()
    with pytest.raises(WorkerError, match="GOLD48_AUTHORIZATION_ALREADY_SPENT_OR_LEDGER_HOLD"):
        gate.authorize_and_consume_before_gpu(**kwargs)
    # A newly constructed object cannot mint a valid second loading permit.
    with pytest.raises(WorkerError, match="GOLD48_LOADER_ONE_SHOT_PERMIT_REUSED_HOLD"):
        gate.verify_and_consume_gold48_load_permit(
            permit=replace(permit, one_shot_nonce="f" * 64),
            adapter_dir=Path(pack[2]["arms"][role]["local_dir"]),
            adapter_sha256=pack[2]["arms"][role]["expected_sha256"],
        )


def test_pre_gpu_invalid_permit_cannot_unlock_loader():
    with pytest.raises(WorkerError, match="GOLD48_SIGNED_LAUNCH_PERMIT_REQUIRED"):
        gate.verify_and_consume_gold48_load_permit(
            permit={"runtime_authorized": True},
            adapter_dir=None, adapter_sha256=None,
        )


def test_provider_independent_trust_anchor_required(tmp_path):
    scope = {
        "run_id": "synthetic-g48-test",
        "model_role": "r46_v02",
        "runtime_image_digest": "sha256:" + "a" * 64,
    }
    with pytest.raises(WorkerError, match="GOLD48_PROVIDER_TRUST_ANCHOR_NOT_PINNED_HOLD"):
        gate.verify_provider_image_measurement(
            attestation_path=tmp_path / "absent-provider-attestation",
            trusted_provider_public_key_path=tmp_path / "absent-pubkey",
            owner_scope=scope,
        )


def test_provider_signed_measurement_scope_and_tamper(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub_bytes = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub = tmp_path / "test-only-provider.pub"
    pub.write_bytes(pub_bytes)
    pub.chmod(0o600)
    monkeypatch.setattr(
        gate, "PROVIDER_TRUSTED_PUBLIC_PEM_SHA256",
        hashlib.sha256(pub_bytes).hexdigest(),
    )
    scope = {
        "run_id": "synthetic-g48-test",
        "model_role": "r46_v02",
        "runtime_image_digest": "sha256:" + "a" * 64,
    }
    measurement = {
        "schema": gate.MEASUREMENT_SCHEMA,
        "provider_job_id": "synthetic-job-only",
        "run_id": scope["run_id"],
        "model_role": scope["model_role"],
        "image_digest": scope["runtime_image_digest"],
        "measurement_source": "PROVIDER_JOB_INSPECT_IMAGE_DIGEST",
        "inspect_receipt_sha256": "b" * 64,
    }
    attestation = {
        "schema": gate.SIGNED_MEASUREMENT_SCHEMA,
        "measurement": measurement,
        "signature_hex": key.sign(canonical(measurement)).hex(),
    }
    path = tmp_path / "synthetic-provider-signed-attestation.private.json"
    path.write_bytes(canonical(attestation) + b"\n")
    path.chmod(0o600)
    assert gate.verify_provider_image_measurement(
        attestation_path=path, trusted_provider_public_key_path=pub,
        owner_scope=scope,
    ) == hashlib.sha256(path.read_bytes()).hexdigest()
    tampered = json.loads(path.read_text())
    tampered["measurement"]["image_digest"] = "sha256:" + "c" * 64
    path.write_bytes(canonical(tampered) + b"\n")
    with pytest.raises(WorkerError, match="GOLD48_PROVIDER_MEASUREMENT_SCOPE_HOLD"):
        gate.verify_provider_image_measurement(
            attestation_path=path, trusted_provider_public_key_path=pub,
            owner_scope=scope,
        )


def test_pre_gpu_runtime_pip_version_measured_not_from_caller(tmp_path, monkeypatch):
    lock = tmp_path / "hash-pinned.lock"
    lock.write_text("synthetic-hashes-only\n")
    lock_sha = hashlib.sha256(lock.read_bytes()).hexdigest()
    contract = tmp_path / "cpu-contract.json"
    contract.write_text(json.dumps({
        "schema": "storyforge_r60_gold48_inference_cpu_dependency_contract_v1",
        "base_image": "pytorch/pytorch@sha256:" + "e" * 64,
        "lock_sha256": lock_sha,
        "require_hashes_install_on_inference_image_verified": True,
        "observed_torch": "2.6.0+cu124",
        "pins": {"torch": "2.6.0", "peft": "0.21.2"},
    }))
    owner_scope = {
        "dependency_lock_sha256": lock_sha,
        "runtime_image_digest": "sha256:" + "e" * 64,
    }
    fake_versions = {"torch": "2.6.0+cu124", "peft": "0.21.2"}
    monkeypatch.setattr(gate.importlib.metadata, "version", lambda name: fake_versions[name])
    monkeypatch.setattr(
        gate.subprocess, "run", lambda *_args, **_kw: SimpleNamespace(returncode=0)
    )
    lock_out, versions = gate.verify_current_dependency_install(
        runtime_lock_path=lock, runtime_contract_path=contract,
        owner_scope=owner_scope,
    )
    assert (lock_out, versions) == (lock_sha, fake_versions)
    fake_versions["peft"] = "0.21.1"
    with pytest.raises(WorkerError, match="GOLD48_RUNTIME_DEPENDENCY_VERSION_HOLD"):
        gate.verify_current_dependency_install(
            runtime_lock_path=lock, runtime_contract_path=contract,
            owner_scope=owner_scope,
        )


def test_production_dispatch_order_signature_first_then_loader_then_worker(
    tmp_path, monkeypatch,
):
    """Synthetic orchestration check: not a real Owner signature or model call."""
    import storyforge_dataset.generation_eval.gold48_contract_bridge as bridge_module
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader_module

    pack = fixture(tmp_path)
    called = []
    mock_permit = SimpleNamespace(
        selected_adapter_dir=None,
        signed_scope={"runtime_image_digest": "sha256:" + "a" * 64},
    )

    def preflight(**_kwargs):
        called.append("signed-provider-versions-and-spend")
        return mock_permit

    def loader(**kwargs):
        assert called == ["signed-provider-versions-and-spend"]
        assert kwargs["launch_permit"] is mock_permit
        called.append("gpu-loader-mocked-only")
        return object()

    def worker(**kwargs):
        assert called == [
            "signed-provider-versions-and-spend", "gpu-loader-mocked-only",
        ]
        called.append("existing-generation-worker-mocked-only")
        return "synthetic-orchestration-pass"

    monkeypatch.setattr(gate, "authorize_and_consume_before_gpu", preflight)
    monkeypatch.setattr(loader_module, "load_pinned_gold48_backend", loader)
    monkeypatch.setattr(bridge_module, "run_gold48_generation_batch", worker)
    outcome = gate.run_authorized_gold48_production(
        frozen=pack[0], owner_freeze=pack[1],
        adapter_bindings=pack[2], input_manifest=pack[3],
        input_path=pack[4], output_path=tmp_path / "synthetic.private.json",
        model_role="base",
        owner_authorization_receipt_path=tmp_path / "absent",
        trusted_owner_public_key_pem_path=tmp_path / "absent-public",
        source_evidence_paths={},
        runtime_lock_path=tmp_path / "absent-lock",
        runtime_contract_path=tmp_path / "absent-contract",
        provider_attestation_path=tmp_path / "absent-provider",
        trusted_provider_public_key_path=tmp_path / "absent-provider-public",
        expected_template_sha256="a" * 64,
    )
    assert outcome == "synthetic-orchestration-pass"
    assert called == [
        "signed-provider-versions-and-spend", "gpu-loader-mocked-only",
        "existing-generation-worker-mocked-only",
    ]


def test_failed_preflight_never_reaches_loader_or_gpu(tmp_path, monkeypatch):
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader_module

    pack = fixture(tmp_path)
    def fail_preflight(**_kwargs):
        raise WorkerError("GOLD48_UNAUTHORIZED_PRODUCTION_RUN_HOLD")

    def reject_gpu_loader(**_kwargs):
        pytest.fail("GPU loader must not run after preflight rejection")

    monkeypatch.setattr(gate, "authorize_and_consume_before_gpu", fail_preflight)
    monkeypatch.setattr(loader_module, "load_pinned_gold48_backend", reject_gpu_loader)
    with pytest.raises(WorkerError, match="GOLD48_UNAUTHORIZED_PRODUCTION_RUN_HOLD"):
        gate.run_authorized_gold48_production(
            frozen=pack[0], owner_freeze=pack[1],
            adapter_bindings=pack[2], input_manifest=pack[3],
            input_path=pack[4], output_path=tmp_path / "synthetic.private.json",
            model_role="base",
            owner_authorization_receipt_path=tmp_path / "absent",
            trusted_owner_public_key_pem_path=tmp_path / "absent-public",
            source_evidence_paths={},
            runtime_lock_path=tmp_path / "absent-lock",
            runtime_contract_path=tmp_path / "absent-contract",
            provider_attestation_path=tmp_path / "absent-provider",
            trusted_provider_public_key_path=tmp_path / "absent-provider-public",
            expected_template_sha256="a" * 64,
        )

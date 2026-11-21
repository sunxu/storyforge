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
        tmp_path, monkeypatch, pack, role, synthetic_test_only=False
    )
    persistent_root = tmp_path / "synthetic-shared-authority-ledger"
    persistent_root.mkdir(mode=0o700)
    monkeypatch.setattr(gate, "JOB_LOCAL_CONSUMPTION_ROOT", persistent_root)
    # The actual production root must be a distinct durable mount. This
    # isolated fixture replaces ONLY that environmental requirement.
    gate._validate_job_local_ledger_root()
    monkeypatch.setattr(
        gate, "verify_current_readonly_adapter_mount",
        lambda **_kwargs: {
            "mount_point": "/synthetic-ro-only",
            "read_only": True,
            "weight_size_bytes": 1867797544,
            "config_size_bytes": 1288,
            "weight_sha256_verified_by_mount_probe": False,
        },
    )
    measured = {"torch": "2.6.0+cu124", "peft": "0.21.2"}
    lock_sha = hashlib.sha256(auth["runtime_lock_path"].read_bytes()).hexdigest()
    monkeypatch.setattr(
        gate, "verify_current_dependency_install",
        lambda **_kwargs: (lock_sha, measured),
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
    # A forged nonce must not consume the legitimate permit.
    gate.verify_and_consume_gold48_load_permit(
        permit=permit, adapter_dir=Path(pack[2]["arms"][role]["local_dir"]),
        adapter_sha256=pack[2]["arms"][role]["expected_sha256"],
    )
    with pytest.raises(WorkerError, match="GOLD48_LOADER_ONE_SHOT_PERMIT_REUSED_HOLD"):
        gate.verify_and_consume_gold48_load_permit(
            permit=permit, adapter_dir=Path(pack[2]["arms"][role]["local_dir"]),
            adapter_sha256=pack[2]["arms"][role]["expected_sha256"],
        )
    gate.verify_consumed_gold48_output_grant(
        spent_receipt_path=permit.spent_receipt_path,
        owner_receipt_sha256=spent["owner_authorization_receipt_sha256"],
        owner_scope=permit.signed_scope, model_role=role, output_path=output,
        adapter_sha256=pack[2]["arms"][role]["expected_sha256"],
        runtime_lock_sha256=lock_sha,
    )
    with pytest.raises(WorkerError, match="GOLD48_SPENT_LEDGER_SCOPE_MISMATCH_HOLD"):
        gate.verify_consumed_gold48_output_grant(
            spent_receipt_path=permit.spent_receipt_path,
            owner_receipt_sha256=spent["owner_authorization_receipt_sha256"],
            owner_scope=permit.signed_scope, model_role=role,
            output_path=output.with_name("wrong.private.json"),
            adapter_sha256=pack[2]["arms"][role]["expected_sha256"],
            runtime_lock_sha256=lock_sha,
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
    monkeypatch.setenv("JOB_ID", "6b00ca46efaf5e14f4b3f8ca")
    measurement = {
        "schema": gate.MEASUREMENT_SCHEMA,
        "provider_job_id": "6b00ca46efaf5e14f4b3f8ca",
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
    # Signed attestation for a DIFFERENT live Job cannot unlock this one.
    monkeypatch.setenv("JOB_ID", "6b00c8544fdc5ab3c55c02dd")
    with pytest.raises(WorkerError, match="GOLD48_PROVIDER_MEASUREMENT_SCOPE_HOLD"):
        gate.verify_provider_image_measurement(
            attestation_path=path, trusted_provider_public_key_path=pub,
            owner_scope=scope,
        )
    monkeypatch.delenv("JOB_ID", raising=False)
    with pytest.raises(WorkerError, match="GOLD48_PROVIDER_CURRENT_JOB_ID_REQUIRED_HOLD"):
        gate.verify_provider_image_measurement(
            attestation_path=path, trusted_provider_public_key_path=pub,
            owner_scope=scope,
        )
    monkeypatch.setenv("JOB_ID", "6b00ca46efaf5e14f4b3f8ca")
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
        "hash_pinned_install_verified_job": "synthetic-job",
    }))
    monkeypatch.setattr(gate, "FROZEN_RUNTIME_LOCK_SHA256", lock_sha)
    monkeypatch.setattr(gate, "FROZEN_RUNTIME_IMAGE",
                        "pytorch/pytorch@sha256:" + "e" * 64)
    monkeypatch.setattr(gate, "FROZEN_RUNTIME_PACKAGES",
                        {"torch": "2.6.0", "peft": "0.21.2"})
    monkeypatch.setattr(gate, "FROZEN_PINNED_INSTALL_JOB", "synthetic-job")
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
        signed_scope={
            "runtime_image_digest": "sha256:" + "a" * 64,
            "run_id": "synthetic-g48-owner-001",
        },
    )

    def preflight(**_kwargs):
        called.append("signed-owner-versions-and-spend")
        return mock_permit

    def loader(**kwargs):
        assert called == ["signed-owner-versions-and-spend"]
        assert kwargs["launch_permit"] is mock_permit
        called.append("gpu-loader-mocked-only")
        return object()

    def worker(**kwargs):
        assert called == [
            "signed-owner-versions-and-spend", "gpu-loader-mocked-only",
        ]
        called.append("existing-generation-worker-mocked-only")
        return "synthetic-orchestration-pass"

    monkeypatch.setattr(gate, "authorize_and_consume_before_gpu", preflight)
    monkeypatch.setattr(loader_module, "load_pinned_gold48_backend", loader)
    monkeypatch.setattr(bridge_module, "run_gold48_generation_batch", worker)

    def delivery(**kwargs):
        assert kwargs["run_id"] == "synthetic-g48-owner-001"
        assert called[-1] == "existing-generation-worker-mocked-only"
        called.append("private-delivery-mocked-only")

    monkeypatch.setattr(gate, "deliver_gold48_private_result", delivery)
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
    )
    assert outcome == "synthetic-orchestration-pass"
    assert called == [
        "signed-owner-versions-and-spend", "gpu-loader-mocked-only",
        "existing-generation-worker-mocked-only",
        "private-delivery-mocked-only",
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
            )



def test_synthetic_owner_signature_cannot_enter_gpu_preflight(tmp_path, monkeypatch):
    """A valid *synthetic* Ed25519 signature is never a production GPU grant."""
    role = "base"
    pack = fixture(tmp_path)
    pack[2].update({
        "status": "OWNER_GOLD48_ADAPTER_BINDINGS_ACCEPTED__MOUNT_PENDING",
        "owner_receipt_verified": True,
        "provider_volume_attestation_verified": False,
        "current_remote_weight_bytes_verified_all_three": False,
    })
    evidence = source_receipt_files(tmp_path, pack)
    auth, output, _ = synthetic_signed_owner_receipt(
        tmp_path, monkeypatch, pack, role,
    )

    def unexpected_package_probe(**_kwargs):
        pytest.fail("synthetic authority must fail before runtime measurement")

    monkeypatch.setattr(gate, "verify_current_dependency_install",
                        unexpected_package_probe)
    with pytest.raises(WorkerError, match="GOLD48_PRODUCTION_GPU_SCOPE_REQUIRED_HOLD"):
        gate.authorize_and_consume_before_gpu(
            frozen=pack[0], owner_freeze=pack[1],
            adapter_bindings=pack[2], input_manifest=pack[3],
            input_path=pack[4], output_path=output,
            model_role=role, source_evidence_paths=evidence,
            owner_authorization_receipt_path=auth["owner_authorization_receipt_path"],
            trusted_owner_public_key_pem_path=auth["trusted_owner_public_key_pem_path"],
            runtime_lock_path=auth["runtime_lock_path"],
            runtime_contract_path=tmp_path / "never-used-contract",
        )
    assert not output.exists()


def test_runtime_contract_pins_reject_modified_package_or_install_job(
    tmp_path, monkeypatch,
):
    """Caller-supplied contract JSON cannot relax the reviewed package pins."""
    lock = tmp_path / "synthetic-lock"
    lock.write_bytes(b"synthetic-lock-bytes")
    sha = hashlib.sha256(lock.read_bytes()).hexdigest()
    pins = {"torch": "2.6.0", "peft": "0.21.2"}
    fake_image = "pytorch/pytorch@sha256:" + "a" * 64
    monkeypatch.setattr(gate, "FROZEN_RUNTIME_LOCK_SHA256", sha)
    monkeypatch.setattr(gate, "FROZEN_RUNTIME_IMAGE", fake_image)
    monkeypatch.setattr(gate, "FROZEN_RUNTIME_PACKAGES", pins)
    monkeypatch.setattr(gate, "FROZEN_PINNED_INSTALL_JOB", "approved-cpu-job")
    contract = {
        "schema": "storyforge_r60_gold48_inference_cpu_dependency_contract_v1",
        "base_image": fake_image, "lock_sha256": sha,
        "pins": pins, "observed_torch": "2.6.0+cu124",
        "require_hashes_install_on_inference_image_verified": True,
        "hash_pinned_install_verified_job": "approved-cpu-job",
    }
    source = tmp_path / "runtime-contract.json"
    scope = {"dependency_lock_sha256": sha,
             "runtime_image_digest": "sha256:" + "a" * 64}
    for field, tampered in [
        ("pins", {"torch": "2.6.0", "peft": "0.21.1"}),
        ("hash_pinned_install_verified_job", "unreviewed-cpu-job"),
        ("base_image", "pytorch/pytorch@sha256:" + "b" * 64),
        ("lock_sha256", "0" * 64),
    ]:
        payload = dict(contract)
        payload[field] = tampered
        source.write_text(json.dumps(payload))
        with pytest.raises(WorkerError, match="GOLD48_RUNTIME_DEPENDENCY_PIN_HOLD"):
            gate.verify_current_dependency_install(
                runtime_lock_path=lock, runtime_contract_path=source,
                owner_scope=scope,
            )


def test_current_launch_ro_mount_preflight_is_kernel_bound_and_zero_weight_reads(
    tmp_path, monkeypatch,
):
    """A previous HF CPU PASS cannot authorize an absent or writable new mount."""
    role = "r54_v03a"
    root = tmp_path / "ro_adapters"
    adapter = root / role
    adapter.mkdir(parents=True, mode=0o700)
    weight = adapter / "adapter_model.safetensors"
    with weight.open("wb") as f:
        f.truncate(gate.ADAPTER_WEIGHT_BYTES)  # sparse: NO weight read or SHA
    config = adapter / "adapter_config.json"
    config.write_bytes(b" " * gate.ADAPTER_CONFIG_BYTES[role])
    info = tmp_path / "synthetic-mountinfo"
    monkeypatch.setattr(gate, "ADAPTER_MOUNT_ROOT", root)
    monkeypatch.setattr(gate, "ADAPTER_MOUNTINFO_PATH", info)

    def set_mount(mode):
        info.write_text(
            "13 1 0:42 / " + str(adapter) + " " + mode
            + ",relatime - fuse.source synthetic rw\n"
        )

    set_mount("rw")
    with pytest.raises(WorkerError, match="GOLD48_RUNTIME_ADAPTER_RO_MOUNT_REQUIRED_HOLD"):
        gate.verify_current_readonly_adapter_mount(
            role=role, adapter_dir=adapter,
        )
    set_mount("ro")
    observed = gate.verify_current_readonly_adapter_mount(
        role=role, adapter_dir=adapter,
    )
    assert observed == {
        "mount_point": str(adapter), "read_only": True,
        "weight_size_bytes": 1867797544, "config_size_bytes": 1282,
        "weight_sha256_verified_by_mount_probe": False,
    }
    with pytest.raises(WorkerError, match="GOLD48_RUNTIME_ADAPTER_MOUNT_TARGET_HOLD"):
        gate.verify_current_readonly_adapter_mount(
            role=role, adapter_dir=root / "r46_v02",
        )
    config.unlink()
    config.symlink_to(weight)
    with pytest.raises(WorkerError, match="GOLD48_RUNTIME_ADAPTER_MOUNT_METADATA_HOLD"):
        gate.verify_current_readonly_adapter_mount(
            role=role, adapter_dir=adapter,
        )
    assert gate.verify_current_readonly_adapter_mount(
        role="base", adapter_dir=None,
    ) is None


def test_no_mount_does_not_pass_preflight_by_previous_cpu_proof(tmp_path):
    with pytest.raises(WorkerError, match="GOLD48_RUNTIME_ADAPTER_MOUNT_TARGET_HOLD"):
        gate.verify_current_readonly_adapter_mount(
            role="r60_base336", adapter_dir=tmp_path / "checkpoint-37"
        )



def test_owner_mac_job_local_private_root_blocks_fuse(tmp_path, monkeypatch):
    """Even a mode-0700 HF FUSE path must not be used for private writes."""
    root = tmp_path / "fuse"
    root.mkdir(mode=0o700)
    original = Path.read_text

    def override(path, *args, **kwargs):
        if str(path) == "/proc/self/mountinfo":
            return ("1 0 0:1 / / rw - overlay overlay rw\n"
                    "2 1 0:2 / " + str(root) +
                    " rw - fuse.hf-mount hf rw\n")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", override)
    with pytest.raises(WorkerError, match="GOLD48_JOB_LOCAL_ONLY_NO_FUSE_HOLD"):
        gate.verify_atomic_private_publication_before_spend(root)
    assert list(root.iterdir()) == []


def test_atomic_publication_probe_uses_existing_outputmanager_and_cleans(
    tmp_path,
):
    """Real filesystem operations, no fake GPU or additional publisher."""
    root = tmp_path / "private-output"
    root.mkdir(mode=0o700)
    gate.verify_atomic_private_publication_before_spend(root)
    assert list(root.iterdir()) == []
    root.chmod(0o755)
    with pytest.raises(WorkerError, match="GOLD48_JOB_LOCAL_PRIVATE_ROOT_0700_HOLD"):
        gate.verify_atomic_private_publication_before_spend(root)
    assert list(root.iterdir()) == []


def test_atomic_publication_probe_holds_before_grant_if_fuse_rejects_create(
    tmp_path, monkeypatch,
):
    """Synthetic emulation of a remote bucket that rejects atomic publication."""
    from storyforge_dataset.hf_runtime.outputs import OutputManager

    root = tmp_path / "isolated-private-mount"
    root.mkdir(mode=0o700)
    original = OutputManager.write_safe.__func__

    def unsupported(cls, path, payload, *, mode=0o600):
        if path.name.startswith(".gold48-atomic-probe-"):
            raise ValueError("OUTPUT_ATOMIC_PUBLISH_UNSUPPORTED")
        return original(cls, path, payload, mode=mode)

    monkeypatch.setattr(OutputManager, "write_safe", classmethod(unsupported))
    with pytest.raises(WorkerError, match="GOLD48_ATOMIC_PUBLICATION_UNSUPPORTED_HOLD"):
        gate.verify_atomic_private_publication_before_spend(root)
    assert list(root.iterdir()) == []


def test_gold48_materialize_ro_file_reuses_verified_input_sha(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_bytes(b'{"private":"synthetic"}\n')
    target_root = tmp_path / "local-private"
    target_root.mkdir(mode=0o700)
    target = target_root / "input.jsonl"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    gate.materialize_gold48_ro_input(
        source=source, target=target, expected_sha256=digest,
    )
    assert target.read_bytes() == source.read_bytes()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    with pytest.raises(WorkerError, match="GOLD48_RO_LOCALIZE_ALREADY_EXISTS_HOLD"):
        gate.materialize_gold48_ro_input(
            source=source, target=target, expected_sha256=digest,
        )
    with pytest.raises(WorkerError):
        gate.materialize_gold48_ro_input(
            source=source, target=target_root / "wrong",
            expected_sha256="0" * 64,
        )
    assert not (target_root / "wrong").exists()


def _mock_gold48_rw_mount(tmp_path, monkeypatch):
    """Synthetic direct FUSE mount for output-transfer tests; no HF Job."""
    root = tmp_path / "native-rw-bucket"
    root.mkdir(mode=0o755)
    monkeypatch.setattr(gate, "BUCKET_RESULT_MOUNT", root)
    original_mount = Path.is_mount
    original_read = Path.read_text
    monkeypatch.setattr(
        Path, "is_mount",
        lambda self: self == root or original_mount(self),
    )

    def mountinfo(path, *args, **kwargs):
        if str(path) == "/proc/self/mountinfo":
            return (
                "1 0 0:1 / / rw,relatime - overlay overlay rw\n"
                f"2 1 0:2 / {root} rw,relatime - fuse.hf-bucket bucket rw\n"
            )
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mountinfo)
    return root


def _synthetic_gold48_output(tmp_path):
    from storyforge_dataset.hf_runtime.outputs import OutputManager

    root = tmp_path / "private-run"
    root.mkdir(mode=0o700)
    output = root / "base.private.json"
    data = b'{"schema":"synthetic-output"}\n'
    output.write_bytes(data)
    output.chmod(0o600)
    for suffix in (".launch.private.json", ".identity.private.json"):
        OutputManager.write_safe(output.with_name(output.name + suffix),
                                 {"schema": "synthetic"}, mode=0o600)
    receipt = SimpleNamespace(
        record_count=48, output_sha256=hashlib.sha256(data).hexdigest()
    )
    return output, receipt


def test_gold48_delivery_uses_native_rw_mount_manifest_last_no_cli(
    tmp_path, monkeypatch,
):
    bucket = _mock_gold48_rw_mount(tmp_path, monkeypatch)
    output, receipt = _synthetic_gold48_output(tmp_path)
    def reject_cli(*_args, **_kwargs):
        pytest.fail("A GPU Job must not need hf CLI or any token for delivery")
    monkeypatch.setattr(gate.subprocess, "run", reject_cli)
    gate.deliver_gold48_private_result(
        output_path=output, run_id="synthetic-g48-owner-001",
        model_role="base", worker_receipt=receipt,
    )
    names = {p.name for p in bucket.iterdir()}
    expected = {
        "base.private.json",
        "base.private.json.launch.private.json",
        "base.private.json.identity.private.json",
        "base.private.json.result-sha256-manifest.private.json",
    }
    assert names == expected
    assert len(names) == 4
    manifest = json.loads(
        (bucket / "base.private.json.result-sha256-manifest.private.json").read_bytes()
    )
    assert manifest["record_count"] == 48
    assert manifest["run_id"] == "synthetic-g48-owner-001"
    assert len(manifest["files"]) == 3
    assert all(
        hashlib.sha256((bucket / row["name"]).read_bytes()).hexdigest()
        == row["sha256"] for row in manifest["files"]
    )


def test_gold48_delivery_holds_on_corrupted_fuse_readback(
    tmp_path, monkeypatch,
):
    bucket = _mock_gold48_rw_mount(tmp_path, monkeypatch)
    output, receipt = _synthetic_gold48_output(tmp_path)
    from storyforge_dataset.hf_runtime.inputs import InputManager
    real_reader = InputManager.open_verified

    def corrupt(path, **kwargs):
        if Path(path).parent == bucket:
            raise ValueError("INPUT_SHA256_MISMATCH")
        return real_reader(path, **kwargs)

    monkeypatch.setattr(InputManager, "open_verified", corrupt)
    with pytest.raises(WorkerError, match="GOLD48_DELIVERY_UNCONFIRMED_NO_RETRY_HOLD"):
        gate.deliver_gold48_private_result(
            output_path=output, run_id="synthetic-g48-owner-002",
            model_role="base", worker_receipt=receipt,
        )
    assert not (bucket / "base.private.json.result-sha256-manifest.private.json").exists()


def test_gold48_delivery_rejects_container_local_fake_mount(
    tmp_path, monkeypatch,
):
    output, receipt = _synthetic_gold48_output(tmp_path)
    root = tmp_path / "not-a-real-mount"
    root.mkdir()
    monkeypatch.setattr(gate, "BUCKET_RESULT_MOUNT", root)
    with pytest.raises(WorkerError, match="GOLD48_DELIVERY_RW_MOUNT_REQUIRED_HOLD"):
        gate.deliver_gold48_private_result(
            output_path=output, run_id="synthetic-g48-owner-003",
            model_role="base", worker_receipt=receipt,
        )
    assert not list(root.iterdir())

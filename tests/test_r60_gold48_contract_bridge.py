"""Synthetic, no-weight Gold48 contract and existing generation-loop integration."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    BINDINGS_SCHEMA,
    EVIDENCE_URIS,
    INPUT_SCHEMA,
    OWNER_SCHEMA,
    PROVENANCE,
    ROLES,
    SOURCE_FIELDS,
    _canonical,
    _digest,
    build_gold48_frozen_input_payload,
    prepare_gold48_generation_contract,
    read_private_contract,
    recover_gold48_identity_sidecar,
    run_gold48_generation_batch,
    verify_gold48_binding_source_evidence,
)
from storyforge_dataset.generation_eval.gold48_owner_receipt import (
    make_owner_scope,
    owner_sign_create_only,
)
from storyforge_dataset.generation_eval.worker import (
    GenerationResult,
    WorkerError,
    _run_validated_generation_batch,
)


def fixture(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    frozen = json.loads(
        (root / "experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json")
        .read_text(encoding="utf-8")
    )
    cases, records = [], []
    for n in range(1, 49):
        case_id = f"G48-C{n:02d}"
        messages = [
            {"role": "system", "content": "Synthetic system."},
            {"role": "user", "content": f"Synthetic request {n}."},
        ]
        cases.append({
            "candidate_case_id_PRIVATE": case_id,
            "reconstructed_messages_sha256_PRIVATE": _digest(messages),
        })
        records.append({"sample_id": case_id, "messages": messages})
    data = b"".join(_canonical(x) + b"\n" for x in records)
    input_path = tmp_path / "inputs.jsonl"
    input_path.write_bytes(data)
    owner = {
        "schema": OWNER_SCHEMA,
        "status": "GOLD48_FROZEN_SCOPED__GENERATION_PROFILE_PENDING",
        "owner_gold48_freeze": True,
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "model_generation_authorized": False,
        "gpu_authorized_by_this_freeze": False,
        "training_authorized_by_this_freeze": False,
        "run_key": frozen["dataset"]["run_key"],
        "cases_PRIVATE": cases,
    }
    bindings = {
        "schema": BINDINGS_SCHEMA,
        "run_key": frozen["dataset"]["run_key"],
        "arms": {},
    }
    for role in ROLES:
        bindings["arms"][role] = {
            "checkpoint_uri": frozen["arms"][role]["adapter_checkpoint"],
            "weight_file_name": None if role == "base" else "adapter_model.safetensors",
            "expected_sha256": None if role == "base" else "b" * 64,
            "local_dir": None if role == "base" else f"/private/{role}",
            "provenance": "BASE_NO_ADAPTER" if role == "base" else PROVENANCE[role],
            "source_evidence_sha256": None if role == "base" else "c" * 64,
            "source_evidence_uri": None if role == "base" else EVIDENCE_URIS[role],
            "source_field": None if role == "base" else SOURCE_FIELDS[role],
            "expected_weight_size_bytes": None if role == "base" else 1867797544,
        }
    manifest = {
        "schema": INPUT_SCHEMA,
        "run_key": frozen["dataset"]["run_key"],
        "record_count": 48,
        "sha256": hashlib.sha256(data).hexdigest(),
        "max_input_tokens": 30720,
        "max_new_tokens": 2048,
        "seed": 42,
        "cases": [
            {"sample_id": case["candidate_case_id_PRIVATE"],
             "messages_sha256": case["reconstructed_messages_sha256_PRIVATE"]}
            for case in cases
        ],
    }
    return frozen, owner, bindings, manifest, input_path


def build_call(pack, *, role="r60_base336"):
    frozen, owner, bindings, manifest, path = pack
    return {
        "frozen": frozen, "owner_freeze": owner,
        "adapter_bindings": bindings, "input_manifest": manifest,
        "input_path": path, "model_role": role,
    }


class RecordingBackend:
    gpu_started = False

    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return GenerationResult(
            text="synthetic-response", input_tokens=16,
            output_tokens=3, finish_reason="eos",
        )


@pytest.mark.parametrize("role", ROLES)
def test_four_arms_compile_to_existing_worker_contract(tmp_path, role):
    pack = fixture(tmp_path)
    profile, manifest = prepare_gold48_generation_contract(**build_call(pack, role=role))
    assert profile["schema"] == "storyforge_r60_gold48_worker_contract_v1"
    assert list(profile["model_profiles"]) == list(ROLES)
    assert profile["model_profiles"][role]["enable_thinking"] is False
    assert profile["model_profiles"][role]["generation_prefix"] is None
    assert profile["model_profiles"][role]["sampling"]["min_p"] == 0
    assert profile["eos_token_ids"][role] == [248046, 248044]
    assert profile["pad_token_ids"][role] == 248044
    assert manifest == {
        "schema": "storyforge_r60_generation_input_manifest_v1",
        "record_count": 48,
        "sha256": pack[3]["sha256"],
        "max_input_tokens": 30720,
        "max_new_tokens": 2048,
        "seed": 42,
    }


def test_synthetic_core_reuse_has_exact_order_seed_budget_no_overwrite(tmp_path):
    pack = fixture(tmp_path)
    profile, manifest = prepare_gold48_generation_contract(**build_call(pack, role="r46_v02"))
    backend = RecordingBackend()
    dest = tmp_path / "output.private.json"
    receipt = _run_validated_generation_batch(
        profile=profile, model_role="r46_v02", manifest=manifest,
        input_path=pack[4], output_path=dest, backend=backend,
    )
    assert receipt.record_count == 48
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    assert [x["seed"] for x in backend.calls] == list(range(42, 90))
    for call in backend.calls:
        assert call["model"] == "Qwen/Qwen3.8-27B"
        assert call["revision"] == pack[0]["base_model"]["revision"]
        assert call["enable_thinking"] is False
        assert call["sampling"]["top_p"] == 0.8
        assert call["eos_token_ids"] == [248046, 248044]
        assert call["max_input_tokens"] == 30720
        assert call["max_new_tokens"] == 2048
    assert all(x["sample_id"] == f"G48-C{i:02d}"
               for i, x in enumerate(json.loads(dest.read_text())["outputs"], 1))
    with pytest.raises(WorkerError, match="OUTPUT_PUBLICATION_FAILED"):
        _run_validated_generation_batch(
            profile=profile, model_role="r46_v02", manifest=manifest,
            input_path=pack[4], output_path=dest, backend=RecordingBackend(),
        )


def test_real_bridge_fails_closed_without_new_owner_permission(tmp_path):
    call = build_call(fixture(tmp_path))
    out = tmp_path / "should_not_exist.json"
    with pytest.raises(WorkerError, match="GOLD48_SEPARATE_OWNER_INFERENCE_AUTHORIZATION_REQUIRED"):
        run_gold48_generation_batch(
            **call, output_path=out,
            backend=RecordingBackend(), owner_authorization_receipt_path=None,
        )
    assert not out.exists()


@pytest.mark.parametrize("where,field,replacement,error", [
    (0, "inference_authorized", True, "GOLD48_FROZEN_PROFILE_INVALID"),
    (0, "training_authorized", True, "GOLD48_FROZEN_PROFILE_INVALID"),
    (1, "model_generation_authorized", True, "GOLD48_OWNER_FREEZE_HOLD"),
    (3, "max_input_tokens", 30719, "GOLD48_INPUT_MANIFEST_HOLD"),
    (3, "seed", 43, "GOLD48_INPUT_MANIFEST_HOLD"),
    (3, "sha256", "0" * 64, "GOLD48_INPUT_FILE_SHA_HOLD"),
])
def test_contract_tamper_fails_closed(tmp_path, where, field, replacement, error):
    pack = list(fixture(tmp_path))
    pack[where][field] = replacement
    with pytest.raises(WorkerError, match=error):
        prepare_gold48_generation_contract(**build_call(pack))


@pytest.mark.parametrize(("field", "bad"), [
    ("enable_thinking", True),
    ("sampling", {"do_sample": False}),
    ("base_revision", "1" * 40),
])
def test_arm_pin_tamper_holds(tmp_path, field, bad):
    pack = fixture(tmp_path)
    pack[0]["arms"]["r54_v03a"][field] = bad
    with pytest.raises(WorkerError, match="GOLD48_ARM_IDENTITY_HOLD"):
        prepare_gold48_generation_contract(**build_call(pack))


def test_checkpoint_uri_and_expected_sha_binding_tamper_holds(tmp_path):
    pack = fixture(tmp_path)
    pack[2]["arms"]["r60_base336"]["checkpoint_uri"] = "hf://wrong"
    with pytest.raises(WorkerError, match="GOLD48_ADAPTER_BINDING_IDENTITY_HOLD"):
        prepare_gold48_generation_contract(**build_call(pack))
    pack = fixture(tmp_path)
    pack[2]["arms"]["r60_base336"]["expected_sha256"] = "wrong"
    with pytest.raises(WorkerError, match="GOLD48_ADAPTER_BINDING_UNTRUSTED_HOLD"):
        prepare_gold48_generation_contract(**build_call(pack))


def test_frozen_case_order_and_input_canonical_sha_binding(tmp_path):
    pack = fixture(tmp_path)
    pack[3]["cases"][0], pack[3]["cases"][1] = pack[3]["cases"][1], pack[3]["cases"][0]
    with pytest.raises(WorkerError, match="GOLD48_FROZEN_CASE_SHA_BINDING_HOLD"):
        prepare_gold48_generation_contract(**build_call(pack))
    pack = fixture(tmp_path)
    pack[3]["cases"][0]["messages_sha256"] = "0" * 64
    with pytest.raises(WorkerError, match="GOLD48_FROZEN_CASE_SHA_BINDING_HOLD"):
        prepare_gold48_generation_contract(**build_call(pack))


def test_input_case_content_tamper_holds_even_when_file_sha_updated(tmp_path):
    pack = fixture(tmp_path)
    records = [json.loads(line) for line in pack[4].read_bytes().splitlines()]
    records[0]["messages"][1]["content"] = "altered"
    raw = b"".join(_canonical(x) + b"\n" for x in records)
    pack[4].write_bytes(raw)
    pack[3]["sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(WorkerError, match="GOLD48_PER_CASE_INPUT_SHA_HOLD"):
        prepare_gold48_generation_contract(**build_call(pack))


def test_private_contract_read_requires_0600(tmp_path):
    path = tmp_path / "private.json"
    path.write_text(json.dumps({"secret": "synthetic-only"}))
    path.chmod(0o644)
    with pytest.raises(WorkerError, match="GOLD48_PRIVATE_CONTRACT_MODE_HOLD"):
        read_private_contract(path)
    path.chmod(0o600)
    assert read_private_contract(path) == {"secret": "synthetic-only"}


def test_source_evidence_exact_sha_and_checkpoint_digest_binding(tmp_path):
    pack = fixture(tmp_path)
    evidence_paths = {}
    for role in PROVENANCE:
        entry = pack[2]["arms"][role]
        content = (
            {"training_evidence": {"adapter_sha256": entry["expected_sha256"]}}
            if role == "r46_v02"
            else {"adapter_sha256": entry["expected_sha256"]}
        )
        if role == "r60_base336":
            content.update({
                "schema": "storyforge_gold48_adapter_sha_cpu_only_safe_v1",
                "status": "R60_ADAPTER_BYTE_SHA_PASS",
                "file_size": 1867797544,
                "gpu_started": False,
                "model_calls": 0,
            })
        raw = _canonical(content)
        path = tmp_path / f"{role}.evidence.private.json"
        path.write_bytes(raw)
        path.chmod(0o600)
        entry["source_evidence_sha256"] = hashlib.sha256(raw).hexdigest()
        evidence_paths[role] = path
    verify_gold48_binding_source_evidence(pack[2], evidence_paths)

    # Byte alteration is detected *before* trusting the adapter digest.
    evidence_paths["r46_v02"].write_bytes(b"{}")
    with pytest.raises(WorkerError, match="GOLD48_SOURCE_EVIDENCE_BYTE_SHA_HOLD"):
        verify_gold48_binding_source_evidence(pack[2], evidence_paths)


def test_evidence_digest_field_must_match_binding_after_valid_byte_sha(tmp_path):
    pack = fixture(tmp_path)
    evidence_paths = {}
    for role in PROVENANCE:
        entry = pack[2]["arms"][role]
        payload = (
            {"training_evidence": {"adapter_sha256": entry["expected_sha256"]}}
            if role == "r46_v02"
            else {"adapter_sha256": entry["expected_sha256"]}
        )
        if role == "r60_base336":
            payload.update({
                "schema": "storyforge_gold48_adapter_sha_cpu_only_safe_v1",
                "status": "R60_ADAPTER_BYTE_SHA_PASS",
                "file_size": 1867797544,
                "gpu_started": False,
                "model_calls": 0,
            })
        if role == "r54_v03a":
            payload["adapter_sha256"] = "0" * 64
        raw = _canonical(payload)
        path = tmp_path / f"{role}.json"
        path.write_bytes(raw)
        path.chmod(0o600)
        entry["source_evidence_sha256"] = hashlib.sha256(raw).hexdigest()
        evidence_paths[role] = path
    with pytest.raises(WorkerError, match="GOLD48_SOURCE_EVIDENCE_ADAPTER_SHA_HOLD"):
        verify_gold48_binding_source_evidence(pack[2], evidence_paths)


def test_materializer_reuses_frozen_case_messages_without_reconstruction(tmp_path):
    pack = fixture(tmp_path)
    records = [json.loads(x) for x in pack[4].read_bytes().splitlines()]
    draft = {
        "schema": "storyforge_r60_gold48_reconstructed_inputs_draft_private_v1",
        "status": "RECONSTRUCTED_48_INPUT_DRAFT__OWNER_FREEZE_PENDING",
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "cases_PRIVATE": [
            {
                "candidate_case_id_PRIVATE": rec["sample_id"],
                "reconstructed_messages_sha256_PRIVATE":
                    pack[1]["cases_PRIVATE"][i]["reconstructed_messages_sha256_PRIVATE"],
                "reconstructed_messages_PRIVATE": rec["messages"],
            }
            for i, rec in enumerate(records)
        ],
    }
    raw, manifest = build_gold48_frozen_input_payload(
        frozen=pack[0], owner_freeze=pack[1], reconstructed_draft=draft
    )
    assert raw == pack[4].read_bytes()
    assert manifest == pack[3]
    draft["cases_PRIVATE"][0]["reconstructed_messages_PRIVATE"][1]["content"] += " tamper"
    with pytest.raises(WorkerError, match="GOLD48_RECONSTRUCTED_DRAFT_CASE_SHA_HOLD"):
        build_gold48_frozen_input_payload(
            frozen=pack[0], owner_freeze=pack[1], reconstructed_draft=draft
        )


def test_create_only_materializer_cli_emits_owner_only_files(tmp_path):
    pack = fixture(tmp_path)
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path / "owner-private"
    root.mkdir(mode=0o700)
    records = [json.loads(x) for x in pack[4].read_bytes().splitlines()]
    draft = {
        "schema": "storyforge_r60_gold48_reconstructed_inputs_draft_private_v1",
        "status": "RECONSTRUCTED_48_INPUT_DRAFT__OWNER_FREEZE_PENDING",
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "cases_PRIVATE": [
            {
                "candidate_case_id_PRIVATE": rec["sample_id"],
                "reconstructed_messages_sha256_PRIVATE":
                    pack[1]["cases_PRIVATE"][i]["reconstructed_messages_sha256_PRIVATE"],
                "reconstructed_messages_PRIVATE": rec["messages"],
            }
            for i, rec in enumerate(records)
        ],
    }
    draft_raw = _canonical(draft) + b"\n"
    pack[1]["reconstructed_draft_sha256_PRIVATE"] = hashlib.sha256(draft_raw).hexdigest()
    owner_path = root / "owner.json"
    draft_path = root / "draft.json"
    owner_path.write_bytes(_canonical(pack[1]) + b"\n")
    draft_path.write_bytes(draft_raw)
    owner_path.chmod(0o600)
    draft_path.chmod(0o600)
    output = root / "run-input"
    command = [
        sys.executable, str(repo / "scripts/r60_gold48_generation_input_materialize_cpu.py"),
        "--frozen-profile",
        str(repo / "experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json"),
        "--owner-freeze", str(owner_path),
        "--reconstructed-draft", str(draft_path),
        "--private-root", str(root), "--output-dir", str(output),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    first = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    assert first.returncode == 0, first.stdout
    safe = json.loads(first.stdout)
    assert safe["status"] == "GOLD48_PRIVATE_WORKER_INPUTS_MATERIALIZED"
    assert safe["private_values_emitted"] is False
    output_jsonl = output / "GOLD48_GENERATION_INPUTS_PRIVATE.jsonl"
    output_manifest = output / "GOLD48_GENERATION_INPUT_MANIFEST_PRIVATE.json"
    assert output_jsonl.read_bytes() == pack[4].read_bytes()
    assert json.loads(output_manifest.read_text()) == pack[3]
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE(output_jsonl.stat().st_mode) == 0o600
    assert stat.S_IMODE(output_manifest.stat().st_mode) == 0o600
    second = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    assert second.returncode == 2
    assert json.loads(second.stdout)["status"] == "HOLD"
    assert output_jsonl.read_bytes() == pack[4].read_bytes()

def source_receipt_files(tmp_path: Path, pack):
    """Three synthetic receipts; real GPU/weights are never touched."""
    files = {}
    for role in PROVENANCE:
        entry = pack[2]["arms"][role]
        payload = (
            {"training_evidence": {"adapter_sha256": entry["expected_sha256"]}}
            if role == "r46_v02" else {"adapter_sha256": entry["expected_sha256"]}
        )
        if role == "r60_base336":
            payload.update({
                "schema": "storyforge_gold48_adapter_sha_cpu_only_safe_v1",
                "status": "R60_ADAPTER_BYTE_SHA_PASS",
                "file_size": 1867797544,
                "gpu_started": False,
                "model_calls": 0,
            })
        raw = _canonical(payload)
        target = tmp_path / f"{role}.receipt.private.json"
        target.write_bytes(raw)
        target.chmod(0o600)
        entry["source_evidence_sha256"] = hashlib.sha256(raw).hexdigest()
        files[role] = target
    return files


class SyntheticIdentityBackend(RecordingBackend):
    # This field is an injected contract-test assertion, NOT real GPU status.
    gpu_started = True
    model_id = "Qwen/Qwen3.8-27B"

    def __init__(self, pack, role):
        super().__init__()
        self.revision = pack[0]["base_model"]["revision"]
        self.gold48_adapter_sha256 = pack[2]["arms"][role]["expected_sha256"]
        value = pack[2]["arms"][role]["local_dir"]
        self.gold48_adapter_dir = None if value is None else Path(value)



def synthetic_signed_owner_receipt(tmp_path: Path, monkeypatch, pack, role):
    """Ephemeral test-only key. Never sets the production trust anchor."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    import storyforge_dataset.generation_eval.gold48_owner_receipt as auth_module

    key = Ed25519PrivateKey.generate()
    private_path = tmp_path / "test-only-owner-private.pem"
    public_path = tmp_path / "test-only-owner-public.pem"
    private_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    public_path.write_bytes(key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    private_path.chmod(0o600)
    public_path.chmod(0o600)
    pub_sha = hashlib.sha256(public_path.read_bytes()).hexdigest()
    monkeypatch.setattr(auth_module, "OWNER_TRUSTED_PUBLIC_PEM_SHA256", pub_sha)
    run_id = "synthetic-g48-" + role
    output_dir = tmp_path / run_id
    output_dir.mkdir(mode=0o700)
    output = output_dir / (role + ".private.json")
    lock = tmp_path / "synthetic-runtime.hashes.lock"
    lock.write_bytes(b"synthetic-only-dependency-lock\\n")
    lock_sha = hashlib.sha256(lock.read_bytes()).hexdigest()
    image = "sha256:" + "e" * 64
    issued = datetime.now(UTC)
    scope = make_owner_scope(
        frozen=pack[0], owner_freeze=pack[1],
        adapter_bindings=pack[2], input_manifest=pack[3],
        model_role=role, run_id=run_id,
        output_filename=output.name, output_directory=str(output_dir),
        dependency_lock_sha256=lock_sha, runtime_image_digest=image,
        issued_at_utc=issued.isoformat(),
        expires_at_utc=(issued + timedelta(hours=1)).isoformat(),
    )
    receipt_file = tmp_path / ("owner-" + role + ".private.json")
    receipt_sha = owner_sign_create_only(
        scope=scope, private_key_path=private_path, receipt_path=receipt_file
    )
    return {
        "owner_authorization_receipt_path": receipt_file,
        "trusted_owner_public_key_pem_path": public_path,
        "runtime_lock_path": lock,
        "runtime_image_digest": image,
    }, output, receipt_sha


@pytest.mark.parametrize("role", ROLES)
def test_complete_bridge_signed_owner_synthetic_48_outputs_sidecar_no_overwrite(
    tmp_path, monkeypatch, role,
):
    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    auth, output, signed_sha = synthetic_signed_owner_receipt(
        tmp_path, monkeypatch, pack, role
    )
    backend = SyntheticIdentityBackend(pack, role)
    receipt = run_gold48_generation_batch(
        **build_call(pack, role=role), **auth,
        backend=backend, output_path=output,
        source_evidence_paths=evidence,
    )
    assert receipt.status == "GENERATION_BATCH_PASS"
    assert receipt.record_count == 48
    assert len(backend.calls) == 48
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    data = json.loads(output.read_text())
    assert [r["effective_seed"] for r in data["outputs"]] == list(range(42, 90))
    assert [r["sample_id"] for r in data["outputs"]] == [
        f"G48-C{i:02d}" for i in range(1, 49)
    ]
    assert all(x["eos_token_ids"] == [248046, 248044]
               and x["pad_token_id"] == 248044
               and x["enable_thinking"] is False
               and x["max_new_tokens"] == 2048 for x in backend.calls)

    sidecar_path = output.with_name(output.name + ".identity.private.json")
    assert stat.S_IMODE(sidecar_path.stat().st_mode) == 0o600
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["schema"] == "storyforge_r60_gold48_generation_identity_private_v1"
    assert sidecar["run_id"] == output.parent.name
    assert sidecar["selected_model_role"] == role
    assert set(sidecar["arms"]) == set(ROLES)
    assert sidecar["arms"][role]["adapter_sha256"] == pack[2]["arms"][role]["expected_sha256"]
    assert sidecar["owner_authorization_receipt_sha256"] == signed_sha
    assert sidecar["runtime_image_measured"] is False
    assert sidecar["runtime_image_identity_source"] == (
        "OWNER_SIGNED_CONFIGURATION_ONLY__NOT_MEASURED"
    )
    assert sidecar["provider_image_attestation_sha256"] is None
    assert sidecar["input_sha256"] == pack[3]["sha256"]
    assert sidecar["model_revision"] == pack[0]["base_model"]["revision"]
    assert sidecar["runtime_image_digest"] == auth["runtime_image_digest"]
    assert sidecar["dependency_lock_sha256"] == hashlib.sha256(
        auth["runtime_lock_path"].read_bytes()
    ).hexdigest()
    assert sidecar["output_sha256"] == receipt.output_sha256
    assert "synthetic-response" not in json.dumps(sidecar)
    second_backend = SyntheticIdentityBackend(pack, role)
    with pytest.raises(WorkerError, match="GOLD48_OUTPUT_ALREADY_EXISTS_HOLD"):
        run_gold48_generation_batch(
            **build_call(pack, role=role), **auth,
            backend=second_backend, output_path=output,
            source_evidence_paths=evidence,
        )
    assert second_backend.calls == []
    assert json.loads(output.read_text()) == data
    assert json.loads(sidecar_path.read_text()) == sidecar


def test_signed_receipt_tampering_and_untrusted_key_rejected_before_generate(
    tmp_path, monkeypatch,
):
    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    role = "r60_base336"
    auth, out, _ = synthetic_signed_owner_receipt(tmp_path, monkeypatch, pack, role)
    backend = SyntheticIdentityBackend(pack, role)
    receipt_path = auth["owner_authorization_receipt_path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["payload"]["input_sha256"] = "0" * 64
    receipt_path.write_bytes(_canonical(receipt) + b"\n")
    with pytest.raises(WorkerError, match="GOLD48_OWNER_RECEIPT_SIGNATURE_INVALID_HOLD"):
        run_gold48_generation_batch(
            **build_call(pack, role=role), **auth,
            backend=backend, output_path=out, source_evidence_paths=evidence,
        )
    assert backend.calls == []
    assert not out.exists()

    # An attacker cannot nominate a different trust anchor via the receipt.
    import storyforge_dataset.generation_eval.gold48_owner_receipt as auth_module
    monkeypatch.setattr(auth_module, "OWNER_TRUSTED_PUBLIC_PEM_SHA256", "0" * 64)
    with pytest.raises(WorkerError, match="GOLD48_OWNER_TRUST_ANCHOR_MISMATCH_HOLD"):
        run_gold48_generation_batch(
            **build_call(pack, role=role), **auth,
            backend=backend, output_path=out, source_evidence_paths=evidence,
        )


def test_signed_receipt_wrong_backend_identity_holds(tmp_path, monkeypatch):
    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    role = "r60_base336"
    auth, out, _ = synthetic_signed_owner_receipt(tmp_path, monkeypatch, pack, role)
    backend = SyntheticIdentityBackend(pack, role)
    backend.gold48_adapter_sha256 = "0" * 64
    with pytest.raises(WorkerError, match="GOLD48_LOADED_BACKEND_IDENTITY_HOLD"):
        run_gold48_generation_batch(
            **build_call(pack, role=role), **auth,
            backend=backend, output_path=out, source_evidence_paths=evidence,
        )
    assert backend.calls == []
    assert not out.exists()

def test_owner_local_accept_and_sign_cli_synthetic_no_gpu(tmp_path):
    """Exercises actual Owner CLI with synthetic receipts only, not Owner Mac."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path / "owner-private"
    root.mkdir(mode=0o700)
    pack[2].update({
        "status": "CANDIDATE_PENDING_OWNER_SOURCE_ATTESTATION_AND_MOUNT",
        "owner_receipt_verified": False,
        "provider_volume_attestation_verified": False,
        "current_remote_weight_bytes_verified_all_three": False,
    })
    files = [
        (root / "owner.json", pack[1]),
        (root / "candidate.json", pack[2]),
        (root / "manifest.json", pack[3]),
    ]
    for path, payload in files:
        path.write_bytes(_canonical(payload) + b"\n")
        path.chmod(0o600)
    pack[4].chmod(0o600)
    script = repo / "scripts/r60_gold48_owner_generation_authority_cpu.py"
    frozen = repo / "experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json"
    base_args = [
        sys.executable, str(script),
        "--frozen-profile", str(frozen),
        "--owner-freeze", str(files[0][0]),
        "--adapter-bindings", str(files[1][0]),
        "--input-manifest", str(files[2][0]),
        "--input-jsonl", str(pack[4]),
        "--r46-evidence", str(evidence["r46_v02"]),
        "--r54-evidence", str(evidence["r54_v03a"]),
        "--r60-evidence", str(evidence["r60_base336"]),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    accepted_path = root / "accepted-bindings.private.json"
    accept = [
        *base_args, "--mode", "accept-bindings",
        "--explicit-owner-accept", "--accepted-output", str(accepted_path),
    ]
    first = subprocess.run(accept, capture_output=True, text=True, env=env, check=False)
    assert first.returncode == 0, first.stdout
    accepted = json.loads(accepted_path.read_text())
    assert accepted["owner_receipt_verified"] is True
    assert accepted["provider_volume_attestation_verified"] is False
    assert stat.S_IMODE(accepted_path.stat().st_mode) == 0o600
    repeated = subprocess.run(accept, capture_output=True, text=True, env=env, check=False)
    assert repeated.returncode == 2
    assert json.loads(repeated.stdout)["status"] == "HOLD"

    private = Ed25519PrivateKey.generate()
    key_path = root / "synthetic-test-owner-key.pem"
    key_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    key_path.chmod(0o600)
    run_id = "synthetic-owner-run-r46"
    receipt_path = root / "signed-one-arm.private.json"
    contract_path = repo / "requirements/r60-gold48-inference-cpu-contract.json"
    contract = json.loads(contract_path.read_text())
    # Construct explicit argv to avoid positional dependencies on base_args.
    sign = [
        sys.executable, str(script),
        "--mode", "sign-one-arm",
        "--frozen-profile", str(frozen),
        "--owner-freeze", str(files[0][0]),
        "--adapter-bindings", str(accepted_path),
        "--input-manifest", str(files[2][0]),
        "--input-jsonl", str(pack[4]),
        "--r46-evidence", str(evidence["r46_v02"]),
        "--r54-evidence", str(evidence["r54_v03a"]),
        "--r60-evidence", str(evidence["r60_base336"]),
        "--explicit-owner-generation-authorization",
        "--model-role", "r46_v02",
        "--run-id", run_id,
        "--output-directory", "/output/" + run_id,
        "--output-filename", "r46_v02.private.json",
        "--dependency-lock", str(repo / contract["lock_path"]),
        "--dependency-contract", str(contract_path),
        "--runtime-image", contract["base_image"],
        "--owner-private-ed25519-key", str(key_path),
        "--signed-receipt-output", str(receipt_path),
    ]
    created = subprocess.run(sign, capture_output=True, text=True, env=env, check=False)
    assert created.returncode == 0, created.stdout
    signed = json.loads(receipt_path.read_text())
    assert signed["schema"] == "storyforge_r60_gold48_owner_generation_ed25519_private_v1"
    assert signed["payload"]["model_role"] == "r46_v02"
    assert signed["payload"]["run_id"] == run_id
    assert signed["payload"]["input_sha256"] == pack[3]["sha256"]
    assert signed["payload"]["adapter_bindings_canonical_sha256"] == _digest(accepted)
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert subprocess.run(sign, capture_output=True, env=env, check=False).returncode == 2


def test_recover_sidecar_from_existing_48_output_without_rerun(tmp_path, monkeypatch):
    """Sidecar failure keeps 48 genuine synthetic outputs, repairs metadata only."""
    from storyforge_dataset.hf_runtime.outputs import OutputManager

    role = "r46_v02"
    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    auth, output, _ = synthetic_signed_owner_receipt(tmp_path, monkeypatch, pack, role)
    backend = SyntheticIdentityBackend(pack, role)
    original = OutputManager.write_safe.__func__

    def fail_only_sidecar(cls, path, payload, *, mode=0o600):
        if path.name.endswith(".identity.private.json"):
            raise ValueError("synthetic-sidecar-publication-failure")
        return original(cls, path, payload, mode=mode)

    monkeypatch.setattr(OutputManager, "write_safe", classmethod(fail_only_sidecar))
    with pytest.raises(WorkerError, match="GOLD48_IDENTITY_SIDECAR_PUBLICATION_HOLD"):
        run_gold48_generation_batch(
            **build_call(pack, role=role), **auth,
            backend=backend, output_path=output,
            source_evidence_paths=evidence,
        )
    assert len(backend.calls) == 48
    assert output.is_file()
    before = hashlib.sha256(output.read_bytes()).hexdigest()
    marker = output.with_name(output.name + ".launch.private.json")
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    sidecar = output.with_name(output.name + ".identity.private.json")
    assert not sidecar.exists()
    monkeypatch.setattr(OutputManager, "write_safe", classmethod(original))
    recovered = recover_gold48_identity_sidecar(
        **build_call(pack, role=role), **auth,
        output_path=output, source_evidence_paths=evidence,
    )
    assert recovered.record_count == 48
    assert recovered.output_sha256 == before
    assert hashlib.sha256(output.read_bytes()).hexdigest() == before
    assert len(backend.calls) == 48  # no second generate() call
    sidecar_doc = json.loads(sidecar.read_text())
    assert sidecar_doc["recovered_from_existing_output_no_model_calls"] is True
    assert sidecar_doc["output_sha256"] == before
    assert sidecar_doc["pre_generation_launch_marker_canonical_sha256"] == _digest(
        json.loads(marker.read_text())
    )
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    with pytest.raises(WorkerError, match="GOLD48_RECOVERY_SIDECAR_ALREADY_EXISTS_HOLD"):
        recover_gold48_identity_sidecar(
            **build_call(pack, role=role), **auth,
            output_path=output, source_evidence_paths=evidence,
        )


def test_recover_rejects_truncated_output_or_missing_marker(tmp_path, monkeypatch):
    role = "base"
    pack = fixture(tmp_path)
    evidence = source_receipt_files(tmp_path, pack)
    auth, output, _ = synthetic_signed_owner_receipt(tmp_path, monkeypatch, pack, role)
    preexisting = {
        "schema": "storyforge_r60_generation_outputs_private_v1",
        "model_role": role, "model": "Qwen/Qwen3.8-27B",
        "revision": pack[0]["base_model"]["revision"],
        "seed": 42, "record_count": 48,
        "outputs": [],
    }
    output.write_bytes(_canonical(preexisting) + b"\n")
    output.chmod(0o600)
    with pytest.raises(WorkerError, match="GOLD48_PRIVATE_CONTRACT_READ_HOLD"):
        recover_gold48_identity_sidecar(
            **build_call(pack, role=role), **auth,
            output_path=output, source_evidence_paths=evidence,
        )
    from storyforge_dataset.generation_eval.gold48_contract_bridge import (
        _gold48_launch_marker,
        _verify_authorized_run,
    )
    from storyforge_dataset.hf_runtime.outputs import OutputManager

    authorized, lock_sha = _verify_authorized_run(
        owner_authorization_receipt_path=auth["owner_authorization_receipt_path"],
        trusted_owner_public_key_pem_path=auth["trusted_owner_public_key_pem_path"],
        runtime_lock_path=auth["runtime_lock_path"],
        runtime_image_digest=auth["runtime_image_digest"],
        frozen=pack[0], owner_freeze=pack[1],
        bindings=pack[2], manifest=pack[3], role=role, output_path=output,
    )
    marker = _gold48_launch_marker(
        frozen=pack[0], bindings=pack[2], input_manifest=pack[3],
        role=role, auth=authorized, lock_sha256=lock_sha,
        runtime_image_digest=auth["runtime_image_digest"], output_path=output,
    )
    OutputManager.write_safe(
        output.with_name(output.name + ".launch.private.json"), marker
    )
    with pytest.raises(WorkerError, match="GOLD48_RECOVERY_OUTPUT_SCHEMA_HOLD"):
        recover_gold48_identity_sidecar(
            **build_call(pack, role=role), **auth,
            output_path=output, source_evidence_paths=evidence,
        )

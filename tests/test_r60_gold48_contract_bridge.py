"""Synthetic, no-weight Gold48 contract and existing generation-loop integration."""
from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path

import pytest

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    INPUT_SCHEMA, OWNER_SCHEMA, BINDINGS_SCHEMA, ROLES, PROVENANCE,
    _canonical, _digest, prepare_gold48_generation_contract,
    run_gold48_generation_batch, read_private_contract,
)
from storyforge_dataset.generation_eval.worker import (
    GenerationResult, WorkerError, _run_validated_generation_batch,
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
    return dict(
        frozen=frozen, owner_freeze=owner,
        adapter_bindings=bindings, input_manifest=manifest,
        input_path=path, model_role=role,
    )


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
            backend=RecordingBackend(), separate_owner_authorization=None,
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

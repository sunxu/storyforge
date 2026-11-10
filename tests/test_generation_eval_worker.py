import hashlib
import json
import stat
from pathlib import Path

import pytest

from storyforge_dataset.generation_eval.profiles import EXPECTED_MODELS
from storyforge_dataset.generation_eval.worker import (
    GenerationResult,
    WorkerError,
    run_generation_batch,
)


class FakeBackend:
    def generate(self, **kwargs):
        return GenerationResult(
            text="synthetic response",
            input_tokens=12,
            output_tokens=4,
        )


def ready_profile():
    models = {}
    for role, (model, revision) in EXPECTED_MODELS.items():
        models[role] = {
            "model": model,
            "revision": revision,
            "enable_thinking": role == "A",
            "sampling": {"do_sample": True, "temperature": 0.7, "top_p": 0.9},
            "chat_template_sha256": "a" * 64,
        }
    return {
        "schema": "storyforge_r60_p3_model_profiles_v1",
        "model_profiles": models,
        "context_ceiling_tokens": 32768,
        "input_budget_tokens": 28672,
        "generation_budget_tokens": 4096,
        "seed": 42,
        "runtime_digest": "sha256:" + "e" * 64,
        "dependency_lock_sha256": "d" * 64,
        "tokenizer_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "profile_freeze_authorized": True,
        "inference_authorized": True,
        "gpu_authorized": True,
        "training_authorized": False,
    }


def write_input(tmp_path: Path, records):
    data = "".join(json.dumps(row) + "\n" for row in records).encode()
    path = tmp_path / "input.jsonl"
    path.write_bytes(data)
    manifest = {
        "schema": "storyforge_r60_generation_input_manifest_v1",
        "record_count": len(records),
        "sha256": hashlib.sha256(data).hexdigest(),
        "max_input_tokens": 100,
        "max_new_tokens": 128,
        "seed": 42,
    }
    return path, manifest


def sample_records():
    return [
        {"sample_id": "case-001", "messages": [
            {"role": "system", "content": "You are a fiction model."},
            {"role": "user", "content": "Continue the story."},
        ]},
        {"sample_id": "case-002", "messages": [
            {"role": "user", "content": "Describe the scene."},
        ]},
    ]


def test_worker_writes_private_output_and_safe_receipt(tmp_path: Path):
    input_path, manifest = write_input(tmp_path, sample_records())
    output_path = tmp_path / "private-output.json"
    receipt = run_generation_batch(
        profile=ready_profile(),
        model_role="A",
        manifest=manifest,
        input_path=input_path,
        output_path=output_path,
        backend=FakeBackend(),
    )
    safe = receipt.to_safe_dict()
    assert receipt.status == "GENERATION_BATCH_PASS"
    assert receipt.record_count == 2
    assert stat.S_IMODE(output_path.stat().st_mode) == 0o600
    assert safe["private_values_emitted"] is False
    assert "synthetic response" not in json.dumps(safe)
    assert json.loads(output_path.read_text())["record_count"] == 2


def test_worker_rejects_unfrozen_profile_before_backend(tmp_path: Path):
    profile = ready_profile()
    profile["gpu_authorized"] = False
    input_path, manifest = write_input(tmp_path, sample_records())
    with pytest.raises(WorkerError, match="GENERATION_PROFILE_NOT_READY"):
        run_generation_batch(
            profile=profile,
            model_role="A",
            manifest=manifest,
            input_path=input_path,
            output_path=tmp_path / "output.json",
            backend=FakeBackend(),
        )


def test_worker_rejects_input_digest_mismatch(tmp_path: Path):
    input_path, manifest = write_input(tmp_path, sample_records())
    manifest["sha256"] = "0" * 64
    with pytest.raises(WorkerError, match="INPUT_VERIFICATION_FAILED"):
        run_generation_batch(
            profile=ready_profile(),
            model_role="A",
            manifest=manifest,
            input_path=input_path,
            output_path=tmp_path / "output.json",
            backend=FakeBackend(),
        )


def test_worker_rejects_duplicate_sample_ids(tmp_path: Path):
    records = sample_records()
    records[1]["sample_id"] = records[0]["sample_id"]
    input_path, manifest = write_input(tmp_path, records)
    with pytest.raises(WorkerError, match="INPUT_SAMPLE_ID_DUPLICATE"):
        run_generation_batch(
            profile=ready_profile(),
            model_role="A",
            manifest=manifest,
            input_path=input_path,
            output_path=tmp_path / "output.json",
            backend=FakeBackend(),
        )


def test_worker_rejects_output_token_overrun(tmp_path: Path):
    class OverrunBackend:
        def generate(self, **kwargs):
            return GenerationResult("too long", 12, 129)

    input_path, manifest = write_input(tmp_path, sample_records())
    with pytest.raises(WorkerError, match="OUTPUT_TOKEN_BUDGET_EXCEEDED"):
        run_generation_batch(
            profile=ready_profile(),
            model_role="A",
            manifest=manifest,
            input_path=input_path,
            output_path=tmp_path / "output.json",
            backend=OverrunBackend(),
        )


def test_worker_never_overwrites_existing_output(tmp_path: Path):
    input_path, manifest = write_input(tmp_path, sample_records())
    output_path = tmp_path / "output.json"
    output_path.write_text("existing")
    with pytest.raises(WorkerError, match="OUTPUT_PUBLICATION_FAILED"):
        run_generation_batch(
            profile=ready_profile(),
            model_role="A",
            manifest=manifest,
            input_path=input_path,
            output_path=output_path,
            backend=FakeBackend(),
        )
    assert output_path.read_text() == "existing"

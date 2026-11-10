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
from storyforge_dataset.generation_eval.worker_cli import main as worker_main


class FakeBackend:
    @property
    def gpu_started(self):
        return False

    def generate(self, **kwargs):
        return GenerationResult(
            text="synthetic response",
            input_tokens=12,
            output_tokens=4,
            finish_reason="eos",
        )


def ready_profile():
    models = {}
    for role, (model, revision) in EXPECTED_MODELS.items():
        models[role] = {
            "model": model,
            "revision": revision,
            "enable_thinking": True if role == "A" else None,
            "thinking_mode": "api_flag" if role == "A" else ("template_default" if role == "B" else "explicit_generation_prefix"),
            "generation_prefix": "<think>" if role == "challenger" else None,
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
        "evaluation_prompt_sha256": "e" * 64,
        "output_schema_sha256": "f" * 64,
        "p3_download_safe_sha256": "a" * 64,
        "tokenizer_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "tokenizer_file_hashes": {"A":{"config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","generation_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","merges.txt":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","vocab.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"B":{"chat_template.jinja":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","generation_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","special_tokens_map.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"challenger":{"chat_template.jinja":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","generation_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","special_tokens_map.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","tokenizer_config.json":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}},
        "generation_config_hashes": {role: "c" * 64 for role in EXPECTED_MODELS},
        "eos_token_ids": {
            "A": [151645, 151643],
            "B": [151329, 151336, 151338],
            "challenger": [151329, 151336, 151338],
        },
        "pad_token_ids": {"A": 151643, "B": 151329, "challenger": 151329},
        "custom_stop_sequences": {"A": [], "B": [], "challenger": []},
        "finish_reason_policy": {
            "eos_source": "pinned_generation_config_eos_token_id",
            "length_definition": "max_new_tokens_exhausted_without_eos",
            "unexpected_stop_action": "hold",
        },
        "truncation_policy": "reject_over_budget_no_silent_prompt_truncation",
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
    assert receipt.finish_reason_counts == {"eos": 2, "length": 0, "unrecognized_stop": 0}
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


def test_worker_records_length_stops_and_effective_per_sample_seeds(tmp_path: Path):
    class LengthBackend(FakeBackend):
        def generate(self, **kwargs):
            return GenerationResult(
                text="partial", input_tokens=12, output_tokens=128, finish_reason="length"
            )

    input_path, manifest = write_input(tmp_path, sample_records())
    output_path = tmp_path / "private-output.json"
    receipt = run_generation_batch(
        profile=ready_profile(), model_role="A", manifest=manifest,
        input_path=input_path, output_path=output_path, backend=LengthBackend(),
    )
    saved = json.loads(output_path.read_text())
    assert receipt.status == "GENERATION_BATCH_PASS_WITH_LENGTH_STOPS"
    assert receipt.finish_reason_counts["length"] == 2
    assert [row["effective_seed"] for row in saved["outputs"]] == [42, 43]
    assert all(row["finish_reason"] == "length" for row in saved["outputs"])


def test_worker_holds_on_unrecognized_stop_reason(tmp_path: Path):
    class UnknownBackend(FakeBackend):
        def generate(self, **kwargs):
            return GenerationResult(
                text="partial", input_tokens=12, output_tokens=4,
                finish_reason="unrecognized_stop",
            )

    input_path, manifest = write_input(tmp_path, sample_records())
    receipt = run_generation_batch(
        profile=ready_profile(), model_role="A", manifest=manifest,
        input_path=input_path, output_path=tmp_path / "private-output.json",
        backend=UnknownBackend(),
    )
    assert receipt.status == "GENERATION_BATCH_HOLD_UNRECOGNIZED_STOP"
    assert receipt.finish_reason_counts["unrecognized_stop"] == 2



def test_worker_cli_holds_before_runtime_when_profile_not_frozen(tmp_path: Path, capsys):
    profile_path = tmp_path / "profile.json"
    profile = ready_profile()
    profile.update({
        "status": "P4_PROFILE_CANDIDATE__NOT_FROZEN",
        "profile_freeze_authorized": False,
        "inference_authorized": False,
        "gpu_authorized": False,
        "training_authorized": False,
    })
    profile_path.write_text(json.dumps(profile))
    code = worker_main([
        "--model-role", "A",
        "--profile", str(profile_path),
        "--manifest", str(tmp_path / "manifest.json"),
        "--input", str(tmp_path / "inputs.jsonl"),
        "--output-dir", "/output/test-run",
        "--repo-root", str(tmp_path),
    ])
    report = json.loads(capsys.readouterr().out)
    assert code == 2
    assert report["status"] == "GENERATION_WORKER_HOLD"
    assert report["reason_code"] == "GENERATION_PROFILE_NOT_AUTHORIZED"
    assert report["inference_started"] is False
    assert report["gpu_started"] is False
    assert report["training_started"] is False

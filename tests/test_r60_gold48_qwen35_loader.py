"""No-model, synthetic Gold48 Qwen3.8 conditional+LoRA loader tests."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from storyforge_dataset.generation_eval.backend import TransformersGenerationBackend
from storyforge_dataset.generation_eval.gold48_qwen35_loader import (
    ALLOWED_TARGETS,
    MODEL,
    REVISION,
    TARGET_PREFIX,
    WorkerError,
    _hash_adapter_weights,
    load_pinned_gold48_backend,
    verify_adapter_config,
    verify_base_snapshot_metadata,
)


def fixture_adapter():
    return {
        "base_model_name_or_path":
            "/tmp/r60/cache/models--Qwen--Qwen3.8-27B/snapshots/" + REVISION,
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "r": 64,
        "lora_alpha": 128,
        "inference_mode": True,
        "target_modules":
            TARGET_PREFIX + "(" + "|".join(sorted(ALLOWED_TARGETS)) + "))$",
    }


def test_pinned_adapter_training_metadata_accepts_reordered_modules():
    v = fixture_adapter()
    verify_adapter_config(v)
    v["target_modules"] = (
        TARGET_PREFIX + "(" + "|".join(sorted(ALLOWED_TARGETS, reverse=True)) + "))$"
    )
    verify_adapter_config(v)


@pytest.mark.parametrize("attribute,change", [
    ("base_model_name_or_path", "/cache/models--Qwen--Qwen3.8-27B/snapshots/bad"),
    ("r", 8),
    ("lora_alpha", 64),
    ("peft_type", "PREFIX_TUNING"),
    ("task_type", "SEQ_2_SEQ_LM"),
    ("inference_mode", False),
    ("target_modules", "q_proj,v_proj"),
])
def test_wrong_adapter_metadata_holds(attribute, change):
    adapter = fixture_adapter()
    adapter[attribute] = change
    with pytest.raises(WorkerError, match="GOLD48_ADAPTER_IDENTITY_OR_GEOMETRY_HOLD"):
        verify_adapter_config(adapter)


def test_missing_target_module_holds():
    adapter = fixture_adapter()
    adapter["target_modules"] = (
        TARGET_PREFIX + "(" + "|".join(sorted(ALLOWED_TARGETS - {"k_proj"})) + "))$"
    )
    with pytest.raises(WorkerError, match="GOLD48_ADAPTER_TARGET_MODULES_HOLD"):
        verify_adapter_config(adapter)


def test_qwen35_generation_config_stop_metadata_exact():
    verify_base_snapshot_metadata(
        {"model_type": "qwen3_5", "architectures": ["Qwen3_5ForConditionalGeneration"]},
        {"eos_token_id": [248046, 248044], "pad_token_id": 248044},
    )
    with pytest.raises(WorkerError, match="GOLD48_BASE_QWEN35_CONFIG_HOLD"):
        verify_base_snapshot_metadata(
            {"model_type": "qwen3", "architectures": ["Qwen3ForCausalLM"]},
            {"eos_token_id": [248046, 248044], "pad_token_id": 248044},
        )


def test_no_runtime_authorization_no_gpu_or_model_import():
    with pytest.raises(WorkerError, match="GOLD48_RUNTIME_NOT_AUTHORIZED"):
        load_pinned_gold48_backend(
            adapter_dir=None, expected_adapter_sha256=None,
            expected_template_sha256="a" * 64,
        )


def test_frozen_expected_adapter_hash_is_mandatory_and_file_is_stream_checked(tmp_path):
    weight_file = tmp_path / "adapter_model.safetensors"
    weight_file.write_bytes(b"synthetic-only")
    with pytest.raises(WorkerError, match="GOLD48_ADAPTER_EXPECTED_SHA_REQUIRED"):
        _hash_adapter_weights(weight_file, "wrong")
    with pytest.raises(WorkerError, match="GOLD48_ADAPTER_FILE_SIZE_HOLD"):
        _hash_adapter_weights(weight_file, "a" * 64)


def test_synthetic_class_loader_only_reuses_existing_generation_engine(monkeypatch, tmp_path):
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader

    calls = []
    template = "{% for message in messages %}{{ message.content }}{% endfor %}"
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()

    class FakeModel:
        def __init__(self):
            self.hf_device_map = {"": 0}

        def eval(self):
            calls.append("eval")
            return self

    class FakeQwen35:
        @staticmethod
        def from_pretrained(model_id, **kwargs):
            assert model_id == MODEL
            assert kwargs["revision"] == REVISION
            assert kwargs["device_map"] == {"": 0}
            assert kwargs["trust_remote_code"] is False
            calls.append("model")
            return FakeModel()

    class FakeTokenizer:
        @staticmethod
        def from_pretrained(model_id, **kwargs):
            assert model_id == MODEL
            assert kwargs["revision"] == REVISION
            calls.append("tokenizer")
            return SimpleNamespace(chat_template=template)

    def peft_adapter_from_pretrained(model, path, **kwargs):
        assert isinstance(model, FakeModel)
        assert kwargs["is_trainable"] is False
        calls.append("adapter")
        return model

    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            is_bf16_supported=lambda: True,
        ),
        bfloat16="bf16",
    )
    fake_transformers = SimpleNamespace(
        AutoTokenizer=FakeTokenizer,
        Qwen3_5ForConditionalGeneration=FakeQwen35,
    )
    fake_peft = SimpleNamespace(
        PeftModel=SimpleNamespace(from_pretrained=peft_adapter_from_pretrained),
    )
    adapter_dir = tmp_path / "ckpt"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps(fixture_adapter()), encoding="utf-8"
    )
    (adapter_dir / "adapter_model.safetensors").write_bytes(b"synthetic-only")
    monkeypatch.setattr(loader, "_hash_adapter_weights",
                        lambda *_args: calls.append("streaming_hash"))

    backend = load_pinned_gold48_backend(
        adapter_dir=adapter_dir,
        expected_adapter_sha256="b" * 64,
        expected_template_sha256=template_hash,
        runtime_authorized=True,
        torch_module=fake_torch,
        transformers_module=fake_transformers,
        peft_module=fake_peft,
    )
    assert isinstance(backend, TransformersGenerationBackend)
    assert backend.model_id == MODEL
    assert backend.revision == REVISION
    assert backend.gpu_started is True  # synthetic mock, not an actual GPU
    assert calls == ["streaming_hash", "tokenizer", "model", "adapter", "eval"]


def test_wrong_template_sha_rejects_before_any_model_load():
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            is_bf16_supported=lambda: True,
        ),
    )
    fake_transformers = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: SimpleNamespace(chat_template="chat")
        ),
        Qwen3_5ForConditionalGeneration=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: pytest.fail("model should not load")
        ),
    )
    with pytest.raises(WorkerError, match="GOLD48_CHAT_TEMPLATE_SHA_MISMATCH_HOLD"):
        load_pinned_gold48_backend(
            adapter_dir=None, expected_adapter_sha256=None,
            expected_template_sha256="a" * 64,
            runtime_authorized=True,
            torch_module=fake_torch,
            transformers_module=fake_transformers,
        )

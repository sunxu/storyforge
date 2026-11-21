"""No-model, synthetic Gold48 Qwen3.8 conditional+LoRA loader tests."""
from __future__ import annotations

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


def test_training_checkpoint_float_lora_alpha_is_accepted():
    adapter = fixture_adapter()
    adapter["lora_alpha"] = 128.0
    verify_adapter_config(adapter)


@pytest.mark.parametrize("attribute,change", [
    ("base_model_name_or_path", "/cache/models--Qwen--Qwen3.8-27B/snapshots/bad"),
    ("r", 8),
    ("lora_alpha", 64),
    ("lora_alpha", 127.5),
    ("lora_alpha", "128"),
    ("lora_alpha", float("nan")),
    ("lora_alpha", True),
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
    with pytest.raises(WorkerError, match="GOLD48_SIGNED_LAUNCH_PERMIT_REQUIRED"):
        load_pinned_gold48_backend(
            adapter_dir=None, expected_adapter_sha256=None,
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

    # Only the synthetic loader unit test substitutes the signed pre-GPU gate.
    # The real gate is exercised in test_r60_gold48_contract_bridge.py.
    monkeypatch.setattr(loader, "verify_and_consume_gold48_load_permit",
                        lambda **_kwargs: None)
    calls = []
    template = "{% set enable_thinking = false %}{% for message in messages %}{{ message.content }}{% endfor %}"
    monkeypatch.setattr(loader, "_load_pinned_chat_template", lambda: template)

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
    def fake_base_config(model_id, **kwargs):
        assert (model_id, kwargs) == (
            MODEL, {"revision": REVISION, "trust_remote_code": False}
        )
        calls.append("base_config")
        return SimpleNamespace(
            model_type="qwen3_5", architectures=["Qwen3_5ForConditionalGeneration"]
        )

    def fake_generation_config(model_id, **kwargs):
        assert (model_id, kwargs) == (MODEL, {"revision": REVISION})
        calls.append("generation_config")
        return SimpleNamespace(eos_token_id=[248046, 248044], pad_token_id=248044)

    fake_transformers = SimpleNamespace(
        AutoConfig=SimpleNamespace(from_pretrained=fake_base_config),
        GenerationConfig=SimpleNamespace(from_pretrained=fake_generation_config),
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
        launch_permit=SimpleNamespace(
            owner_receipt_path=tmp_path / "test-only-owner",
            runtime_lock_path=tmp_path / "test-only-lock",
            provider_attestation_path=tmp_path / "test-only-provider",
            provider_public_key_path=tmp_path / "test-only-provider-pub",
            spent_receipt_path=tmp_path / "test-only-spent-grant",
        ),
        torch_module=fake_torch,
        transformers_module=fake_transformers,
        peft_module=fake_peft,
    )
    assert isinstance(backend, TransformersGenerationBackend)
    assert backend.model_id == MODEL
    assert backend.revision == REVISION
    assert backend.gpu_started is True  # synthetic mock, not an actual GPU
    assert calls == [
        "base_config", "generation_config", "tokenizer",
        "streaming_hash", "model", "adapter", "eval",
    ]


def test_mismatched_pinned_template_rejects_before_any_model_load(monkeypatch):
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader

    monkeypatch.setattr(loader, "verify_and_consume_gold48_load_permit",
                        lambda **_kwargs: None)
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            is_bf16_supported=lambda: True,
        ),
    )
    fake_transformers = SimpleNamespace(
        AutoConfig=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: SimpleNamespace(
                model_type="qwen3_5", architectures=["Qwen3_5ForConditionalGeneration"]
            )
        ),
        GenerationConfig=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: SimpleNamespace(
                eos_token_id=[248046, 248044], pad_token_id=248044
            )
        ),
        AutoTokenizer=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: SimpleNamespace(chat_template="chat")
        ),
        Qwen3_5ForConditionalGeneration=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: pytest.fail("model should not load")
        ),
    )
    monkeypatch.setattr(loader, "_load_pinned_chat_template",
                        lambda: "{% set enable_thinking = false %}pinned")
    with pytest.raises(WorkerError, match="GOLD48_PINNED_CHAT_TEMPLATE_MISMATCH_HOLD"):
        load_pinned_gold48_backend(
            adapter_dir=None, expected_adapter_sha256=None,
            launch_permit=object(),
            torch_module=fake_torch,
            transformers_module=fake_transformers,
        )


@pytest.mark.parametrize(("bad_field", "bad_value"), [
    ("model_type", "qwen3"),
    ("architectures", ["Qwen3_5ForCausalLM"]),
    ("eos_token_id", [248046]),
    ("pad_token_id", 123),
])
def test_runtime_base_metadata_mismatch_holds_before_weight_load(
    bad_field, bad_value, monkeypatch,
):
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader

    monkeypatch.setattr(loader, "verify_and_consume_gold48_load_permit",
                        lambda **_kwargs: None)
    config = {
        "model_type": "qwen3_5",
        "architectures": ["Qwen3_5ForConditionalGeneration"],
    }
    generation = {"eos_token_id": [248046, 248044], "pad_token_id": 248044}
    if bad_field in config:
        config[bad_field] = bad_value
    else:
        generation[bad_field] = bad_value

    def reject_weight_load(*_args, **_kwargs):
        pytest.fail("model weights must not be loaded on metadata mismatch")

    fake_transformers = SimpleNamespace(
        AutoConfig=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: SimpleNamespace(**config)
        ),
        GenerationConfig=SimpleNamespace(
            from_pretrained=lambda *_a, **_kw: SimpleNamespace(**generation)
        ),
        AutoTokenizer=SimpleNamespace(from_pretrained=reject_weight_load),
        Qwen3_5ForConditionalGeneration=SimpleNamespace(from_pretrained=reject_weight_load),
    )
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True, is_bf16_supported=lambda: True)
    )
    with pytest.raises(WorkerError, match="GOLD48_BASE_QWEN35_CONFIG_HOLD"):
        load_pinned_gold48_backend(
            adapter_dir=None,
            expected_adapter_sha256=None,
            launch_permit=object(),  # synthetic-only gate stub, no actual GPU
            torch_module=fake_torch,
            transformers_module=fake_transformers,
        )


def test_legacy_boolean_cannot_unlock_loader_before_gpu():
    with pytest.raises(TypeError, match="runtime_authorized"):
        load_pinned_gold48_backend(
            adapter_dir=None, expected_adapter_sha256=None,
            runtime_authorized=True,
        )


def test_forged_launch_object_rejected_before_torch_import(monkeypatch):
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader

    def reject_gpu_import(_name):
        pytest.fail("untrusted pre-GPU authorization must not import torch")

    monkeypatch.setattr(loader.importlib, "import_module", reject_gpu_import)
    with pytest.raises(WorkerError, match="GOLD48_SIGNED_LAUNCH_PERMIT_REQUIRED"):
        load_pinned_gold48_backend(
            adapter_dir=None,
            expected_adapter_sha256=None,
            launch_permit={"caller": "provided-dict"},
        )

def test_pinned_public_template_is_fetched_at_exact_model_revision(
    tmp_path, monkeypatch,
):
    import storyforge_dataset.generation_eval.gold48_qwen35_loader as loader

    template = "{% set enable_thinking = false %}exact-pinned-template"
    path = tmp_path / "chat_template.jinja"
    path.write_text(template, encoding="utf-8")
    observed = []

    def fake_download(**kwargs):
        observed.append(kwargs)
        return str(path)

    fake_module = SimpleNamespace(hf_hub_download=fake_download)
    monkeypatch.setattr(
        loader, "importlib",
        SimpleNamespace(import_module=lambda name: (
            fake_module if name == "huggingface_hub" else
            pytest.fail("unexpected module import")
        )),
    )
    assert loader._load_pinned_chat_template() == template
    assert observed == [{
        "repo_id": MODEL,
        "filename": "chat_template.jinja",
        "revision": REVISION,
    }]
    path.write_bytes(b"x" * 65537)
    with pytest.raises(WorkerError, match="GOLD48_PINNED_TEMPLATE_FILE_HOLD"):
        loader._load_pinned_chat_template()



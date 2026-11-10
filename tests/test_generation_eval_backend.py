import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from storyforge_dataset.generation_eval.backend import TransformersGenerationBackend
from storyforge_dataset.generation_eval.worker import WorkerError


class FakeTensor:
    def __init__(self, values):
        self.values = values
        self.shape = (1, len(values))

    def __getitem__(self, index):
        return FakeTensor(self.values[index]) if isinstance(index, slice) else self.values[index]

    def to(self, device):
        return self


class FakeTokenizer:
    chat_template = "embedded template"
    pad_token_id = 0

    def apply_chat_template(self, messages, **kwargs):
        return {"input_ids": FakeTensor([1, 2, 3])}

    def decode(self, tokens, skip_special_tokens=True):
        return "fake output"


class FakeModel:
    hf_device_map = {"model": 0}
    device = SimpleNamespace(type="cuda")
    config = SimpleNamespace(_name_or_path="fake-model")

    def eval(self):
        return self

    def generate(self, **kwargs):
        return [FakeTensor([1, 2, 3, 4, 5])]


class FakeCuda:
    def is_available(self):
        return True

    def is_bf16_supported(self):
        return True

    def manual_seed_all(self, seed):
        self.seed = seed


class FakeTorch:
    bfloat16 = "bfloat16"
    cuda = FakeCuda()

    def manual_seed(self, seed):
        self.seed = seed

    class inference_mode:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False


class FakeAutoTokenizer:
    @staticmethod
    def from_pretrained(*args, **kwargs):
        return FakeTokenizer()


class FakeAutoModel:
    @staticmethod
    def from_pretrained(*args, **kwargs):
        return FakeModel()


class FakeTransformers:
    AutoTokenizer = FakeAutoTokenizer
    AutoModelForCausalLM = FakeAutoModel


def test_embedded_template_hash_and_gpu_device_map_are_verified():
    digest = hashlib.sha256(b"embedded template").hexdigest()
    backend = TransformersGenerationBackend.from_pretrained(
        model_id="fake-model",
        revision="a" * 40,
        template_source="embedded_tokenizer_config",
        expected_template_sha256=digest,
        torch_module=FakeTorch(),
        transformers_module=FakeTransformers(),
    )
    assert backend.gpu_started is True


def test_standalone_template_hash_is_verified(tmp_path: Path):
    path = tmp_path / "chat_template.jinja"
    path.write_text("standalone template", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    backend = TransformersGenerationBackend.from_pretrained(
        model_id="fake-model",
        revision="a" * 40,
        template_source="standalone_chat_template.jinja",
        expected_template_sha256=digest,
        template_path=path,
        torch_module=FakeTorch(),
        transformers_module=FakeTransformers(),
    )
    assert backend.tokenizer.chat_template == "standalone template"


def test_template_hash_mismatch_fails_before_model_load(tmp_path: Path):
    path = tmp_path / "chat_template.jinja"
    path.write_text("unexpected template", encoding="utf-8")
    with pytest.raises(WorkerError, match="CHAT_TEMPLATE_SHA256_MISMATCH"):
        TransformersGenerationBackend.from_pretrained(
            model_id="fake-model",
            revision="a" * 40,
            template_source="standalone_chat_template.jinja",
            expected_template_sha256="0" * 64,
            template_path=path,
            torch_module=FakeTorch(),
            transformers_module=FakeTransformers(),
        )


def test_cpu_offload_is_rejected():
    with pytest.raises(WorkerError, match="MODEL_DEVICE_MAP_CPU_OFFLOAD_REJECTED"):
        TransformersGenerationBackend._verify_cuda_device_map(
            SimpleNamespace(hf_device_map={"layer": "cpu"})
        )


def test_generation_uses_explicit_sampling_and_reports_token_counts():
    backend = TransformersGenerationBackend(
        tokenizer=FakeTokenizer(),
        model=FakeModel(),
        torch_module=FakeTorch(),
    )
    result = backend.generate(
        model="fake-model",
        revision="a" * 40,
        messages=[{"role": "user", "content": "hello"}],
        sampling={"do_sample": True, "temperature": 0.6, "top_p": 0.95, "top_k": 20},
        enable_thinking=True,
        seed=42,
        max_input_tokens=100,
        max_new_tokens=10,
    )
    assert result.text == "fake output"
    assert result.input_tokens == 3
    assert result.output_tokens == 2


def test_greedy_mode_does_not_forward_sampling_knobs():
    class InspectModel(FakeModel):
        def generate(self, **kwargs):
            self.last_kwargs = kwargs
            return [FakeTensor([1, 2, 3, 4])]

    model = InspectModel()
    backend = TransformersGenerationBackend(
        tokenizer=FakeTokenizer(),
        model=model,
        torch_module=FakeTorch(),
    )
    backend.generate(
        model="fake-model",
        revision="a" * 40,
        messages=[{"role": "user", "content": "hello"}],
        sampling={"do_sample": False},
        enable_thinking=None,
        seed=1,
        max_input_tokens=100,
        max_new_tokens=10,
    )
    assert model.last_kwargs["do_sample"] is False
    assert "temperature" not in model.last_kwargs

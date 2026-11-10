import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

from storyforge_dataset.generation_eval.backend import TransformersGenerationBackend
from storyforge_dataset.generation_eval.worker import WorkerError


class FakeTensor:
    def __init__(self, values):
        self.values = values
        self.shape = (1, len(values))

    def __getitem__(self, index):
        return FakeTensor(self.values[index]) if isinstance(index, slice) else self.values[index]

    def tolist(self):
        return list(self.values)

    def to(self, device):
        return self


class FakeBatchEncoding(dict):
    def to(self, device):
        return self


class FakeTokenizer:
    chat_template = "embedded template"
    pad_token_id = 0

    def apply_chat_template(self, messages, **kwargs):
        return FakeBatchEncoding({"input_ids": FakeTensor([1, 2, 3])})

    def decode(self, tokens, skip_special_tokens=True):
        return "fake output"


class FakeModel:
    hf_device_map: ClassVar[dict[str, int]] = {"model": 0}
    device = SimpleNamespace(type="cuda")
    config = SimpleNamespace(_name_or_path="fake-model")

    def eval(self):
        return self

    def generate(self, **kwargs):
        return SimpleNamespace(sequences=[FakeTensor([1, 2, 3, 4, 5])])


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
    last_kwargs: ClassVar[dict[str, Any] | None] = None

    @staticmethod
    def from_pretrained(*args, **kwargs):
        FakeAutoModel.last_kwargs = kwargs
        return FakeModel()


class FakeTransformers:
    AutoTokenizer = FakeAutoTokenizer
    AutoModelForCausalLM = FakeAutoModel


def make_snapshot(tmp_path: Path, *, standalone: bool = False, template: str = "standalone template"):
    path = tmp_path / ("snapshot-standalone" if standalone else "snapshot-embedded")
    path.mkdir()
    names = (
        ["chat_template.jinja", "config.json", "generation_config.json",
         "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"]
        if standalone else
        ["config.json", "generation_config.json", "merges.txt", "tokenizer.json",
         "tokenizer_config.json", "vocab.json"]
    )
    hashes = {}
    for name in names:
        content = template.encode() if name == "chat_template.jinja" else ("fake:" + name).encode()
        (path / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    return path, hashes


def test_embedded_template_hash_and_gpu_device_map_are_verified(tmp_path: Path):
    digest = hashlib.sha256(b"embedded template").hexdigest()
    snapshot, file_hashes = make_snapshot(tmp_path)
    backend = TransformersGenerationBackend.from_pretrained(
        model_id="fake-model",
        revision="a" * 40,
        template_source="embedded_tokenizer_config",
        expected_template_sha256=digest,
        tokenizer_snapshot=snapshot,
        expected_tokenizer_file_hashes=file_hashes,
        torch_module=FakeTorch(),
        transformers_module=FakeTransformers(),
    )
    assert backend.gpu_started is True
    assert FakeAutoModel.last_kwargs["device_map"] == {"": 0}


def test_standalone_template_hash_is_verified(tmp_path: Path):
    snapshot, file_hashes = make_snapshot(tmp_path, standalone=True)
    digest = file_hashes["chat_template.jinja"]
    backend = TransformersGenerationBackend.from_pretrained(
        model_id="fake-model",
        revision="a" * 40,
        template_source="standalone_chat_template.jinja",
        expected_template_sha256=digest,
        tokenizer_snapshot=snapshot,
        expected_tokenizer_file_hashes=file_hashes,
        torch_module=FakeTorch(),
        transformers_module=FakeTransformers(),
    )
    assert backend.tokenizer.chat_template == "standalone template"


def test_template_hash_mismatch_fails_before_model_load(tmp_path: Path):
    snapshot, file_hashes = make_snapshot(
        tmp_path, standalone=True, template="unexpected template"
    )
    with pytest.raises(WorkerError, match="CHAT_TEMPLATE_SHA256_MISMATCH"):
        TransformersGenerationBackend.from_pretrained(
            model_id="fake-model",
            revision="a" * 40,
            template_source="standalone_chat_template.jinja",
            expected_template_sha256="0" * 64,
            tokenizer_snapshot=snapshot,
            expected_tokenizer_file_hashes=file_hashes,
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
        eos_token_ids=[5],
        pad_token_id=0,
    )
    assert result.text == "fake output"
    assert result.input_tokens == 3
    assert result.output_tokens == 2
    assert result.finish_reason == "eos"


def test_greedy_mode_does_not_forward_sampling_knobs():
    class InspectModel(FakeModel):
        def generate(self, **kwargs):
            self.last_kwargs = kwargs
            return SimpleNamespace(sequences=[FakeTensor([1, 2, 3, 4])])

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
        eos_token_ids=[4],
        pad_token_id=0,
    )
    assert model.last_kwargs["do_sample"] is False
    assert model.last_kwargs["eos_token_id"] == [4]
    assert model.last_kwargs["return_dict_in_generate"] is True
    assert "temperature" not in model.last_kwargs


def test_finish_reason_distinguishes_eos_length_and_unrecognized_stop():
    from storyforge_dataset.generation_eval.backend import classify_finish_reason

    assert classify_finish_reason([1, 2, 9], eos_token_ids=[9], max_new_tokens=10) == "eos"
    assert classify_finish_reason([1, 2, 3], eos_token_ids=[9], max_new_tokens=3) == "length"
    assert classify_finish_reason([1, 2], eos_token_ids=[9], max_new_tokens=10) == "unrecognized_stop"


def test_tokenizer_snapshot_hash_mismatch_fails_before_model_loading(tmp_path: Path):
    from storyforge_dataset.generation_eval.backend import verify_tokenizer_snapshot

    snapshot, file_hashes = make_snapshot(tmp_path)
    (snapshot / "tokenizer.json").write_text("tampered", encoding="utf-8")
    with pytest.raises(WorkerError, match="TOKENIZER_FILE_HASH_MISMATCH"):
        verify_tokenizer_snapshot(snapshot, file_hashes)

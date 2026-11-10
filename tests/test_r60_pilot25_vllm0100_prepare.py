"""CPU-only tests: never import vllm or submit Hugging Face jobs."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


SOURCE = (
    Path(__file__).resolve().parents[1] /
    "experiments/r58_quality/r60_pilot25_vllm0100_prepare.py"
)
spec = importlib.util.spec_from_file_location("r60_pilot25_vllm0100_prepare", SOURCE)
assert spec is not None and spec.loader is not None
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def private_file(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    os.chmod(path, 0o600)


def private_dir(path: Path) -> None:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)


def source_fixture(tmp_path: Path) -> tuple[Path, Path]:
    private_dir(tmp_path / "private")
    root = tmp_path / "private"
    source = root / "original"
    private_dir(source)
    for role in ("A", "B"):
        inp, out = source / f"input_{role}", source / f"output_{role}"
        private_dir(inp)
        private_dir(out)
        lines = [
            json.dumps({
                "schema": "storyforge_hf_literary_blind_input_v1",
                "blind_id": f"{i:032x}",
                "visible_history": [
                    {"role": "user", "content": "synthetic"},
                    {"role": "assistant", "content": "synthetic"},
                    {"role": "user", "content": "synthetic"},
                ],
                "target_text": "synthetic",
                "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
                "policy": "storyforge_hf_literary_visible_history_v1",
            }) + "\n" for i in range(1000)
        ]
        private_file(inp / "source.private.jsonl", "".join(lines).encode())
        old_script = (
            "from vllm.sampling_params import StructuredOutputsParams\n"
            "def make_main(SamplingParams, schema):\n"
            "    return SamplingParams(temperature=0, structured_outputs=StructuredOutputsParams(json=schema))\n"
            "def make_repair(SamplingParams, structured_factory, schema):\n"
            "    return SamplingParams(structured_outputs=structured_factory(json=schema))\n"
        )
        private_file(inp / "runner.py", old_script.encode())
        for filename in ("token_core.py", "runtime_inputs.py", "runtime_resources.py"):
            private_file(inp / filename, b"# placeholder synthetic module\n")
    return source, root / "pilot25"


def test_prepare_private_25_exact_and_original_unchanged(tmp_path):
    source, dest = source_fixture(tmp_path)
    originals = [(source / f"input_{r}" / "source.private.jsonl").read_bytes()
                 for r in ("A", "B")]
    receipt = pilot.prepare(source, dest)
    assert receipt["status"] == "R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED"
    assert receipt["hf_jobs_submitted"] == 0
    for role, original in zip(("A", "B"), originals):
        derived = (dest / f"input_{role}" / "source.private.jsonl")
        assert len(derived.read_bytes().splitlines()) == 25
        assert derived.read_bytes() == b"".join(original.splitlines(keepends=True)[:25])
        assert (source / f"input_{role}" / "source.private.jsonl").read_bytes() == original
        script = (dest / f"input_{role}" / "runner.py").read_text()
        assert "GuidedDecodingParams" in script
        assert "guided_decoding=" in script
        assert "StructuredOutputsParams" not in script
        assert (derived.stat().st_mode & 0o777) == 0o600


def test_existing_output_is_rejected(tmp_path):
    source, dest = source_fixture(tmp_path)
    pilot.prepare(source, dest)
    with pytest.raises(pilot.Hold, match="DEST_ALREADY_EXISTS"):
        pilot.prepare(source, dest)


def test_existing_original_checkpoint_is_rejected(tmp_path):
    source, dest = source_fixture(tmp_path)
    private_file(source / "output_A" / "review_0001.private.json", b"already reviewed")
    with pytest.raises(pilot.Hold, match="ORIGINAL_STAGE_ALREADY_REVIEWED"):
        pilot.prepare(source, dest)


def test_code_patch_api_drift_rejected(tmp_path):
    source, dest = source_fixture(tmp_path)
    private_file(source / "input_B" / "runner.py", b"unexpected runner version")
    with pytest.raises(pilot.Hold, match="VLLM0100_IMPORT_HOLD"):
        pilot.prepare(source, dest)


def test_older_runner_without_quote_repair_can_be_patched(tmp_path):
    source, dest = source_fixture(tmp_path)
    old = (
        "from vllm.sampling_params import StructuredOutputsParams\\n"
        "def build(SamplingParams, schema):\\n"
        "    return SamplingParams(structured_outputs = StructuredOutputsParams(json=schema))\\n"
    )
    for role in ("A", "B"):
        private_file(source / f"input_{role}" / "runner.py", old.encode())
    receipt = pilot.prepare(source, dest)
    assert receipt["status"] == "R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED"
    for role in ("A", "B"):
        patched = (dest / f"input_{role}" / "runner.py").read_text()
        assert "guided_decoding = GuidedDecodingParams(json=schema)" in patched
        assert "structured_outputs" not in patched

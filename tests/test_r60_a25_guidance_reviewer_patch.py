"""CPU-only checks for audited XGrammar -> Guidance reviewer variant."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SRC = (Path(__file__).resolve().parents[1] /
       "experiments/r58_quality/r60_a25_guidance_reviewer_patch.py")
spec = importlib.util.spec_from_file_location("guidance_patch", SRC)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def runner_text():
    return '''
from vllm.sampling_params import GuidedDecodingParams

def inference():
    params = SamplingParams(
        temperature=0, max_tokens=2400,
        guided_decoding=GuidedDecodingParams(json=response_schema()))
    return params
'''


def test_only_backend_added_with_create_only(tmp_path):
    origin = tmp_path / "original"
    origin.mkdir()
    target = tmp_path / "isolated"
    target.mkdir()
    source = origin / "runner.py"
    source.write_text(runner_text())
    dest = target / "runner.py"
    result = mod.patch(source, dest)
    assert result["status"] == "PATCH_GUIDANCE_ONLY_READY"
    assert result["changed_occurrences"] == 1
    assert dest.read_text() == runner_text().replace(
        mod.NEEDLE, mod.REPLACEMENT)
    assert source.read_text() == runner_text()
    with pytest.raises(mod.Hold, match="PATCH_PATH_HOLD"):
        mod.patch(source, dest)


def test_unknown_runner_shape_fails_closed(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    src = a / "runner.py"
    src.write_text("def inference(): return 'unchanged'\n")
    with pytest.raises(mod.Hold, match="PATCH_FROZEN_RUNNER_SHAPE_HOLD"):
        mod.patch(src, b / "runner.py")
    assert not (b / "runner.py").exists()


def test_reject_same_dir_and_symlink(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    src = a / "runner.py"
    src.write_text(runner_text())
    with pytest.raises(mod.Hold, match="PATCH_PATH_HOLD"):
        mod.patch(src, a / "other.py")
    link = tmp_path / "link.py"
    link.symlink_to(src)
    b = tmp_path / "b"
    b.mkdir()
    with pytest.raises(mod.Hold, match="PATCH_PATH_HOLD"):
        mod.patch(link, b / "runner.py")

"""Synthetic tests for the P3 weight-excluding snapshot downloader."""
from pathlib import Path

import pytest

from scripts import r60_p3_prepare_model_snapshots_v1 as p3


def test_exact_revision_pins_and_allowlists_exclude_weights():
    assert p3.MODEL_PINS == {
        "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
        "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
        "challenger": (
            "zai-org/GLM-Z1-32B-0414",
            "8eb2858992c1f749e2a6d4075455decc2484722d",
        ),
    }
    assert all(not any(name.endswith(suffix) for suffix in p3.WEIGHT_SUFFIXES)
               for names in p3.ALLOWLIST.values() for name in names)


def test_prepare_uses_only_pinned_allowlisted_files(tmp_path):
    calls = []

    def fake_download(**kwargs):
        calls.append(kwargs)
        folder = Path(kwargs["local_dir"])
        folder.mkdir(parents=True)
        for name in kwargs["allow_patterns"]:
            (folder / name).write_text("synthetic", encoding="utf-8")

    output = tmp_path / "snapshots"
    safe = p3.prepare_snapshots(output, downloader=fake_download)
    assert len(calls) == 3
    assert safe["status"] == "P3_PINNED_TOKENIZER_FILES_READY__NO_WEIGHTS"
    assert safe["model_count"] == 3
    assert safe["model_weights_downloaded"] is False
    for role, (_, revision) in p3.MODEL_PINS.items():
        call = next(item for item in calls if item["revision"] == revision)
        assert call["repo_id"] == p3.MODEL_PINS[role][0]
        assert set(call["allow_patterns"]) == set(p3.ALLOWLIST[role])
        assert call["token"] is False
        assert safe["models"][role]["file_count"] == len(p3.ALLOWLIST[role])


def test_prepare_rejects_weight_file_even_if_downloaded(tmp_path):
    def fake_download(**kwargs):
        folder = Path(kwargs["local_dir"])
        folder.mkdir(parents=True)
        for name in kwargs["allow_patterns"]:
            (folder / name).write_text("synthetic", encoding="utf-8")
        (folder / "accidental.safetensors").write_bytes(b"not-a-model")

    with pytest.raises(ValueError, match="P3_MODEL_WEIGHT_DETECTED"):
        p3.prepare_snapshots(tmp_path / "snapshots", downloader=fake_download)


def test_prepare_requires_create_only_absolute_output(tmp_path):
    with pytest.raises(ValueError, match="P3_OUTPUT_ROOT_MUST_BE_ABSENT_ABSOLUTE"):
        p3.prepare_snapshots(Path("relative"))
    existing = tmp_path / "exists"
    existing.mkdir()
    with pytest.raises(ValueError, match="P3_OUTPUT_ROOT_MUST_BE_ABSENT_ABSOLUTE"):
        p3.prepare_snapshots(existing)

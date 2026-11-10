"""Synthetic CPU-only tests: never import vLLM or fetch model weights."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_qwen32b_weight_stage.py")
spec = importlib.util.spec_from_file_location("weight_stage", SOURCE)
assert spec is not None and spec.loader is not None
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def fake_snapshot(root):
    (root / "config.json").write_bytes(b'{"model_type":"qwen3"}')
    (root / "model.safetensors.index.json").write_text(
        '{"weight_map":{"x":"model-00001-of-00001.safetensors"}}')
    (root / "model-00001-of-00001.safetensors").write_bytes(b"fakeweights")
    files = []
    for path in root.iterdir():
        if path.is_file():
            h, size = stage.sha_file(path)
            files.append({"name": path.name, "sha256": h, "size": size})
    manifest = {"schema": stage.SCHEMA, "model": stage.MODEL,
                "revision": stage.REV, "files": files}
    (root / stage.MANIFEST).write_text(json.dumps(manifest))
    return manifest


def test_manifest_read_and_local_copy(tmp_path, monkeypatch, capsys):
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    manifest = fake_snapshot(bucket)
    monkeypatch.setattr(stage, "MIN_FREE_OVERHEAD", 0)
    monkeypatch.setattr(stage.shutil, "disk_usage",
                        lambda _: type("Space", (), {"free": 10**9})())
    destination = tmp_path / "model"
    assert stage.localize(bucket, destination) == 0
    assert stage.frozen_manifest(destination) == manifest
    assert "LOCAL_WEIGHTS_READY" in capsys.readouterr().out
    assert (destination / "model-00001-of-00001.safetensors").read_bytes() == b"fakeweights"


def test_corrupted_bucket_content_rejected(tmp_path, monkeypatch):
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    fake_snapshot(bucket)
    (bucket / "model-00001-of-00001.safetensors").write_bytes(b"wrong")
    monkeypatch.setattr(stage, "MIN_FREE_OVERHEAD", 0)
    monkeypatch.setattr(stage.shutil, "disk_usage",
                        lambda _: type("Space", (), {"free": 10**9})())
    with pytest.raises(stage.Hold, match="STREAM_SIZE_OR_SHA_MISMATCH"):
        stage.localize(bucket, tmp_path / "local")


def test_manifest_rejects_path_traversal(tmp_path):
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    fake_snapshot(bucket)
    manifest = json.loads((bucket / stage.MANIFEST).read_text())
    manifest["files"][0]["name"] = "../secret"
    (bucket / stage.MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(stage.Hold, match="MANIFEST_INVALID"):
        stage.frozen_manifest(bucket)


def test_existing_sha_mismatch_fails_closed(tmp_path):
    path = tmp_path / "model.safetensors"
    path.write_bytes(b"wrong")
    with pytest.raises(stage.Hold, match="EXISTING_SHA_MISMATCH"):
        stage.check_existing(path, len(b"wrong"), "0" * 64)


def test_stream_size_and_sha_enforced(tmp_path):
    good = b"ABCDEFG"
    import hashlib

    digest = hashlib.sha256(good).hexdigest()
    target = tmp_path / "model.safetensors"
    stage.atomic_stream_copy([good[:3], good[3:]], target, len(good), digest)
    assert target.read_bytes() == good
    with pytest.raises(stage.Hold, match="STREAM_SIZE_OR_SHA_MISMATCH"):
        stage.atomic_stream_copy([good], tmp_path / "bad", len(good), "0" * 64)
    assert not (tmp_path / "bad").exists()

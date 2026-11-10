"""CPU only; synthetic files and fake Hub metadata (no model downloads)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_qwen32b_servercopy_localize.py")
spec = importlib.util.spec_from_file_location("r60_servercopy_localize", SOURCE)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def setup_snapshot(tmp_path):
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    weights = {f"model-{i:05d}-of-00017.safetensors": b"x" + bytes([i])
               for i in range(1, 18)}
    weights.update({
        "config.json": b"{}",
        "tokenizer.json": b"{}",
        "model.safetensors.index.json": json.dumps({
            "weight_map": {str(i): f"model-{i:05d}-of-00017.safetensors"
                           for i in range(1, 18)}}).encode(),
    })
    siblings = []
    for name, blob in weights.items():
        (bucket / name).write_bytes(blob)
        sha = hashlib.sha256(blob).hexdigest()
        siblings.append(SimpleNamespace(
            rfilename=name, size=len(blob),
            lfs={"sha256": sha} if name.endswith(".safetensors") else None))
    return bucket, SimpleNamespace(sha=mod.REV, siblings=siblings)


def test_local_copy_and_manifest(tmp_path, monkeypatch, capsys):
    bucket, info = setup_snapshot(tmp_path)
    monkeypatch.setattr(mod, "OVERHEAD", 0)
    monkeypatch.setattr(mod.shutil, "disk_usage",
                        lambda _: SimpleNamespace(free=10**9))
    output = tmp_path / "local"
    result = mod.run(bucket, output, info)
    assert len(result["files"]) == 20
    assert (output / mod.MANIFEST).is_file()
    assert '"event":"LOCAL_WEIGHTS_READY"' in capsys.readouterr().out
    with pytest.raises(mod.Hold, match="LOCAL_DIR_HOLD"):
        mod.run(bucket, output, info)


def test_corrupt_bucket_weight_rejected(tmp_path, monkeypatch):
    bucket, info = setup_snapshot(tmp_path)
    (bucket / "model-00002-of-00017.safetensors").write_bytes(b"xy")
    monkeypatch.setattr(mod, "OVERHEAD", 0)
    monkeypatch.setattr(mod.shutil, "disk_usage",
                        lambda _: SimpleNamespace(free=10**9))
    with pytest.raises(mod.Hold, match="BUCKET_WEIGHT_INTEGRITY_HOLD"):
        mod.run(bucket, tmp_path / "local", info)
    assert not (tmp_path / "local" / mod.MANIFEST).exists()


def test_capacity_gate_no_copy(tmp_path, monkeypatch):
    bucket, info = setup_snapshot(tmp_path)
    monkeypatch.setattr(mod.shutil, "disk_usage",
                        lambda _: SimpleNamespace(free=0))
    with pytest.raises(mod.Hold, match="LOCAL_DISK_INSUFFICIENT"):
        mod.run(bucket, tmp_path / "local", info)
    assert not (tmp_path / "local").exists()


def test_wrong_revision_or_missing_shard_fails(tmp_path):
    bucket, info = setup_snapshot(tmp_path)
    info.sha = "0" * 40
    with pytest.raises(mod.Hold, match="UPSTREAM_REVISION_MISMATCH"):
        mod.inventory(info)
    info.sha = mod.REV
    info.siblings.pop()
    with pytest.raises(mod.Hold, match="UPSTREAM_INVENTORY_MISMATCH"):
        mod.inventory(info)

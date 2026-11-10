"""CPU-only synthetic tests for R60 weight isolation. No HF or vLLM imports."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/r58_quality/r60_vllm_weight_isolation_probe.py"
spec = importlib.util.spec_from_file_location("weight_isolation", SOURCE)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_absent_pin_is_not_treated_as_ready(tmp_path):
    assert probe.cache_probe(tmp_path / "absent")["status"] == "PINNED_SNAPSHOT_NOT_LOCAL"


def test_complete_synthetic_shards_are_readable(tmp_path):
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({
        "weight_map": {"layer1": "model-00001-of-00002.safetensors",
                       "layer2": "model-00002-of-00002.safetensors"}}))
    for name in ("model-00001-of-00002.safetensors",
                 "model-00002-of-00002.safetensors"):
        (tmp_path / name).write_bytes(b"x" * 8192)
    result = probe.cache_probe(tmp_path)
    assert result["status"] == "LOCAL_SHARDS_ACCESSIBLE"
    assert result["shards_expected"] == result["shards_present"] == 2
    assert result["sample_read_ms"] >= 0
    (tmp_path / "model-00002-of-00002.safetensors").unlink()
    incomplete = probe.cache_probe(tmp_path)
    assert incomplete["status"] == "LOCAL_SHARDS_INCOMPLETE"
    assert incomplete["shards_expected"] == 2
    assert incomplete["shards_present"] == 1


def test_malformed_and_path_traversal_index_fails_closed(tmp_path):
    index = tmp_path / "model.safetensors.index.json"
    index.write_text('{"weight_map":{"layer":"../private.safetensors"}}')
    assert probe.cache_probe(tmp_path)["status"] == "PINNED_INDEX_INVALID"
    index.write_text("{")
    assert probe.cache_probe(tmp_path)["status"] == "PINNED_INDEX_INVALID"

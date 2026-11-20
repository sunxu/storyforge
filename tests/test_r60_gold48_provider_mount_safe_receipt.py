"""Validate public SAFE scope of the one new HF CPU-only RO mount witness."""
from __future__ import annotations

import json
from pathlib import Path


def test_gold48_provider_cpu_mount_witness_has_exact_limited_scope():
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((
        root / "experiments/r60_quality/gold48_provider_ro_mount_cpu_safe_receipt_20261121.json"
    ).read_text())
    assert payload["schema"] == (
        "storyforge_r60_gold48_provider_three_ro_mount_cpu_receipt_safe_v1"
    )
    assert payload["status"] == "THREE_ADAPTER_PROVIDER_RO_MOUNT_METADATA_PASS"
    assert payload["job_id"] == "6b00c1024fdc5ab3c55bfcf3"
    assert payload["job_status"] == "COMPLETED"
    assert payload["flavor"] == "cpu-basic"
    assert payload["image"] == (
        "pytorch/pytorch@sha256:"
        "77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"
    )
    assert payload["gpu_started"] is False
    assert payload["model_calls"] == 0
    assert payload["weights_read"] is False
    assert payload["weights_hashed"] is False
    assert payload["production_gpu_mount_verified"] is False
    assert payload["production_adapter_sha256_verified"] is False
    assert payload["owner_binding_receipt_mutated"] is False
    assert payload["source_volume_uris_published"] is False
    assert set(payload["arms"]) == {"r46_v02", "r54_v03a", "r60_base336"}
    assert [payload["arms"][role]["checkpoint"] for role in (
        "r46_v02", "r54_v03a", "r60_base336"
    )] == ["checkpoint-7", "checkpoint-16", "checkpoint-37"]
    for role, item in payload["arms"].items():
        assert item["mount_point"] == "/ro_adapters/" + role
        assert item["weight_file_bytes"] == 1867797544
        assert item["mount_present"] is True
        assert item["mount_read_only"] is True
        assert item["weight_size_match"] is True
        assert item["adapter_config_geometry_match"] is True
        assert item["weight_sha256_verified"] is False

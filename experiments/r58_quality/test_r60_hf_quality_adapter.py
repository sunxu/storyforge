"""Synthetic R60 1000-case -> shared Gold Quality HF adapter tests; no real text."""
from __future__ import annotations

import json

import pytest
import r60_hf_quality_adapter as adapter
import r60_real_private_batch as g1

from storyforge_gold_quality import hf_literary_review as reviewer


def synthetic_pool():
    cases = []
    for i in range(1000):
        cases.extend(g1.parse_rows([(
            f"synthetic-story-{i}", f"synthetic-session-{i}",
            f"synthetic-assistant-id-{i}", f"u-{i}", f"a-{i}", f"pu-{i}",
            i * 4 + 4, "玩家第一次提问", "NPC 警觉地看向走廊。",
            "玩家请求NPC提供地图", "NPC 在窗前展开地图，提示城门夜间关闭。" * 16,
        )]))
    return cases


def test_real_thin_adapter_stages_all_1000_and_audits_without_inference(
        tmp_path, monkeypatch):
    base = tmp_path / "owner-private"
    base.mkdir(mode=0o700)
    monkeypatch.setattr(g1, "BASE", base)
    source = base / "source-frozen"
    source.mkdir(mode=0o700)
    cases = synthetic_pool()
    monkeypatch.setattr(adapter.local_batch, "frozen_pool",
                        lambda _path: (cases, "c" * 64))
    stage = base / "r60-hf-quality-synthetic"
    result = adapter.prepare(
        source, stage, "Qwen/Qwen3-32B", "a" * 40,
        "zai-org/GLM-4-32B-0414", "b" * 40,
    )
    assert result["cases_staged"] == 1000
    assert result["status"] == "HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED"
    assert not (stage / "input_A" / "owner_crosswalk.private.json").exists()
    a = reviewer.read_input(stage / "input_A" / "source.private.jsonl")
    b = reviewer.read_input(stage / "input_B" / "source.private.jsonl")
    assert len(a) == len(b) == 1000
    assert a[0]["blind_id"] != b[0]["blind_id"]
    assert "synthetic-story-0" not in json.dumps(a)
    audit = adapter.audit(source, stage)
    assert audit["quality_decisions"]["HOLD"] == 1000
    assert audit["quality_pass"] == audit["quality_v1_admitted"] == 0
    assert audit["training_authorized"] is False
    assert audit["r50_body_accessed"] is False
    assert audit["status"] == "HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION"


def test_real_thin_adapter_rejects_non_1000_source(tmp_path, monkeypatch):
    cases = synthetic_pool()[:-1]
    monkeypatch.setattr(adapter.local_batch, "frozen_pool",
                        lambda _path: (cases, "c" * 64))
    with pytest.raises(adapter.hf_blind_stage.StageError,
                       match="R60_1000_FROZEN_SOURCE_REQUIRED"):
        adapter.frozen_source(tmp_path)


def test_real_thin_adapter_rejects_non_owner_stage_path(tmp_path, monkeypatch):
    base = tmp_path / "owner-private"
    base.mkdir(mode=0o700)
    monkeypatch.setattr(g1, "BASE", base)
    cases = synthetic_pool()
    monkeypatch.setattr(adapter.local_batch, "frozen_pool",
                        lambda _path: (cases, "c" * 64))
    with pytest.raises(adapter.hf_blind_stage.StageError,
                       match="R60_STAGE_PRIVATE_PATH_HOLD"):
        adapter.prepare(
            base / "source",
            tmp_path / "uncontrolled-review-path", "Qwen/Qwen3-32B",
            "a" * 40, "zai-org/GLM-4-32B-0414", "b" * 40,
        )

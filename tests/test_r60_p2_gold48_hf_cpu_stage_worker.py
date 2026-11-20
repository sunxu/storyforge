"""Synthetic-only Mac-stage and HF CPU worker contract tests.

No HF Jobs, private data, Hub calls, Transformers or model weights are used.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from r60_p2_gold48_reconstructed_input_draft_cpu import draft
from test_r60_p2_gold48_candidate_preflight_cpu import private_file
from test_r60_p2_gold48_reconstructed_input_draft_cpu import prepare
from test_r60_p2_gold48_token_preflight_cpu import FakeTokenizer


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


stage_tool = load(ROOT / "scripts/r60_p2_gold48_hf_cpu_stage.py", "r60_p2_gold48_hf_cpu_stage")
worker = load(ROOT / "scripts/r60_p2_gold48_hf_cpu_worker.py", "r60_p2_gold48_hf_cpu_worker")

KEY = "r60-gold48-cpu-20261121T010101Z-012345abcdef"


def make_stage(tmp_path):
    tmp_path.chmod(0o700)
    candidate, source_binding, evidence, manifest = prepare(tmp_path)
    doc, safe = draft(candidate, source_binding, evidence, manifest)
    assert safe["case_count"] == 48
    draft_dir = tmp_path / "draft"
    draft_dir.mkdir(mode=0o700)
    draft_file = draft_dir / "GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
    private_file(draft_file, doc)
    stage = tmp_path / KEY
    stage_safe = stage_tool.prepare(draft_file, stage, KEY)
    return stage, stage_safe


def test_stage_minimizes_private_data_and_worker_reuses_real_core(tmp_path):
    stage, safe = make_stage(tmp_path)
    assert safe["status"] == "GOLD48_HF_CPU_STAGE_VERIFIED__NOT_SUBMITTED"
    assert safe["case_count"] == 48
    assert safe["historical_original_replies_staged"] is False
    assert safe["actual_story_ids_staged"] is False
    raw = (stage / stage_tool.INPUT).read_text()
    assert "synthetic-story-" not in raw
    assert "original response" not in raw
    assert "session-" not in raw
    assert "request-" not in raw
    assert len(json.loads(raw)["cases_PRIVATE"]) == 48
    assert stage_tool.verify(stage, KEY)["files_verified"] > 8
    receipt = worker.run(
        stage, KEY, tokenizer_factory=lambda *_args, **_kwargs: FakeTokenizer(),
        check_runtime=False,
    )
    assert receipt["status"] == "GOLD48_HF_CPU_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE"
    assert receipt["case_count"] == 48
    assert receipt["tokenizer_checked"] is True
    assert receipt["gpu_started"] is False
    assert receipt["model_calls"] == 0
    assert receipt["owner_gold48_freeze"] is False
    assert "original response" not in json.dumps(receipt)


def test_staged_input_modified_fails_hash(tmp_path):
    stage, _ = make_stage(tmp_path)
    path = stage / stage_tool.INPUT
    doc = json.loads(path.read_text())
    doc["cases_PRIVATE"][0]["reconstructed_messages_PRIVATE"][0]["content"] += "modified"
    private_file(path, doc)
    with pytest.raises(stage_tool.Hold, match="STAGE_HASH_BINDING_HOLD"):
        stage_tool.verify(stage, KEY)
    result = worker.run(stage, KEY, tokenizer_factory=lambda *a, **kw: FakeTokenizer(),
                        check_runtime=False)
    assert result["status"] == "GOLD48_HF_CPU_TOKEN_PREFLIGHT_HOLD"
    assert result["reason_code"] == "INPUT_INTEGRITY_HOLD"


def test_stage_does_not_overwrite(tmp_path):
    stage, _ = make_stage(tmp_path)
    draft_file = tmp_path / "draft/GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
    with pytest.raises(stage_tool.Hold, match="PRIVATE_STAGE_PATH_SCOPE_HOLD"):
        stage_tool.prepare(draft_file, stage, KEY)


def test_original_reference_changes_do_not_affect_stage(tmp_path):
    stage, _ = make_stage(tmp_path)
    assert all("GOLD48_CANDIDATE_ORIGINAL_REFERENCES" not in p.name
               for p in stage.rglob("*") if p.is_file())
    assert stage_tool.INPUT in json.loads(
        (stage / stage_tool.MANIFEST).read_text())["files"]


def test_source_staging_refuses_unauthorized_owner_freeze(tmp_path):
    make_stage(tmp_path)
    draft_file = tmp_path / "draft/GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
    doc = json.loads(draft_file.read_text())
    doc["prompt_owner_freeze"] = True
    private_file(draft_file, doc)
    new_key = "r60-gold48-cpu-20261121T010101Z-fedcba654321"
    with pytest.raises(stage_tool.Hold, match="DRAFT_INPUT_CONTRACT_HOLD"):
        stage_tool.prepare(draft_file, tmp_path / new_key, new_key)

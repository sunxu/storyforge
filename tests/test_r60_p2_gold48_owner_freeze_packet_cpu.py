"""Synthetic only Gold48 Owner freeze-readiness packet; no Owner signoff."""
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

from test_r60_p2_gold48_candidate_preflight_cpu import private_file
from test_r60_p2_gold48_hf_cpu_stage_worker import (
    KEY,
    make_stage,
    worker,
)
from test_r60_p2_gold48_token_preflight_cpu import FakeTokenizer

spec = importlib.util.spec_from_file_location(
    "r60_p2_gold48_owner_freeze_packet_cpu",
    ROOT / "scripts/r60_p2_gold48_owner_freeze_packet_cpu.py",
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixtures(tmp_path):
    stage, _ = make_stage(tmp_path)
    receipt_dir = tmp_path / "receipt"
    receipt_dir.mkdir(mode=0o700)
    receipt = worker.run(
        stage, KEY,
        tokenizer_factory=lambda *args, **kwargs: FakeTokenizer(),
        check_runtime=False,
    )
    assert receipt["status"] == gate.RECEIPT_STATUS
    private_file(receipt_dir / gate.RECEIPT_NAME, receipt)
    args = (
        tmp_path / "candidate",
        tmp_path / "bindings",
        tmp_path / "draft",
        stage,
        receipt_dir,
        KEY,
    )
    return args


def test_all_48_source_bound_with_reference_segregation_and_risk_scope(tmp_path):
    args = fixtures(tmp_path)
    packet, safe = gate.make_packet(*args)
    assert safe["status"] == "GOLD48_OWNER_FREEZE_PACKET_READY__AWAITING_SIGNOFF"
    assert safe["case_count"] == 48
    assert safe["main_analysis_count"] == 48
    assert safe["sensitivity_analysis_count"] == 42
    assert safe["verified_original_reference_hash_count"] == 48
    assert safe["verified_reconstructed_input_sha_count"] == 48
    assert safe["stage_manifest_and_cpu_receipt_bound"] is True
    assert safe["owner_gold48_freeze"] is False
    assert safe["model_generation_authorized"] is False
    assert packet["historical_actual_sent_prompt_verified"] is False
    assert packet["p2_c_full_protected_universe_verified"] is False
    assert packet["prior_provisional_48_exact_identity_verified"] is False
    assert len(packet["cases_PRIVATE"]) == 48
    assert sum(x["exclude_from_42_sensitivity"] for x in packet["cases_PRIVATE"]) == 6
    serialized = json.dumps(packet)
    assert "synthetic-story" not in serialized
    assert "original response" not in serialized
    assert "historical assistant" not in serialized
    assert "request-" not in serialized
    assert len({x["original_reference_sha256_PRIVATE"]
                for x in packet["cases_PRIVATE"]}) == 48


def test_original_reply_modified_holds(tmp_path):
    args = fixtures(tmp_path)
    path = args[0] / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json"
    original = json.loads(path.read_text())
    original["cases_PRIVATE"][0]["original_reply_PRIVATE"] = "tampered synthetic reply"
    private_file(path, original)
    with pytest.raises(Exception, match="SHA_BINDING"):
        gate.make_packet(*args)


def test_changed_cpu_safe_receipt_holds(tmp_path):
    args = fixtures(tmp_path)
    path = args[4] / gate.RECEIPT_NAME
    raw = json.loads(path.read_text())
    raw["mode_stats"]["disabled"]["context_16384_reserve_1536"]["over_budget_count"] = 1
    private_file(path, raw)
    with pytest.raises(gate.Hold, match="GOLD48_TOKEN_BUDGET_NOT_PASS_HOLD"):
        gate.make_packet(*args)


def test_changed_stage_code_or_input_holds(tmp_path):
    args = fixtures(tmp_path)
    path = args[3] / "private/GOLD48_HF_CPU_MINIMAL_INPUT_PRIVATE.json"
    payload = json.loads(path.read_text())
    payload["cases_PRIVATE"][0]["reconstructed_messages_PRIVATE"][0]["content"] += "edit"
    private_file(path, payload)
    with pytest.raises(Exception):
        gate.make_packet(*args)


def test_draft_changed_after_stage_holds(tmp_path):
    args = fixtures(tmp_path)
    path = args[2] / gate.DRAFT_NAME
    doc = json.loads(path.read_text())
    doc["system_template_sha256_PRIVATE"] = "a" * 64
    private_file(path, doc)
    with pytest.raises(gate.Hold, match="GOLD48_STAGE_DRAFT_SHA_OR_MODEL_HOLD"):
        gate.make_packet(*args)

"""CPU-only synthetic S1 comparison tests with no external services."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

import r60_real1000_s1_blind20_prepare_cpu as blind
import r60_real1000_s1_compare_cpu as compare

SPEC = importlib.util.spec_from_file_location(
    "r60_s0_fixture_for_compare",
    ROOT / "tests/test_r60_real1000_s0_audit_cpu.py",
)
assert SPEC and SPEC.loader
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


def setup(monkeypatch, tmp_path):
    sample_dir, _, review_dir = fixture.setup(monkeypatch, tmp_path)
    blind_dir = tmp_path / "blind"
    owner_dir = tmp_path / "owner"
    blind_doc, map_doc = blind.prepare(sample_dir, review_dir)[1:]
    blind_dir.mkdir()
    owner_dir.mkdir()
    (blind_dir / blind.BLIND_FILENAME).write_bytes(
        compare.pilot.canonical(blind_doc))
    (owner_dir / blind.CROSSWALK_FILENAME).write_bytes(
        compare.pilot.canonical(map_doc))
    results = []
    for i in range(1, 21):
        results.append({
            "blind_id": f"B{i:03d}",
            "decision": "HOLD",
            "scores": {name: 3 for name in compare.private.FLOORS},
            "severe_flags": {name: False for name in compare.private.SEVERE},
            "reason_cn": "合成样本，证据不足，保持HOLD。",
        })
    codex = tmp_path / "codex.json"
    codex.write_bytes(compare.pilot.canonical({
        "schema": compare.CODEX_SCHEMA, "reviews": results,
    }))
    return sample_dir, review_dir, blind_dir, owner_dir, codex


def test_codex_claude_complete_safe_cross_tab(monkeypatch, tmp_path):
    args = setup(monkeypatch, tmp_path)
    safe, priv = compare.compare(*args)
    assert safe["status"] == (
        "S1_CODEX_CLAUDE_COMPARE_PASS__OWNER_ADJUDICATION_PENDING")
    assert safe["cases"] == 20
    assert safe["agreement_on_18_valid_claude"] == 20
    assert safe["codex_model_decisions"]["HOLD"] == 20
    assert safe["decision_cross_tab_valid_claude"]["HOLD"]["HOLD"] == 20
    assert safe["quality_v1_admitted"] == 0
    assert len(priv["rows"]) == 20
    assert all("reason_cn" not in row and "assistant_target" not in row
               for row in priv["rows"])


def test_codex_duplicate_blind_id_rejected(monkeypatch, tmp_path):
    args = setup(monkeypatch, tmp_path)
    p = args[-1]
    doc = json.loads(p.read_bytes())
    doc["reviews"][1]["blind_id"] = "B001"
    p.write_bytes(compare.pilot.canonical(doc))
    try:
        compare.compare(*args)
    except compare.Hold as exc:
        assert str(exc) == "CODEX_ID_HOLD"
    else:
        raise AssertionError("duplicate blind ID must hold")


def test_frozen_blind_case_tamper_rejected(monkeypatch, tmp_path):
    args = setup(monkeypatch, tmp_path)
    blind_path = args[2] / blind.BLIND_FILENAME
    doc = json.loads(blind_path.read_bytes())
    doc["cases"][0]["assistant_target"] += "修改"
    blind_path.write_bytes(compare.pilot.canonical(doc))
    try:
        compare.compare(*args)
    except compare.Hold as exc:
        assert str(exc) == "S1_FROZEN_INPUT_OR_MAP_MISMATCH_HOLD"
    else:
        raise AssertionError("tampered blind input must hold")


def test_rubric_inconsistent_codex_pass_rejected(monkeypatch, tmp_path):
    args = setup(monkeypatch, tmp_path)
    p = args[-1]
    doc = json.loads(p.read_bytes())
    doc["reviews"][0]["decision"] = "PASS"
    p.write_bytes(compare.pilot.canonical(doc))
    try:
        compare.compare(*args)
    except compare.reviewer.Hold as exc:
        assert str(exc) == "QUALITY_FLOOR_DECISION_INCONSISTENT"
    else:
        raise AssertionError("invalid PASS cannot be accepted")

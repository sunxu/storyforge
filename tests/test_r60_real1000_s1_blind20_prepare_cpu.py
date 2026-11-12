"""S1 blind packet preparation synthetic checks, no real data or API."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
import r60_real1000_s1_blind20_prepare_cpu as s1

SPEC = importlib.util.spec_from_file_location(
    "r60_s0_test_fixture", ROOT / "tests/test_r60_real1000_s0_audit_cpu.py",
)
assert SPEC and SPEC.loader
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


def test_blind20_separates_model_advisory_and_owner_mapping(monkeypatch, tmp_path):
    sample_dir, _, review_dir = fixture.setup(monkeypatch, tmp_path)
    safe, blind, mapping = s1.prepare(sample_dir, review_dir)
    assert safe["status"] == "S1_BLIND20_PACKETS_READY__INDEPENDENT_REVIEW_PENDING"
    assert safe["cases_prepared"] == 20
    assert safe["model_inference_calls"] == 0
    assert safe["model_advisory_excluded"] is True
    assert len(blind["cases"]) == len(mapping["entries"]) == 20
    assert {c["blind_id"] for c in blind["cases"]} == {
        f"B{i:03d}" for i in range(1, 21)
    }
    for case in blind["cases"]:
        assert set(case) == {
            "blind_id", "history_messages", "assistant_target", "reference_status",
        }
        assert case["reference_status"] == "NOT_ADJUDICATED"
    blob = json.dumps(blind, ensure_ascii=False)
    for prohibited in (
        "pilot_position", "sample100_position", "original_model_decision",
        "reason_cn", "model_id", "claude-opus", "PASS_BELOW_FLOOR_CONFLICT",
        "review_kind", "scores", "receipt_sha256",
    ):
        assert prohibited not in blob
    assert mapping["blind_input_sha256"] == s1.pilot_review.sha(
        s1.pilot_review.canonical(blind)
    )


def test_blind20_rejects_broken_source_binding(monkeypatch, tmp_path):
    sample_dir, _, review_dir = fixture.setup(monkeypatch, tmp_path)
    path = review_dir / s1.pilot_review.receipt_name(1)
    data = json.loads(path.read_bytes())
    data["scores"]["chinese_prose"] = 5
    path.write_bytes(s1.pilot_review.canonical(data))
    try:
        s1.prepare(sample_dir, review_dir)
    except (s1.Hold, s1.pilot_review.Hold):
        return
    raise AssertionError("must reject tampered source receipt")


def test_blind20_output_is_create_only_and_separated(monkeypatch, tmp_path):
    sample_dir, _, review_dir = fixture.setup(monkeypatch, tmp_path)
    blind_dir = tmp_path / "blind"
    owner_dir = tmp_path / "owner"
    safe, blind, mapping = s1.prepare(sample_dir, review_dir)
    assert not blind_dir.exists() and not owner_dir.exists()
    s1.private.private_dir(blind_dir, create=True)
    s1.private.write_new(blind_dir / s1.BLIND_FILENAME,
                         s1.pilot_review.canonical(blind))
    s1.private.private_dir(owner_dir, create=True)
    s1.private.write_new(owner_dir / s1.CROSSWALK_FILENAME,
                         s1.pilot_review.canonical(mapping))
    assert safe["crosswalk_entries"] == 20
    assert (blind_dir / s1.BLIND_FILENAME).exists()
    assert (owner_dir / s1.CROSSWALK_FILENAME).exists()
    assert not (blind_dir / s1.CROSSWALK_FILENAME).exists()
    assert not (owner_dir / s1.BLIND_FILENAME).exists()

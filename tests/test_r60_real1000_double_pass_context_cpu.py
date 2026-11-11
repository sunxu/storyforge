"""CPU-only synthetic training-context gate tests; never touch real Owner data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
import r60_real1000_double_pass_context_cpu as context


def setup(monkeypatch, tmp_path, *, changed=False):
    cases = []
    for i in range(1, 1001):
        cases.append({
            "source": {
                "story_id": f"story-{i}",
                "assistant_message_id": f"target-{i}",
            },
            "history_messages": [
                {"role": "user", "content": "一"},
                {"role": "assistant", "content": "二"},
                {"role": "user", "content": "三"},
            ],
            "target_text": "四" * 350,
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
        })
    manifest = {
        "schema": context.sample.SCHEMA,
        "status": "CALIBRATION_SAMPLE100_PRIVATE__NOT_REVIEWED",
        "pool_sha256": "a" * 64,
        "method": "stable_sha256_rank_unique_story_per_bin_v1",
        "cases": [{"position": i, "target_char_bin": "300_499"}
                  for i in range(1, 101)],
        "quality_review_performed": False, "train_admitted": 0,
    }
    packets = {
        "packets": [
            {
                "sample100_position": i,
                "target_char_bin": "300_499",
                "history_messages": cases[i - 1]["history_messages"],
                "assistant_target": cases[i - 1]["target_text"],
            } for i in range(1, 21)
        ],
    }
    monkeypatch.setattr(context.quality, "frozen_pool",
                        lambda _: (cases, "a" * 64))
    monkeypatch.setattr(context.technical, "profile", lambda _: {})
    monkeypatch.setattr(context.sample, "select", lambda c, d: manifest)
    monkeypatch.setattr(context.private, "private_dir",
                        lambda p, create: None)
    monkeypatch.setattr(context.private, "read_private",
                        lambda p, maximum: Path(p).read_bytes())
    monkeypatch.setattr(context.pilot, "get_state",
                        lambda p: ({
                            "packets_sha256": "b" * 64, "packet_dir": str(tmp_path),
                        }, packets, {"processed": 20}))
    monkeypatch.setattr(context.pilot, "sha",
                        lambda data: "b" * 64)
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / context.sample.FILENAME).write_text(json.dumps(manifest))
    (tmp_path / context.pilot.pilot.FILENAME).write_text("{}")
    candidate_file = tmp_path / "candidates.json"
    candidate_file.write_text(json.dumps({
        "schema": context.double.PRIVATE_SCHEMA,
        "status": "DOUBLE_PASS_TRAIN_CANDIDATES__NOT_ADMITTED",
        "quality_v1_admitted": 0, "train_admitted": 0,
        "candidates": [
            {"pilot_position": i, "status": "TRAIN_CANDIDATE__NOT_ADMITTED"}
            for i in (1, 2, 3)
        ],
    }))
    if changed:
        packets["packets"][1]["assistant_target"] = "unexpected mutation"
    return sample_dir, tmp_path, candidate_file


def test_frozen_double_pass_context_is_still_admission_hold(monkeypatch, tmp_path):
    sample_dir, review_dir, candidate_file = setup(monkeypatch, tmp_path)
    safe = context.check(tmp_path, sample_dir, review_dir, candidate_file)
    assert safe["candidate_count"] == 3
    assert safe["distinct_story_count"] == 3
    assert safe["historical_system_unverified"] == 3
    assert safe["world_component_unverified"] == 3
    assert safe["r50_exclusion_unverified"] == 3
    assert safe["train_admitted"] == 0
    assert safe["status"].endswith("TRAIN_ADMISSION_HOLD")


def test_source_target_mutation_is_rejected(monkeypatch, tmp_path):
    sample_dir, review_dir, candidate_file = setup(
        monkeypatch, tmp_path, changed=True)
    try:
        context.check(tmp_path, sample_dir, review_dir, candidate_file)
    except context.Hold as exc:
        assert str(exc) == "SOURCE_PAYLOAD_MISMATCH_HOLD"
    else:
        raise AssertionError("must reject mutated frozen source")


def test_duplicate_position_manifest_rejected(monkeypatch, tmp_path):
    sample_dir, review_dir, candidate_file = setup(monkeypatch, tmp_path)
    manifest = json.loads(candidate_file.read_text())
    manifest["candidates"][2]["pilot_position"] = 2
    candidate_file.write_text(json.dumps(manifest))
    try:
        context.check(tmp_path, sample_dir, review_dir, candidate_file)
    except context.Hold as exc:
        assert str(exc) == "CANDIDATE_POSITIONS_HOLD"
    else:
        raise AssertionError("must reject duplicate position")

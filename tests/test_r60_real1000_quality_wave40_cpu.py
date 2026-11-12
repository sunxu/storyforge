"""Synthetic selection tests; no private data, model or database."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/r58_quality"))
import r60_real1000_quality_wave40_cpu as wave


def build(monkeypatch):
    cases = []
    for i in range(1000):
        size = 350 if i % 3 == 0 else 750 if i % 3 == 1 else 1200
        cases.append({
            "case_key": f"synthetic-{i}",
            "source": {"story_id": f"synthetic-story-{i}"},
            "target_text": "合" * size,
        })
    frozen = {"cases": [
        {"position": p, "target_char_bin": wave.sample.bucket(len(cases[p - 1]["target_text"]))}
        for p in range(1, 101)
    ]}
    monkeypatch.setattr(wave.technical, "profile", lambda _: {"ok": True})
    monkeypatch.setattr(wave.sample, "select", lambda *_: frozen)
    return cases, frozen


def test_wave40_is_deterministic_and_disjoint(monkeypatch):
    cases, frozen = build(monkeypatch)
    one = wave.select(cases, "a" * 64, frozen)
    two = wave.select(cases, "a" * 64, frozen)
    assert one == two
    assert len(one["cases"]) == 40
    assert len({x["position"] for x in one["cases"]}) == 40
    assert all(x["position"] > 100 for x in one["cases"])
    assert Counter(x["target_char_bin"] for x in one["cases"]) == wave.QUOTAS
    assert one["quality_review_performed"] is False
    assert one["train_admitted"] == 0


def test_reject_non_frozen_sample100(monkeypatch):
    cases, frozen = build(monkeypatch)
    invalid = {"cases": frozen["cases"][:-1]}
    with pytest.raises(wave.Hold, match="CALIBRATION_SAMPLE100_CHANGED_HOLD"):
        wave.select(cases, "a" * 64, invalid)


def test_fail_closed_when_distinct_story_quota_unavailable(monkeypatch):
    cases, frozen = build(monkeypatch)
    for i in range(100, 1000):
        cases[i]["source"]["story_id"] = "already-in-sample-1"
    with pytest.raises(wave.Hold, match="WAVE40_COUNT_HOLD"):
        wave.select(cases, "a" * 64, frozen)

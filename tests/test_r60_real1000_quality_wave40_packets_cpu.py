"""Synthetic Wave40 packet security and integrity tests; no private data."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/r58_quality"))
import r60_real1000_quality_wave40_packets_cpu as packets


def synthetic(monkeypatch):
    cases = []
    for i in range(180):
        category_size = (350, 750, 1200)[i % 3]
        cases.append({
            "case_key": f"case-{i}",
            "source": {"story_id": f"story-{i}", "assistant_message_id": f"target-{i}"},
            "target_text": "测" * category_size,
            "history_messages": [
                {"role": "user", "content": "用户前情", "id": f"prior-{i}"},
                {"role": "assistant", "content": "角色行动", "id": f"middle-{i}"},
                {"role": "user", "content": "玩家回复", "id": f"recent-{i}"},
            ],
        })
    frozen = {"schema": "sample", "cases": []}
    locators = {
        "schema": packets.wave.SCHEMA,
        "status": packets.wave.STATUS,
        "pool_sha256": "a" * 64,
        "sample100_frozen_binding": True,
        "excludes_all_sample100_stories": True,
        "quality_review_performed": False,
        "train_admitted": 0,
        "cases": [
            {"position": i + 1, "target_char_bin": packets.sample.bucket(len(cases[i]["target_text"]))}
            for i in range(40)
        ],
    }
    monkeypatch.setattr(packets.wave, "select", lambda *_: copy.deepcopy(locators))
    return cases, locators, frozen


def test_blind_excludes_source_votes_and_positions(monkeypatch):
    cases, locators, frozen = synthetic(monkeypatch)
    blind, mapping, template = packets.construct(cases, "a" * 64, locators, frozen)
    assert len(blind["cases"]) == len(mapping["cases"]) == len(template["cases"]) == 40
    assert len({x["source_position"] for x in mapping["cases"]}) == 40
    assert all(set(p) == {"blind_index", "history_messages", "assistant_target"} for p in blind["cases"])
    assert all(set(m) == {"role", "content"} for x in blind["cases"] for m in x["history_messages"])
    assert "story-0" not in str(blind)
    assert "target-0" not in str(blind)
    assert "prior-0" not in str(blind)
    assert "source_position" not in str(blind)
    assert "PASS" not in str(blind)
    assert template["train_admitted"] == 0


def test_reject_tampered_frozen_wave(monkeypatch):
    cases, locators, frozen = synthetic(monkeypatch)
    frozen_valid_locators = copy.deepcopy(locators)
    monkeypatch.setattr(packets.wave, "select", lambda *_: copy.deepcopy(frozen_valid_locators))
    locators["cases"][0]["position"] = 88
    with pytest.raises(packets.Hold, match="WAVE40_SOURCE_RECOMPUTE_HOLD"):
        packets.construct(cases, "a" * 64, locators, frozen)


def test_reject_duplicate_positions(monkeypatch):
    cases, locators, frozen = synthetic(monkeypatch)
    locators["cases"][1]["position"] = locators["cases"][0]["position"]
    monkeypatch.setattr(packets.wave, "select", lambda *_: copy.deepcopy(locators))
    with pytest.raises(packets.Hold, match="WAVE40_DUPLICATE_HOLD"):
        packets.construct(cases, "a" * 64, locators, frozen)

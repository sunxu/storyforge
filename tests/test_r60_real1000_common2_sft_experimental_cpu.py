"""CPU synthetic test for source-bound Common2 experimental SFT output."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/r58_quality"))
import r60_real1000_common2_sft_experimental_cpu as sft


def fixture(monkeypatch):
    cases, recovery_rows, blind_rows = [], [], []
    for i, n in enumerate((103, 243)):
        history = [{
            "id": f"msg-{i}-{j}",
            "role": "user" if j % 2 == 0 else "assistant",
            "content": f"合成文本-{i}-{j}",
            "turn_index": j,
        } for j in range(n)]
        source = {
            "assistant_message_id": f"target-{i}",
            "story_id": f"story-{i}",
            "session_id": f"session-{i}",
            "assistant_turn_index": n,
        }
        prior = [{"role": m["role"], "content": m["content"]} for m in history[-3:]]
        target = f"合成最终回复-{i}"
        cases.append({
            "source": source, "target_text": target,
            "history_messages": prior,
        })
        recovery_rows.append({
            **source,
            "target_turn_index": n,
            "message_count_before_target": n,
            "history_messages": history,
            "last_three_exact_source_match": True,
            "actual_sent_prompt_verified": False,
            "historical_system_verified": False,
            "historical_world_components_verified": False,
            "r50_full_exclusion_verified": False,
        })
        blind_rows.append({
            "blind_index": i + 1,
            "assistant_target": target,
            "history_messages": prior,
        })
    cases.extend({
        "source": {
            "assistant_message_id": f"other-{j}",
            "story_id": f"otherstory-{j}",
            "session_id": f"othersession-{j}",
            "assistant_turn_index": 20,
        },
        "target_text": "不相关",
        "history_messages": [],
    } for j in range(998))
    blind = {"cases": blind_rows}
    decisions = {"review_decisions": "synthetic"}
    recovered = {
        "schema": sft.recovery.PRIVATE_SCHEMA,
        "status": "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT",
        "cases": recovery_rows, "train_admitted": 0,
    }
    monkeypatch.setattr(sft.common, "validate", lambda *_: {
        "review_decisions": {"PASS": 2, "HOLD": 0, "REJECT": 0},
    })
    return cases, blind, decisions, recovered


def test_construct_exact_targets_without_system(monkeypatch):
    cases, blind, decisions, recovered = fixture(monkeypatch)
    records, manifest = sft.create(cases, blind, decisions, recovered, 11)
    assert len(records) == 2
    assert len(records[0]["messages"]) == 12
    assert records[0]["messages"][0]["role"] == "user"
    assert records[0]["messages"][-1]["role"] == "assistant"
    assert records[0]["messages"][-1]["content"] == "合成最终回复-0"
    assert all(record["system_prompt"] is None and record["world_card"] is None
               for record in records)
    assert all(record["train_admitted"] is False for record in records)
    assert manifest["collator_verified"] is False


def test_reject_unverified_history(monkeypatch):
    cases, blind, decisions, recovered = fixture(monkeypatch)
    recovered["cases"][0]["last_three_exact_source_match"] = False
    with pytest.raises(sft.Hold, match="SOURCE_ATTESTATION_HOLD"):
        sft.create(cases, blind, decisions, recovered, 11)


def test_reject_tampered_frozen_target(monkeypatch):
    cases, blind, decisions, recovered = fixture(monkeypatch)
    blind["cases"][1]["assistant_target"] += "后续"
    with pytest.raises(sft.Hold, match="BLIND_EXACT_SOURCE_HOLD"):
        sft.create(cases, blind, decisions, recovered, 11)


def test_reject_wrong_window_or_quality(monkeypatch):
    cases, blind, decisions, recovered = fixture(monkeypatch)
    with pytest.raises(sft.Hold, match="WINDOW_NOT_APPROVED_HOLD"):
        sft.create(cases, blind, decisions, recovered, 12)
    monkeypatch.setattr(sft.common, "validate", lambda *_: {
        "review_decisions": {"PASS": 1, "HOLD": 1, "REJECT": 0},
    })
    with pytest.raises(sft.Hold, match="INDEPENDENT_REVIEW_NOT_2PASS_HOLD"):
        sft.create(cases, blind, decisions, recovered, 11)


def test_reject_reordered_history(monkeypatch):
    cases, blind, decisions, recovered = fixture(monkeypatch)
    last = recovered["cases"][0]["history_messages"]
    last[-1]["role"] = "assistant"
    with pytest.raises(sft.Hold, match="FROZEN_LAST_THREE_HOLD"):
        sft.create(cases, blind, decisions, recovered, 11)

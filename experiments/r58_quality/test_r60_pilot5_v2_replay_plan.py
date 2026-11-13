"""Offline synthetic tests for create-only Pilot5 v2 failed-side plan."""
from __future__ import annotations

import json

import r60_pilot5_v2_replay_plan as plan
import r60_real_private_batch as priv
import r60_real_quality_batch as q


def arrange(tmp_path, monkeypatch):
    base = tmp_path / "private"
    base.mkdir(mode=0o700)
    folder = base / "v1"
    folder.mkdir(mode=0o700)
    source = base / "source"
    source.mkdir(mode=0o700)
    monkeypatch.setattr(priv, "BASE", base)
    monkeypatch.setattr(q, "inspect", lambda _: {"cases_reviewed": 5})
    config = {"source": str(source), "pool_sha256": "frozen-pool",
              "model_a": "claude", "model_b": "deepseek",
              "protocol_a": "claude-proxy-top-system",
              "protocol_b": "deepseek-chat"}
    monkeypatch.setattr(q, "validate_config", lambda _: config)
    cases = [
        {"case_key": f"case-{i}", "history_messages_sha256": f"h-{i}",
         "assistant_target_sha256": f"t-{i}"} for i in range(1, 6)
    ]
    monkeypatch.setattr(q, "frozen_pool",
                        lambda _: (cases, "frozen-pool"))
    decisions = [
        ([{"reviewer_key": "ai-model-a"}],
         ["QUALITY_FLOOR_DECISION_INCONSISTENT"]),
        ([{"reviewer_key": "ai-model-a"},
          {"reviewer_key": "ai-model-b"}], []),
        ([], ["MODEL_JSON_INVALID", "MODEL_JSON_INVALID"]),
        ([{"reviewer_key": "ai-model-a"},
          {"reviewer_key": "ai-model-b"}], []),
        ([{"reviewer_key": "ai-model-a"},
          {"reviewer_key": "ai-model-b"}], []),
    ]
    for i, (reviews, holds) in enumerate(decisions, 1):
        record = {
            "case_key": f"case-{i}", "reviews": reviews,
            "attempt_holds": holds,
        }
        record["receipt_sha256"] = priv.digest(record)
        (folder / q.receipt_name(i)).write_text(
            json.dumps(record), encoding="utf-8"
        )
    return folder, base / "pilot5-v2", base


def test_three_failed_side_plan_is_offline_create_only(tmp_path, monkeypatch):
    folder, output, _ = arrange(tmp_path, monkeypatch)
    first = (folder / q.receipt_name(1)).read_bytes()
    status = plan.prepare(folder, output)
    assert status["status"] == "PILOT5_V2_REPLAY_PLAN_PREPARED__NO_REQUEST"
    assert status["failed_slots"] == 3
    assert status["planned_positions"] == 2
    assert status["model_requests"] == 0
    assert status["train_admitted"] == 0
    data = json.loads((output / plan.PLAN_NAME).read_text())
    assert [(x["position"], x["side"]) for x in data["slots"]] == [
        (1, "b"), (3, "a"), (3, "b")
    ]
    assert all(x["status"] == "REPLAY_NOT_AUTHORIZED" for x in data["slots"])
    assert (output / plan.PLAN_NAME).stat().st_mode & 0o777 == 0o600
    assert output.stat().st_mode & 0o777 == 0o700
    assert (folder / q.receipt_name(1)).read_bytes() == first
    assert plan.prepare(folder, output)["status"] == "PILOT5_V2_REPLAY_PLAN_HOLD"


def test_missing_v1_receipt_is_hold_without_creating_plan(tmp_path, monkeypatch):
    folder, output, _ = arrange(tmp_path, monkeypatch)
    (folder / q.receipt_name(3)).unlink()
    result = plan.prepare(folder, output)
    assert result["status"] == "PILOT5_V2_REPLAY_PLAN_HOLD"
    assert not output.exists()


def test_tampered_v1_receipt_fails_closed(tmp_path, monkeypatch):
    folder, output, _ = arrange(tmp_path, monkeypatch)
    path = folder / q.receipt_name(1)
    raw = json.loads(path.read_text())
    raw["attempt_holds"] = ["MODEL_JSON_INVALID"]
    path.write_text(json.dumps(raw))
    assert plan.prepare(folder, output)["status"] == "PILOT5_V2_REPLAY_PLAN_HOLD"
    assert not output.exists()


def test_finished_slots_never_requeued(tmp_path, monkeypatch):
    folder, output, _ = arrange(tmp_path, monkeypatch)
    path = folder / q.receipt_name(4)
    data = json.loads(path.read_text())
    data["reviews"][0]["decision"] = "HOLD"
    data["receipt_sha256"] = priv.digest({
        k: v for k, v in data.items() if k != "receipt_sha256"
    })
    path.write_text(json.dumps(data))
    result = plan.prepare(folder, output)
    assert result["failed_slots"] == 3
    data = json.loads((output / plan.PLAN_NAME).read_text())
    assert all(x["position"] != 4 for x in data["slots"])

"""Synthetic, no-network tests for the Pilot5 v1/v2 crosswalk."""
from __future__ import annotations

import json

import r60_pilot5_v2_crosswalk as crosswalk


def _fixture(tmp_path, monkeypatch):
    qdir = tmp_path / "quality"
    vdir = tmp_path / "replay"
    qdir.mkdir()
    vdir.mkdir()
    slots = [
        {"position": 1, "side": "b", "original_receipt_sha256": "r1",
         "history_messages_sha256": "h1", "assistant_target_sha256": "t1",
         "original_failure": "MODEL_JSON_INVALID", "model_id": "m",
         "protocol": "deepseek-chat"},
        {"position": 3, "side": "a", "original_receipt_sha256": "r3",
         "history_messages_sha256": "h3", "assistant_target_sha256": "t3",
         "original_failure": "MODEL_JSON_INVALID", "model_id": "m",
         "protocol": "claude-proxy-top-system"},
        {"position": 3, "side": "b", "original_receipt_sha256": "r3",
         "history_messages_sha256": "h3", "assistant_target_sha256": "t3",
         "original_failure": "MODEL_JSON_INVALID", "model_id": "m",
         "protocol": "deepseek-chat"},
    ]
    monkeypatch.setattr(crosswalk.replay, "verify", lambda a, b: ({}, [], slots))
    monkeypatch.setattr(crosswalk.quality, "receipt_name", lambda p: f"{p}.json")
    for i, count in enumerate((1, 2, 0, 2, 2), start=1):
        receipt = qdir / f"{i}.json"
        receipt.write_text(json.dumps({
            "reviews": [{"decision": "HOLD"}] * count,
        }))
        receipt.chmod(0o600)
    # Existing-slot checks are deliberately reused and independently exercised
    # in test_r60_pilot5_v2_replay_execute.py.
    return qdir, vdir, slots


def test_initial_plan_is_partial_no_api(tmp_path, monkeypatch):
    qdir, vdir, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(crosswalk.replay, "verify_existing_slot",
                        lambda path, slot: False)
    safe = crosswalk.audit(qdir, vdir)
    assert safe["status"] == "PILOT5_V2_CROSSWALK_PARTIAL__QUALITY_HOLD"
    assert safe["v1_valid_reviews"] == 7
    assert safe["v2_recorded"] == 0
    assert safe["unresolved_slots"] == 3
    assert safe["model_requests"] == safe["train_admitted"] == 0


def test_three_receipts_still_hold_quality(tmp_path, monkeypatch):
    qdir, vdir, slots = _fixture(tmp_path, monkeypatch)
    for slot in slots:
        path = crosswalk.replay.receipt_file(
            vdir, slot["position"], slot["side"],
        )
        path.write_text(json.dumps({"attempt_status": "HOLD"
                                    if slot["position"] == 1 else "SUCCESS"}))
        path.chmod(0o600)
    monkeypatch.setattr(crosswalk.replay, "verify_existing_slot",
                        lambda path, slot: True)
    safe = crosswalk.audit(qdir, vdir)
    assert safe["status"] == "PILOT5_V2_CROSSWALK_INTEGRITY_PASS__QUALITY_HOLD"
    assert safe["v2_recorded"] == 3
    assert safe["v2_success"] == 2
    assert safe["v2_attempt_holds"] == 1
    assert safe["unresolved_slots"] == 1


def test_inconsistent_v1_review_count_fails_closed(tmp_path, monkeypatch):
    qdir, vdir, _ = _fixture(tmp_path, monkeypatch)
    (qdir / "5.json").write_text(json.dumps({"reviews": []}))
    (qdir / "5.json").chmod(0o600)
    assert crosswalk.audit(qdir, vdir)["status"] == "PILOT5_V2_CROSSWALK_HOLD"


def test_invalid_v2_receipt_fails_closed(tmp_path, monkeypatch):
    qdir, vdir, _ = _fixture(tmp_path, monkeypatch)
    def bad(*args):
        raise crosswalk.replay.Hold("V2_RECEIPT_BINDING_HOLD")
    monkeypatch.setattr(crosswalk.replay, "verify_existing_slot", bad)
    assert crosswalk.audit(qdir, vdir)["status"] == "PILOT5_V2_CROSSWALK_HOLD"

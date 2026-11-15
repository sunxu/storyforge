"""Synthetic-only proof-order tests; NO network, paid API or private cases."""
import json
import stat

import pytest
import r60_forward_reviewer_v2_ledger as ledger
from test_r60_forward_evidence_gate_v1 import protection, source, world


def case():
    return {
        "history_messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "早上好"},
            {"role": "user", "content": "出发吗？"},
        ],
        "target_text": "一起出发。",
        "history_messages_sha256": "a" * 64,
        "assistant_target_sha256": "a" * 64,
    }


def specs():
    return [
        {"side": "a", "provider": "mock-a", "model_id": "model-a",
         "profile": "claude-proxy-top-system", "json_mode": False},
        {"side": "b", "provider": "mock-b", "model_id": "model-b",
         "profile": "deepseek-chat", "json_mode": False},
    ]


def response():
    return {
        "status": 200, "provider_request_id": "mock-observation-123",
        "review": {
            "decision": "PASS",
            "scores": {
                "chinese_prose": 4, "character_consistency": 4,
                "npc_initiative": 4, "player_agency": 4,
                "rule_fidelity": 4, "narrative_continuity": 4,
            },
            "severe_flags": {
                "serious_player_agency": False,
                "hard_fact_or_ban": False, "safety_exclusion": False,
            },
            "reason_cn": "纯合成审核",
        },
    }


def setup(monkeypatch, tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(ledger.private, "BASE", root)
    return root / "new-ledger"


def test_seal_precedes_transport_no_other_review_in_request(monkeypatch, tmp_path):
    path = setup(monkeypatch, tmp_path)
    calls = []

    def fake_transport(side, body):
        assert (path / "PRE_REVIEW_SEAL_PRIVATE.json").exists()
        assert (path / ("REQUEST_" + side.upper() + "_PRIVATE.json")).exists()
        assert "纯合成审核" not in json.dumps(body, ensure_ascii=False)
        calls.append(side)
        result = response()
        result["provider_request_id"] = "synthetic-" + side + "-1234"
        return result

    safe = ledger.execute_synthetic(
        output_dir=path, source=source(), protection=protection(),
        world=world(), case=case(), specs=specs(), transport=fake_transport)
    assert calls == ["a", "b"]
    assert safe["train_admitted"] == 0
    assert safe["provider_execution_independence_verified"] is False
    assert safe["status"].endswith("INDEPENDENCE_HOLD")
    files = list(path.iterdir())
    assert len(files) == 5
    assert all(stat.S_IMODE(f.stat().st_mode) == 0o600 for f in files)
    for side in ("A", "B"):
        out = json.loads((path / f"OUTCOME_{side}_PRIVATE.json").read_text())
        assert out["receipt_level"].endswith("NOT_AUTHENTICATED")


def test_no_request_without_pre_review_proof(monkeypatch, tmp_path):
    path = setup(monkeypatch, tmp_path)
    protected = protection()
    protected["covers_all_protected_sets"] = False
    called = []
    with pytest.raises(ledger.gate.Hold, match="EVALUATION_PROTECTION_HOLD"):
        ledger.execute_synthetic(
            output_dir=path, source=source(), protection=protected,
            world=world(), case=case(), specs=specs(),
            transport=lambda *_: called.append(1))
    assert not called
    assert not path.exists()


def test_no_second_reviewer_on_first_failure(monkeypatch, tmp_path):
    path = setup(monkeypatch, tmp_path)
    called = []

    def broken(side, body):
        called.append(side)
        raise ValueError("synthetic dangerous private reply")

    with pytest.raises(ledger.Hold, match="TRANSPORT_OR_REVIEW_HOLD"):
        ledger.execute_synthetic(
            output_dir=path, source=source(), protection=protection(),
            world=world(), case=case(), specs=specs(), transport=broken)
    assert called == ["a"]
    assert (path / "OUTCOME_A_PRIVATE.json").exists()
    assert not (path / "REQUEST_B_PRIVATE.json").exists()
    assert not (path / "OUTCOME_B_PRIVATE.json").exists()


def test_create_only_no_retry(monkeypatch, tmp_path):
    path = setup(monkeypatch, tmp_path)
    path.mkdir(mode=0o700)
    called = []
    with pytest.raises(ledger.Hold, match="LEDGER_CREATE_ONLY_HOLD"):
        ledger.execute_synthetic(
            output_dir=path, source=source(), protection=protection(),
            world=world(), case=case(), specs=specs(),
            transport=lambda *_: called.append(1))
    assert called == []


def test_duplicate_routes_refused(monkeypatch, tmp_path):
    path = setup(monkeypatch, tmp_path)
    routes = specs()
    routes[1]["model_id"] = routes[0]["model_id"]
    routes[1]["provider"] = routes[0]["provider"]
    with pytest.raises(ledger.Hold, match="TWO_DISTINCT_ROUTES_HOLD"):
        ledger.execute_synthetic(
            output_dir=path, source=source(), protection=protection(),
            world=world(), case=case(), specs=routes,
            transport=lambda *_: None)
    assert not path.exists()

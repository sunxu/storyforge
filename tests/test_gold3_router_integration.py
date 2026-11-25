"""Owner-local integration against the pinned R60 archive, no inference calls."""
import argparse
import json
import os

import httpx
import pytest

from scripts import gold3_ai_judge_owner_local as gold3
from storyforge_inference import hf_router

# Main deliberately does not include the frozen R60 evaluator.
pytestmark = pytest.mark.skipif(
    os.getenv("STORYFORGE_GOLD3_ARCHIVE_TEST") != "1",
    reason="requires pinned R60 archive on PYTHONPATH; see HF Router documentation",
)

MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
TARGET = "林舟收起长剑，低声说道：山中昨夜传来异响。我已派人调查，你若愿意，可以随我去看看。"
USER = "我询问林舟山门为何关闭。"
RULE = "玩家控制旅人，NPC林舟负责守护山门。不得替玩家决定行动。"


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "synthetic-token")
    rows, pins = [], []
    for label in gold3.CASE_IDS:
        rows.append({
            "case": label, "source_card_revision": 1,
            "story_card_at_target": {"rule": RULE},
            "effective_history": [{"role": "user", "content": USER}],
            "assistant_target": TARGET,
            "context_provenance": "READONLY_HISTORICAL_RECONSTRUCTION_NOT_PROVIDER_BYTE_EXACT",
            "gold_quality_admitted": False,
        })
        pins.append({"case": label, "integrity_PRIVATE": {
            "story_card_revision": 1,
            "preceding_user_sha256": gold3.sha_text(USER),
            "assistant_sha256": gold3.sha_text(TARGET),
        }})
    material = tmp_path / "material.json"
    manifest = tmp_path / "manifest.json"
    receipt = tmp_path / "receipt.json"
    gold3.write_new(material, {"schema": gold3.MATERIAL_SCHEMA, "cases": rows})
    gold3.write_new(manifest, {"schema": gold3.MANIFEST_SCHEMA, "cases": pins})
    gold3.write_new(receipt, {
        "schema": gold3.RECOVERY_SCHEMA, "cases_recovered": 3,
        "source_target_digest_verified": 3, "source_card_asof_sha256_verified": 3,
        "case_labels": list(gold3.CASE_IDS),
        "status": "GOLD3_REVIEW_MATERIAL_READY__HUMAN_PRIVACY_QUALITY_AND_WORLD_HOLD",
    })
    out = tmp_path / "out"
    out.mkdir(mode=0o700)
    args = argparse.Namespace(
        material=material, manifest=manifest, recovery_safe=receipt, out_dir=out,
        execute=True, case="C3-S1-Q1", provider="deepinfra", model=MODEL,
        bill_to="adradar", temperature=0, max_tokens=2048,
        approve_private_transfer=True, attest_privacy_reviewed=True, approve_paid_call=True,
    )
    return args


def response():
    # Replay the Owner's observed synthetic score with swapped quote fields.
    return {
        "scores": {
            "narrative_continuity": 3, "character_consistency": 4,
            "rule_fidelity": 4, "chinese_prose": 4,
            "npc_initiative": 4, "player_agency": 5,
        },
        "severe_flags": {
            "serious_player_agency": False, "hard_fact_or_ban": False,
            "safety_exclusion": False,
        },
        "specific_source_quotes": [TARGET],
        "specific_target_quotes": [RULE, USER],
        "literary_quality_notes": "语言简洁自然，有动作、低声道和悬念，情绪克制；细节稍少。",
        "uncertainty": "候选未直接回答山门关闭原因，可视为连续性上的轻度瑕疵；未发现明确硬事实矛盾或严重安全问题。",
    }


def install_mock(monkeypatch, pilot, *, live=True, invalid=False, race=False):
    calls = []
    original = hf_router.HFRouterClient

    def handler(request):
        calls.append(request.method)
        if request.method == "GET":
            if race:
                gold3.write_new(path(pilot, "attempt.private.json"), {"existing": True})
            return httpx.Response(200, json={"data": [{
                "id": MODEL, "providers": [{
                    "provider": "deepinfra", "status": "live" if live else "offline",
                    "supports_structured_output": True,
                }],
            }]})
        assert path(pilot, "attempt.private.json").exists()
        body = json.loads(request.content)
        if pilot.max_tokens is None:
            assert "max_tokens" not in body
        else:
            assert body["max_tokens"] == pilot.max_tokens
        if getattr(pilot, "compensate_length_hold", False):
            suffix = "compensation2" if pilot.max_tokens is None else "compensation1"
            assert path(pilot, suffix + ".attempt.private.json").exists()
        if getattr(pilot, "compensate_legacy_hold", False):
            assert path(pilot, "compensation1.attempt.private.json").exists()
        assert body["model"] == MODEL + ":deepinfra"
        assert "reasoning_effort" not in body
        assert body["response_format"]["type"] == "json_schema"
        raw = response()
        if invalid:
            raw["specific_target_quotes"].append("不存在的引文")
        return httpx.Response(200, json={
            "model": "deepseek/deepseek-v4.1-flash-1017", "provider": "DeepInfra",
            "choices": [{"message": {"content": json.dumps(raw, ensure_ascii=False)},
                         "finish_reason": "stop"}],
        })

    def factory(**kwargs):
        return original(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(hf_router, "HFRouterClient", factory)
    return calls


def path(args, suffix):
    return args.out_dir / ("GOLD3_AI_" + args.case + "." + suffix)


def test_replay_and_no_duplicate(pilot, monkeypatch):
    calls = install_mock(monkeypatch, pilot)
    safe = gold3.run(pilot)
    assert safe["scores"] == response()["scores"]
    assert safe["severe_flags"] == response()["severe_flags"]
    assert safe["quote_relocations"] == {"source_to_target": 1, "target_to_source": 2}
    assert safe["below_quality_floors"] == ["narrative_continuity"]
    assert safe["quality_v1_admitted"] == 0
    raw = json.loads(path(pilot, "response.private.json").read_text())
    assert json.loads(raw["content"]) == response()
    score = json.loads(path(pilot, "score.private.json").read_text())["score"]
    assert score["specific_source_quotes"] == [RULE, USER]
    assert score["specific_target_quotes"] == [TARGET]
    with pytest.raises(gold3.Hold, match="ALREADY_ATTEMPTED"):
        gold3.run(pilot)
    assert calls == ["GET", "POST"]


def test_invalid_quote_stays_hold(pilot, monkeypatch):
    calls = install_mock(monkeypatch, pilot, invalid=True)
    with pytest.raises(gold3.Hold, match="ATTEMPT_UNKNOWN_OR_FAILED"):
        gold3.run(pilot)
    assert path(pilot, "response.private.json").exists()
    assert not path(pilot, "score.private.json").exists()
    diagnostic = json.loads(path(pilot, "diagnostic.safe.json").read_text())
    assert diagnostic["reason_code"] == "JUDGE_NONEXACT_QUOTE_HOLD"
    assert calls == ["GET", "POST"]


def test_unavailable_preflight_no_attempt(pilot, monkeypatch):
    calls = install_mock(monkeypatch, pilot, live=False)
    with pytest.raises(gold3.Hold, match="PROVIDER_UNAVAILABLE"):
        gold3.run(pilot)
    assert list(pilot.out_dir.iterdir()) == []
    assert calls == ["GET"]


def test_create_only_race_no_post_or_false_diagnostic(pilot, monkeypatch):
    calls = install_mock(monkeypatch, pilot, race=True)
    with pytest.raises(gold3.Hold, match="ALREADY_ATTEMPTED"):
        gold3.run(pilot)
    assert json.loads(path(pilot, "attempt.private.json").read_text()) == {"existing": True}
    assert not path(pilot, "diagnostic.safe.json").exists()
    assert calls == ["GET"]


def prior_length(pilot):
    gold3.write_new(path(pilot, "attempt.private.json"), {
        "schema": "storyforge_gold3_ai_attempt_private_v1", "case": pilot.case,
        "source_material_sha256": gold3.sha_bytes(pilot.material.read_bytes()),
        "manifest_sha256": gold3.sha_bytes(pilot.manifest.read_bytes()),
        "model": pilot.model, "provider": pilot.provider, "bill_to": pilot.bill_to,
        "transport": "hf-router", "max_tokens": 2048, "temperature": 0,
    })
    gold3.write_new(path(pilot, "diagnostic.safe.json"), {
        "schema": "storyforge_gold3_ai_judge_diagnostic_safe_v2",
        "case": pilot.case, "status": "HOLD", "attempt_consumed": True,
        "automatic_retry_allowed": False,
        "router_diagnostic": {"http_status": 200, "finish_reason": "length",
                              "content_chars": None},
    })


def test_compensation_once_preserves_prior(pilot, monkeypatch):
    prior_length(pilot)
    old = path(pilot, "attempt.private.json").read_bytes()
    old_diag = path(pilot, "diagnostic.safe.json").read_bytes()
    pilot.compensate_length_hold = True
    pilot.max_tokens = 4096
    calls = install_mock(monkeypatch, pilot)
    assert gold3.run(pilot)["compensation"] is True
    marker = json.loads(path(pilot, "compensation1.attempt.private.json").read_text())
    assert marker["prior_attempt_sha256"] == gold3.sha_bytes(old)
    assert marker["prior_diagnostic_sha256"] == gold3.sha_bytes(old_diag)
    assert path(pilot, "attempt.private.json").read_bytes() == old
    assert path(pilot, "diagnostic.safe.json").read_bytes() == old_diag
    with pytest.raises(gold3.Hold, match="ALREADY_ATTEMPTED"):
        gold3.run(pilot)
    assert calls == ["GET", "POST"]


def test_compensation_requires_exact_prior(pilot, monkeypatch):
    pilot.compensate_length_hold = True
    pilot.max_tokens = 4096
    calls = install_mock(monkeypatch, pilot)
    with pytest.raises(gold3.Hold):
        gold3.run(pilot)
    assert calls == []


def test_default_budget_omits_wire_limit(pilot, monkeypatch):
    pilot.max_tokens = None
    calls = install_mock(monkeypatch, pilot)
    assert gold3.run(pilot)["scores"] == response()["scores"]
    assert json.loads(path(pilot, "attempt.private.json").read_text())["max_tokens"] is None
    assert calls == ["GET", "POST"]


def test_second_compensation_preserves_chain(pilot, monkeypatch):
    prior_length(pilot)
    attempt = path(pilot, "attempt.private.json")
    diagnostic = path(pilot, "diagnostic.safe.json")
    first = json.loads(attempt.read_text())
    first.update(max_tokens=4096, prior_attempt_sha256=gold3.sha_bytes(attempt.read_bytes()),
                 prior_diagnostic_sha256=gold3.sha_bytes(diagnostic.read_bytes()))
    gold3.write_new(path(pilot, "compensation1.attempt.private.json"), first)
    diag = json.loads(diagnostic.read_text())
    diag["router_diagnostic"]["usage"] = {
        "completion_tokens": 4096, "reasoning_tokens": 4092,
    }
    gold3.write_new(path(pilot, "compensation1.diagnostic.safe.json"), diag)
    prior = {p: p.read_bytes() for p in pilot.out_dir.iterdir()}
    pilot.compensate_length_hold = True
    pilot.max_tokens = None
    calls = install_mock(monkeypatch, pilot)
    assert gold3.run(pilot)["compensation"] is True
    marker = json.loads(path(pilot, "compensation2.attempt.private.json").read_text())
    assert marker["max_tokens"] is None
    assert marker["second_attempt_sha256"] == gold3.sha_bytes(
        prior[path(pilot, "compensation1.attempt.private.json")])
    assert all(p.read_bytes() == content for p, content in prior.items())
    with pytest.raises(gold3.Hold, match="ALREADY_ATTEMPTED"):
        gold3.run(pilot)
    assert calls == ["GET", "POST"]


def test_default_budget_compensation_requires_second_failure(pilot, monkeypatch):
    prior_length(pilot)
    pilot.compensate_length_hold = True
    pilot.max_tokens = None
    calls = install_mock(monkeypatch, pilot)
    with pytest.raises(gold3.Hold):
        gold3.run(pilot)
    assert calls == []


@pytest.mark.parametrize("case,with_diag", [("C1-S1-Q1", False), ("C2-S2-Q1", True)])
def test_legacy_compensation_once(pilot, monkeypatch, case, with_diag):
    pilot.case = case
    pilot.max_tokens = None
    pilot.compensate_legacy_hold = True
    attempt = path(pilot, "attempt.private.json")
    gold3.write_new(attempt, {
        "schema": "storyforge_gold3_ai_attempt_private_v1", "case": case,
        "source_material_sha256": gold3.sha_bytes(pilot.material.read_bytes()),
        "manifest_sha256": gold3.sha_bytes(pilot.manifest.read_bytes()),
        "max_api_calls": 1, "automatic_retries": 0, "gold_quality_admitted": False,
    })
    if with_diag:
        gold3.write_new(path(pilot, "diagnostic.safe.json"), {
            "schema": "storyforge_gold3_ai_judge_diagnostic_safe_v2",
            "case": case, "status": "HOLD", "reason_code": "JUDGE_API_OR_FORMAT_HOLD",
            "attempt_consumed": True, "automatic_retry_allowed": False,
        })
    prior = {p: p.read_bytes() for p in pilot.out_dir.iterdir()}
    calls = install_mock(monkeypatch, pilot)
    assert gold3.run(pilot)["compensation"] is True
    marker = json.loads(path(pilot, "compensation1.attempt.private.json").read_text())
    assert marker["prior_attempt_sha256"] == gold3.sha_bytes(prior[attempt])
    assert marker["prior_api_outcome_or_billing_unknown"] is True
    assert (marker["prior_diagnostic_sha256"] is not None) == with_diag
    assert all(p.read_bytes() == blob for p, blob in prior.items())
    with pytest.raises(gold3.Hold, match="ALREADY_ATTEMPTED"):
        gold3.run(pilot)
    assert calls == ["GET", "POST"]


def test_legacy_compensation_rejects_c3(pilot, monkeypatch):
    pilot.max_tokens = None
    pilot.compensate_legacy_hold = True
    calls = install_mock(monkeypatch, pilot)
    with pytest.raises(gold3.Hold, match="COMPENSATION_SCOPE"):
        gold3.run(pilot)
    assert calls == []


def test_legacy_compensation_blocks_existing_reply(pilot, monkeypatch):
    pilot.case = "C1-S1-Q1"
    pilot.max_tokens = None
    pilot.compensate_legacy_hold = True
    gold3.write_new(path(pilot, "attempt.private.json"), {
        "schema": "storyforge_gold3_ai_attempt_private_v1", "case": pilot.case,
        "source_material_sha256": gold3.sha_bytes(pilot.material.read_bytes()),
        "manifest_sha256": gold3.sha_bytes(pilot.manifest.read_bytes()),
        "max_api_calls": 1, "automatic_retries": 0, "gold_quality_admitted": False,
    })
    gold3.write_new(path(pilot, "response.private.json"), {"synthetic": True})
    calls = install_mock(monkeypatch, pilot)
    with pytest.raises(gold3.Hold, match="COMPENSATION_EXISTING_RESULT"):
        gold3.run(pilot)
    assert calls == []

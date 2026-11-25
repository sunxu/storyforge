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

"""Pure synthetic R60 1000-case quality batch tests. No network or private user data."""
from __future__ import annotations

import json

import pytest
import r60_real_ai_dual_review as ai
import r60_real_expand_private as exp
import r60_real_private_batch as g1
import r60_real_quality_batch as q


def synthetic_case(n):
    return g1.parse_rows([(
        f"story-{n}", f"session-{n}", f"assistant-id-{n}", f"user-{n}",
        f"prior-assistant-{n}", f"prior-user-{n}", 10,
        "玩家提出要离开这里。", "NPC 听到请求后有所犹豫。",
        "玩家表示希望离开。", "中文互动叙事描述，NPC 作出自己的决定。" * 35,
    )])[0]


def synthetic_answer(decision="PASS", severe=False):
    return {
        "decision": decision,
        "scores": {k: 5 for k in g1.FLOORS},
        "severe_flags": {
            k: bool(severe and k == "serious_player_agency") for k in g1.SEVERE
        },
        "reason_cn": "NPC 局部行动与可见玩家请求一致，完整世界历史尚未核验。",
    }


def setup_batch(tmp_path, monkeypatch, *, attest=True):
    base = tmp_path / "owner-private"
    base.mkdir(mode=0o700)
    monkeypatch.setattr(g1, "BASE", base)
    monkeypatch.setattr(exp, "BASE", base)
    monkeypatch.setattr(q, "EXPECTED_CASES", 3)
    source = base / "original-expand"
    source.mkdir(mode=0o700)
    cases = [synthetic_case(i) for i in range(3)]
    monkeypatch.setattr(q, "frozen_pool", lambda path: (cases, "pool-sha-synthetic"))
    out = base / "new-quality"
    safe = q.create_config(
        out, source, "http://127.0.0.1:11434/v1", "model-alpha",
        "http://127.0.0.1:11434/v1", "model-beta",
        False, attest, True, 120,
    )
    return base, source, out, cases, safe


def test_init_and_safe_no_identifiers(tmp_path, monkeypatch):
    _base, source, folder, cases, safe = setup_batch(tmp_path, monkeypatch)
    assert safe["candidate_total"] == 3
    assert safe["quality_pass"] == 0 and safe["train_admitted"] == 0
    assert "story-0" not in json.dumps(safe)
    assert "assistant-id-" not in json.dumps(safe)
    assert folder.stat().st_mode & 0o777 == 0o700
    assert (folder / q.CONFIG_FILE).stat().st_mode & 0o777 == 0o600
    assert q.validate_config(folder)["source"] == str(source)
    with pytest.raises(q.Hold, match="QUALITY_OUTPUT_EXISTS_HOLD"):
        q.create_config(folder, source, "http://localhost:1/v1", "A",
                        "http://localhost:1/v1", "B", False, True, False, 100)
    assert len(cases) == 3


def test_independent_dual_pass_resume_and_no_replay(tmp_path, monkeypatch):
    _base, _source, folder, cases, _ = setup_batch(tmp_path, monkeypatch)
    calls = []

    def fake_api(endpoint, model, key, prompt, timeout, json_mode):
        calls.append((model, prompt))
        return synthetic_answer()

    monkeypatch.setattr(ai, "model_request", fake_api)
    first = q.advance(folder, 2)
    assert first["cases_reviewed"] == 2
    assert first["quality_decisions"] == {"PASS": 2, "HOLD": 0, "REJECT": 0}
    assert first["train_admitted"] == 0
    assert first["remaining_cases"] == 1
    assert len(calls) == 4
    assert calls[0][1] == calls[1][1]
    assert "story-0" not in calls[0][1]
    first_bytes = (folder / q.receipt_name(1)).read_bytes()
    second = q.advance(folder, 2)
    assert second["cases_reviewed"] == 3
    assert second["quality_pass"] == 3
    assert second["status"] == "QUALITY_BATCH_REVIEWED__TRAIN_ADMISSION_HOLD"
    assert len(calls) == 6
    assert (folder / q.receipt_name(1)).read_bytes() == first_bytes
    assert (folder / q.receipt_name(3)).stat().st_mode & 0o777 == 0o600
    assert q.inspect(folder)["cases_reviewed"] == 3
    assert q.advance(folder, 2)["cases_reviewed"] == 3
    assert len(calls) == 6
    assert cases[0]["source"]["assistant_message_id"] not in json.dumps(second)


def test_no_attestation_means_hold_not_fake_pass(tmp_path, monkeypatch):
    base, _, folder, _, _ = setup_batch(tmp_path, monkeypatch, attest=False)
    assert base.is_dir()
    monkeypatch.setattr(ai, "model_request", lambda *args: synthetic_answer())
    safe = q.advance(folder, 1)
    assert safe["quality_pass"] == 0
    assert safe["quality_decisions"]["HOLD"] == 1
    assert safe["hold_reject_codes"] == {"INDEPENDENCE_NOT_ATTESTED": 1}
    assert safe["reviewer_independence_independently_proven_by_script"] is False


def test_severe_player_agency_exclusion(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)

    def fake(endpoint, model, key, prompt, timeout, json_mode):
        if model == "model-beta":
            return synthetic_answer("REJECT", True)
        return synthetic_answer()

    monkeypatch.setattr(ai, "model_request", fake)
    safe = q.advance(folder, 1)
    assert safe["quality_decisions"]["REJECT"] == 1
    assert safe["quality_pass"] == 0
    assert safe["train_admitted"] == 0


def test_one_model_refusal_keeps_case_hold(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)

    def fake(endpoint, model, key, prompt, timeout, json_mode):
        if model == "model-beta":
            raise ai.Hold("MODEL_JSON_INVALID")
        return synthetic_answer()

    monkeypatch.setattr(ai, "model_request", fake)
    safe = q.advance(folder, 1)
    assert safe["cases_reviewed"] == 1
    assert safe["quality_decisions"]["HOLD"] == 1
    assert safe["model_attempt_hold_counts"] == {"MODEL_JSON_INVALID": 1}
    assert safe["train_admitted"] == 0
    assert len(json.loads((folder / q.receipt_name(1)).read_bytes())["reviews"]) == 1


def test_both_models_unavailable_not_recorded(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)

    def down(*args):
        raise ai.Hold("MODEL_TRANSPORT_HOLD")

    monkeypatch.setattr(ai, "model_request", down)
    with pytest.raises(q.Hold, match="BOTH_REVIEW_MODELS_UNAVAILABLE"):
        q.advance(folder, 2)
    assert not (folder / q.receipt_name(1)).exists()
    assert q.inspect(folder)["cases_reviewed"] == 0


def test_receipt_tampering_blocks_inspect_or_replay(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)
    monkeypatch.setattr(ai, "model_request", lambda *args: synthetic_answer())
    q.advance(folder, 2)
    path = folder / q.receipt_name(1)
    result = json.loads(path.read_bytes())
    result["reviews"][0]["reason_cn"] = "事后擅改"
    path.write_bytes(exp.private_bytes(result))
    with pytest.raises(q.Hold, match="QUALITY_SOURCE_OR_RECEIPT_TAMPER_HOLD"):
        q.inspect(folder)
    with pytest.raises(q.Hold, match="QUALITY_SOURCE_OR_RECEIPT_TAMPER_HOLD"):
        q.advance(folder, 1)


def test_source_pool_mutation_blocks_future_model_calls(tmp_path, monkeypatch):
    _, _, folder, cases, _ = setup_batch(tmp_path, monkeypatch)
    monkeypatch.setattr(q, "frozen_pool", lambda path: (cases, "changed-pool"))
    monkeypatch.setattr(ai, "model_request", lambda *args: pytest.fail("network!"))
    with pytest.raises(q.Hold, match="FROZEN_POOL_CHANGED_HOLD"):
        q.advance(folder, 2)
    assert not (folder / q.receipt_name(1)).exists()


def test_security_remote_requires_explicit_opt_in(tmp_path, monkeypatch):
    base, source, _folder, _cases, _safe = setup_batch(tmp_path, monkeypatch)
    with pytest.raises(ai.Hold, match="REMOTE_REVIEW_REQUIRES_EXPLICIT_HTTPS_OPT_IN"):
        q.create_config(
            base / "bad-remote", source, "https://example.invalid/v1", "AA",
            "http://127.0.0.1:11434/v1", "BB", False, False, False, 90)
    assert not (base / "bad-remote").exists()


def test_config_same_models_and_timeout_rejected(tmp_path, monkeypatch):
    base, source, _folder, _, _ = setup_batch(tmp_path, monkeypatch)
    with pytest.raises(q.Hold, match="DISTINCT_MODELS_REQUIRED"):
        q.create_config(
            base / "bad-models", source, "http://localhost:10/v1", "SAME",
            "http://localhost:11/v1", "same", False, True, False, 60)
    with pytest.raises(q.Hold, match="TIMEOUT_BOUNDS_HOLD"):
        q.create_config(
            base / "bad-timeout", source, "http://localhost:10/v1", "A",
            "http://localhost:11/v1", "B", False, True, False, 1)


def test_max_cases_is_bounded_and_folder_missing(tmp_path, monkeypatch):
    base, _source, folder, _, _ = setup_batch(tmp_path, monkeypatch)
    with pytest.raises(q.Hold, match="MAX_CASES_PER_CALL_HOLD"):
        q.advance(folder, 100)
    with pytest.raises(q.Hold, match="QUALITY_BATCH_NOT_INITIALIZED"):
        q.advance(base / "absent", 1)
    with pytest.raises(q.Hold, match="QUALITY_BATCH_NOT_INITIALIZED"):
        q.inspect(base / "absent")


def test_duplicate_reviewer_in_private_receipt_denied(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)
    monkeypatch.setattr(ai, "model_request", lambda *args: synthetic_answer())
    q.advance(folder, 1)
    path = folder / q.receipt_name(1)
    value = json.loads(path.read_bytes())
    value["reviews"][1]["reviewer_key"] = "ai-model-a"
    value["receipt_sha256"] = g1.digest({
        k: v for k, v in value.items() if k != "receipt_sha256"})
    path.write_bytes(exp.private_bytes(value))
    with pytest.raises(q.Hold, match="QUALITY_DUPLICATE_REVIEWER_HOLD"):
        q.inspect(folder)


def test_case_output_immutable_not_overwritten(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)
    monkeypatch.setattr(ai, "model_request", lambda *args: synthetic_answer())
    q.advance(folder, 1)
    original = (folder / q.receipt_name(1)).read_bytes()
    with pytest.raises(q.Hold, match="QUALITY_RECEIPT_ALREADY_EXISTS"):
        q.atomic_case_file(folder, 1, {"schema": q.CASE_SCHEMA})
    assert (folder / q.receipt_name(1)).read_bytes() == original


def test_model_id_tampering_with_recomputed_digest_rejected(tmp_path, monkeypatch):
    _, _, folder, _, _ = setup_batch(tmp_path, monkeypatch)
    monkeypatch.setattr(ai, "model_request", lambda *args: synthetic_answer())
    q.advance(folder, 1)
    path = folder / q.receipt_name(1)
    value = json.loads(path.read_bytes())
    value["reviews"][0]["model_id"] = "fraud"
    value["receipt_sha256"] = g1.digest({
        k: v for k, v in value.items() if k != "receipt_sha256"})
    path.write_bytes(exp.private_bytes(value))
    with pytest.raises(q.Hold, match="QUALITY_REVIEW_MODEL_MISMATCH_HOLD"):
        q.inspect(folder)

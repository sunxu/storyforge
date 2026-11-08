"""Synthetic-only reusable HF Quality Pipeline review and isolated A/B stage tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from storyforge_gold_quality import hf_blind_stage as stage
from storyforge_gold_quality import hf_literary_review as review

SHA_A = "a" * 40
SHA_B = "b" * 40
MODEL_A = "Qwen/Qwen3-32B"
MODEL_B = "zai-org/GLM-4-32B-0414"


def case(i):
    history = [
        {"role": "user", "content": f"第{i}章，玩家请NPC带路。"},
        {"role": "assistant", "content": "NPC犹豫片刻，向窗外望去。"},
        {"role": "user", "content": "玩家说：我想先看地图。"},
    ]
    target = "NPC缓缓展开地图，指着城门说：夜间城门关闭，请注意安全。"
    return {
        "case_key": f"private-case-{i}",
        "source": {"story_id": f"PRIVATE_STORY_{i}"},
        "history_messages": history, "history_messages_sha256": review.digest(history),
        "target_text": target, "assistant_target_sha256": review.digest(target),
        "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
    }


def blind(i=0):
    row = case(i)
    return {
        "schema": review.SCHEMA, "blind_id": f"{i+1:032x}",
        "visible_history": row["history_messages"], "target_text": row["target_text"],
        "target_semantics": row["target_semantics"], "policy": review.POLICY,
    }


def answer(row, decision="PASS"):
    return {
        "decision": decision, "scores": {k: 5 for k in review.FLOORS},
        "severe_flags": {k: False for k in review.SEVERE},
        "specific_source_quotes": [row["visible_history"][-1]["content"]],
        "specific_target_quotes": [row["target_text"][0:12]],
        "literary_quality_notes": "NPC响应玩家意图并推动剧情，但只可判断可见历史。",
        "uncertainty": "缺少历史世界规则" if decision == "HOLD" else "",
    }


def private_home(tmp_path):
    p = tmp_path / "private"
    p.mkdir(mode=0o700)
    return p


def setup(tmp_path):
    base = private_home(tmp_path)
    source = [case(i) for i in range(3)]
    root = base / "hf-stage"
    code = Path(review.__file__)
    prepared = stage.stage(root, source, "c" * 64, code,
                           MODEL_A, SHA_A, MODEL_B, SHA_B)
    return root, source, prepared


def test_validator_pass_with_strict_source_and_target_quotes():
    row = blind(1)
    assert review.validate_response(answer(row), row) == "PASS"
    prompt = review.prompt_messages(row)
    assert prompt[0]["role"] == "system"
    assert "world_card_verified" in prompt[-1]["content"]
    assert "PRIVATE_STORY" not in json.dumps(prompt)


def test_no_fabricated_card_requirements():
    fields = review.response_schema()["properties"]
    assert "card_snapshot_suitable_for_offline_training" not in fields
    assert "card_conflicts_with_visible_history_or_gold" not in fields
    assert set(review.FLOORS) == {
        "chinese_prose", "character_consistency", "npc_initiative",
        "player_agency", "rule_fidelity", "narrative_continuity",
    }


def test_rejects_non_exact_quote_and_missing_pass_evidence():
    row = blind()
    invalid = answer(row)
    invalid["specific_target_quotes"] = ["虚构的对话引文"]
    with pytest.raises(review.ReviewError, match="MODEL_NONEXACT_QUOTE_HOLD"):
        review.validate_response(invalid, row)
    invalid = answer(row)
    invalid["specific_source_quotes"] = []
    with pytest.raises(review.ReviewError, match="MODEL_NONEXACT_QUOTE_HOLD"):
        review.validate_response(invalid, row)


def test_rejects_severe_without_reject_and_low_pass_floor():
    row = blind()
    invalid = answer(row)
    invalid["severe_flags"]["serious_player_agency"] = True
    with pytest.raises(review.ReviewError, match="MODEL_SEVERE_MUST_REJECT"):
        review.validate_response(invalid, row)
    invalid = answer(row)
    invalid["scores"]["chinese_prose"] = 3
    with pytest.raises(review.ReviewError, match="MODEL_BELOW_QUALITY_FLOOR_HOLD"):
        review.validate_response(invalid, row)
    rejected = answer(row, "REJECT")
    rejected["severe_flags"]["serious_player_agency"] = True
    assert review.validate_response(rejected, row) == "REJECT"


def test_hold_requires_uncertainty_not_guessing():
    row = blind()
    valid = answer(row, "HOLD")
    assert review.validate_response(valid, row) == "HOLD"
    valid["uncertainty"] = ""
    with pytest.raises(review.ReviewError, match="MODEL_UNCERTAINTY_HOLD"):
        review.validate_response(valid, row)


def test_checkpoint_source_model_pinned_and_append_only(tmp_path):
    row = blind()
    output = tmp_path / "output"
    output.mkdir()
    path = output / review.checkpoint_name(1)
    record = review.checkpoint_record(1, row, answer(row), MODEL_A, SHA_A)
    review.write_checkpoint(path, record)
    assert review.read_checkpoint(path, 1, row, MODEL_A, SHA_A) == record
    with pytest.raises(FileExistsError):
        review.write_checkpoint(path, record)
    with pytest.raises(review.ReviewError, match="CHECKPOINT_SOURCE_OR_MODEL_HOLD"):
        review.read_checkpoint(path, 1, row, MODEL_A, SHA_B)
    assert review.safe_summary([row], output, MODEL_A, SHA_A)["quality_decisions"]["PASS"] == 1


def test_checkpoint_tamper_detected(tmp_path):
    row = blind()
    path = tmp_path / review.checkpoint_name(1)
    record = review.checkpoint_record(1, row, answer(row), MODEL_A, SHA_A)
    review.write_checkpoint(path, record)
    record["response"]["literary_quality_notes"] = "有人事后修改评分"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(review.ReviewError, match="CHECKPOINT_SOURCE_OR_MODEL_HOLD"):
        review.read_checkpoint(path, 1, row, MODEL_A, SHA_A)


def test_read_input_rejects_private_identifiers_or_future_role(tmp_path):
    row = blind()
    row["source"] = {"story_id": "PRIVATE_STORY"}
    with pytest.raises(review.ReviewError, match="BLIND_INPUT_SCHEMA_HOLD"):
        review.validate_input(row)
    row = blind()
    row["visible_history"][-1]["role"] = "system"
    with pytest.raises(review.ReviewError, match="BLIND_HISTORY_BOUNDARY_HOLD"):
        review.validate_input(row)


def test_a_b_blind_staging_no_crosswalk_or_private_ids_in_job(tmp_path):
    root, cases, safe = setup(tmp_path)
    assert safe["status"] == "HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED"
    assert safe["cases_staged"] == 3
    assert safe["paid_gpu_submitted"] is False
    for side in ("A", "B"):
        input_folder = root / f"input_{side}"
        assert input_folder.stat().st_mode & 0o777 == 0o700
        payload = (input_folder / "source.private.jsonl").read_text()
        assert "PRIVATE_STORY" not in payload
        assert "private-case-" not in payload
        assert "owner_crosswalk" not in payload
        assert (input_folder / "runner.py").stat().st_mode & 0o777 == 0o600
        assert len(review.read_input(input_folder / "source.private.jsonl")) == len(cases)
    assert not (root / "input_A" / "source.private.jsonl").read_bytes() == (
        root / "input_B" / "source.private.jsonl").read_bytes()
    assert (root / "owner" / stage.MAP_NAME).is_file()
    assert not (root / "input_A" / stage.MAP_NAME).exists()


def test_stage_refuses_overwrite_and_wrong_revision(tmp_path):
    root, cases, _ = setup(tmp_path)
    with pytest.raises(stage.StageError, match="PRIVATE_STAGE_OUTPUT_EXISTS_HOLD"):
        stage.stage(root, cases, "c" * 64, Path(review.__file__),
                    MODEL_A, SHA_A, MODEL_B, SHA_B)
    with pytest.raises(stage.StageError, match="MODEL_REVISION_CONTRACT_HOLD"):
        stage.stage(root.parent / "other", cases, "c" * 64,
                    Path(review.__file__), MODEL_A, "HEAD", MODEL_B, SHA_B)


def test_a_b_audit_stays_hold_until_both_present(tmp_path):
    root, cases, _ = setup(tmp_path)
    empty = stage.audit(root, "c" * 64, cases)
    assert empty["quality_pass"] == 0
    assert empty["quality_decisions"]["HOLD"] == 3
    assert empty["training_authorized"] is False
    for position, row in enumerate(
            review.read_input(root / "input_A" / "source.private.jsonl"), 1):
        review.write_checkpoint(
            root / "output_A" / review.checkpoint_name(position),
            review.checkpoint_record(position, row, answer(row), MODEL_A, SHA_A))
    one = stage.audit(root, "c" * 64, cases)
    assert one["model_a_reviewed"] == 3
    assert one["model_b_reviewed"] == 0
    assert one["quality_pass"] == 0


def test_a_b_audit_all_pass_and_severe_reject(tmp_path):
    root, cases, _ = setup(tmp_path)
    for side, model, revision in (("A", MODEL_A, SHA_A), ("B", MODEL_B, SHA_B)):
        for position, row in enumerate(
                review.read_input(root / f"input_{side}" / "source.private.jsonl"), 1):
            result = answer(row)
            if side == "B" and position == 1:
                result["decision"] = "REJECT"
                result["severe_flags"]["serious_player_agency"] = True
            review.write_checkpoint(
                root / f"output_{side}" / review.checkpoint_name(position),
                review.checkpoint_record(position, row, result, model, revision))
    safe = stage.audit(root, "c" * 64, cases)
    assert safe["complete_pairs"] == 3
    assert safe["quality_pass"] == 2
    assert safe["quality_decisions"] == {"PASS": 2, "HOLD": 0, "REJECT": 1}
    assert safe["training_authorized"] is False
    assert safe["r50_complete_exclusion_verified"] is False


def test_stage_source_drift_prevents_audit(tmp_path):
    root, cases, _ = setup(tmp_path)
    cases[0]["target_text"] = "已改变的候选目标"
    with pytest.raises(stage.StageError, match="STAGE_SOURCE_DRIFT_HOLD"):
        stage.audit(root, "c" * 64, cases)


def test_stage_crosswalk_mutation_prevents_audit(tmp_path):
    root, cases, _ = setup(tmp_path)
    crosswalk = root / "owner" / stage.MAP_NAME
    data = json.loads(crosswalk.read_bytes())
    data["bindings"]["A"][0]["case_key"] = "fake"
    crosswalk.write_bytes(stage.safe_bytes(data))
    with pytest.raises(stage.StageError, match="STAGE_SOURCE_DRIFT_HOLD"):
        stage.audit(root, "c" * 64, cases)


def test_stage_tampered_model_revision_held(tmp_path):
    root, cases, _ = setup(tmp_path)
    manifest = root / "owner" / stage.MANIFEST_NAME
    data = json.loads(manifest.read_bytes())
    data["model_pins"]["A"][1] = "d" * 40
    manifest.write_bytes(stage.safe_bytes(data))
    with pytest.raises(stage.StageError, match="STAGE_OWNER_SOURCE_HOLD"):
        stage.audit(root, "c" * 64, cases)


def test_verifier_never_submits_or_initializes_model(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "private"
    input_dir.mkdir()
    file = input_dir / "source.private.jsonl"
    file.write_bytes(stage.safe_bytes(blind()))
    monkeypatch.setattr(sys, "argv", [
        "runner.py", "--verify-only", "--input", str(file),
        "--output-dir", str(input_dir), "--model", MODEL_A,
        "--revision", SHA_A])
    assert review.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE"
    assert result["training_authorized"] is False

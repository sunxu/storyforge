"""Synthetic-only reusable HF Quality Pipeline review and isolated A/B stage tests."""
from __future__ import annotations

import json
import os
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


def test_severe_reject_without_target_quote_is_evidence_hold():
    row = blind(1)
    rejected = answer(row, "REJECT")
    rejected["severe_flags"]["safety_exclusion"] = True
    rejected["specific_target_quotes"] = []
    with pytest.raises(review.ReviewError, match="MODEL_SEVERE_EVIDENCE_HOLD"):
        review.validate_response(rejected, row)
    # Do not silently fabricate a quote; a verbatim existing one is valid.
    rejected["specific_target_quotes"] = [row["target_text"][0:12]]
    assert review.validate_response(rejected, row) == "REJECT"


def test_reason_field_safe_subcodes_are_distinct():
    row = blind()
    for field, value, reason in (
        ("literary_quality_notes", "", "MODEL_NOTES_TOO_SHORT_HOLD"),
        ("literary_quality_notes", "很短", "MODEL_NOTES_TOO_SHORT_HOLD"),
        ("literary_quality_notes", None, "MODEL_NOTES_TYPE_HOLD"),
        ("uncertainty", None, "MODEL_UNCERTAINTY_TYPE_HOLD"),
    ):
        invalid = answer(row)
        invalid[field] = value
        with pytest.raises(review.ReviewError, match=reason):
            review.validate_response(invalid, row)
    assert len(answer(row)["literary_quality_notes"].strip()) >= 8
    assert review.validate_response(answer(row), row) == "PASS"


def test_legacy_v1_checkpoint_not_implicitly_trusted_under_v2(tmp_path):
    row = blind()
    record = review.checkpoint_record(1, row, answer(row), MODEL_A, SHA_A)
    record["schema"] = "storyforge_hf_literary_checkpoint_private_v1"
    record["receipt_sha256"] = review.digest({
        k: value for k, value in record.items() if k != "receipt_sha256"
    })
    path = tmp_path / review.checkpoint_name(1)
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(review.ReviewError, match="CHECKPOINT_SOURCE_OR_MODEL_HOLD"):
        review.read_checkpoint(path, 1, row, MODEL_A, SHA_A)


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
    assert (root / "input_A" / "source.private.jsonl").read_bytes() != (
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


def test_exact_shared_tokenizer_core_is_staged_and_pinned(tmp_path):
    from storyforge_dataset import token_preflight

    root, cases, _ = setup(tmp_path)
    expected = Path(token_preflight.__file__).read_bytes()
    for side in ("A", "B"):
        staged = root / f"input_{side}" / "token_core.py"
        assert staged.read_bytes() == expected
        assert staged.stat().st_mode & 0o777 == 0o600
    stage.verified_stage(root, "c" * 64, cases)


def test_tampered_shared_core_fails_closed(tmp_path):
    root, cases, _ = setup(tmp_path)
    path = root / "input_A" / "token_core.py"
    path.write_bytes(path.read_bytes() + b"\n# altered\n")
    with pytest.raises(stage.StageError, match="STAGE_BYTES_CHANGED_HOLD"):
        stage.audit(root, "c" * 64, cases)


def test_hf_pipeline_export_reuses_existing_append_review_manifest(tmp_path):
    from argparse import Namespace

    from storyforge_gold_quality.cli import append_review
    from storyforge_gold_quality.manifest import load_events

    root, cases, _ = setup(tmp_path)
    for side, model, revision in (("A", MODEL_A, SHA_A), ("B", MODEL_B, SHA_B)):
        for position, row in enumerate(
                review.read_input(root / f"input_{side}" / "source.private.jsonl"), 1):
            review.write_checkpoint(
                root / f"output_{side}" / review.checkpoint_name(position),
                review.checkpoint_record(
                    position, row, answer(row), model, revision))
    receipt = stage.export_pipeline_reviews(root, "c" * 64, cases)
    assert receipt["status"] == "HF_QUALITY_PIPELINE_PRIVATE_IMPORT_READY__NOT_IMPORTED"
    assert receipt["manifest_modified"] is False
    assert receipt["reviewer_a_rows"] == receipt["reviewer_b_rows"] == 3
    repo = tmp_path / "checkout"
    repo.mkdir()
    private_manifest = root.parent / "manifest.jsonl"
    for side in ("A", "B"):
        file = root / "owner" / f"reviewer_{side}_pipeline.private.jsonl"
        assert file.stat().st_mode & 0o777 == 0o600
        data = [json.loads(x) for x in file.read_text().splitlines()]
        assert len(data) == 3
        assert "PRIVATE_STORY" not in json.dumps(data)
        result = append_review(Namespace(
            batch="r60-real", event_type="BLIND_REVIEW",
            input=file, manifest=private_manifest, repo_root=repo))
        assert result["events_appended"] == 3
    events = load_events(private_manifest)
    assert len(events) == 6
    assert {e["payload"]["reviewer_role"] for e in events} == {
        "REVIEWER_A", "REVIEWER_B"}
    assert all(e["event_type"] == "BLIND_REVIEW" for e in events)
    with pytest.raises(stage.StageError, match="HF_PIPELINE_IMPORT_ALREADY_EXISTS"):
        stage.export_pipeline_reviews(root, "c" * 64, cases)


def test_hf_pipeline_export_incomplete_pair_is_hold(tmp_path):
    root, cases, _ = setup(tmp_path)
    with pytest.raises(stage.StageError, match="HF_DUAL_REVIEW_INCOMPLETE_HOLD"):
        stage.export_pipeline_reviews(root, "c" * 64, cases)
    assert not (root / "owner" / "reviewer_A_pipeline.private.jsonl").exists()


def test_quality_pipeline_inspect_command_uses_shared_reviewer(tmp_path):
    from argparse import Namespace

    from storyforge_gold_quality.cli import inspect_hf_review

    root, _, _ = setup(tmp_path)
    infile = root / "input_A" / "source.private.jsonl"
    out = root / "output_A"
    result = inspect_hf_review(Namespace(
        input=infile, output_dir=out, model=MODEL_A, revision=SHA_A))
    assert result["cases_total"] == 3
    assert result["status"] == "HF_REVIEW_PARTIAL__NO_ADMISSION"
    assert result["quality_v1_admitted"] == 0


def test_cpu_tokenizer_preflight_reuses_shared_core_without_gpu(tmp_path, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    answer_safe = review.token_preflight(
        [blind(1), blind(2)], MODEL_A, SHA_A, 4096, 2400,
        tokenizer_factory=lambda *args, **kwargs: object(),
        encode_fn=lambda tokenizer, prompt: list(range(100)),
    )
    assert answer_safe["status"] == "HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU"
    assert answer_safe["cases_checked"] == 2
    assert answer_safe["model_revision_pinned"] is True
    assert answer_safe["gpu_started"] is False
    assert answer_safe["over_budget_count"] == 0
    assert "PRIVATE_STORY" not in json.dumps(answer_safe)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""


def test_cpu_tokenizer_budget_hold_is_not_review_pass():
    hold = review.token_preflight(
        [blind()], MODEL_A, SHA_A, 4096, 2400,
        tokenizer_factory=lambda *args, **kwargs: object(),
        encode_fn=lambda tokenizer, prompt: list(range(2000)),
    )
    assert hold["status"] == "HF_REVIEW_CPU_TOKEN_BUDGET_HOLD__NO_GPU"
    assert hold["over_budget_count"] == 1
    assert hold["training_authorized"] is False


def test_cpu_preflight_refuses_visible_gpu(tmp_path, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    with pytest.raises(review.ReviewError, match="HF_CPU_RESOURCE_GUARD_HOLD"):
        review.token_preflight(
            [blind()], MODEL_A, SHA_A, 4096, 2400,
            tokenizer_factory=lambda *args, **kwargs: pytest.fail("tokenizer"),
            encode_fn=lambda t, p: pytest.fail("encode"),
        )


def test_staged_hf_runtime_exact_input_and_cpu_resource_modules(tmp_path):
    from storyforge_dataset.hf_runtime import inputs, resources

    root, cases, _ = setup(tmp_path)
    for side in ("A", "B"):
        assert (root / f"input_{side}" / "runtime_inputs.py").read_bytes() == (
            Path(inputs.__file__).read_bytes())
        assert (root / f"input_{side}" / "runtime_resources.py").read_bytes() == (
            Path(resources.__file__).read_bytes())
    stage.verified_stage(root, "c" * 64, cases)


def test_tokenizer_load_failure_emits_only_safe_error_code():
    def fail(*_args, **_kwargs):
        raise RuntimeError("PRIVATE_INPUT_TEXT_MUST_NOT_APPEAR")

    with pytest.raises(review.ReviewError, match="HF_CPU_TOKENIZER_LOAD_HOLD") as info:
        review.token_preflight(
            [blind()], MODEL_A, SHA_A, 4096, 2400,
            tokenizer_factory=fail, encode_fn=lambda _t, _m: [1] * 100)
    assert "PRIVATE_INPUT_TEXT" not in str(info.value)


def test_tokenizer_chat_template_failure_emits_bounded_error():
    def fail(_tokenizer, _messages):
        raise ValueError("private model response: do not reveal")

    with pytest.raises(review.ReviewError, match="HF_CPU_CHAT_TEMPLATE_HOLD") as info:
        review.token_preflight(
            [blind()], MODEL_A, SHA_A, 4096, 2400,
            tokenizer_factory=lambda *_args, **_kwargs: object(),
            encode_fn=fail)
    assert "private model response" not in str(info.value)


def test_unknown_input_failure_reports_phase_only(tmp_path, monkeypatch, capsys):
    input_file = tmp_path / "synthetic.jsonl"
    input_file.write_bytes(stage.safe_bytes(blind()))
    monkeypatch.setattr(review, "read_input", lambda _: 1 / 0)
    monkeypatch.setattr(sys, "argv", [
        "runner.py", "--input", str(input_file),
        "--output-dir", str(tmp_path), "--model", MODEL_A,
        "--revision", SHA_A, "--verify-only"])
    assert review.main() == 42
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "HF_REVIEW_HOLD"
    assert result["reason_code"] == "HF_REVIEW_INPUT_RUNTIME_HOLD"
    assert result["private_values_emitted"] is False


@pytest.mark.parametrize(
    ("core_error", "expected"),
    [
        ("TOKEN_IDS_INVALID", "HF_CPU_TOKEN_IDS_INVALID"),
        ("CHAT_MESSAGES_INVALID", "HF_CPU_CHAT_MESSAGES_INVALID"),
        ("CHAT_TEMPLATE_RENDER_FAILED_TYPE_ERROR",
         "HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_TYPE_ERROR"),
        ("CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR",
         "HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR"),
        ("CHAT_TEMPLATE_RENDER_FAILED_CLASS_CUSTOMTOKENIZERERROR",
         "HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_CLASS_CUSTOMTOKENIZERERROR"),
        ("private text: CHAT_TEMPLATE_RENDER_FAILED_TYPE_ERROR",
         "HF_CPU_CHAT_TEMPLATE_HOLD"),
    ],
)
def test_cpu_token_preflight_preserves_only_shared_core_safe_code(
        core_error, expected):
    def fake_encode(_tokenizer, _messages):
        raise ValueError(core_error)

    with pytest.raises(review.ReviewError) as info:
        review.token_preflight(
            [blind()], MODEL_A, SHA_A, 4096, 2400,
            tokenizer_factory=lambda *_args, **_kwargs: object(),
            encode_fn=fake_encode)
    assert str(info.value) == expected


def test_cpu_token_error_code_strict_bounded_allowlist():
    assert review.cpu_token_error_code(
        ValueError("CHAT_TEMPLATE_RENDER_FAILED_CLASS_" + "A" * 10000)
    ) == "HF_CPU_CHAT_TEMPLATE_HOLD"
    assert review.cpu_token_error_code(
        ValueError("CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR")
    ) == "HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR"

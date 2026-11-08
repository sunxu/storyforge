"""Synthetic only: Owner-local A/B blind pilot pairing and receipt replay."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from storyforge_gold_quality import hf_blind_stage as stage
from storyforge_gold_quality import hf_literary_review as review
from storyforge_gold_quality import hf_pilot_pairwise_audit as audit
from storyforge_gold_quality import hf_pilot_semantic_c as calibration


def fake_case(i: int) -> dict:
    history = [
        {"role": "user", "content": f"第{i}条：帮我看地图。"},
        {"role": "assistant", "content": "NPC指向地图上的旧城门。"},
        {"role": "user", "content": "玩家说：先走到城门。"},
    ]
    target = f"第{i}条NPC抬起手指向城门，说道路暂时安全。"
    return {
        "case_key": f"private-source-{i}",
        "history_messages": history,
        "history_messages_sha256": review.digest(history),
        "target_text": target,
        "assistant_target_sha256": review.digest(target),
        "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
    }


def fake_response(row: dict) -> dict:
    return {
        "decision": "PASS", "scores": {k: 5 for k in review.FLOORS},
        "severe_flags": {k: False for k in review.SEVERE},
        "specific_source_quotes": [row["visible_history"][-1]["content"]],
        "specific_target_quotes": [row["target_text"][:12]],
        "literary_quality_notes": "NPC响应历史中的玩家要求，提供了下一步观察机会。",
        "uncertainty": "",
    }


@pytest.fixture
def staged(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    # Deterministic disjoint first-five inputs; avoid a ~2.5% overlap flake
    # from the real cryptographic shuffling in synthetic fixtures only.
    class TestShuffle:
        calls = 0

        def shuffle(self, values):
            TestShuffle.calls += 1
            if TestShuffle.calls == 2:
                values[:] = values[5:] + values[:5]
            elif TestShuffle.calls == 3:
                values[:] = values[3:] + values[:3]

    monkeypatch.setattr(stage.secrets, "SystemRandom", TestShuffle)
    source = [fake_case(i) for i in range(1000)]
    root = tmp_path / "private" / "stage"
    root.parent.mkdir(mode=0o700)
    stage.stage(
        root, source, "c" * 64, Path(review.__file__),
        audit.A_MODEL, audit.A_REV, audit.B_MODEL, audit.B_REV)
    outputs = []
    for slot in ("A", "B"):
        review_dir = tmp_path / f"reviews-{slot}"
        review_dir.mkdir(mode=0o700)
        rows = review.read_input(root / f"input_{slot}" / "source.private.jsonl")
        for position, row in enumerate(rows[:5], 1):
            record = review.checkpoint_record(
                position, row, fake_response(row),
                audit.MODEL_PINS[slot][0], audit.MODEL_PINS[slot][1])
            if slot == "A":
                record["schema"] = audit.CHECKPOINT_SCHEMAS[slot]
                record["receipt_sha256"] = review.digest({
                    k: v for k, v in record.items() if k != "receipt_sha256"
                })
            review.write_checkpoint(review_dir / review.checkpoint_name(position), record)
        outputs.append(review_dir)
    return root, outputs[0], outputs[1]


def test_pairwise_audit_proves_real_source_binding_and_exact_receipts(staged):
    root, a_dir, b_dir = staged
    result = audit.audit(root, a_dir, b_dir)
    assert result["status"] == "OWNER_PAIRWISE_AUDIT_COMPLETE__SEMANTIC_HOLD"
    assert result["owner_manifest_receipt_verified"] is True
    assert result["input_hash_and_cross_slot_binding_verified"] is True
    assert result["checkpoint_receipt_and_input_sha256_verified"] == {"A": 5, "B": 5}
    assert result["unique_source_cases_in_pilot"] == 10 - result["matched_cases"]
    assert result["matched_decision_agreement"] == result["matched_cases"]
    assert result["quality_v1_admitted"] == 0
    assert result["private_values_emitted"] is False
    assert "case_key" not in json.dumps(result)
    assert "blind_id" not in json.dumps(result)


def test_pairwise_audit_rejects_tampered_checkpoint_and_crosswalk(staged):
    root, a_dir, b_dir = staged
    item = a_dir / "review_0001.private.json"
    record = json.loads(item.read_text())
    record["response"]["scores"]["chinese_prose"] = 1
    item.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(audit.AuditHold, match="CHECKPOINT_IDENTITY_OR_DIGEST_HOLD"):
        audit.audit(root, a_dir, b_dir)

    # Recompute a plausible checkpoint with a changed local source binding:
    # the cross-slot full-source equality guard must still catch the drift.
    item.write_bytes(review.canonical({
        **record,
        "response": fake_response(
            review.read_input(root / "input_A" / "source.private.jsonl")[0]),
    }) + b"\n")
    crosswalk = root / "owner" / "owner_crosswalk.private.json"
    binding = json.loads(crosswalk.read_text())
    binding["bindings"]["A"][0]["case_key"] = "tampered-owner-map"
    crosswalk.write_text(json.dumps(binding), encoding="utf-8")
    with pytest.raises(audit.AuditHold, match="OWNER_CROSS_SLOT_SOURCE_HOLD"):
        audit.audit(root, a_dir, b_dir)


def test_pairwise_audit_rejects_changed_frozen_input(staged):
    root, a_dir, b_dir = staged
    input_path = root / "input_B" / "source.private.jsonl"
    with input_path.open("ab") as dest:
        dest.write(b" ")
    with pytest.raises(audit.AuditHold, match="BLIND_INPUT_HASH_HOLD"):
        audit.audit(root, a_dir, b_dir)


def test_c_prepare_blinds_model_results_and_reconciles_without_admission(staged, tmp_path):
    root, a_dir, b_dir = staged
    out = tmp_path / "independent-c"
    safe = calibration.prepare(root, a_dir, b_dir, out)
    assert safe["status"] == "C_BLIND_PACKETS_READY__REVIEW_NOT_STARTED"
    assert safe["model_judgments_exposed_in_blind_packet"] is False
    packets = calibration.private_jsonl(out / "C_BLIND_PACKETS_PRIVATE.jsonl")
    assert len(packets) == 10
    assert len({p["calibration_id"] for p in packets}) == 10
    for packet in packets:
        assert set(packet) == {
            "schema", "calibration_id", "visible_history",
            "target_text", "target_semantics",
        }
        assert "scores" not in json.dumps(packet)
        assert "severe_flags" not in json.dumps(packet)
        assert "source_index" not in json.dumps(packet)
    assert (out / "C_OWNER_MAP_PRIVATE.json").stat().st_mode & 0o777 == 0o600
    results = []
    for packet in packets:
        results.append({
            "schema": calibration.RESULT_SCHEMA,
            "calibration_id": packet["calibration_id"],
            "assessments": {
                "player_agency": {
                    "verdict": "NOT_SUPPORTED", "target_quotes": [],
                    "history_quotes": [],
                    "rationale": "可见对话中NPC自主回应，缺少严重玩家越权依据。",
                },
                "hard_rule": {
                    "verdict": "INSUFFICIENT_CONTEXT", "target_quotes": [],
                    "history_quotes": [],
                    "rationale": "未给世界设定和明确硬禁令，不作猜测。",
                },
                "safety": {
                    "verdict": "NOT_SUPPORTED", "target_quotes": [],
                    "history_quotes": [],
                    "rationale": "可见内容没有直接支持安全排除的具体证据。",
                },
            },
        })
    result_path = tmp_path / "C_RESULTS_PRIVATE.jsonl"
    result_path.write_bytes(calibration.jsonl_bytes(results))
    report = calibration.reconcile(
        root, a_dir, b_dir, out, result_path, out / "C_CALIBRATION_SAFE.json"
    )
    assert report["status"] == "C_BLIND_SEMANTIC_RECONCILED__QUALITY_HOLD"
    assert report["cases_reviewed"] == 10
    assert report["c_verdict_counts"]["player_agency"] == {"NOT_SUPPORTED": 10}
    assert report["reviewer_c_execution_verified"] is False
    assert report["reviewer_c_independence_verified"] is False
    assert report["quality_v1_admitted"] == 0


def test_c_validator_requires_grounded_quotes_and_no_identity_leak():
    row = {
        "schema": calibration.PACKET_SCHEMA,
        "calibration_id": "a" * 32,
        "visible_history": [
            {"role": "user", "content": "我打算先去城门观察情况。"},
        ],
        "target_text": "NPC回应：城门暂时关闭，请小心巡逻兵。",
        "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
    }
    assessments = {
        field: {
            "verdict": "NOT_SUPPORTED",
            "target_quotes": [],
            "history_quotes": [],
            "rationale": "没有足够证据支持该类别的严重异常标签。",
        }
        for field in calibration.CATEGORIES
    }
    result = {
        "schema": calibration.RESULT_SCHEMA,
        "calibration_id": row["calibration_id"],
        "assessments": assessments,
    }
    assert len(calibration.validate_c_result(result, row)) == 3
    result["assessments"]["player_agency"]["verdict"] = "SUPPORTED"
    with pytest.raises(calibration.CalibrationHold, match="C_RESULT_UNSUPPORTED_EVIDENCE_HOLD"):
        calibration.validate_c_result(result, row)
    result["assessments"]["player_agency"]["target_quotes"] = ["捏造引用"]
    with pytest.raises(calibration.CalibrationHold, match="C_RESULT_NONEXACT_QUOTE_HOLD"):
        calibration.validate_c_result(result, row)
    result["assessments"]["player_agency"]["target_quotes"] = ["城门暂时关闭"]
    assert calibration.validate_c_result(result, row)["player_agency"] == "SUPPORTED"


def test_c_preparation_never_overwrites_existing_output(staged, tmp_path):
    root, a_dir, b_dir = staged
    out = tmp_path / "independent-c"
    calibration.prepare(root, a_dir, b_dir, out)
    with pytest.raises(calibration.CalibrationHold,
                       match="PRIVATE_OUTPUT_DIRECTORY_HOLD"):
        calibration.prepare(root, a_dir, b_dir, out)

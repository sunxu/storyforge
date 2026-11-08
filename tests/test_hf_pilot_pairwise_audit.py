"""Synthetic only: Owner-local A/B blind pilot pairing and receipt replay."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from storyforge_gold_quality import hf_blind_stage as stage
from storyforge_gold_quality import hf_literary_review as review
from storyforge_gold_quality import hf_pilot_pairwise_audit as audit


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
def staged(tmp_path: Path) -> tuple[Path, Path, Path]:
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

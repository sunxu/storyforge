"""CPU-only synthetic tests for strict formal input pairing."""
import json

import pytest

from storyforge_dataset.generation_eval.formal_pairing_gate import (
    FormalPairingError,
    assess_pairing,
)


def _write(path, cases):
    with path.open("w", encoding="utf-8") as handle:
        for sample_id, content in cases:
            handle.write(json.dumps({
                "sample_id": sample_id,
                "messages": [{"role": "user", "content": content}],
            }, ensure_ascii=False) + "\n")


def _inputs(tmp_path, count=6):
    cases = [(f"synthetic-{i}", f"synthetic message {i}") for i in range(count)]
    result = {}
    for role in ("A", "B", "challenger"):
        path = tmp_path / f"{role}.jsonl"
        _write(path, cases)
        result[role] = path
    return result


def test_exact_pairing_pass_cpu_only(tmp_path):
    paths = _inputs(tmp_path)
    result = assess_pairing(track="W-pilot", paths=paths)
    assert result["status"] == "FORMAL_PAIRING_STRUCTURE_PASS__OTHER_GATES_PENDING"
    assert result["record_count_per_role"] == 6
    assert result["messages_exactly_paired"] is True
    assert result["formal_gpu_authorized"] is False
    assert result["input_token_budget_verified"] is False
    assert result["reference_label_absence_verified"] is False
    assert result["hf_jobs_submitted"] == 0
    assert result["private_values_emitted"] is False
    assert len(result["input_sha256_by_role"]) == 3


def test_order_independent_but_messages_fixed(tmp_path):
    paths = _inputs(tmp_path)
    cases = [(f"synthetic-{i}", f"synthetic message {i}") for i in reversed(range(6))]
    _write(paths["B"], cases)
    assert assess_pairing(track="W-pilot", paths=paths)["messages_exactly_paired"]


def test_duplicate_case_rejected(tmp_path):
    paths = _inputs(tmp_path)
    _write(paths["B"], [("same", "synthetic text")] * 6)
    with pytest.raises(FormalPairingError, match="INPUT_DUPLICATE_SAMPLE_ID"):
        assess_pairing(track="W-pilot", paths=paths)


def test_same_ids_different_prompt_rejected(tmp_path):
    paths = _inputs(tmp_path)
    _write(paths["challenger"], [
        (f"synthetic-{i}", f"different synthetic message {i}") for i in range(6)
    ])
    with pytest.raises(FormalPairingError, match="PAIRED_MESSAGES_DIFFER"):
        assess_pairing(track="W-pilot", paths=paths)


def test_case_count_rejected(tmp_path):
    paths = _inputs(tmp_path, count=5)
    with pytest.raises(FormalPairingError, match="INPUT_RECORD_COUNT_MISMATCH"):
        assess_pairing(track="W-pilot", paths=paths)


def test_reference_answer_extra_field_rejected(tmp_path):
    paths = _inputs(tmp_path)
    bad = [{
        "sample_id": f"synthetic-{i}",
        "messages": [{"role": "user", "content": "synthetic"}],
        "reference_answer": "hidden",
    } for i in range(6)]
    paths["A"].write_text(
        "".join(json.dumps(item) + "\n" for item in bad), encoding="utf-8",
    )
    with pytest.raises(FormalPairingError, match="INPUT_RECORD_SCHEMA_INVALID"):
        assess_pairing(track="W-pilot", paths=paths)


def test_missing_final_user_rejected(tmp_path):
    paths = _inputs(tmp_path)
    with paths["A"].open("w", encoding="utf-8") as handle:
        for i in range(6):
            handle.write(json.dumps({
                "sample_id": f"synthetic-{i}",
                "messages": [{"role": "assistant", "content": "synthetic"}],
            }) + "\n")
    with pytest.raises(FormalPairingError, match="INPUT_MUST_END_WITH_USER"):
        assess_pairing(track="W-pilot", paths=paths)

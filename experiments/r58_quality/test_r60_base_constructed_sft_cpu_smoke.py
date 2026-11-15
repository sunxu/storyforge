"""Synthetic CPU smoke contract tests; CI never downloads or loads Qwen."""
import pytest
import r60_base_constructed_sft_cpu_smoke as subject


def test_synthetic_three_variant_contract():
    rows = subject.synthetic_rows()
    assert len(rows) == 3
    assert all(len(row["messages"]) == 5 for row in rows)
    assert [row["messages"][0]["role"] for row in rows] == ["system"] * 3
    assert "当前故事世界规则" not in rows[0]["messages"][0]["content"]
    assert "当前故事世界规则" in rows[1]["messages"][0]["content"]
    assert "当前故事角色设定" in rows[2]["messages"][0]["content"]


def test_token_only_result_stays_held():
    result = subject.check_report({
        "cases": 3, "tokenizer_verified": True,
        "collator_verified": False,
        "tokenizer_input_token_counts": [101, 102, 103],
    }, stage="token")
    assert result["train_admitted"] == 0
    assert result["actual_collator_verified"] is False
    assert result["status"].endswith("COLLATOR_HOLD")


def test_mocked_actual_collator_result_is_not_real_candidate_proof():
    result = subject.check_report({
        "cases": 3, "tokenizer_verified": True,
        "collator_verified": True,
        "tokenizer_input_token_counts": [101, 102, 103],
        "real_collator_token_counts": [95, 96, 97],
        "supervised_token_counts": [35, 35, 35],
    }, stage="both")
    assert result["actual_collator_verified"] is True
    assert result["real_candidate_contract_verified"] is False
    assert result["r50_complete_exclusion_verified"] is False
    assert result["train_admitted"] == 0


def test_collator_without_labels_fails_closed():
    with pytest.raises(subject.Hold, match="COLLATOR_LABELS_HOLD"):
        subject.check_report({
            "cases": 3, "tokenizer_verified": True,
            "collator_verified": True,
            "tokenizer_input_token_counts": [101, 102, 103],
            "real_collator_token_counts": [95, 96, 97],
            "supervised_token_counts": [],
        }, stage="both")


def test_negative_or_noninteger_tokens_fail_closed():
    with pytest.raises(subject.Hold, match="TOKEN_COUNT_HOLD"):
        subject.check_report({
            "cases": 3, "tokenizer_verified": True,
            "collator_verified": False,
            "tokenizer_input_token_counts": [101, -1, 103],
        }, stage="token")


def test_zero_weight_or_inference_calls_are_mandatory():
    result = subject.check_report({
        "cases": 3, "tokenizer_verified": True,
        "collator_verified": False,
        "tokenizer_input_token_counts": [100, 100, 100],
    }, stage="token")
    assert result["model_requests"] == 0
    assert result["model_weights_loaded"] is False
    assert result["gpu_started"] is False

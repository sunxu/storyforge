"""Synthetic contract tests for the complete P3 CPU preflight."""
from scripts import r60_p3_cpu_model_preflight_v2 as p3


def test_shared_budget_boundary_and_invalid_values():
    assert p3.budget_fits(28_672, 4_096, 32_768)
    assert not p3.budget_fits(28_673, 4_096, 32_768)
    assert not p3.budget_fits(True, 4_096, 32_768)
    assert not p3.budget_fits(28_672, -1, 32_768)


def test_exact_three_model_pins_and_90_case_contract():
    assert p3.MODEL_PINS == {
        "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
        "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
        "challenger": (
            "zai-org/GLM-Z1-32B-0414",
            "8eb2858992c1f749e2a6d4075455decc2484722d",
        ),
    }
    assert p3.SYNTHETIC_CASES == 90
    assert p3.DEFAULT_INPUT_BUDGET + p3.DEFAULT_OUTPUT_BUDGET == p3.CONTEXT_CEILING == 32_768


def test_synthetic_messages_have_multiturn_chinese_and_think_markers():
    messages = p3.synthetic_messages(7, "synthetic rubric")
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert "合成测试第 7 轮" in messages[1]["content"]
    assert "PRIVATE_SYNTHETIC_REASONING_7" in messages[2]["content"]
    assert "VISIBLE_SYNTHETIC_HISTORY_7" in messages[2]["content"]


def test_percentile_95_is_nearest_rank():
    assert p3.percentile95(list(range(1, 91))) == 86


def test_response_schema_contract_is_checked_without_model_calls():
    from storyforge_gold_quality.hf_severity_evidence_v2 import response_schema_v2

    schema = response_schema_v2()
    assert schema["required"] == ["schema", "rubric_version", "case_ref", "assessments"]
    assert set(schema["properties"]["assessments"]["required"]) == {
        "player_agency", "hard_rule", "safety"
    }

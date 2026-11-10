"""Synthetic tests for R60 P3 v3 HF tokenizer adapter contracts."""
from scripts import r60_p3_cpu_model_preflight_v3 as p3
from storyforge_dataset.token_preflight import describe_token_lengths


def test_fixed_model_pins_and_context_budget():
    assert p3.MODEL_PINS == {
        "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
        "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
        "challenger": (
            "zai-org/GLM-Z1-32B-0414",
            "8eb2858992c1f749e2a6d4075455decc2484722d",
        ),
    }
    assert p3.DEFAULT_INPUT_BUDGET + p3.DEFAULT_OUTPUT_BUDGET == p3.CONTEXT_CEILING
    assert p3.SYNTHETIC_CASES == 90


def test_synthetic_messages_follow_hf_role_content_contract():
    messages = p3.synthetic_messages(3, "synthetic rubric")
    assert [set(message) for message in messages] == [
        {"role", "content"}, {"role", "content"},
        {"role", "content"}, {"role", "content"},
    ]
    assert [message["role"] for message in messages] == [
        "system", "user", "assistant", "user"
    ]
    assert "PRIVATE_SYNTHETIC_REASONING_3" in messages[2]["content"]
    assert "VISIBLE_SYNTHETIC_HISTORY_3" in messages[2]["content"]


def test_shared_token_preflight_budget_core_is_the_only_summary_algorithm():
    summary = describe_token_lengths(
        [100, 200, 300], max_model_len=32768, reserved_output_tokens=4096
    )
    assert summary["cases_checked"] == 3
    assert summary["over_budget_count"] == 0
    assert summary["max_total_tokens"] == 4396


def test_weight_suffix_guard_is_explicit():
    assert {".safetensors", ".bin", ".pt", ".pth", ".gguf", ".onnx", ".h5"} <= p3.WEIGHT_SUFFIXES


def test_embedded_template_is_read_from_tokenizer_config_not_loaded_active_template(tmp_path):
    folder = tmp_path
    (folder / "tokenizer_config.json").write_text(
        '{"chat_template":"EMBEDDED_TEMPLATE"}', encoding="utf-8"
    )
    assert p3._embedded_template(folder) == "EMBEDDED_TEMPLATE"

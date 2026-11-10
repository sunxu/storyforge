"""CPU-only tests for synthetic 32K input calibration (no network, no models)."""
import json

import pytest

from storyforge_dataset.generation_eval.synthetic_32k import (
    _verify_owner_authorization,
    calibrate_synthetic_input,
)


class FakeTokenizer:
    def __init__(self):
        self.calls = 0

    def apply_chat_template(self, messages, **kwargs):
        self.calls += 1
        assert kwargs["tokenize"] is True
        assert kwargs["add_generation_prompt"] is True
        if kwargs.get("enable_thinking") is True:
            assert kwargs["enable_thinking"] is True
        return [17] * (7 + len(messages[0]["content"]) // 5)

    def encode(self, content, **kwargs):
        assert kwargs["add_special_tokens"] is False
        assert content == "<think>"
        return [99]


def test_calibration_bounded_and_deterministic():
    tokenizer = FakeTokenizer()
    role = {"enable_thinking": True}
    a, tokens_a = calibrate_synthetic_input(
        tokenizer=tokenizer, role_config=role, target_tokens=2800,
        ceiling_tokens=3000, tolerance_tokens=100,
    )
    b, tokens_b = calibrate_synthetic_input(
        tokenizer=tokenizer, role_config=role, target_tokens=2800,
        ceiling_tokens=3000, tolerance_tokens=100,
    )
    assert a == b
    assert tokens_a == tokens_b
    assert 2700 <= tokens_a <= 2800
    assert a[-1]["role"] == "user"
    assert "合成负载" in a[-1]["content"]


def test_challenger_generation_prefix_is_counted():
    tokenizer = FakeTokenizer()
    messages, n = calibrate_synthetic_input(
        tokenizer=tokenizer,
        role_config={"enable_thinking": None, "generation_prefix": "<think>"},
        target_tokens=2600, ceiling_tokens=2700, tolerance_tokens=100,
    )
    assert len(messages) == 1
    assert 2500 <= n <= 2600


@pytest.mark.parametrize("target,ceiling,tolerance", [
    (0, 28672, 96), (28673, 28672, 96), (28600, 0, 96),
    (28600, 28672, -1), (28600, 28672, 1025),
])
def test_bad_target_holds(target, ceiling, tolerance):
    with pytest.raises(ValueError):
        calibrate_synthetic_input(
            tokenizer=FakeTokenizer(), role_config={"enable_thinking": True},
            target_tokens=target, ceiling_tokens=ceiling,
            tolerance_tokens=tolerance,
        )


def test_owner_authorization_cannot_be_omitted():
    authorization = {
        "schema": "storyforge_r60_p4_staged_execution_authorization_v1",
        "frozen_profile_sha256": "a" * 64,
        "stages": {"synthetic_32k": {"owner_authorized": True}},
        "denied": {"training_authorized": False},
    }
    _verify_owner_authorization(authorization, "a" * 64)
    for mutation in (
        {"stages": {"synthetic_32k": {"owner_authorized": False}}},
        {"denied": {"training_authorized": True}},
        {"frozen_profile_sha256": "b" * 64},
    ):
        modified = json.loads(json.dumps(authorization))
        modified.update(mutation)
        with pytest.raises(ValueError, match="SYNTHETIC_STAGE_NOT_OWNER_AUTHORIZED"):
            _verify_owner_authorization(modified, "a" * 64)

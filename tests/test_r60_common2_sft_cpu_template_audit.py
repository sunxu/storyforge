"""Synthetic, no HF downloads or real private text."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/r58_quality"))
import r60_common2_sft_cpu_template_audit as runner


def fixture():
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"合成历史{i}"}
        for i in range(11)
    ]
    rows = [{
        "schema": "storyforge_r60_source_bound_experimental_sft_v1",
        "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
        "supervision_scope": "FINAL_ASSISTANT_ONLY",
        "messages": history + [{"role": "assistant", "content": "目标文本"}],
        "system_prompt": None,
        "world_card": None,
        "train_admitted": False,
    } for _ in range(2)]
    raw = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows).encode()
    manifest = {
        "schema": "storyforge_r60_common2_sft_experimental_manifest_private_v1",
        "status": "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED",
        "examples": 2, "window": 11, "train_admitted": 0,
        "r50_complete_exclusion_verified": False,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
    }
    return rows, raw, manifest


class DummyTokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize and add_generation_prompt is False
        return list(range(80))


def test_private_contract_valid_and_tokenizer_only():
    rows, raw, manifest = fixture()
    runner.validate_payload(rows, manifest, raw)
    output = runner.inspect_rows(rows, DummyTokenizer())
    assert output["cases"] == 2
    assert output["tokenizer_input_token_counts"] == [80, 80]
    assert output["collator_verified"] is False
    assert output["train_admitted"] == 0


def test_tamper_detected():
    rows, raw, manifest = fixture()
    manifest["data_sha256"] = "0" * 64
    with pytest.raises(runner.Hold, match="PRIVATE_EXPERIMENT_CONTRACT_HOLD"):
        runner.validate_payload(rows, manifest, raw)


def test_wrong_order_rejected():
    rows, raw, manifest = fixture()
    rows[0]["messages"][3]["role"] = "user"
    with pytest.raises(runner.Hold, match="EXPERIMENT_MESSAGE_SEQUENCE_HOLD"):
        runner.validate_payload(rows, manifest, raw)


def test_token_overflow_holds():
    rows, _, _ = fixture()
    class Overflow:
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            return list(range(runner.CEILING + 1))
    with pytest.raises(runner.Hold, match="TOKEN_BUDGET_HOLD"):
        runner.inspect_rows(rows, Overflow())

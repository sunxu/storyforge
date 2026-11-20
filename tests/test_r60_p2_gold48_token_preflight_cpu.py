"""Synthetic-only tests for Gold48 shared-core CPU Tokenizer preflight."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_r60_p2_gold48_candidate_preflight_cpu import private_file
from test_r60_p2_gold48_reconstructed_input_draft_cpu import prepare
from r60_p2_gold48_reconstructed_input_draft_cpu import draft

spec = importlib.util.spec_from_file_location(
    "r60_p2_gold48_token_preflight_cpu",
    ROOT / "scripts/r60_p2_gold48_token_preflight_cpu.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeTokenizer:
    chat_template = "synthetic-chat-template-for-test-only"

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs["tokenize"] is True
        assert kwargs["add_generation_prompt"] is True
        size = 35 + sum(len(item["content"]) // 7 for item in messages)
        if kwargs.get("enable_thinking") is False:
            size += 3
        return list(range(size))


def setup_draft(tmp_path):
    candidate, binding, evidence, manifest = prepare(tmp_path)
    doc, _ = draft(candidate, binding, evidence, manifest)
    folder = tmp_path / "draft"
    folder.mkdir(mode=0o700)
    path = folder / "GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
    private_file(path, doc)
    return path


def test_48_cpu_lengths_and_sha_checked_no_inference(tmp_path):
    path = setup_draft(tmp_path)
    private, safe = module.assess(path, FakeTokenizer(), "5.16.1")
    assert safe["status"] == "GOLD48_48_INPUT_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE"
    assert safe["case_count"] == 48
    assert safe["source_count"] == 8
    assert safe["memory_pretarget_verified_count"] == 1
    assert safe["memory_unverified_omitted_count"] == 47
    assert safe["chat_template_modes_checked"] == 2
    assert safe["owner_gold48_freeze"] is False
    assert safe["history_original_reference_read"] is False
    assert safe["gpu_started"] is False
    assert len(private["mode_token_counts_PRIVATE"]["default"]) == 48
    assert len(private["mode_token_counts_PRIVATE"]["disabled"]) == 48
    assert private["mode_token_counts_PRIVATE"]["default"][0] > 32
    assert "synthetic verified memory" not in json.dumps(safe)


def test_mutated_reconstructed_prompt_sha_holds(tmp_path):
    path = setup_draft(tmp_path)
    doc = json.loads(path.read_text())
    doc["cases_PRIVATE"][0]["reconstructed_messages_PRIVATE"][0]["content"] += "changed"
    private_file(path, doc)
    with pytest.raises(module.Hold, match="DRAFT_MESSAGES_SHA_OR_HISTORY_MISMATCH_HOLD"):
        module.assess(path, FakeTokenizer(), "5.16.1")


def test_original_reply_answer_key_cannot_be_added_to_messages(tmp_path):
    path = setup_draft(tmp_path)
    doc = json.loads(path.read_text())
    doc["cases_PRIVATE"][0]["reconstructed_messages_PRIVATE"].append({
        "role": "assistant", "content": "synthetic original reference",
    })
    private_file(path, doc)
    with pytest.raises(module.Hold, match="DRAFT_MESSAGES_STRUCTURE_HOLD"):
        module.assess(path, FakeTokenizer(), "5.16.1")


def test_private_file_mode_holds(tmp_path):
    path = setup_draft(tmp_path)
    path.chmod(0o644)
    with pytest.raises(module.Hold, match="DRAFT_PRIVATE_FILE_MODE_OR_SIZE_HOLD"):
        module.assess(path, FakeTokenizer(), "5.16.1")


def test_unauthorized_freeze_status_holds(tmp_path):
    path = setup_draft(tmp_path)
    doc = json.loads(path.read_text())
    doc["prompt_owner_freeze"] = True
    private_file(path, doc)
    with pytest.raises(module.Hold, match="DRAFT_INPUT_CONTRACT_HOLD"):
        module.assess(path, FakeTokenizer(), "5.16.1")

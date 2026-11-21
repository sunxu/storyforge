"""Synthetic-only Gold48 HF Providers judge contract tests; no network."""
from __future__ import annotations

import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from storyforge_gold_quality.gold48_blind import PACK_SCHEMA
from storyforge_gold_quality.gold48_hf_judge import (
    JudgeHold,
    judge_one,
    make_hf_client,
    prompt_messages,
    response_schema,
    validate_score,
)
from storyforge_gold_quality.hf_literary_review import FLOORS, SEVERE


def item() -> dict:
    return {
        "schema": PACK_SCHEMA,
        "blind_id": "0123456789abcdef0123456789abcdef",
        "visible_messages": [
            {"role": "system", "content": "世界规则：必须留给玩家选择。"},
            {"role": "user", "content": "由你描述NPC接下来的动作。"},
        ],
        "target_text": "NPC走到门边，向玩家发问，等待回答。",
    }


def score() -> dict:
    return {
        "scores": {dim: 3 for dim in FLOORS},
        "severe_flags": {name: False for name in SEVERE},
        "specific_source_quotes": ["必须留给玩家选择"],
        "specific_target_quotes": ["等待回答"],
        "literary_quality_notes": "描述简洁，有下一轮互动空间，玩家选择权保留。",
        "uncertainty": "",
    }


class FakeClient:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(self.reply, ensure_ascii=False),
            )),
        ])


class HFJudgeSyntheticTest(unittest.TestCase):
    def test_six_dims_and_no_source_metadata_in_prompt(self) -> None:
        s = response_schema()
        self.assertEqual(set(s["properties"]["scores"]["properties"]), set(FLOORS))
        self.assertEqual(set(s["properties"]["severe_flags"]["properties"]), set(SEVERE))
        self.assertEqual(set(s["properties"]), set(score()))
        messages = prompt_messages(item())
        material = json.loads(messages[1]["content"])
        self.assertNotIn("source_role_PRIVATE", material)
        self.assertNotIn("original", set(material))
        self.assertIn("visible_history", material)

    def test_one_mock_call_no_batch_no_source_leak(self) -> None:
        fake = FakeClient(score())
        result = judge_one(
            item=item(), client=fake, model="synthetic-judge",
            temperature=0, max_tokens=512, private_transfer_authorized=True,
        )
        self.assertEqual(result["scores"]["player_agency"], 3)
        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["model"], "synthetic-judge")
        self.assertEqual(call["response_format"]["type"], "json_schema")
        self.assertEqual(call["response_format"]["json_schema"]["strict"], True)
        self.assertNotIn("G48-C", str(call))
        self.assertNotIn("source_role_PRIVATE", str(call))

    def test_empty_reply_score_is_fixed_and_has_no_api_call(self) -> None:
        blank = item()
        blank["target_text"] = ""
        fake = FakeClient(score())
        result = judge_one(
            item=blank, client=fake, model="synthetic-judge",
            temperature=0, max_tokens=512, private_transfer_authorized=True,
        )
        self.assertEqual(fake.calls, [])
        self.assertEqual(set(result["scores"].values()), {1})
        self.assertEqual(set(result["severe_flags"].values()), {False})
        self.assertEqual(result["specific_target_quotes"], [])
        self.assertIn("非 AI", result["uncertainty"])
        validate_score(result, blank)

        fabricated = dict(result, specific_target_quotes=["不存在的候选引文"])
        with self.assertRaisesRegex(JudgeHold, "JUDGE_NONEXACT_QUOTE_HOLD"):
            validate_score(fabricated, blank)
        changed = dict(result, scores={**result["scores"], "player_agency": 5})
        with self.assertRaisesRegex(JudgeHold, "JUDGE_NO_RESPONSE_POLICY_HOLD"):
            validate_score(changed, blank)

    def test_empty_reply_still_requires_explicit_authorization(self) -> None:
        blank = item()
        blank["target_text"] = ""
        fake = FakeClient(score())
        with self.assertRaisesRegex(JudgeHold, "PRIVATE_TRANSFER_NOT_AUTHORIZED"):
            judge_one(item=blank, client=fake, model="synthetic-judge",
                      temperature=0, max_tokens=512)
        self.assertEqual(fake.calls, [])

    def test_no_authorization_means_zero_calls(self) -> None:
        fake = FakeClient(score())
        with self.assertRaisesRegex(JudgeHold, "PRIVATE_TRANSFER_NOT_AUTHORIZED"):
            judge_one(item=item(), client=fake, model="synthetic-judge",
                      temperature=0, max_tokens=512)
        self.assertEqual(fake.calls, [])

    def test_nonexact_quote_fails_closed(self) -> None:
        bad = score()
        bad["specific_target_quotes"] = ["不存在的引用"]
        with self.assertRaisesRegex(JudgeHold, "JUDGE_NONEXACT_QUOTE_HOLD"):
            validate_score(bad, item())

    def test_boolean_score_fails_closed(self) -> None:
        bad = score()
        bad["scores"]["player_agency"] = True
        with self.assertRaisesRegex(JudgeHold, "JUDGE_SCORES_HOLD"):
            validate_score(bad, item())

    def test_api_exception_does_not_echo_private_text(self) -> None:
        class FailedClient:
            def chat_completion(self, **_kwargs):
                raise RuntimeError("secret token and private story leaked in error")
        with self.assertRaisesRegex(JudgeHold, "^JUDGE_API_OR_FORMAT_HOLD$"):
            judge_one(item=item(), client=FailedClient(), model="synthetic-judge",
                      temperature=0, max_tokens=512, private_transfer_authorized=True)

    def test_org_billing_client_constructor(self) -> None:
        seen = []
        fake_module = SimpleNamespace(
            InferenceClient=lambda **kwargs: seen.append(kwargs) or object()
        )
        with patch.dict(sys.modules, {"huggingface_hub": fake_module}):
            client = make_hf_client(hf_token="synthetic-credential", fixed_provider="test-provider")
        self.assertIsNotNone(client)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["provider"], "test-provider")
        self.assertEqual(seen[0]["bill_to"], "adradar")


if __name__ == "__main__":
    unittest.main()

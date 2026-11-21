"""Offline synthetic tests of one-at-a-time HF judge execution safety."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from storyforge_gold_quality.gold48_blind import PACK_SCHEMA
from storyforge_gold_quality.gold48_hf_judge import DIMENSIONS
from storyforge_gold_quality.gold48_judge_lock import CONFIG_SCHEMA, prepare
from storyforge_gold_quality.gold48_judge_step import (
    LockHold,
    single_call_guard,
    step,
)
from storyforge_gold_quality.hf_literary_review import SEVERE, canonical


class FakeClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = []
        self.fail = fail

    def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("PRIVATE PROMPT MUST NOT ECHO")
        score = {
            "scores": {dimension: 3 for dimension in DIMENSIONS},
            "severe_flags": {name: False for name in SEVERE},
            "specific_source_quotes": ["synthetic history"],
            "specific_target_quotes": ["synthetic reply"],
            "literary_quality_notes": "合成评审测试，回复继续推进情节，存在一些不足。",
            "uncertainty": "仅合成数据。",
        }
        return SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(score, ensure_ascii=False))),
        ])


class JudgeStepSyntheticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "owner"
        self.root.mkdir(mode=0o700)
        self.reviewer_folder = self.root / "reviewers"
        self.owner_folder = self.root / "owner"
        self.reviews = self.root / "reviews"
        for path in (self.reviewer_folder, self.owner_folder, self.reviews,
                     self.reviews / "J1", self.reviews / "J2"):
            path.mkdir(mode=0o700)
        self.packet = self.reviewer_folder / "GOLD48_BLIND_240_PRIVATE.jsonl"
        self.config = self.owner_folder / "config.private.json"
        self.lock = self.owner_folder / "GOLD48_JUDGE_LOCK_PRIVATE.json"
        self.rows = [{
            "schema": PACK_SCHEMA, "blind_id": f"{n:032x}",
            "visible_messages": [{
                "role": "user", "content": f"synthetic history for case {n // 5}"
            }],
            "target_text": "" if n == 0 else f"synthetic reply {n}",
        } for n in range(240)]
        self.save(self.packet, b"".join(canonical(x) + b"\n" for x in self.rows))
        config = {
            "schema": CONFIG_SCHEMA,
            "reviewers": [
                {"reviewer_id": "J1",
                 "model": "deepseek-ai/DeepSeek-V4.1-Flash",
                 "provider": "fireworks-ai",
                 "temperature": 0, "max_tokens": 2048},
                {"reviewer_id": "J2",
                 "model": "zai-org/GLM-5.2",
                 "provider": "deepinfra",
                 "temperature": 0, "max_tokens": 2048},
            ], "max_cost_usd": 25.0,
        }
        self.save(self.config, canonical(config) + b"\n")
        prepare(packet=self.packet, config=self.config, output=self.lock)
        self.client = FakeClient()
        self.factory_calls = 0

    @staticmethod
    def save(path: Path, payload: bytes) -> None:
        path.write_bytes(payload)
        os.chmod(path, 0o600)

    def factory(self, **kwargs):
        self.factory_calls += 1
        self.assertEqual(kwargs["fixed_provider"], "fireworks-ai")
        self.assertEqual(kwargs["hf_token"], "synthetic-token")
        return self.client

    def run_one(self, *, position: int = 2, reviewer: str = "J1",
                private: bool = True, billing: bool = True,
                spending_cap: bool = True, factory=None):
        return step(
            packet=self.packet, lock_path=self.lock,
            output_dir=self.reviews / reviewer, reviewer_id=reviewer,
            position=position,
            approve_private_transfer=private, approve_paid_calls=billing,
            confirm_hf_spending_cap=spending_cap, hf_token="synthetic-token",
            client_factory=factory or self.factory,
        )

    def test_one_paid_attempt_then_create_only_checkpoint(self) -> None:
        safe = self.run_one()
        self.assertEqual(safe["status"], "GOLD48_JUDGE_ONE_SCORED__NO_UNBLIND")
        self.assertEqual(safe["paid_api_attempts"], 1)
        self.assertIsNone(safe["cost_usd"])
        self.assertEqual(self.factory_calls, 1)
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(
            self.client.calls[0]["extra_body"], {"thinking": {"type": "disabled"}}
        )
        receipt = json.loads((self.reviews / "J1" /
                              "002.score.private.json").read_text())
        self.assertEqual(receipt["score_origin"], "ai_judge")
        self.assertEqual(receipt["model"], "deepseek-ai/DeepSeek-V4.1-Flash")
        self.assertEqual(receipt["response"]["scores"]["player_agency"], 3)
        self.assertEqual((self.reviews / "J1" /
                          "002.score.private.json").stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(LockHold, "JUDGE_ITEM_ALREADY_ATTEMPTED_HOLD"):
            self.run_one()
        self.assertEqual(len(self.client.calls), 1)
        self.assertFalse((self.reviews / "J1" /
                          "002.diagnostic.private.json").exists())

    def test_blank_is_fixed_and_does_not_construct_client(self) -> None:
        safe = self.run_one(position=1)
        self.assertEqual(safe["paid_api_attempts"], 0)
        self.assertEqual(self.factory_calls, 0)
        self.assertEqual(self.client.calls, [])
        receipt = json.loads((self.reviews / "J1" /
                              "001.score.private.json").read_text())
        self.assertEqual(receipt["score_origin"], "fixed_no_response_rule")
        self.assertEqual(set(receipt["response"]["scores"].values()), {1})
        self.assertFalse((self.reviews / "J1" /
                          "001.execution.private.json").exists())
        self.assertEqual(receipt["response"]["specific_target_quotes"], [])
        self.assertEqual(receipt["response"]["specific_source_quotes"], [])

    def test_no_spending_cap_confirmation_does_not_block_owner_approved_calls(self) -> None:
        result = self.run_one(spending_cap=False)
        self.assertEqual(result["paid_api_attempts"], 1)
        marker = json.loads((self.reviews / "J1" /
                             "002.attempt.private.json").read_text())
        self.assertFalse(marker["hf_spend_cap_owner_confirmed"])

    def test_exact_quote_field_reclassification_without_score_change(self) -> None:
        class MisfiledClient:
            def chat_completion(self, **kwargs):
                score = {
                    "scores": {dimension: 4 for dimension in DIMENSIONS},
                    "severe_flags": {name: False for name in SEVERE},
                    "specific_source_quotes": ["synthetic reply 1"],
                    "specific_target_quotes": [],
                    "literary_quality_notes": "这是合成的离线引用归位单元测试案例。",
                    "uncertainty": "模型判断存在一定不确定性。",
                }
                return SimpleNamespace(choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content=json.dumps(score, ensure_ascii=False),
                        ),
                    ),
                ])

        self.run_one(factory=lambda **kwargs: MisfiledClient())
        receipt = json.loads((self.reviews / "J1" /
                              "002.score.private.json").read_text())
        self.assertEqual(receipt["response"]["specific_source_quotes"], [])
        self.assertEqual(receipt["response"]["specific_target_quotes"],
                         ["synthetic reply 1"])
        self.assertEqual(set(receipt["response"]["scores"].values()), {4})
        audit = json.loads((self.reviews / "J1" /
                            "002.execution.private.json").read_text())
        self.assertEqual(audit["quote_relocations"]["source_to_target"], 1)
        self.assertEqual(audit["quote_relocations"]["target_to_source"], 0)
        self.assertFalse(audit["model_scores_or_flags_changed"])
        self.assertFalse(audit["model_quote_text_changed"])
        self.assertIsNotNone(audit["original_model_content_sha256"])

    def test_raw_hf_debug_blocked_before_attempt_marker(self) -> None:
        with patch.dict(os.environ, {"HF_DEBUG": "1"}), self.assertRaisesRegex(
            LockHold, "HF_DEBUG_PRIVATE_PAYLOAD_HOLD"
        ):
            self.run_one()
        self.assertFalse((self.reviews / "J1" /
                          "002.attempt.private.json").exists())
        self.assertEqual(self.client.calls, [])

    def test_approval_flags_refuse_even_zero_cost(self) -> None:
        for name in ("private", "billing"):
            kwargs = {name: False}
            with self.subTest(name=name), self.assertRaises(LockHold):
                self.run_one(**kwargs)
        self.assertEqual(self.factory_calls, 0)
        self.assertFalse((self.reviews / "J1" / "002.attempt.private.json").exists())

    def test_external_failure_keeps_consumption_marker(self) -> None:
        self.client.fail = True
        with self.assertRaisesRegex(Exception, "JUDGE_API_OR_FORMAT_HOLD"):
            self.run_one()
        self.assertTrue((self.reviews / "J1" /
                         "002.attempt.private.json").exists())
        self.assertFalse((self.reviews / "J1" /
                          "002.score.private.json").exists())
        with self.assertRaisesRegex(LockHold, "JUDGE_ITEM_ALREADY_ATTEMPTED_HOLD"):
            self.run_one()
        self.assertEqual(len(self.client.calls), 1)
        diag_path = self.reviews / "J1" / "002.diagnostic.private.json"
        self.assertEqual(diag_path.stat().st_mode & 0o777, 0o600)
        raw = diag_path.read_text()
        self.assertNotIn("PRIVATE PROMPT", raw)
        diag = json.loads(raw)
        self.assertEqual(diag["sdk"]["phase"], "api_exception")
        self.assertEqual(diag["sdk"]["exception_class"], "RuntimeError")
        self.assertIsNone(diag["sdk"]["http_status"])
        self.assertEqual(diag["reason"], "JUDGE_API_OR_FORMAT_HOLD")

    def test_http_status_diagnostic_never_echoes_private_exception(self) -> None:
        class PrivateHttpError(RuntimeError):
            status_code = 422

        class FailClient:
            def chat_completion(self, **kwargs):
                raise PrivateHttpError("private prompt and API key in message")

        with self.assertRaisesRegex(Exception, "JUDGE_API_OR_FORMAT_HOLD"):
            self.run_one(factory=lambda **kwargs: FailClient())
        diag_path = self.reviews / "J1" / "002.diagnostic.private.json"
        raw = diag_path.read_text()
        self.assertNotIn("private prompt", raw)
        self.assertNotIn("API key", raw)
        diag = json.loads(raw)
        self.assertEqual(diag["sdk"]["phase"], "api_exception")
        self.assertEqual(diag["sdk"]["http_status"], 422)
        self.assertEqual(diag["sdk"]["exception_class"], "PrivateHttpError")
        self.assertFalse(diag["private_values_emitted"])

    def test_malformed_json_records_only_structure(self) -> None:
        class BadJsonClient:
            def chat_completion(self, **kwargs):
                return SimpleNamespace(choices=[
                    SimpleNamespace(finish_reason="length",
                                    message=SimpleNamespace(
                                        content="secret model output <invalid"))
                ])

        with self.assertRaisesRegex(Exception, "JUDGE_API_OR_FORMAT_HOLD"):
            self.run_one(factory=lambda **kwargs: BadJsonClient())
        raw = (self.reviews / "J1" /
               "002.diagnostic.private.json").read_text()
        self.assertNotIn("secret model output", raw)
        diag = json.loads(raw)
        self.assertEqual(diag["sdk"]["phase"], "api_response_received")
        self.assertEqual(diag["sdk"]["finish_reason"], "length")
        self.assertEqual(diag["sdk"]["content_chars"],
                         len("secret model output <invalid"))
        self.assertFalse(diag["sdk"]["json_valid"])
        self.assertTrue(diag["sdk"]["failed_response_saved_private"])
        saved_path = self.reviews / "J1" / "002.failed_response.private.json"
        self.assertEqual(saved_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(saved_path.read_text())["model_output_text"],
                         "secret model output <invalid")

    def test_nonexact_quote_holds_and_retains_private_model_output(self) -> None:
        class NonexactQuoteClient:
            def chat_completion(self, **kwargs):
                value = {
                    "scores": {dimension: 3 for dimension in DIMENSIONS},
                    "severe_flags": {name: False for name in SEVERE},
                    "specific_source_quotes": ["invented synthetic quotation"],
                    "specific_target_quotes": ["synthetic reply 1"],
                    "literary_quality_notes": "合成数据的引用不能逐字匹配历史内容。",
                    "uncertainty": "不确定性只用于合成测试。",
                }
                return SimpleNamespace(choices=[
                    SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
                        content=json.dumps(value, ensure_ascii=False),
                    )),
                ])

        with self.assertRaisesRegex(Exception, "JUDGE_NONEXACT_QUOTE_HOLD"):
            self.run_one(factory=lambda **kwargs: NonexactQuoteClient())
        saved_path = self.reviews / "J1" / "002.failed_response.private.json"
        self.assertEqual(saved_path.stat().st_mode & 0o777, 0o600)
        saved = json.loads(saved_path.read_text())
        self.assertEqual(saved["schema"],
                         "storyforge_gold48_failed_response_private_v1")
        self.assertIn("invented synthetic quotation", saved["model_output_text"])
        diag_raw = (self.reviews / "J1" /
                    "002.diagnostic.private.json").read_text()
        self.assertNotIn("invented synthetic quotation", diag_raw)
        diag = json.loads(diag_raw)
        self.assertTrue(diag["sdk"]["failed_response_saved_private"])
        self.assertFalse((self.reviews / "J1" /
                          "002.score.private.json").exists())
        with self.assertRaisesRegex(LockHold, "JUDGE_ITEM_ALREADY_ATTEMPTED_HOLD"):
            self.run_one()

    def test_packet_changed_after_lock_fails_closed(self) -> None:
        self.rows[1]["target_text"] = "changed synthetic reply"
        self.save(self.packet, b"".join(canonical(x) + b"\n" for x in self.rows))
        with self.assertRaisesRegex(LockHold, "JUDGE_LOCK_IDENTITY_HOLD"):
            self.run_one()
        self.assertEqual(self.factory_calls, 0)

    def test_j1_official_revision_uses_actual_model_provider_and_audit(self) -> None:
        from storyforge_gold_quality.gold48_j1_official import REVISION_SCHEMA
        from storyforge_gold_quality.gold48_judge_lock import digest

        lock_raw = self.lock.read_bytes()
        lock = json.loads(lock_raw)
        revision_path = (self.owner_folder /
                         "GOLD48_J1_OFFICIAL_REVISION_PRIVATE.json")
        self.save(revision_path, canonical({
            "schema": REVISION_SCHEMA,
            "status": "J1_OFFICIAL_REVISION_PREPARED__NO_EXTERNAL_CALLS",
            "reviewer_id": "J1",
            "lock_sha256": digest(lock_raw),
            "frozen_judge_sha256": lock["judge_source_sha256"],
            "frozen_model": "deepseek-ai/DeepSeek-V4.1-Flash",
            "frozen_provider": "fireworks-ai",
            "actual_model": "deepseek-flash",
            "model_version": "DeepSeek-V4.1-Flash-1017",
            "actual_provider": "deepseek-official",
            "api_origin": "https://api.deepseek.com",
            "response_format": "json_object",
            "thinking": "disabled",
            "concurrency_policy": {
                "scope": "j1_official_and_j2_separate_single_call_lanes",
                "max_total_in_flight": 2,
                "max_per_reviewer": 1,
                "j1_lock": ".gold48_j1_official_call.lock",
                "j2_lock": ".gold48_single_call.lock",
                "frozen_global_limit_overridden_for_j1_only": True,
            },
        }) + b"\n")
        direct = FakeClient()
        def official_factory(*, hf_token, fixed_provider):
            self.assertEqual(fixed_provider, "deepseek-official")
            self.assertEqual(hf_token, "synthetic-token")
            return direct
        # A live J2 global lock must not block a J1 official paid request.
        with single_call_guard(self.reviews):
            result = step(
                packet=self.packet, lock_path=self.lock,
                output_dir=self.reviews / "J1",
                reviewer_id="J1", position=2,
                approve_private_transfer=True, approve_paid_calls=True,
                confirm_hf_spending_cap=False,
                hf_token="synthetic-token", client_factory=official_factory,
                official_revision=revision_path,
            )
        self.assertEqual(result["paid_api_attempts"], 1)
        self.assertEqual(direct.calls[0]["model"], "deepseek-flash")
        self.assertEqual(direct.calls[0]["extra_body"],
                         {"thinking": {"type": "disabled"}})
        receipt = json.loads((self.reviews / "J1" /
                              "002.score.private.json").read_text())
        self.assertEqual(receipt["model"], "deepseek-flash")
        self.assertEqual(receipt["provider"], "deepseek-official")
        self.assertEqual(receipt["execution_revision_sha256"],
                         digest(revision_path.read_bytes()))
        audit = json.loads((self.reviews / "J1" /
                            "002.execution.private.json").read_text())
        self.assertEqual(audit["revision"],
                         "j1_deepseek_official_json_object_v1")
        self.assertEqual(audit["api_origin"], "https://api.deepseek.com")
        self.assertEqual(audit["max_total_in_flight"], 2)
        marker = json.loads((self.reviews / "J1" /
                             "002.attempt.private.json").read_text())
        self.assertEqual(marker["concurrency_lane_lock"],
                         ".gold48_j1_official_call.lock")
        self.assertFalse(audit["model_scores_or_flags_changed"])

    def test_j1_official_lane_serializes_itself(self) -> None:
        with (
            single_call_guard(
                self.reviews, lock_name=".gold48_j1_official_call.lock"
            ),
            self.assertRaisesRegex(
                LockHold, "JUDGE_CONCURRENT_EXECUTION_HOLD"
            ),
        ):
            with single_call_guard(
                self.reviews, lock_name=".gold48_j1_official_call.lock"
            ):
                self.fail("J1 official lock was unexpectedly available")

    def test_official_revision_rejected_for_j2_before_call(self) -> None:
        revision_path = (self.owner_folder /
                         "GOLD48_J1_OFFICIAL_REVISION_PRIVATE.json")
        with self.assertRaisesRegex(LockHold,
                                    "J1_OFFICIAL_REVISION_BINDING_HOLD"):
            step(
                packet=self.packet, lock_path=self.lock,
                output_dir=self.reviews / "J2",
                reviewer_id="J2", position=2,
                approve_private_transfer=True, approve_paid_calls=True,
                confirm_hf_spending_cap=False, hf_token="synthetic-token",
                client_factory=self.factory, official_revision=revision_path,
            )
        self.assertFalse((self.reviews / "J2" /
                          "002.attempt.private.json").exists())

    def test_second_slot_has_its_own_identity(self) -> None:
        other_client = FakeClient()
        seen = []
        safe = self.run_one(
            reviewer="J2", factory=lambda **kwargs:
            seen.append(kwargs) or other_client,
        )
        self.assertEqual(safe["paid_api_attempts"], 1)
        self.assertEqual(seen[0]["fixed_provider"], "deepinfra")
        self.assertEqual(other_client.calls[0]["model"], "zai-org/GLM-5.2")
        self.assertEqual(other_client.calls[0]["extra_body"],
                         {"reasoning_effort": "none"})
        self.assertEqual(self.client.calls, [])

    def test_single_call_guard_rejects_concurrent_attempt(self) -> None:
        with single_call_guard(self.reviews), self.assertRaisesRegex(
            LockHold, "JUDGE_CONCURRENT_EXECUTION_HOLD"
        ):
            self.run_one()
        self.assertEqual(self.client.calls, [])
        self.assertFalse((self.reviews / "J1" /
                          "002.attempt.private.json").exists())

    def test_reject_output_dir_outside_owner_root(self) -> None:
        outside = Path(self.temp.name) / "outside"
        outside.mkdir(mode=0o700)
        with self.assertRaisesRegex(LockHold, "JUDGE_OUTPUT_FOLDER_HOLD"):
            step(
                packet=self.packet, lock_path=self.lock, output_dir=outside,
                reviewer_id="J1", position=2,
                approve_private_transfer=True, approve_paid_calls=True,
                confirm_hf_spending_cap=True, hf_token="synthetic-token",
                client_factory=self.factory,
            )
        self.assertEqual(self.factory_calls, 0)


if __name__ == "__main__":
    unittest.main()

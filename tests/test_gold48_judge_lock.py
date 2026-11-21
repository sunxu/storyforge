"""Synthetic-only contract lock tests; no HF API, tokens, or private Story data."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from storyforge_gold_quality.gold48_blind import PACK_SCHEMA
from storyforge_gold_quality.gold48_judge_lock import (
    CONFIG_SCHEMA,
    LockHold,
    prepare,
)
from storyforge_gold_quality.hf_literary_review import canonical


class Gold48JudgeLockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "owner"
        self.root.mkdir(mode=0o700)
        self.reviewer = self.root / "reviewers"
        self.reviewer.mkdir(mode=0o700)
        self.pack = self.reviewer / "GOLD48_BLIND_240_PRIVATE.jsonl"
        self.config = self.root / "config.private.json"
        self.output = self.root / "GOLD48_JUDGE_LOCK_PRIVATE.json"
        self.rows = []
        n = 0
        for i in range(48):
            for j in range(5):
                self.rows.append({
                    "schema": PACK_SCHEMA,
                    "blind_id": f"{n:032x}",
                    "visible_messages": [
                        {"role": "user", "content": f"synthetic history {i}"},
                    ],
                    "target_text": "" if n == 0 else f"synthetic reply {i}/{j}",
                })
                n += 1
        self.write_packet()
        self.settings = {
            "schema": CONFIG_SCHEMA,
            "reviewers": [
                {"reviewer_id": "J1", "model": "deepseek-ai/DeepSeek-V4.1-Flash",
                 "provider": "novita", "temperature": 0, "max_tokens": 2048},
                {"reviewer_id": "J2", "model": "zai-org/GLM-5.2",
                 "provider": "deepinfra", "temperature": 0, "max_tokens": 2048},
            ],
            "max_cost_usd": 25.0,
        }
        self.write_config()

    @staticmethod
    def private_file(path: Path, content: bytes) -> None:
        path.write_bytes(content)
        os.chmod(path, 0o600)

    def write_packet(self) -> None:
        self.private_file(self.pack, b"".join(
            canonical(row) + b"\n" for row in self.rows
        ))

    def write_config(self) -> None:
        self.private_file(self.config, canonical(self.settings) + b"\n")

    def test_read_only_preflight_does_not_write_or_contact_provider(self) -> None:
        result = prepare(packet=self.pack, config=self.config, output=None)
        self.assertEqual(result["status"],
                         "GOLD48_JUDGE_CONFIG_PREFLIGHT_PASS__NO_OUTPUT_NO_API")
        self.assertEqual(result["answers"], 240)
        self.assertEqual(result["planned_paid_judge_scores"], 478)
        self.assertEqual(result["fixed_no_response_scores"], 2)
        self.assertEqual(result["api_calls"], 0)
        self.assertFalse(result["private_transfer_authorized"])
        self.assertFalse(self.output.exists())

    def test_create_once_freezes_pack_and_code_identity(self) -> None:
        result = prepare(packet=self.pack, config=self.config,
                         output=self.output)
        self.assertEqual(result["status"],
                         "GOLD48_JUDGE_CONFIG_LOCKED__NO_API_NO_TRANSFER")
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        lock = json.loads(self.output.read_text())
        self.assertEqual(lock["config"], self.settings)
        self.assertEqual(len(lock["packet_sha256"]), 64)
        self.assertEqual(len(lock["judge_source_sha256"]), 64)
        self.assertEqual(lock["max_total_api_calls"], 478)
        self.assertTrue(lock["fixed_no_response_policy"])
        self.assertFalse(lock["private_transfer_authorized"])
        self.assertFalse(lock["paid_calls_authorized"])
        self.assertFalse(lock["unblinding_authorized"])
        with self.assertRaises(LockHold):
            prepare(packet=self.pack, config=self.config,
                    output=self.output)

    def test_duplicate_blind_id_rejected(self) -> None:
        self.rows[3]["blind_id"] = self.rows[0]["blind_id"]
        self.write_packet()
        with self.assertRaisesRegex(LockHold, "BLIND_PACKET_48X5_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_case_group_multiplicity_rejected(self) -> None:
        self.rows[1]["visible_messages"] = [{"role": "user", "content": "other"}]
        self.write_packet()
        with self.assertRaisesRegex(LockHold, "BLIND_PACKET_48X5_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_blank_count_requires_exactly_one(self) -> None:
        self.rows[0]["target_text"] = "not blank"
        self.write_packet()
        with self.assertRaisesRegex(LockHold, "BLIND_PACKET_NO_RESPONSE_COUNT_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_jsonl_not_canonical_rejected(self) -> None:
        self.private_file(self.pack, b"".join(
            json.dumps(row, ensure_ascii=False).encode() + b"\n"
            for row in self.rows
        ))
        with self.assertRaisesRegex(LockHold, "BLIND_PACKET_CANONICAL_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_same_model_does_not_count_as_independent_model(self) -> None:
        self.settings["reviewers"][1]["model"] = self.settings["reviewers"][0]["model"]
        self.write_config()
        with self.assertRaisesRegex(LockHold, "JUDGE_DISTINCT_MODELS_PROVIDERS_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_same_provider_rejected(self) -> None:
        self.settings["reviewers"][1]["provider"] = "novita"
        self.write_config()
        with self.assertRaisesRegex(LockHold, "JUDGE_DISTINCT_MODELS_PROVIDERS_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_budget_and_temperature_fail_closed(self) -> None:
        self.settings["max_cost_usd"] = 0
        self.write_config()
        with self.assertRaisesRegex(LockHold, "JUDGE_BUDGET_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)
        self.settings["max_cost_usd"] = 25.0
        self.settings["reviewers"][0]["temperature"] = 0.2
        self.write_config()
        with self.assertRaisesRegex(LockHold, "JUDGE_REVIEWER_CONFIG_HOLD"):
            prepare(packet=self.pack, config=self.config, output=None)

    def test_git_ancestor_rejected(self) -> None:
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(LockHold, "PRIVATE_OUTPUT_INSIDE_GIT_HOLD"):
            prepare(packet=self.pack, config=self.config,
                    output=self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

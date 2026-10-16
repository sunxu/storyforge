#!/usr/bin/env python3
"""No network, HF credentials, model or private data: R50 receipt validator tests."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "v03_r50_verify_and_archive_tokenizer.py"
spec = importlib.util.spec_from_file_location("r50_verifier", SCRIPT)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture() -> dict:
    ids = [f"SFH50-W{w}-{i:03d}"
           for w, count in m.EXPECTED_WORLDS.items()
           for i in range(1, count + 1)]
    # Some IDs in the synthetic fixture may be excluded historical IDs,
    # so generate 46 permitted IDs with the exact frozen per-world counts.
    ids = []
    for w, count in m.EXPECTED_WORLDS.items():
        for i in range(1, 12):
            candidate = f"SFH50-W{w}-{i:03d}"
            if candidate not in m.EXCLUDE and len(
                [x for x in ids if x.startswith(f"SFH50-W{w}-")]) < count:
                ids.append(candidate)
    assert len(ids) == 46 and not set(ids) & m.EXCLUDE
    cases = [{
        "case_id": ident,
        "history_count": 8 if i < 42 else 7,
        "consecutive_user": i < 12,
        "input_tokens": 100 + i,
        "input_plus_output_budget": 100 + i + 1536,
        "within_budget": True,
        "input_id_sha256": hashlib.sha256(str(i).encode()).hexdigest(),
    } for i, ident in enumerate(ids)]
    # 42 * 8 + 4 * 7 = 364
    return {
        "schema": "storyforge-r50-cpu-real-tokenizer-preflight-v1",
        "status": "PREFLIGHT_ONLY_NO_FINAL_SEAL",
        "pinned_model_revision": m.EXPECTED_MODEL,
        "candidate_original_sha256": m.EXPECTED_CANDIDATE,
        "system_sha256": m.EXPECTED_SYSTEM,
        "chat_template_sha256": "a" * 64,
        "tokenizer_file_sha256": {
            "tokenizer.json": "b"*64, "tokenizer_config.json": "c"*64},
        "tokenizer_snapshot": "/tmp/qwen/" + m.EXPECTED_MODEL,
        "thinking_mode": "disabled",
        "max_context": 16384,
        "reserved_output_tokens": 1536,
        "case_count": 46,
        "overflow_count": 0,
        "actual_four_model_inference_input_equality": "NOT_VERIFIED_NO_MODEL_EXECUTED",
        "no_model_generation": True,
        "no_gpu": True,
        "no_final_heldout_seal": True,
        "strategy": "PRESERVE_CONSECUTIVE_USER_AND_INJECT_WORLD_RULES_TO_SHARED_SYSTEM__DRAFT_ONLY",
        "cases": cases,
    }


def validate(obj: dict) -> dict:
    return m.verify_report(json.dumps(obj).encode(), "6ad1fd155ccb47ba0f7b1ec6")


class VerifyPrivateReportTests(unittest.TestCase):
    def test_valid_report_is_aggregate(self):
        out = validate(fixture())
        self.assertEqual(out["case_count"], 46)
        self.assertEqual(out["history_message_count"], 364)
        self.assertEqual(out["overflow_count"], 0)
        self.assertEqual(out["input_token_distribution"]["max"], 145)
        self.assertNotIn("cases", out)
        self.assertNotIn("stage_key", out)

    def test_overflow_is_rejected(self):
        data = fixture()
        data["cases"][0]["within_budget"] = False
        with self.assertRaises(ValueError):
            validate(data)

    def test_wrong_candidate_sha_rejected(self):
        data = fixture()
        data["candidate_original_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate(data)

    def test_duplicate_case_rejected(self):
        data = fixture()
        data["cases"][1]["case_id"] = data["cases"][0]["case_id"]
        with self.assertRaises(ValueError):
            validate(data)

    def test_missing_files_rejected(self):
        data = fixture()
        data["tokenizer_file_sha256"].pop("tokenizer_config.json")
        with self.assertRaises(ValueError):
            validate(data)

    def test_wrong_token_budget_rejected(self):
        data = fixture()
        data["cases"][0]["input_plus_output_budget"] += 1
        with self.assertRaises(ValueError):
            validate(data)

    def test_history_sum_rejected(self):
        data = fixture()
        data["cases"][0]["history_count"] += 1
        with self.assertRaises(ValueError):
            validate(data)

    def test_case_level_data_never_archived(self):
        data = fixture()
        data["cases"][0]["secret_dialogue"] = "DO NOT ARCHIVE"
        out = validate(data)
        self.assertNotIn("DO NOT ARCHIVE", json.dumps(out))


if __name__ == "__main__":
    unittest.main()

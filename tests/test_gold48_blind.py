"""Synthetic-only regression for Gold48 five-source blind packet."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    INPUT_SCHEMA,
    MODEL,
    REVISION,
    ROLES,
)
from storyforge_gold_quality.gold48_blind import Gold48BlindHold, prepare
from storyforge_gold_quality.hf_literary_review import canonical


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def private_file(path: Path, raw: bytes) -> Path:
    path.write_bytes(raw)
    os.chmod(path, 0o600)
    return path


def json_file(path: Path, data: object) -> Path:
    return private_file(path, canonical(data) + b"\n")


class Gold48BlindSyntheticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "owner"
        self.root.mkdir(mode=0o700)
        cases, inputs, originals, locators = [], [], [], []
        for i in range(48):
            sample_id = f"G48-C{i + 1:02d}"
            messages = [
                {"role": "system", "content": "fictional world instruction"},
                {"role": "user", "content": f"turn {i}: decide what happens"},
            ]
            ref = f"Historical reference response {i}"
            group = i // 6
            cases.append({
                "candidate_case_id_PRIVATE": sample_id,
                "reconstructed_messages_sha256_PRIVATE": digest(canonical(messages)),
                "original_reference_sha256_PRIVATE": digest(ref.encode()),
                "anonymous_group_PRIVATE": f"ANON-GROUP-{group}",
                "exclude_from_42_sensitivity": group == 0,
            })
            inputs.append({"sample_id": sample_id, "messages": messages})
            originals.append({
                "candidate_case_id_PRIVATE": sample_id,
                "original_reply_PRIVATE": ref,
                "original_reply_sha256_PRIVATE": digest(ref.encode()),
            })
            locators.append({
                "candidate_case_id_PRIVATE": sample_id,
                "story_id_PRIVATE": f"source-story-{group}",
                "session_id_PRIVATE": f"source-session-{i % 25}",
                "exclude_from_42_sensitivity": group == 0,
            })
        self.freeze = json_file(self.root / "freeze.json", {
            "schema": "storyforge_r60_gold48_owner_scoped_freeze_private_v1",
            "owner_gold48_freeze": True,
            "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
            "main_analysis_count": 48, "sensitivity_analysis_count": 42,
            "session_count": 25, "cases_PRIVATE": cases,
        })
        self.input = private_file(
            self.root / "input.private.jsonl",
            b"".join(canonical(x) + b"\n" for x in inputs),
        )
        self.input_manifest = json_file(self.root / "input_manifest.json", {
            "schema": INPUT_SCHEMA,
            "record_count": 48, "seed": 42,
            "sha256": digest(self.input.read_bytes()),
            "cases": [{
                "sample_id": x["sample_id"],
                "messages_sha256": digest(canonical(x["messages"])),
            } for x in inputs],
        })
        self.original = json_file(self.root / "original.json", {
            "schema": "storyforge_r60_gold48_recovered_references_private_v1",
            "cases_PRIVATE": originals,
        })
        self.locators = json_file(self.root / "locators.json", {
            "schema": "storyforge_r60_gold48_recovered_locators_private_v1",
            "cases_PRIVATE": locators,
        })
        self.generated = {}
        length_counts = {"base": 1, "r46_v02": 2, "r54_v03a": 1, "r60_base336": 3}
        for role in ROLES:
            out = self.root / f"{role}.private.json"
            doc = {
                "schema": "storyforge_r60_generation_outputs_private_v1",
                "model_role": role, "model": MODEL, "revision": REVISION,
                "seed": 42, "record_count": 48,
                "outputs": [{
                    "sample_id": f"G48-C{i + 1:02d}",
                    "effective_seed": 42 + i,
                    "text": f"Generated story answer for role {role} case {i}",
                    "input_tokens": 20, "output_tokens": 10,
                    "finish_reason": "length" if i < length_counts[role] else "eos",
                } for i in range(48)],
            }
            json_file(out, doc)
            out_sha = digest(out.read_bytes())
            json_file(self.root / f"{role}.private.json.result-sha256-manifest.private.json", {
                "schema": "storyforge_r60_gold48_private_result_delivery_v1",
                "model_role": role, "record_count": 48,
                "files": [{"name": out.name, "sha256": out_sha},
                          {"name": "unused-launch", "sha256": "a" * 64},
                          {"name": "unused-identity", "sha256": "b" * 64}],
            })
            json_file(self.root / f"{role}.private.json.identity.private.json", {
                "input_sha256": digest(self.input.read_bytes()),
                "selected_model_role": role,
                "output_sha256": out_sha,
            })
            self.generated[role] = out

    def build(self) -> dict:
        return prepare(
            freeze_path=self.freeze, input_path=self.input,
            input_manifest_path=self.input_manifest, original_path=self.original,
            locator_path=self.locators, generated=self.generated,
            output_dir=self.root / "out",
        )

    def test_240_objects_and_private_key_split(self) -> None:
        safe = self.build()
        self.assertEqual(safe["status"], "GOLD48_240_BLIND_OBJECTS_PREPARED__NO_JUDGE_CALLS")
        self.assertEqual((safe["answers"], safe["sensitivity_cases"]), (240, 42))
        self.assertEqual(safe["api_calls"], 0)
        reviewer = self.root / "out" / "reviewers" / "GOLD48_BLIND_240_PRIVATE.jsonl"
        lines = [json.loads(line) for line in reviewer.read_bytes().splitlines()]
        self.assertEqual(len(lines), 240)
        self.assertEqual(len({x["blind_id"] for x in lines}), 240)
        self.assertEqual(set(lines[0]), {
            "schema", "blind_id", "visible_messages", "target_text",
        })
        self.assertNotIn(b"source_role_PRIVATE", reviewer.read_bytes())
        self.assertNotIn(b"session_id_PRIVATE", reviewer.read_bytes())
        mapping = json.loads(
            (self.root / "out" / "owner" / "GOLD48_COORDINATOR_KEY_PRIVATE.json").read_text()
        )
        self.assertEqual(len(mapping["bindings"]), 240)
        self.assertEqual({x["source_role_PRIVATE"] for x in mapping["bindings"]},
                         set(ROLES) | {"original"})
        self.assertEqual(sum(x["exclude_from_42_sensitivity"]
                             for x in mapping["bindings"]), 30)
        self.assertEqual(mapping["reviewer_packet_sha256"], digest(reviewer.read_bytes()))
        self.assertEqual(reviewer.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / "out").stat().st_mode & 0o777, 0o700)
        with self.assertRaises(Gold48BlindHold):
            self.build()

    def test_read_only_preflight_does_not_create_output(self) -> None:
        safe = prepare(
            freeze_path=self.freeze, input_path=self.input,
            input_manifest_path=self.input_manifest, original_path=self.original,
            locator_path=self.locators, generated=self.generated,
            output_dir=None,
        )
        self.assertEqual(safe["status"],
                         "GOLD48_48X5_SOURCE_PREFLIGHT_PASS__NO_OUTPUT_NO_JUDGE")
        self.assertEqual(safe["answers"], 240)
        self.assertEqual(safe["judge_scores_completed"], 0)
        self.assertFalse((self.root / "out").exists())

    def test_rejects_git_directory_output(self) -> None:
        git = self.root / ".git"
        git.mkdir(mode=0o700)
        with self.assertRaisesRegex(Gold48BlindHold, "PRIVATE_OUTPUT_INSIDE_GIT_HOLD"):
            self.build()
        self.assertFalse((self.root / "out").exists())

    def test_rejects_drifted_original_sha(self) -> None:
        data = json.loads(self.original.read_text())
        data["cases_PRIVATE"][0]["original_reply_PRIVATE"] = "changed original"
        json_file(self.original, data)
        with self.assertRaisesRegex(Gold48BlindHold, "ORIGINAL_FROZEN_REPLY_HOLD"):
            self.build()
        self.assertFalse((self.root / "out").exists())

    def test_rejects_frozen_input_sha_drift(self) -> None:
        data = json.loads(self.input_manifest.read_text())
        data["sha256"] = "0" * 64
        json_file(self.input_manifest, data)
        with self.assertRaisesRegex(Gold48BlindHold, "FROZEN_INPUT_SHA_HOLD"):
            self.build()

    def test_rejects_wrong_risk_story(self) -> None:
        data = json.loads(self.locators.read_text())
        data["cases_PRIVATE"][7]["exclude_from_42_sensitivity"] = True
        json_file(self.locators, data)
        with self.assertRaisesRegex(Gold48BlindHold, "OWNER_CASE_ALIGNMENT_HOLD"):
            self.build()


if __name__ == "__main__":
    unittest.main()

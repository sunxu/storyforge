"""Synthetic-only candidate packaging regression. Never reads real Gold text."""
from __future__ import annotations

import copy
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import quality_v1_sft_candidates as packer
from quality_v1 import EVIDENCE, FLOORS, SCHEMA, SCORES, SEVERE, canonical, sha


def case(cid="case01", world="world01", split="train"):
    messages = [
        {"role": "system", "content": "原创虚构互动剧情。"},
        {"role": "assistant", "content": "角色先行开口。"},
        {"role": "user", "content": f"请角色继续推进，保留玩家选择。{cid}"},
    ]
    target = f"她推开窗，把一封信递给玩家，等待选择。{cid}"
    evidence = {key: True for key in EVIDENCE}
    evidence.update({
        "known_protected_overlap": False,
        "final_heldout_overlap": False,
        "protected_test_body_accessed": False,
    })
    reviews = [{
        "reviewer_key": reviewer,
        "decision": "PASS",
        "private_evidence_ref": f"synthetic-{reviewer}",
        "severe_flags": {key: False for key in SEVERE},
        "scores": {key: max(4, FLOORS[key]) for key in SCORES},
    } for reviewer in ("reviewer_a", "reviewer_b")]
    return {
        "schema": SCHEMA,
        "case_id": cid,
        "corpus": "gold195",
        "source_kind": "original_gold",
        "source_version_sha256": "a" * 64,
        "world_graph_sha256": "b" * 64,
        "world_component_id": world,
        "split": split,
        "messages": messages,
        "target_text": target,
        "input_messages_sha256": sha(canonical(messages)),
        "assistant_target_sha256": sha(target.encode()),
        "evidence": evidence,
        "reviews": reviews,
    }


class CandidatePackTests(unittest.TestCase):
    def test_compiles_only_pass_and_exact_last_assistant_mask(self):
        a = case()
        b = case("case02", "world02", "validation")
        c = case("case03", "world03")
        c["reviews"][1]["decision"] = "HOLD"
        rows, safe = packer.compile_candidates([a, b, c])
        self.assertEqual(len(rows), 2)
        self.assertEqual(safe["candidate_train"], 1)
        self.assertEqual(safe["candidate_validation"], 1)
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["training_authorized"])
        self.assertFalse(safe["tokenizer_collator_checked"])
        for row in rows:
            self.assertEqual(row["status"], "CANDIDATE_NOT_ADMITTED")
            self.assertEqual(row["messages"][-2]["role"], "user")
            self.assertEqual(row["messages"][-1]["role"], "assistant")
            self.assertEqual(
                [m.get("loss") for m in row["messages"] if m["role"] == "assistant"],
                [False, True],
            )

    def test_world_collision_holds_even_if_one_case_rejected(self):
        a, b = case(), case("case02", "world01", "validation")
        b["reviews"][1]["decision"] = "REJECT"
        with self.assertRaisesRegex(
            packer.CandidateHold, "TRAIN_VALIDATION_WORLD_COLLISION"
        ):
            packer.compile_candidates([a, b])

    def test_duplicate_input_or_target_holds(self):
        a = case()
        b = copy.deepcopy(a)
        b["case_id"] = "case02"
        b["world_component_id"] = "world02"
        with self.assertRaisesRegex(
            packer.CandidateHold, "DUPLICATE_SOURCE_OR_TARGET"
        ):
            packer.compile_candidates([a, b])

    def test_private_write_create_only_and_safe_counts(self):
        a = case()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private = root / "private"
            private.mkdir(mode=0o700)
            source = private / "reviewed.jsonl"
            source.write_bytes(canonical(a) + b"\n")
            os.chmod(source, 0o600)
            output = private / "out"
            safe = packer.run(source, output)
            self.assertEqual(safe["candidate_cases"], 1)
            self.assertFalse(safe["private_values_emitted"])
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            result_file = output / "SFT_CANDIDATES_PRIVATE.jsonl"
            self.assertEqual(stat.S_IMODE(result_file.stat().st_mode), 0o600)
            row = json.loads(result_file.read_text().strip())
            self.assertEqual(row["messages"][-1]["content"], a["target_text"])
            self.assertNotIn(a["target_text"], json.dumps(safe, ensure_ascii=False))
            with self.assertRaisesRegex(
                packer.CandidateHold, "OUTPUT_ALREADY_EXISTS"
            ):
                packer.run(source, output)

    def test_unreviewed_or_malformed_row_not_packaged(self):
        bad = case()
        bad["target_text"] = "hash changed"
        rows, safe = packer.compile_candidates([bad])
        self.assertEqual(rows, [])
        self.assertEqual(safe["held_or_rejected"], 1)
        self.assertEqual(safe["quality_v1_admitted"], 0)

    def test_no_false_admission_on_pass_case(self):
        rows, safe = packer.compile_candidates([case()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["dataset_frozen"])
        self.assertFalse(safe["reviewer_independence_independently_proven"])


if __name__ == "__main__":
    unittest.main()

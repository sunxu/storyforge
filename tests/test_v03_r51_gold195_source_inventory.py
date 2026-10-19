"""R51 synthetic only: frozen Gold candidate structural preflight."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

scripts = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location(
    "gold195", scripts / "v03_r51_gold195_source_inventory.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture() -> dict:
    result = {}
    for cohort in ("87", "108"):
        result[cohort] = []
        for j in range(module.COHORTS[cohort]["expected_rows"]):
            result[cohort].append({
                "id": f"{cohort}-synthetic-{j}",
                "messages": [
                    {"role": "user", "content": "Synthetic input"},
                    {"role": "assistant", "content": f"Synthetic output {cohort} {j}"},
                ],
                "metadata": {
                    "story_id": f"synthetic-story-{cohort}",
                    "source_file": ("01" if cohort=="87" else "06")+"-synthetic.jsonl",
                    "target_message_id": f"synthetic-target-{j}",
                    "training_admission": "PENDING_NOT_APPROVED",
                    "split": None,
                    "story_card_version_id": None,
                    "supervision_contract": {
                        "supervised_message_index": 1,
                        "only_final_assistant_supervised": True,
                    },
                    "target_text_modified": False,
                    "history_text_modified": False,
                    "system_prompt_added": False,
                },
            })
    return result


class Gold195InventoryTests(unittest.TestCase):
    def test_frozen_195_not_train_admitted(self):
        result = module.inspect(fixture())
        self.assertEqual(result["total_original_candidates"], 195)
        self.assertEqual(result["training_admitted_rows"], 0)
        self.assertEqual(result["train_rows_assigned"], 0)
        self.assertFalse(result["world_component_alias_graph_certified"])
        self.assertEqual(result["per_cohort"]["108"]["rows"], 108)

    def test_last_assistant_required(self):
        f=fixture()
        f["87"][0]["messages"][-1]["role"]="user"
        with self.assertRaisesRegex(ValueError,"GOLD_FINAL_SUPERVISION_TARGET_NOT_ASSISTANT"):
            module.inspect(f)

    def test_duplicate_record_id_hard_fail(self):
        f=fixture()
        f["108"][0]["id"]=f["87"][0]["id"]
        with self.assertRaisesRegex(ValueError,"GOLD_ID_COLLISION_ACROSS_COHORTS"):
            module.inspect(f)

    def test_declared_target_label_index_must_be_final(self):
        f=fixture()
        f["87"][0]["metadata"]["supervision_contract"]["supervised_message_index"]=0
        with self.assertRaisesRegex(ValueError,"GOLD_LAST_ASSISTANT_LABEL_CONTRACT_MISMATCH"):
            module.inspect(f)

    def test_split_assignment_cannot_be_silently_accepted(self):
        f=fixture()
        f["87"][0]["metadata"]["split"]="train"
        with self.assertRaisesRegex(ValueError,"GOLD_UNAUTHORIZED_TRAIN_VALIDATION_SPLIT"):
            module.inspect(f)

    def test_source_modified_candidate_rejected(self):
        f=fixture()
        f["108"][0]["metadata"]["target_text_modified"]=True
        with self.assertRaisesRegex(ValueError,"GOLD_ORIGINAL_SOURCE_MODIFIED_OR_SYSTEM_ADDED"):
            module.inspect(f)

    def test_target_sha_mismatch_rejected(self):
        f=fixture()
        f["87"][0]["metadata"]["target_sha256_utf8"]="0"*64
        with self.assertRaisesRegex(ValueError,"GOLD_TARGET_SHA256_MISMATCH"):
            module.inspect(f)


if __name__ == "__main__":
    unittest.main()

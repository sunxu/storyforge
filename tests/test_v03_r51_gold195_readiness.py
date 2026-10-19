"""Synthetic R51 Gold195 admission refusal and original source structural tests."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location(
    "r51", SCRIPTS / "v03_r51_gold195_readiness.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixtures():
    cohort87 = []
    cohort108 = []
    index = []
    for rank, count in m.COUNT_BY_STORY.items():
        for k in range(count):
            group = 87 if rank <= 5 else 108
            ident = f"synthetic-{rank:02d}-{k:03d}"
            target = f"synthetic assistant completion {ident}"
            meta = {
                "story_id": f"synthetic-story-{rank}-{int(rank == 10 and k == 0)}",
                "target_message_id": ident,
                "training_admission": "PENDING_NOT_APPROVED",
                "split": None,
            }
            if group == 87:
                meta.update(source_file=f"{rank:02d}-synthetic.jsonl",
                            story_card_status="EXACT_TARGET_TIME_VERSION_UNVERIFIED",
                            target_sha256_utf8=m.sha256(target.encode()),
                            target_text_modified=False,
                            history_text_modified=False,
                            source_character_age="UNSPECIFIED" if rank == 4 else None)
            else:
                meta.update(target_sha256=m.sha256(target.encode()),
                            story_number=rank,
                            story_card_as_of_target="NOT_AVAILABLE_NOT_INJECTED",
                            raw_assistant_text_edited=False,
                            raw_history_text_edited=False)
                index.append({
                    "candidate_id": ident,
                    "story_number": str(rank),
                    "target_sha256": meta["target_sha256"],
                })
            row = {"id": ident, "metadata": meta,
                   "messages": [
                       {"role": "user", "content": "synthetic user input"},
                       {"role": "assistant", "content": target},
                   ]}
            (cohort87 if group == 87 else cohort108).append(row)
    return cohort87, cohort108, index


class Gold195ReadinessTests(unittest.TestCase):
    def test_originals_pass_but_no_train_admission(self):
        a, b, i = fixtures()
        summary = m.inspect_rows(a, b, i)
        self.assertEqual(summary["candidate_count"], 195)
        self.assertEqual(summary["source_story_ranks_with_selected_gold"], 13)
        self.assertEqual(summary["r51_admitted_train_records"], 0)
        self.assertEqual(summary["r51_admitted_validation_records"], 0)
        self.assertEqual(summary["r51_status"],
                         "GOLD195_ORIGINAL_INTEGRITY_PASS__TRAINING_ADMISSION_HOLD")

    def test_train_approval_or_split_mutation_rejected(self):
        a, b, i = fixtures()
        a[0]["metadata"]["training_admission"] = "APPROVED"
        with self.assertRaisesRegex(ValueError, "PREMATURE_TRAINING_ADMISSION"):
            m.inspect_rows(a, b, i)
        a, b, i = fixtures()
        a[0]["metadata"]["split"] = "train"
        with self.assertRaisesRegex(ValueError, "PREMATURE_TRAINING_ADMISSION"):
            m.inspect_rows(a, b, i)

    def test_target_bytes_mismatch_rejected(self):
        a, b, i = fixtures()
        b[0]["messages"][-1]["content"] = "tampered"
        with self.assertRaisesRegex(ValueError, "TARGET_SHA256_MISMATCH"):
            m.inspect_rows(a, b, i)

    def test_second_cohort_legacy_target_hash_fields_supported(self):
        a, b, i = fixtures()
        for field, row in zip(("target_sha256_utf8", "target_content_sha256"),
                              b[:2], strict=True):
            row["metadata"][field] = row["metadata"].pop("target_sha256")
        report = m.inspect_rows(a, b, i)
        self.assertEqual(report["original_target_hashes_verified"], 195)

    def test_conflicting_target_hash_fields_are_rejected(self):
        a, b, i = fixtures()
        b[0]["metadata"]["target_sha256_utf8"] = "0" * 64
        with self.assertRaisesRegex(
            ValueError, "TARGET_DIGEST_MISSING_OR_CONFLICTING"
        ):
            m.inspect_rows(a, b, i)

    def test_review_index_order_mismatch_rejected(self):
        a, b, i = fixtures()
        i[0]["candidate_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "REVIEW_INDEX_ORDER_INVALID"):
            m.inspect_rows(a, b, i)

    def test_duplicate_id_or_target_rejected(self):
        a, b, i = fixtures()
        b[0]["id"] = a[0]["id"]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID_ID"):
            m.inspect_rows(a, b, i)
        a, b, i = fixtures()
        b[0]["metadata"]["story_id"] = a[0]["metadata"]["story_id"]
        b[0]["metadata"]["target_message_id"] = a[0]["metadata"]["target_message_id"]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SOURCE_TARGET"):
            m.inspect_rows(a, b, i)

    def test_frozen_story_count_enforced(self):
        a, b, i = fixtures()
        a[0]["metadata"]["source_file"] = "04-synthetic.jsonl"
        with self.assertRaisesRegex(ValueError, "STORY_DISTRIBUTION_CHANGED"):
            m.inspect_rows(a, b, i)

    def test_original_history_cannot_claim_supervision(self):
        a, b, i = fixtures()
        a[0]["messages"][0]["loss"] = True
        with self.assertRaisesRegex(ValueError,
                                    "HISTORY_SUPERVISION_ALREADY_ENABLED"):
            m.inspect_rows(a, b, i)

    def test_original_target_text_modification_rejected(self):
        a, b, i = fixtures()
        b[0]["metadata"]["raw_assistant_text_edited"] = True
        with self.assertRaisesRegex(ValueError, "CANONICAL_TEXT_WAS_EDITED"):
            m.inspect_rows(a, b, i)


if __name__ == "__main__":
    unittest.main()

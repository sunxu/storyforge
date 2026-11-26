"""Synthetic only: W17 evidence path diagnostic does not leak raw references."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "w17diagnostic", SCRIPTS / "v03_r50_diagnose_w17_evidence_paths.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_kit() -> dict:
    return {
        "old_world_contexts": {
            "2": {"context_examples": [{
                "neighbors": [{"text_excerpt": "PRIVATE SYNTHETIC SECRET"}]}]},
            "4": {"context_examples": [{"neighbors": []}]},
            "7": {"linked_world_07_context_sample": []},
            "10": {"context_examples": []},
        },
        "w17_context": {"context_examples": [{"neighbors": [{
            "text_excerpt": "PRIVATE W17 TEXT"
        }]}]},
        "w17_export_card_review_hints": {"character_briefs": []},
        "shared_literal_322_codepoints": "X" * 322,
    }


class W17DiagnosticTests(unittest.TestCase):
    def test_legitimate_nested_path_accepted(self):
        x = mod.safe_classification(
            synthetic_kit(),
            "old_world_contexts.2.context_examples[0].neighbors[0].text_excerpt",
            old_rank=2, pointer_index=8,
        )
        self.assertEqual(x["recommended_action"], "STRUCTURALLY_ACCEPTED")
        self.assertEqual(x["scope"], "ALLOWED_OLD")
        self.assertNotIn("PRIVATE SYNTHETIC SECRET", str(x))

    def test_existing_other_old_world_classified_not_auto_approved(self):
        x = mod.safe_classification(
            synthetic_kit(),
            "old_world_contexts.4.context_examples[0]",
            old_rank=2, pointer_index=8,
        )
        self.assertTrue(x["exists_in_pinned_kit"])
        self.assertEqual(x["referenced_old_rank"], 4)
        self.assertEqual(x["scope"], "OUTSIDE_SCOPED_ALLOWLIST")
        self.assertEqual(x["recommended_action"],
                         "VALID_KIT_FIELD_REQUIRES_HUMAN_SCOPE_REVIEW")

    def test_invalid_reference_is_not_silently_accepted(self):
        x = mod.safe_classification(
            synthetic_kit(),
            "old_world_contexts.2.context_examples[999].text_excerpt",
            old_rank=2, pointer_index=8,
        )
        self.assertFalse(x["exists_in_pinned_kit"])
        self.assertEqual(x["recommended_action"],
                         "INVALID_CITATION__REVIEWER_MUST_CORRECT")

    def test_invalid_user_created_root_not_exposed(self):
        x = mod.safe_classification(synthetic_kit(),
                                    "my-secret.private_user_message",
                                    old_rank=2, pointer_index=8)
        self.assertEqual(x["root_class"], "UNKNOWN")
        self.assertNotIn("my-secret", str(x))

    def test_aggregate_never_includes_citations_or_source_text(self):
        records = []
        for n in (2, 4, 10):
            records.append({
                "old_rank": n, "new_rank": 17,
                "fact_evidence_paths": [
                    "old_world_contexts.2.context_examples[0]"
                ],
            })
        x = mod.diagnose(synthetic_kit(), {"pair_reviews": records})
        blob = str(x)
        self.assertEqual(x["pair_count"], 3)
        self.assertNotIn("PRIVATE SYNTHETIC SECRET", blob)
        self.assertNotIn("old_world_contexts.2.context_examples", blob)
        self.assertEqual(x["heldout_final_seal"], "NOT_PERFORMED")

    def test_reject_missing_or_duplicated_pairs(self):
        rows = [{"old_rank": 2, "new_rank": 17,
                 "fact_evidence_paths": ["w17_context"]} for _ in range(3)]
        with self.assertRaisesRegex(ValueError, "INVALID_OR_DUPLICATE_REVIEW_PAIR"):
            mod.diagnose(synthetic_kit(), {"pair_reviews": rows})


if __name__ == "__main__":
    unittest.main()

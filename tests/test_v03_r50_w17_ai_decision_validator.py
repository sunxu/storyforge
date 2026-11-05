"""Synthetic-only tests for W17 independent AI review receipt validator."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "v03_r50_verify_w17_ai_decisions.py"
spec = importlib.util.spec_from_file_location("review_gate", SCRIPT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def kit() -> dict:
    return {
        "schema": "storyforge-r50-w17-private-ai-semantic-kit-v1",
        "status": "PRIVATE_EVIDENCE_BUILT__AI_REVIEW_PENDING",
        "semantic_world_alias_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "exact_flagged_pairs": [[2, 17], [4, 17], [10, 17]],
        "known_historical_link": [4, 7],
        "shared_literal_322_codepoints": "S" * 322,
        "old_world_contexts": {str(rank): {
            "context_examples": [{
                "source_message_index": 1,
                "neighbors": [{"relative_offset": 0, "role": "assistant",
                               "text_excerpt": "SYNTHETIC SOURCE"}],
            }],
            "story_metadata_excerpt": "synthetic world evidence",
        } for rank in (2, 4, 7, 10)},
        "w17_context": {"context_examples": [{
            "source_message_index": 3,
            "neighbors": [{"relative_offset": 0, "role": "assistant",
                           "text_excerpt": "SYNTHETIC NEW"}],
        }]},
        "w17_export_card_review_hints": {
            "character_briefs": [{"name": "synthetic-character",
                                  "brief": "synthetic private character"}],
            "world": "synthetic world context",
        },
    }


def reviewed(generic: bool = False) -> dict:
    return {
        "schema": "storyforge-r50-w17-private-ai-semantic-adjudication-v1",
        "status": "INDEPENDENT_AI_REVIEW__NOT_FINAL_SEAL",
        "reviewed_kit_sha256": "",
        "shared_literal_type": "UNCERTAIN",
        "shared_literal_evidence": "Synthetic source dialogue demonstrates limited evidence.",
        "pair_reviews": [
            {"old_rank": n, "new_rank": 17,
             "decision": "INSUFFICIENT_EVIDENCE" if not generic else "CLEAR_WITH_EVIDENCE",
             "fact_evidence_paths": [
                 f"old_world_contexts.{n}.context_examples",
                 "w17_context",
             ],
             "reasoning": "The synthetic evidence shows only a shared literal; this is insufficient for world identity closure."}
            for n in (2, 4, 10)
        ],
        "known_04_07_graph_edge": "LINKED_CONFIRMED_IN_PRIOR_SCOPE",
        "possible_transitive_link_to_w17": "INSUFFICIENT_EVIDENCE",
        "remaining_evidence_requirements": ["Full old-world identities"],
        "full_semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "model_promotion": False,
    }


def valid_summary(k: dict | None = None, d: dict | None = None) -> dict:
    k = kit() if k is None else k
    d = reviewed() if d is None else d
    b = json.dumps(k, ensure_ascii=False).encode()
    d["reviewed_kit_sha256"] = hashlib.sha256(b).hexdigest()
    return m.validate(b, json.dumps(d, ensure_ascii=False).encode(),
                      expected_kit_sha=d["reviewed_kit_sha256"])


class W17DecisionValidatorTests(unittest.TestCase):
    def test_good_review_is_safe_hold(self):
        summary = valid_summary()
        self.assertEqual(summary["scoped_pair_count"], 3)
        self.assertEqual(summary["full_semantic_world_graph_gate"], "HOLD")
        self.assertFalse(summary["reviewer_independence_or_correctness_verified_by_script"])
        self.assertEqual(summary["decision_counts"]["INSUFFICIENT_EVIDENCE"], 3)
        self.assertEqual(summary["private_decision_sha256"].__len__(), 64)
        text = json.dumps(summary)
        self.assertNotIn("Synthetic source dialogue", text)
        self.assertNotIn("The synthetic evidence", text)
        self.assertNotIn("Full old-world identities", text)
        self.assertNotIn("S" * 60, text)

    def test_missing_one_pair_rejected(self):
        d = reviewed()
        d["pair_reviews"].pop()
        with self.assertRaisesRegex(ValueError, "REQUIRED_THREE_PAIR_REVIEWS"):
            valid_summary(d=d)

    def test_duplicate_pair_rejected(self):
        d = reviewed()
        d["pair_reviews"][1]["old_rank"] = 2
        with self.assertRaisesRegex(ValueError, "INVALID_OR_DUPLICATE_PAIR"):
            valid_summary(d=d)

    def test_indexed_nested_paths_resolve_against_real_kit_shape(self):
        d = reviewed(generic=True)
        d["pair_reviews"][0]["fact_evidence_paths"] = [
            "old_world_contexts.2.context_examples[0].neighbors[0].text_excerpt",
            "w17_context.context_examples[0].neighbors[0].text_excerpt",
            "w17_export_card_review_hints.character_briefs[0].name",
        ]
        result = valid_summary(d=d)
        self.assertEqual(result["pair_decisions"][0]["evidence_pointer_count"], 3)

    def test_jsonpath_quoted_keys_resolve(self):
        d = reviewed(generic=True)
        d["pair_reviews"][1]["fact_evidence_paths"] = [
            '$["old_world_contexts"]["4"]["context_examples"][0]["neighbors"][0]["text_excerpt"]',
            "$.w17_context.context_examples[0].neighbors[0].text_excerpt",
        ]
        result = valid_summary(d=d)
        self.assertEqual(result["pair_decisions"][1]["evidence_pointer_count"], 2)

    def test_nonexistent_index_rejected_without_raw_path(self):
        d = reviewed()
        d["pair_reviews"][0]["fact_evidence_paths"] = [
            "old_world_contexts.2.context_examples[999].neighbors[0].text_excerpt",
            "w17_context",
        ]
        with self.assertRaisesRegex(ValueError,
                                    "EVIDENCE_PATH_NOT_FOUND_IN_PINNED_KIT"):
            valid_summary(d=d)

    def test_other_old_world_reference_rejected(self):
        d = reviewed()
        d["pair_reviews"][0]["fact_evidence_paths"] = [
            "old_world_contexts.10.context_examples[0]",
            "w17_context",
        ]
        with self.assertRaisesRegex(ValueError,
                                    "UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH"):
            valid_summary(d=d)

    def test_empty_old_evidence_cannot_support_world_link(self):
        k = kit()
        k["old_world_contexts"]["2"]["context_examples"] = []
        k["old_world_contexts"]["2"]["story_metadata_excerpt"] = ""
        d = reviewed(generic=True)
        with self.assertRaisesRegex(ValueError,
                                    "STRONG_PAIR_DECISION_REQUIRES_TWO_SOURCE_ANCHORS"):
            valid_summary(k=k, d=d)

    def test_duplicate_canonical_evidence_paths_rejected(self):
        d = reviewed()
        d["pair_reviews"][0]["fact_evidence_paths"] = [
            "old_world_contexts.2.context_examples[0]",
            'old_world_contexts["2"].context_examples.0',
        ]
        with self.assertRaisesRegex(ValueError,
                                    "DUPLICATE_CANONICAL_EVIDENCE_PATH"):
            valid_summary(d=d)

    def test_malicious_or_invented_citations_fail(self):
        for bad in ("__class__", "secrets.API_KEY",
                    "old_world_contexts.2.context_examples[-1]",
                    "old_world_contexts.2.context_examples[0].neighbors[999]",
                    "w17_context.context_examples[0].invented",
                    "old_world_contexts.2.__dict__"):
            d = reviewed()
            d["pair_reviews"][0]["fact_evidence_paths"] = [bad]
            with self.subTest(path=bad), self.assertRaises(ValueError):
                valid_summary(d=d)

    def test_card_warning_is_real_but_not_substantive_evidence(self):
        k = kit()
        k["w17_export_card_review_hints"]["WARNING"] = (
            "Export-time card is not automatically valid at test cutoff"
        )
        d = reviewed(generic=True)
        for row in d["pair_reviews"]:
            row["fact_evidence_paths"].append(
                "w17_export_card_review_hints.WARNING"
            )
        summary = valid_summary(k=k, d=d)
        self.assertEqual(summary["scoped_pair_count"], 3)
        self.assertEqual(summary["full_semantic_world_graph_gate"], "HOLD")
        self.assertTrue(all(
            row["evidence_pointer_count"] == 3
            for row in summary["pair_decisions"]
        ))

    def test_card_warning_alone_does_not_support_world_clear(self):
        k = kit()
        k["w17_export_card_review_hints"]["WARNING"] = (
            "Export-time card is not automatically valid at test cutoff"
        )
        d = reviewed(generic=True)
        d["pair_reviews"][0]["fact_evidence_paths"] = [
            "old_world_contexts.2.context_examples[0]",
            "w17_export_card_review_hints.WARNING",
        ]
        with self.assertRaisesRegex(
            ValueError, "STRONG_PAIR_DECISION_REQUIRES_TWO_SOURCE_ANCHORS"
        ):
            valid_summary(k=k, d=d)

    def test_unknown_w17_card_warning_alias_still_rejected(self):
        k = kit()
        k["w17_export_card_review_hints"]["WARNING"] = (
            "Export-time card is not automatically valid at test cutoff"
        )
        d = reviewed()
        d["pair_reviews"][0]["fact_evidence_paths"].append(
            "w17_export_card_review_hints.UNKNOWN_WARNING"
        )
        with self.assertRaisesRegex(
            ValueError, "UNTRUSTED_OR_OUT_OF_SCOPE_EVIDENCE_PATH"
        ):
            valid_summary(k=k, d=d)

    def test_untrusted_evidence_path_rejected(self):
        d = reviewed()
        d["pair_reviews"][0]["fact_evidence_paths"] = ["secrets.API_KEY"]
        with self.assertRaisesRegex(ValueError, "UNTRUSTED_OR_OUT_OF_SCOPE"):
            valid_summary(d=d)

    def test_unanchored_clear_rejected(self):
        d = reviewed(generic=True)
        d["pair_reviews"][0]["fact_evidence_paths"] = ["w17_context"]
        with self.assertRaisesRegex(ValueError, "STRONG_PAIR_DECISION_REQUIRES"):
            valid_summary(d=d)

    def test_no_evidence_list_when_uncertain_rejected(self):
        d = reviewed()
        d["remaining_evidence_requirements"] = []
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REVIEW_MISSING"):
            valid_summary(d=d)

    def test_no_premature_seal_or_semantic_pass(self):
        d = reviewed()
        d["full_semantic_world_graph_gate"] = "PASS"
        with self.assertRaisesRegex(ValueError, "DECISION_FIELD_MISMATCH"):
            valid_summary(d=d)

    def test_bad_kit_hash_rejected(self):
        k = kit()
        d = reviewed()
        b = json.dumps(k).encode()
        d["reviewed_kit_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "PINNED_PRIVATE_KIT_SHA_MISMATCH"):
            m.validate(b, json.dumps(d).encode(), expected_kit_sha="b" * 64)

    def test_missing_previous_link_rejected(self):
        d = reviewed()
        d["known_04_07_graph_edge"] = "UNLINKED"
        with self.assertRaisesRegex(ValueError, "DECISION_FIELD_MISMATCH"):
            valid_summary(d=d)

    def test_positive_world_link_still_does_not_seal(self):
        d = reviewed()
        d["pair_reviews"][0]["decision"] = "WORLD_LINK"
        d["possible_transitive_link_to_w17"] = "YES"
        summary = valid_summary(d=d)
        self.assertEqual(summary["decision_counts"]["WORLD_LINK"], 1)
        self.assertEqual(summary["full_semantic_world_graph_gate"], "HOLD")


if __name__ == "__main__":
    unittest.main()

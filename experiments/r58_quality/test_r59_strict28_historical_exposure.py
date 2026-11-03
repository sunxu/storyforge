"""Synthetic-only tests for R59 Strict28 target/context exposure auditing."""
from __future__ import annotations

import hashlib
import unittest
from collections import Counter

from r59_strict28_historical_exposure import (
    PACKETS_SHA256,
    REVIEWER_B_SHA256,
    AuditHold,
    compare_one,
    normalize_for_ngrams,
    select_strict28,
    similarity,
    validate_contexts,
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scores():
    return {
        "chinese_prose": 4,
        "character_consistency": 4,
        "npc_initiative": 3,
        "player_agency": 4,
        "narrative_continuity": 4,
        "rule_fidelity": 4,
    }


class Strict28Tests(unittest.TestCase):
    def synthetic_reviews(self):
        packets = []
        packet_cases = []
        for i in range(192):
            packet_cases.append({
                "case_id": f"case-{i:03d}",
                "target_sha256": digest(f"target-{i}"),
            })
        for start in range(0, 192, 15):
            packets.append({
                "story_uuid": f"story-{start // 15:02d}",
                "cases": packet_cases[start:start + 15],
            })
        # The real frozen source has 13 story packets. Rebalance the final
        # packet count without changing the 192 unique synthetic identities.
        while len(packets) > 13:
            tail = packets.pop()
            packets[-1]["cases"].extend(tail["cases"])
        a_rows, b_rows = [], []
        for i, case in enumerate(packet_cases):
            selected = i < 31
            a_rows.append({
                **case,
                "case_level_scored_review_present": selected,
                "evidence_granularity": (
                    "CASE_LEVEL_SCORED_REVIEW" if selected else "AGGREGATE_COMPLEMENT_ONLY"
                ),
                "reported_final_decision": "PASS_ONLY" if selected else "HOLD",
                "scores_1_to_5": scores() if selected else None,
            })
            b_rows.append({
                **case,
                "decision": "PASS" if i < 28 or i >= 31 else "HOLD",
                "scores_1_to_5": scores() if i < 28 else None,
                "severe_flags": [],
            })
        exclusions = [{
            "target_sha256": digest(f"target-{i}"),
            "exclusion_reason": "EXCLUDED_FROM_TRAINING_DISAGREEMENT",
        } for i in range(31, 42)]
        reconciled = {
            "schema": "r58_gold192_reviewer_a_results_v3_reconciled_private_v1",
            "source_pins": {"packets": PACKETS_SHA256, "reviewer_b": REVIEWER_B_SHA256},
            "records": a_rows,
        }
        reviewer_b = {
            "schema": "r58_gold192_reviewer_b_results_v1",
            "cases": b_rows,
        }
        return reconciled, reviewer_b, exclusions, packets

    def test_selects_only_28_case_level_ab_passes_and_checks_exclusions(self):
        reconciled, reviewer_b, exclusions, packets = self.synthetic_reviews()
        selected = select_strict28(reconciled, reviewer_b, exclusions, packets)
        self.assertEqual(len(selected), 28)
        self.assertEqual(len({row["target_sha256"] for row in selected}), 28)
        self.assertFalse({row["target_sha256"] for row in selected}
                         & {row["target_sha256"] for row in exclusions})

    def test_nonempty_reviewer_b_severe_flags_fail_closed(self):
        reconciled, reviewer_b, exclusions, packets = self.synthetic_reviews()
        reviewer_b["cases"][0]["severe_flags"] = ["serious_player_agency"]
        with self.assertRaisesRegex(AuditHold, "STRICT_B_SEVERE_FLAGS_NOT_EMPTY"):
            select_strict28(reconciled, reviewer_b, exclusions, packets)

    def test_exact_history_and_last12_are_separately_detected(self):
        history = [
            {"role": "user", "content": "春日的长街上，远处传来钟声。"},
            {"role": "assistant", "content": "檐下的灯火随着风轻轻摇曳。"},
            {"role": "user", "content": "我停下脚步，望向街角。"},
        ]
        result = compare_one({"history": history}, [{
            "sample_id": "synthetic-row-1", "history": history,
        }])
        self.assertTrue(result["history_exact"])
        self.assertTrue(result["last12_exact"])
        self.assertTrue(result["near_candidate"])

    def test_ngram_similarity_ignores_whitespace_and_punctuation(self):
        left_text = (
            "春日的长街上，远处传来钟声。檐下灯火摇曳，行人渐渐散去。" * 12
        )
        right_text = (
            "春日的长街上 远处传来钟声 檐下灯火摇曳 行人渐渐散去 " * 12
        )
        left = [{"role": "user", "content": left_text}]
        right = [{"role": "user", "content": right_text}]
        self.assertEqual(normalize_for_ngrams(left), normalize_for_ngrams(right))
        jaccard, containment = similarity(left, right)
        self.assertEqual(jaccard, 1.0)
        self.assertEqual(containment, 1.0)

    def test_strict28_story_distribution_is_not_inferred_from_priority72(self):
        selected = []
        contexts = []
        for i in range(72):
            if i < 28:
                story_index = 0 if i < 20 else 1
                session_id = f"session-{story_index}"
                story_id = f"story-{story_index}"
            else:
                story_index = 2 + (i - 28) % 11
                session_id = f"session-{story_index}"
                story_id = f"story-{story_index}"
            target = f"target-{i}"
            row = {
                "case_id": f"case-{i:03d}", "target_sha256": digest(target),
                "target_assistant_text": target, "story_id": story_id,
                "session_id": session_id, "turn_index": 3,
                "history": [{"role": "user", "content": "past", "turn_index": 2}],
                "session_summary_used": False, "training_admitted": False,
                "story_draft_source": "CURRENT_V2_DATA_NOT_HISTORICAL",
            }
            contexts.append(row)
            if i < 28:
                selected.append({
                    "case_id": row["case_id"], "story_uuid": story_id,
                    "target_sha256": row["target_sha256"],
                })
        drafts = [{
            "story_id": f"story-{i}",
            "source_label": "CURRENT_V2_DATA_NOT_HISTORICAL",
        } for i in range(13)]
        result = validate_contexts(contexts, selected, drafts)
        self.assertEqual(len(result), 28)
        group_sizes = sorted(Counter(row["story_id"] for row in result.values()).values())
        self.assertEqual(group_sizes, [8, 20])
        self.assertEqual(len({row["session_id"] for row in result.values()}), 2)

    def test_context_future_leakage_is_rejected(self):
        selected = [{
            "case_id": "case-000", "story_uuid": "story-0",
            "target_sha256": digest("target-0"),
        }]
        context = {
            "case_id": "case-000", "target_sha256": digest("target-0"),
            "target_assistant_text": "target-0", "story_id": "story-0",
            "turn_index": 3,
            "history": [
                {"role": "assistant", "content": "future", "turn_index": 3},
                {"role": "user", "content": "past", "turn_index": 2},
            ],
            "session_summary_used": False, "training_admitted": False,
            "story_draft_source": "CURRENT_V2_DATA_NOT_HISTORICAL",
        }
        contexts = [context]
        for i in range(1, 72):
            contexts.append({
                "case_id": f"other-{i}", "target_sha256": digest(f"other-{i}"),
                "target_assistant_text": f"other-{i}", "story_id": f"draft-{i % 13}",
                "turn_index": 3,
                "history": [{"role": "user", "content": "past", "turn_index": 2}],
                "session_summary_used": False, "training_admitted": False,
                "story_draft_source": "CURRENT_V2_DATA_NOT_HISTORICAL",
            })
        drafts = [{"story_id": f"draft-{i}", "source_label": "CURRENT_V2_DATA_NOT_HISTORICAL"}
                  for i in range(13)]
        with self.assertRaisesRegex(AuditHold, "CONTEXT_FUTURE_LEAKAGE"):
            validate_contexts(contexts, selected, drafts)


if __name__ == "__main__":
    unittest.main()

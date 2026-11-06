"""R59 bounded Supabase extraction identity and safety tests. No DB/network required."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

try:
    from . import r60_gold192_supabase_extract_v3 as m
except ImportError:
    import r60_gold192_supabase_extract_v3 as m


SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


class R60Gold192ExtractV3Test(unittest.TestCase):
    def test_pilot_story_diversity(self):
        cases = [
            {"case_id": f"s{i}-t{n:05d}", "story_id": f"s{i}", "turn_index": n}
            for i in range(3) for n in (1, 900)
        ]
        selected = m.choose_pilot(cases, 5)
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({c["case_id"] for c in selected}), 5)
        self.assertEqual(len({c["story_id"] for c in selected}), 3)

    def test_exact_and_root_resolution(self):
        case = {"target_sha256": m.sha_text("目标")}
        self.assertEqual(m.decide_matches(case, [])[0], "SOURCE_NOT_FOUND")
        self.assertEqual(m.decide_matches(case, [{"content": "改变"}])[0],
                         "SOURCE_FOUND_BUT_CONTENT_CHANGED")
        exact = {"content": "目标", "parent_session_id": None, "session_id": "root"}
        fork = {"content": "目标", "parent_session_id": "root", "session_id": "fork"}
        self.assertEqual(m.decide_matches(case, [exact, fork]), ("EXACT_MATCH", exact))
        self.assertEqual(m.decide_matches(case, [fork, fork])[0], "IDENTITY_AMBIGUOUS")
        self.assertEqual(m.decide_matches(case, [exact, exact])[0], "IDENTITY_AMBIGUOUS")

    def test_exclusive_private_file_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "safe.json"
            digest = m.atomic_private_write(path, b"{}\n")
            self.assertEqual(digest, hashlib.sha256(b"{}\n").hexdigest())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                m.atomic_private_write(path, b"REPLACED")
            self.assertEqual(path.read_bytes(), b"{}\n")

    def test_scope_uses_only_case_scored_a_v3_pass_and_b_pass(self):
        cases = [
            {
                "case_id": f"s{i // 16}-t{i:05d}",
                "target_assistant_text": f"target {i}",
                "target_sha256": m.sha_text(f"target {i}"),
            }
            for i in range(192)
        ]
        packets = [
            {"story_uuid": f"uuid-{i}", "cases": cases[i * 16:(i + 1) * 16]}
            for i in range(12)
        ] + [{"story_uuid": "uuid-12", "cases": []}]
        indexed = m.index_packets(packets)

        a_records = []
        b_cases = []
        for i, case in enumerate(cases):
            if i < 31:
                granularity = "CASE_LEVEL_SCORED_REVIEW"
                decision, strict, scored, aggregate, scores = (
                    "PASS_ONLY", "PASS_ONLY", True, False, dict(SCORES)
                )
            elif i < 82:
                granularity = "CASE_ID_IN_EXPLICIT_HOLD_GROUP"
                decision, strict, scored, aggregate, scores = (
                    "HOLD", "HOLD", False, False, None
                )
            elif i == 82:
                granularity = "CASE_ID_IN_EXPLICIT_REJECT_GROUP"
                decision, strict, scored, aggregate, scores = (
                    "REJECT", "REJECT", False, False, None
                )
            else:
                granularity = "AGGREGATE_COMPLEMENT_ONLY"
                decision, strict, scored, aggregate, scores = (
                    "PASS_ONLY", None, False, True, None
                )
            a_records.append({
                "case_id": case["case_id"],
                "target_sha256": case["target_sha256"],
                "reported_final_decision": decision,
                "decision_for_strict_ab_decision_comparison": strict,
                "evidence_granularity": granularity,
                "case_level_scored_review_present": scored,
                "aggregate_complement_only": aggregate,
                "scores_1_to_5": scores,
            })
            b_decision = "PASS" if i < 178 else "HOLD" if i < 190 else "REJECT"
            b_cases.append({
                "target_sha256": case["target_sha256"],
                "decision": b_decision,
                "blind_case_id": f"blind-{i:03d}",
            })

        a = {
            "schema": m.A_SCHEMA,
            "status": m.A_STATUS,
            "source_pins": dict(m.A_SOURCE_PINS),
            "records": a_records,
        }
        b = {
            "schema": m.B_SCHEMA,
            "counts": dict(m.B_COUNTS),
            "cases": b_cases,
        }
        exclusions = [
            {
                "target_sha256": case["target_sha256"],
                "exclusion_reason": "EXCLUDED_FROM_TRAINING_DISAGREEMENT",
            }
            for case in cases[:7] + cases[100:104]
        ]

        selected = m.select_candidates(a, b, exclusions, indexed)
        self.assertEqual(len(selected), 24)
        selected_ids = {case["case_id"] for case in selected}
        self.assertTrue({case["case_id"] for case in cases[7:31]} <= selected_ids)
        self.assertFalse({case["case_id"] for case in cases[31:]} & selected_ids)
        self.assertEqual(len(m.choose_pilot(selected, 0)), 24)

        # A legacy field cannot upgrade an aggregate-complement PASS into
        # strict case-level evidence.
        a["records"][100]["decision_for_strict_ab_pairing"] = "PASS_ONLY"
        selected_with_legacy_alias = m.select_candidates(a, b, exclusions, indexed)
        self.assertEqual(
            {case["case_id"] for case in selected_with_legacy_alias}, selected_ids
        )

        a["records"][7]["case_id"] = "other-case"
        with self.assertRaisesRegex(ValueError, "REVIEW_CASE_ID_MISMATCH"):
            m.select_candidates(a, b, exclusions, indexed)

    def test_rejects_superseded_a_schema(self):
        report = {
            "schema": "superseded-r59-a-schema",
            "status": m.A_STATUS,
            "source_pins": dict(m.A_SOURCE_PINS),
            "records": [],
        }
        with self.assertRaisesRegex(ValueError, "CANONICAL_A_V3_REQUIRED"):
            m.select_candidates(report, {}, [], {})


if __name__ == "__main__":
    unittest.main()

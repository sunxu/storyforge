"""Synthetic regression tests for read-only historical context recovery."""
import unittest
from datetime import datetime, timezone

from storyforge_gold_quality import history_recovery as h


def dt(seconds):
    return datetime(2026, 1, 1, 0, 0, seconds, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self):
        self.rows = []
        self.one = None
        self.sessions = {
            "child": {
                "session_id": "child", "parent_session_id": "parent",
                "forked_from_turn": 3, "memory_summary": "child pretarget summary",
                "recent_summary": "", "rolling_outline": "",
                "last_summary_turn": 2, "last_extract_turn": 2,
                "updated_at": dt(5), "created_at": dt(4),
                "summary_source_end_index": 5,
                "summary_source_dependency_end_index": None,
                "summary_text_end_index": 5, "summary_legacy_text_end_index": 5,
            },
            "parent": {
                "session_id": "parent", "parent_session_id": None,
                "forked_from_turn": None, "memory_summary": "parent pretarget summary",
                "recent_summary": "recent", "rolling_outline": "outline",
                "last_summary_turn": 5, "last_extract_turn": 5,
                "updated_at": dt(5), "created_at": dt(1),
                "summary_source_end_index": 5,
                "summary_source_dependency_end_index": 5,
                "summary_text_end_index": 5, "summary_legacy_text_end_index": 5,
            },
        }
        self.target = {
            "message_id": "target-id", "story_id": "story-a",
            "session_id": "child", "turn_index": 7, "role": "assistant",
            "content": "exact target", "status": "completed", "created_at": dt(10),
        }
        self.messages = [
            self.msg("p1", "parent", 1, "user", "parent user", 1),
            self.msg("p2", "parent", 2, "assistant", "parent assistant", 2),
            self.msg("p5", "parent", 5, "user", "fork point user", 3),
            self.msg("c1", "child", 1, "user", "parent user", 1),
            self.msg("c2", "child", 2, "assistant", "parent assistant", 2),
            self.msg("c5", "child", 5, "user", "fork point user", 3),
            self.msg("c6", "child", 6, "user", "current user", 4),
            self.target,
            self.msg("c8", "child", 8, "assistant", "future assistant", 11),
        ]
        self.content_version = {
            "id": 1, "content_revision": 3, "title": "Historical title",
            "description": "description", "tags": [], "v2_data": {"world": "past"},
            "source": "before_update", "source_updated_at": dt(4), "archived_at": dt(6),
        }
        self.admin_version = {
            "id": "admin-1", "content": {"characters": []},
            "created_at": dt(3), "updated_at": dt(7),
        }

    @staticmethod
    def msg(mid, sid, turn, role, content, seconds):
        return {
            "message_id": mid, "story_id": "story-a", "session_id": sid,
            "turn_index": turn, "role": role, "content": content,
            "status": "completed", "created_at": dt(seconds),
        }

    def execute(self, query, params=()):
        self.rows, self.one = [], None
        if "FROM public.story_v2_sessions" in query:
            self.one = self.sessions.get(params[1])
        elif "FROM public.v2_chat_messages" in query and "AND role = 'assistant'" in query:
            self.rows = [self.target] if params[1] == "child" and params[2] == 7 else []
        elif "FROM public.v2_chat_messages" in query:
            story_id, session_id, cutoff, target_time = params
            self.rows = [
                row for row in self.messages
                if row["story_id"] == story_id and row["session_id"] == session_id
                and row["turn_index"] <= cutoff and row["created_at"] < target_time
                and row["role"] in {"user", "assistant"}
            ]
            self.rows.sort(key=lambda row: (row["created_at"], row["message_id"]))
        elif "FROM public.story_content_versions" in query:
            self.one = self.content_version
        elif "FROM public.story_admin_versions" in query:
            self.one = self.admin_version
        else:
            raise AssertionError("unexpected query")

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.one


class HistoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.cursor = FakeCursor()
        self.case = {
            "case_id": "story-a-t00007", "story_id": "story-a",
            "session_id": "child", "turn_index": 7,
            "target_sha256": h.sha256_text("exact target"),
        }

    def test_reconstructs_materialized_fork_history_and_pre_target_versions(self):
        result = h.recover_case(self.cursor, self.case)
        self.assertEqual([x["message_id"] for x in result["history"]],
                         ["c1", "c2", "c5", "c6"])
        self.assertEqual(result["history"][-1]["role"], "user")
        self.assertEqual(len(result["session_lineage"]), 2)
        self.assertEqual(result["session_lineage"][0]["session_id"], "child")
        self.assertEqual(result["session_lineage"][1]["session_id"], "parent")
        self.assertEqual(result["session_lineage"][0]["forked_from_turn_story_turn"], 3)
        self.assertEqual(len(result["pretarget_summaries"]), 1)
        self.assertEqual(result["pretarget_summaries"][0]["session_id"], "child")
        self.assertEqual(result["story_content_version_status"], "PRETARGET_VERSION_FOUND")
        self.assertEqual(result["story_admin_version_status"], "PRETARGET_VERSION_FOUND")
        self.assertFalse(result["historical_system_prompt_verified"])
        self.assertFalse(result["training_admitted"])

    def test_target_hash_mismatch_holds(self):
        self.case["target_sha256"] = "0" * 64
        with self.assertRaisesRegex(h.HistoryRecoveryError, "TARGET_MESSAGE_IDENTITY_AMBIGUOUS"):
            h.recover_case(self.cursor, self.case)

    def test_failed_target_holds(self):
        self.cursor.target["status"] = "failed"
        with self.assertRaisesRegex(h.HistoryRecoveryError, "TARGET_MESSAGE_NOT_COMPLETED"):
            h.recover_case(self.cursor, self.case)

    def test_parent_fork_cutoff_excludes_parent_future_turns(self):
        self.cursor.messages.append(
            self.cursor.msg("p6", "parent", 6, "assistant", "after fork", 6)
        )
        result = h.recover_case(self.cursor, self.case)
        self.assertNotIn("p6", [x["message_id"] for x in result["history"]])
        self.assertNotIn("p1", [x["message_id"] for x in result["history"]])

    def test_summary_updated_after_target_is_not_used(self):
        self.cursor.sessions["child"]["updated_at"] = dt(12)
        result = h.recover_case(self.cursor, self.case)
        self.assertEqual(result["pretarget_summaries"], [])
        self.assertEqual(result["summary_status"], "NO_VERIFIED_PRETARGET_SUMMARY")

    def test_summary_cutoff_after_fork_is_not_used(self):
        self.cursor.sessions["child"]["summary_source_end_index"] = 7
        result = h.recover_case(self.cursor, self.case)
        self.assertEqual(result["pretarget_summaries"], [])

    def test_lineage_cycle_holds(self):
        self.cursor.sessions["parent"]["parent_session_id"] = "child"
        with self.assertRaisesRegex(h.HistoryRecoveryError, "SESSION_LINEAGE_CYCLE"):
            h.recover_case(self.cursor, self.case)

    def test_history_limit_fails_without_truncation(self):
        with self.assertRaisesRegex(h.HistoryRecoveryError, "HISTORY_LIMIT_EXCEEDED"):
            h.recover_case(self.cursor, self.case, max_history=3)

    def test_timestamp_comparison_normalizes_timezone_offsets(self):
        earlier = "2026-01-01T01:00:00+01:00"
        later = "2026-01-01T00:30:00+00:00"
        self.assertTrue(h._before(earlier, later))
        self.assertFalse(h._before(later, earlier))

    def test_naive_timestamp_is_rejected(self):
        self.cursor.target["created_at"] = datetime(2026, 1, 1)
        with self.assertRaisesRegex(h.HistoryRecoveryError, "DATABASE_TIMESTAMP_TIMEZONE_MISSING"):
            h.recover_case(self.cursor, self.case)

    def test_duplicate_case_set_fails(self):
        with self.assertRaisesRegex(h.HistoryRecoveryError, "CASE_SET_DUPLICATE"):
            h.recover_cases(self.cursor, [self.case, self.case])


if __name__ == "__main__":
    unittest.main()

"""Synthetic regression tests for read-only historical context recovery."""
import unittest
from datetime import UTC, datetime

from storyforge_gold_quality import history_recovery as h


def dt(seconds):
    return datetime(2026, 1, 1, 0, 0, seconds, tzinfo=UTC)


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
        self.ledger_events = [
            self.ledger_marker(1, "c1", 1, "user", 1),
            self.ledger_marker(2, "c2", 2, "assistant", 2),
            self.ledger_marker(3, "c5", 5, "user", 3),
            self.ledger_marker(4, "c6", 6, "user", 4),
            self.ledger_marker(5, "target-id", 7, "assistant", 10),
        ]

    @staticmethod
    def msg(mid, sid, turn, role, content, seconds):
        return {
            "message_id": mid, "story_id": "story-a", "session_id": sid,
            "turn_index": turn, "role": role, "content": content,
            "status": "completed", "created_at": dt(seconds),
            "mutation_revision": 0,
        }

    @staticmethod
    def ledger_marker(event_id, message_id, turn, role, seconds):
        return {
            "id": event_id, "message_id": message_id, "story_id": "story-a",
            "session_id": "child", "role": role, "turn_index": turn,
            "operation": "insert", "row_data": {"_ledger_event": "marker_v1"},
            "recorded_at": dt(seconds),
        }

    @staticmethod
    def ledger_snapshot(event_id, message_id, turn, role, operation, seconds,
                        content, revision=0):
        return {
            "id": event_id, "message_id": message_id, "story_id": "story-a",
            "session_id": "child", "role": role, "turn_index": turn,
            "operation": operation,
            "row_data": {
                "id": message_id, "story_id": "story-a", "session_id": "child",
                "turn_index": turn, "role": role, "content": content,
                "status": "completed", "created_at": dt(seconds - 10).isoformat(),
                "mutation_revision": revision,
            },
            "recorded_at": dt(seconds),
        }

    def execute(self, query, params=()):
        self.rows, self.one = [], None
        if "WHERE id = ANY(%s)" in query:
            ids = set(params[0])
            self.rows = [
                {"id": event["id"], "row_data": event["row_data"]}
                for event in self.ledger_events if event["id"] in ids
            ]
        elif "FROM public.v2_chat_message_ledger" in query:
            story_id, session_id, max_turn, limit = params
            self.rows = []
            for source in self.ledger_events:
                if (source["story_id"] == story_id
                        and source["session_id"] == session_id
                        and 1 <= source["turn_index"] <= max_turn):
                    event = dict(source)
                    if event["operation"] in {"update_before", "delete"}:
                        event["row_data"] = None
                    self.rows.append(event)
            self.rows = self.rows[:limit]
        elif "FROM public.story_v2_sessions" in query:
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
        self.assertFalse(
            result["history_reconstruction"]["ledger_commit_order_verified"]
        )
        self.assertFalse(
            result["history_reconstruction"]["ledger_trigger_continuity_verified"]
        )

    def test_per_case_suffix_diagnostic_reports_recovered_case(self):
        results = h.diagnose_history_suffixes(self.cursor, [self.case])
        self.assertEqual(results, [{
            "safe_index": 0,
            "result": "RECOVERED",
            "history_message_count": 4,
            "history_suffix_role": "user",
            "ledger_event_count": 5,
            "history_rows_restored": 0,
            "history_rows_excluded": 0,
            "current_history_suffix_role": "user",
            "current_suffix_first_post_target_operation": None,
            "first_post_target_operation_counts": {},
            "excluded_rows_with_preboundary_snapshot": 0,
            "excluded_rows_without_preboundary_snapshot": 0,
            "excluded_rows_prior_snapshot_same_timestamp_as_boundary": 0,
        }])

    def test_per_case_suffix_diagnostic_identifies_marker_exclusion(self):
        self.cursor.ledger_events.extend([
            self.cursor.ledger_marker(6, "c5", 5, "user", 11),
            self.cursor.ledger_marker(7, "c6", 6, "user", 12),
        ])
        self.cursor.ledger_events[-2]["operation"] = "update_after"
        self.cursor.ledger_events[-1]["operation"] = "update_after"
        results = h.diagnose_history_suffixes(self.cursor, [self.case])
        self.assertEqual(results, [{
            "safe_index": 0,
            "result": "HOLD",
            "reason_code": "HISTORY_SUFFIX_NOT_USER",
            "current_history_message_count": 4,
            "current_history_suffix_role": "user",
            "current_history_suffix_turn": 6,
            "reconstructed_history_message_count": 2,
            "history_suffix_role": "assistant",
            "history_suffix_turn": 2,
            "current_suffix_first_post_target_operation": "update_after",
            "ledger_event_count": 7,
            "history_rows_restored": 0,
            "history_rows_excluded": 2,
            "first_post_target_operation_counts": {"update_after": 2},
            "excluded_rows_with_preboundary_snapshot": 0,
            "excluded_rows_without_preboundary_snapshot": 2,
            "excluded_rows_prior_snapshot_same_timestamp_as_boundary": 0,
        }])

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

    def test_legacy_null_summary_indexes_are_not_accepted(self):
        self.cursor.sessions["child"]["summary_source_end_index"] = None
        result = h.recover_case(self.cursor, self.case)
        self.assertEqual(result["pretarget_summaries"], [])

    def test_dependency_cutoff_after_target_is_not_accepted(self):
        self.cursor.sessions["child"]["summary_source_dependency_end_index"] = 7
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

    def test_history_edit_after_target_uses_ledger_before_image(self):
        current = next(row for row in self.cursor.messages if row["message_id"] == "c1")
        current["content"] = "edited after target"
        current["mutation_revision"] = 1
        self.cursor.ledger_events.extend([
            self.cursor.ledger_snapshot(
                6, "c1", 1, "user", "update_before", 11, "parent user"
            ),
            self.cursor.ledger_marker(7, "c1", 1, "user", 11),
        ])
        result = h.recover_case(self.cursor, self.case)
        first = next(row for row in result["history"] if row["message_id"] == "c1")
        self.assertEqual(first["content"], "parent user")
        self.assertEqual(
            result["history_reconstruction"]["history_rows_restored_from_snapshot"], 1
        )
        self.assertEqual(
            result["history_reconstruction"]["ledger_detail_rows_loaded"], 2
        )

    def test_history_deleted_after_target_uses_ledger_delete_snapshot(self):
        self.cursor.messages = [
            row for row in self.cursor.messages if row["message_id"] != "c1"
        ]
        self.cursor.ledger_events.append(
            self.cursor.ledger_snapshot(
                6, "c1", 1, "user", "delete", 11, "parent user"
            )
        )
        result = h.recover_case(self.cursor, self.case)
        self.assertIn("c1", {row["message_id"] for row in result["history"]})

    def test_negative_current_mutation_revision_holds(self):
        current = next(row for row in self.cursor.messages if row["message_id"] == "c1")
        current["mutation_revision"] = -1
        with self.assertRaisesRegex(
            h.HistoryRecoveryError, "LEDGER_MUTATION_REVISION_INVALID"
        ):
            h.recover_case(self.cursor, self.case)

    def test_batch_prefetches_target_and_recovers_through_shared_ledger(self):
        results = h.recover_cases(self.cursor, [self.case])
        self.assertEqual(len(results), 1)
        self.assertEqual(
            [row["message_id"] for row in results[0]["history"]],
            ["c1", "c2", "c5", "c6"],
        )
        self.assertEqual(
            results[0]["history_reconstruction"]["ledger_event_count"], 5
        )

    def test_duplicate_case_set_fails(self):
        with self.assertRaisesRegex(h.HistoryRecoveryError, "CASE_SET_DUPLICATE"):
            h.recover_cases(self.cursor, [self.case, self.case])


if __name__ == "__main__":
    unittest.main()

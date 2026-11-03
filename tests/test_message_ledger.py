"""Synthetic regression tests for sparse v2 message-ledger reconstruction."""
import unittest
from datetime import UTC, datetime

from storyforge_gold_quality import message_ledger as ledger


def dt(seconds):
    return datetime(2026, 1, 1, 0, 0, seconds, tzinfo=UTC)


class FakeCursor:
    def __init__(self, events):
        self.events = events
        self.rows = []
        self.query = ""
        self.params = ()

    def execute(self, query, params=()):
        self.query = query
        self.params = params
        if "WHERE id = ANY(%s)" in query:
            ids = set(params[0])
            self.rows = [
                {"id": event["id"], "row_data": event["row_data"]}
                for event in self.events if event["id"] in ids
            ]
            return
        story_id, session_id, max_turn, limit = params
        self.rows = []
        for source in self.events:
            if (source["story_id"] == story_id
                    and source["session_id"] == session_id
                    and source["turn_index"] <= max_turn):
                event = dict(source)
                if event["operation"] in ledger.SNAPSHOTS:
                    event["row_data"] = None
                self.rows.append(event)
        self.rows = self.rows[:limit]

    def fetchall(self):
        return list(self.rows)


def marker(event_id, message_id, session, turn, role, operation, seconds):
    return {
        "id": event_id, "message_id": message_id, "story_id": "story",
        "session_id": session, "role": role, "turn_index": turn,
        "operation": operation, "row_data": {"_ledger_event": "marker_v1"},
        "recorded_at": dt(seconds),
    }


def snapshot(event_id, message_id, session, turn, role, operation, seconds,
             *, content="old", revision=0, status="completed"):
    data = {
        "id": message_id, "story_id": "story", "session_id": session,
        "turn_index": turn, "role": role, "content": content,
        "status": status, "created_at": dt(turn).isoformat(),
        "mutation_revision": revision,
    }
    return {
        "id": event_id, "message_id": message_id, "story_id": "story",
        "session_id": session, "role": role, "turn_index": turn,
        "operation": operation, "row_data": data, "recorded_at": dt(seconds),
    }


def current(message_id, session, turn, role, content, revision=0):
    return {
        "message_id": message_id, "story_id": "story", "session_id": session,
        "turn_index": turn, "role": role, "content": content,
        "status": "completed", "created_at": dt(turn).isoformat(),
        "mutation_revision": revision, "lineage_depth": 0,
    }


class MessageLedgerTests(unittest.TestCase):
    def setUp(self):
        self.target = {
            "message_id": "target", "story_id": "story", "session_id": "s",
            "turn_index": 5, "role": "assistant", "created_at": dt(10),
        }
        self.events = [
            marker(1, "u1", "s", 1, "user", "insert", 1),
            marker(2, "a2", "s", 2, "assistant", "insert", 2),
            marker(3, "u3", "s", 3, "user", "insert", 3),
            marker(4, "target", "s", 5, "assistant", "insert", 10),
        ]

    def test_query_is_session_scoped_and_capped(self):
        cursor = FakeCursor(self.events)
        rows = ledger.load_session_events(cursor, "story", "s", 5, [self.target], max_events=20)
        self.assertEqual(len(rows), 4)
        self.assertIn("WHERE story_id = %s AND session_id = %s", cursor.query)
        self.assertEqual(cursor.params, ("story", "s", 5, 21))

    def test_edited_after_target_uses_first_update_before_snapshot(self):
        events = self.events + [
            snapshot(5, "u1", "s", 1, "user", "update_before", 11),
            marker(6, "u1", "s", 1, "user", "update_after", 11),
        ]
        rows, report = ledger.reconstruct_history(
            [current("u1", "s", 1, "user", "edited", 1),
             current("a2", "s", 2, "assistant", "reply"),
             current("u3", "s", 3, "user", "next")],
            events, self.target, "story", "s", 4,
        )
        by_id = {row["message_id"]: row for row in rows}
        self.assertEqual(by_id["u1"]["content"], "old")
        self.assertEqual(report["history_rows_restored_from_snapshot"], 1)

    def test_deleted_after_target_is_restored_from_delete_snapshot(self):
        events = self.events + [
            snapshot(5, "u1", "s", 1, "user", "delete", 11),
        ]
        rows, report = ledger.reconstruct_history(
            [current("a2", "s", 2, "assistant", "reply"),
             current("u3", "s", 3, "user", "next")],
            events, self.target, "story", "s", 4,
        )
        self.assertEqual({row["message_id"] for row in rows}, {"u1", "a2", "u3"})
        self.assertEqual(report["history_rows_restored_from_snapshot"], 1)

    def test_message_inserted_after_target_is_excluded(self):
        events = self.events + [
            marker(5, "late", "s", 4, "user", "insert", 11),
        ]
        rows, report = ledger.reconstruct_history(
            [current("u1", "s", 1, "user", "first"),
             current("a2", "s", 2, "assistant", "reply"),
             current("u3", "s", 3, "user", "next"),
             current("late", "s", 4, "user", "late")],
            events, self.target, "story", "s", 4,
        )
        self.assertNotIn("late", {row["message_id"] for row in rows})
        self.assertEqual(report["history_rows_excluded_by_post_target_marker"], 1)

    def test_first_update_after_marker_excludes_streaming_placeholder(self):
        events = self.events + [
            marker(5, "stream", "s", 4, "assistant", "update_after", 11),
        ]
        rows, _ = ledger.reconstruct_history(
            [current("u1", "s", 1, "user", "first"),
             current("a2", "s", 2, "assistant", "reply"),
             current("u3", "s", 3, "user", "next"),
             current("stream", "s", 4, "assistant", "generated", 1)],
            events, self.target, "story", "s", 4,
        )
        self.assertNotIn("stream", {row["message_id"] for row in rows})

    def test_unlogged_mutation_revision_mismatch_holds(self):
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_MUTATION_REVISION_MISMATCH"
        ):
            ledger.reconstruct_history(
                [current("u1", "s", 1, "user", "changed", 1),
                 current("a2", "s", 2, "assistant", "reply"),
                 current("u3", "s", 3, "user", "next")],
                self.events, self.target, "story", "s", 4,
            )

    def test_event_limit_fails_closed(self):
        cursor = FakeCursor(self.events)
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_SESSION_EVENT_LIMIT_EXCEEDED"
        ):
            ledger.load_session_events(cursor, "story", "s", 5, max_events=2)

    def test_missing_target_boundary_holds(self):
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "TARGET_LEDGER_BOUNDARY_MISSING"
        ):
            ledger.target_boundary(self.events[:3], self.target)

    def test_incomplete_snapshot_holds(self):
        bad = snapshot(5, "u1", "s", 1, "user", "delete", 11)
        del bad["row_data"]["mutation_revision"]
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_SNAPSHOT_FIELDS_INCOMPLETE"
        ):
            ledger.reconstruct_history(
                [], self.events[:3] + [bad, self.events[3]],
                self.target, "story", "s", 4,
            )


if __name__ == "__main__":
    unittest.main()

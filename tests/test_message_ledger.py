"""Synthetic regression tests for sparse v2 message-ledger reconstruction."""
import unittest
from datetime import UTC, datetime, timedelta

from storyforge_gold_quality import message_ledger as ledger


def dt(seconds):
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds)


class FakeCursor:
    def __init__(self, events):
        self.events = events
        self.rows = []
        self.query = ""
        self.params = ()
        self.queries = []
        self.query_params = []

    def execute(self, query, params=()):
        self.query = query
        self.params = params
        self.queries.append(query)
        self.query_params.append(params)
        if "WHERE id = ANY(%s)" in query:
            ids = set(params[0])
            self.rows = [
                {"id": event["id"], "row_data": event["row_data"]}
                for event in self.events if event["id"] in ids
            ]
            return
        story_id, session_id, max_turn = params[:3]
        if len(params) == 4:
            last_key = None
            limit = params[3]
        else:
            last_key = (params[3], params[4])
            limit = params[5]
        self.rows = []
        for source in self.events:
            if (source["story_id"] == story_id
                    and source["session_id"] == session_id
                    and 1 <= source["turn_index"] <= max_turn
                    and (last_key is None or
                         (source["recorded_at"], source["id"]) > last_key)):
                event = dict(source)
                if event["operation"] in ledger.SNAPSHOTS:
                    event["row_data"] = None
                self.rows.append(event)
        self.rows.sort(key=lambda event: (event["recorded_at"], event["id"]))
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

    def test_indexed_reconstruction_matches_legacy_reconstruction(self):
        events = list(self.events) + [
            snapshot(5, "u1", "s", 1, "user", "update_before", 11, content="old user"),
            marker(6, "u1", "s", 1, "user", "update_after", 11),
            marker(7, "future", "s", 9, "user", "insert", 12),
        ]
        rows = [
            current("u1", "s", 1, "user", "current user"),
            current("a2", "s", 2, "assistant", "current assistant"),
            current("u3", "s", 3, "user", "current third"),
        ]
        index = ledger.LedgerEventIndex(events)
        plain, plain_report = ledger.reconstruct_history(
            rows, events, self.target, "story", "s", 4
        )
        indexed, indexed_report = ledger.reconstruct_history(
            rows, events, self.target, "story", "s", 4, event_index=index
        )
        self.assertEqual(indexed, plain)
        self.assertEqual(indexed_report, plain_report)

    def test_event_index_target_boundary_and_cutoff(self):
        events = list(self.events) + [
            marker(5, "u1", "s", 9, "user", "update_after", 11),
            marker(6, "u1", "s", 1, "user", "update_after", 12),
        ]
        index = ledger.LedgerEventIndex(events)
        boundary = index.target_boundary(self.target)
        first = index.first_post_boundary_event("u1", ledger._key(boundary), 4)
        self.assertIsNotNone(first)
        self.assertEqual(first["id"], 6)

    def test_query_is_session_scoped_and_capped(self):
        cursor = FakeCursor(self.events)
        rows = ledger.load_session_events(cursor, "story", "s", 5, [self.target], max_events=20)
        self.assertEqual(len(rows), 4)
        self.assertIn("WHERE story_id = %s AND session_id = %s", cursor.queries[0])
        self.assertEqual(cursor.query_params[0], ("story", "s", 5, 21))
        self.assertIn("WHERE id = ANY(%s)", cursor.queries[1])

    def test_nonpositive_turn_events_are_outside_positive_turn_query(self):
        events = self.events + [
            marker(5, "archived-user", "s", -3, "user", "update_after", 11),
            snapshot(6, "archived-assistant", "s", -4, "assistant",
                     "update_before", 12),
            marker(7, "turn-zero", "s", 0, "user", "insert", 13),
        ]
        cursor = FakeCursor(events)
        rows = ledger.load_session_events(
            cursor, "story", "s", 5, [self.target], max_events=20
        )
        self.assertEqual([row["id"] for row in rows], [1, 2, 3, 4])
        self.assertIn("turn_index BETWEEN 1 AND %s", cursor.queries[0])
        self.assertEqual(cursor.query_params[0], ("story", "s", 5, 21))

    def test_nonpositive_locator_direct_validation_still_holds(self):
        for value in (0, -3, -999):
            with self.subTest(turn_index=value):
                bad = marker(10, "bad", "s", value, "user", "update_after", 11)
                with self.assertRaisesRegex(
                    ledger.LedgerRecoveryError,
                    "LEDGER_EVENT_TURN_INDEX_NONPOSITIVE",
                ):
                    ledger._validate_event_locator(bad, "story", "s")

    def test_legacy_full_insert_target_marker_is_accepted(self):
        events = list(self.events)
        old = events[-1].copy()
        legacy = {
            "id": "target", "story_id": "story", "session_id": "s",
            "turn_index": 5, "role": "assistant", "content": "old reply",
            "status": "completed", "created_at": dt(10).isoformat(),
        }
        old["row_data"] = legacy  # Historical schema has no mutation_revision.
        events[-1] = old
        rows = ledger.load_session_events(
            FakeCursor(events), "story", "s", 5, [self.target], max_events=20
        )
        self.assertEqual(
            ledger._validate_business_event_detail(rows[-1]),
            "LEGACY_FULL_AFTER_IMAGE",
        )

    def test_legacy_full_update_after_is_accepted(self):
        events = self.events + [
            marker(5, "u1", "s", 1, "user", "update_after", 11)
        ]
        events[-1]["row_data"] = {
            "id": "u1", "story_id": "story", "session_id": "s",
            "turn_index": 1, "role": "user", "content": "historical text",
            "status": "completed", "created_at": dt(1).isoformat(),
        }
        rows = ledger.load_session_events(
            FakeCursor(events), "story", "s", 5, [self.target], max_events=20
        )
        self.assertEqual(
            ledger._validate_business_event_detail(rows[-1]),
            "LEGACY_FULL_AFTER_IMAGE",
        )

    def test_legacy_detail_mismatched_identity_is_rejected(self):
        bad = marker(4, "target", "s", 5, "assistant", "insert", 10)
        bad["row_data"] = {
            "id": "other", "story_id": "story", "session_id": "s",
            "turn_index": 5, "role": "assistant", "content": "x",
            "status": "completed", "created_at": dt(10).isoformat(),
        }
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_LEGACY_DETAIL_IDENTITY_MISMATCH"
        ):
            ledger._validate_business_event_detail(bad)

    def test_legacy_detail_incomplete_is_rejected(self):
        bad = marker(4, "target", "s", 5, "assistant", "insert", 10)
        bad["row_data"] = {"id": "target", "content": "x"}
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_LEGACY_DETAIL_FIELDS_INVALID"
        ):
            ledger._validate_business_event_detail(bad)

    def test_unknown_sparse_marker_version_is_rejected(self):
        bad = marker(4, "target", "s", 5, "assistant", "insert", 10)
        bad["row_data"] = {"_ledger_event": "marker_v2"}
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_MARKER_INVALID"
        ):
            ledger._validate_business_event_detail(bad)

    def test_large_snapshot_jsonb_is_loaded_only_for_first_post_target_event(self):
        events = self.events + [
            snapshot(5, "u1", "s", 1, "user", "update_before", 11),
            marker(6, "u1", "s", 1, "user", "update_after", 11),
            snapshot(7, "u1", "s", 1, "user", "update_before", 12,
                     content="intermediate", revision=1),
        ]
        cursor = FakeCursor(events)
        rows = ledger.load_session_events(
            cursor, "story", "s", 5, [self.target], max_events=20
        )
        by_id = {event["id"]: event for event in rows}
        self.assertEqual(by_id[5]["row_data"]["content"], "old")
        self.assertIsNone(by_id[7]["row_data"])
        self.assertNotIn("row_data", cursor.queries[0])
        self.assertIn("WHERE id = ANY(%s)", cursor.queries[1])
        self.assertEqual(cursor.query_params[1], ([4, 5],))

    def test_snapshot_fetch_missing_row_holds(self):
        class MissingSnapshotCursor(FakeCursor):
            def execute(self, query, params=()):
                super().execute(query, params)
                if "WHERE id = ANY(%s)" in query:
                    self.rows = []

        events = self.events + [
            snapshot(5, "u1", "s", 1, "user", "update_before", 11)
        ]
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_DETAIL_MISSING"
        ):
            ledger.load_session_events(
                MissingSnapshotCursor(events), "story", "s", 5,
                [self.target], max_events=20,
            )

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

    def test_negative_current_mutation_revision_holds(self):
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_MUTATION_REVISION_INVALID"
        ):
            ledger.reconstruct_history(
                [current("u1", "s", 1, "user", "changed", -1),
                 current("a2", "s", 2, "assistant", "reply"),
                 current("u3", "s", 3, "user", "next")],
                self.events, self.target, "story", "s", 4,
            )

    def test_invalid_locator_fields_have_safe_specific_reasons(self):
        cases = [
            ("message_id", None, "LEDGER_EVENT_MESSAGE_ID_INVALID"),
            ("story_id", "other-story", "LEDGER_EVENT_STORY_ID_MISMATCH"),
            ("session_id", "other-session", "LEDGER_EVENT_SESSION_ID_MISMATCH"),
            ("turn_index", 0, "LEDGER_EVENT_TURN_INDEX_NONPOSITIVE"),
            ("turn_index", "1", "LEDGER_EVENT_TURN_INDEX_TYPE_INVALID"),
            ("operation", "unknown", "LEDGER_EVENT_OPERATION_INVALID"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field, reason=reason):
                event = dict(self.events[0])
                event[field] = value
                with self.assertRaisesRegex(ledger.LedgerRecoveryError, reason):
                    ledger._validate_event_locator(event, "story", "s")

    def test_legacy_snapshot_without_mutation_revision_is_accepted_and_reported(self):
        events = self.events + [
            snapshot(5, "u1", "s", 1, "user", "update_before", 11),
            marker(6, "u1", "s", 1, "user", "update_after", 11),
        ]
        del events[-2]["row_data"]["mutation_revision"]
        rows, report = ledger.reconstruct_history(
            [current("u1", "s", 1, "user", "edited", 1),
             current("a2", "s", 2, "assistant", "reply"),
             current("u3", "s", 3, "user", "next")],
            events, self.target, "story", "s", 4,
        )
        self.assertEqual(
            next(row for row in rows if row["message_id"] == "u1")["content"],
            "old",
        )
        self.assertEqual(
            report["history_rows_restored_from_legacy_snapshot_without_revision"], 1
        )
        self.assertEqual(
            report["mutation_revision_evidence_state"],
            "LEGACY_SNAPSHOT_REVISION_UNAVAILABLE",
        )

    def test_non_revision_ledger_updates_do_not_increment_revision_assumption(self):
        events = self.events + [
            marker(5, "u1", "s", 1, "user", "update_after", 4),
            marker(6, "u1", "s", 1, "user", "update_after", 5),
        ]
        rows, report = ledger.reconstruct_history(
            [current("u1", "s", 1, "user", "current", 0),
             current("a2", "s", 2, "assistant", "reply"),
             current("u3", "s", 3, "user", "next")],
            events, self.target, "story", "s", 4,
        )
        self.assertIn("u1", {row["message_id"] for row in rows})
        self.assertEqual(
            report["history_rows_using_unchanged_current_state"], 3
        )

    def test_metadata_reads_use_stable_keyset_pages(self):
        events = list(self.events) + [
            marker(5 + index, f"bulk-{index}", "s", 1, "user",
                   "update_after", 20 + index)
            for index in range(10001)
        ]
        cursor = FakeCursor(events)
        rows = ledger.load_session_events(
            cursor, "story", "s", 5, [self.target], max_events=11000
        )
        self.assertEqual(len(rows), 10005)
        metadata_queries = [
            (query, params) for query, params in zip(
                cursor.queries, cursor.query_params, strict=True
            ) if "FROM public.v2_chat_message_ledger" in query
            and "WHERE id = ANY(%s)" not in query
        ]
        self.assertEqual(len(metadata_queries), 2)
        self.assertIn("(recorded_at, id) > (%s, %s)", metadata_queries[1][0])
        self.assertEqual(metadata_queries[1][1][4], 10000)

    def test_event_limit_fails_closed(self):
        cursor = FakeCursor(self.events)
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_SESSION_EVENT_LIMIT_EXCEEDED"
        ):
            ledger.load_session_events(cursor, "story", "s", 5, [self.target], max_events=2)

    def test_explicit_event_limit_can_exceed_legacy_500k_ceiling(self):
        cursor = FakeCursor(self.events)
        rows = ledger.load_session_events(
            cursor, "story", "s", 5, [self.target], max_events=700000
        )
        self.assertEqual(len(rows), 4)
        self.assertEqual(cursor.query_params[0][-1], 10000)

    def test_event_limit_remains_hard_bounded_at_one_million(self):
        cursor = FakeCursor(self.events)
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_QUERY_SCOPE_INVALID"
        ):
            ledger.load_session_events(
                cursor, "story", "s", 5, [self.target], max_events=1000001
            )
        self.assertEqual(cursor.queries, [])

    def test_missing_target_boundary_holds(self):
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "TARGET_LEDGER_BOUNDARY_MISSING"
        ):
            ledger.target_boundary(self.events[:3], self.target)

    def test_incomplete_snapshot_holds(self):
        bad = snapshot(5, "u1", "s", 1, "user", "delete", 11)
        del bad["row_data"]["content"]
        with self.assertRaisesRegex(
            ledger.LedgerRecoveryError, "LEDGER_SNAPSHOT_FIELDS_INCOMPLETE"
        ):
            ledger.reconstruct_history(
                [], self.events[:3] + [bad, self.events[3]],
                self.target, "story", "s", 4,
            )


if __name__ == "__main__":
    unittest.main()

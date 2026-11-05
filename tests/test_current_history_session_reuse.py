from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from storyforge_gold_quality import history_recovery as recovery


def _ts(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, tzinfo=timezone.utc)


def _message(message_id: str, turn: int, hour: int) -> dict:
    return {
        "message_id": message_id,
        "story_id": "story",
        "session_id": "session",
        "turn_index": turn,
        "role": "user" if turn % 2 else "assistant",
        "content": f"content-{message_id}",
        "status": "completed",
        "created_at": _ts(hour),
        "mutation_revision": 0,
    }


def _target(case_id: str, turn: int, hour: int) -> tuple[dict, dict]:
    content = f"target-{case_id}"
    case = {
        "case_id": case_id,
        "story_id": "story",
        "session_id": "session",
        "turn_index": turn,
        "target_sha256": hashlib.sha256(content.encode()).hexdigest(),
    }
    row = {
        "message_id": f"target-message-{case_id}",
        "story_id": "story",
        "session_id": "session",
        "turn_index": turn,
        "role": "assistant",
        "content": content,
        "status": "completed",
        "created_at": _ts(hour),
    }
    return case, row


class FakeCursor:
    def __init__(self, targets: list[dict], history_rows: list[dict]):
        self.targets = targets
        self.history_rows = history_rows
        self.queries: list[tuple[str, tuple]] = []
        self._rows: list[dict] = []

    def execute(self, query: str, params: tuple) -> None:
        self.queries.append((query, params))
        if "turn_index = ANY(%s)" in query:
            self._rows = self.targets
        elif "FROM public.v2_chat_messages" in query and "LIMIT %s" in query:
            self._rows = self.history_rows[:params[-1]]
        else:
            raise AssertionError("UNEXPECTED_QUERY_SHAPE")

    def fetchall(self) -> list[dict]:
        return list(self._rows)


class SessionHistoryReuseTests(unittest.TestCase):
    def _run_recovery(self, cases, targets, rows, *, max_history=20000):
        cursor = FakeCursor(targets, rows)
        captured = {}

        def fake_recover_case(_cursor, case, **kwargs):
            captured[case["case_id"]] = kwargs.get("current_history")
            return {"case_id": case["case_id"]}

        fake_lineage = [{
            "session": {"session_id": "session", "created_at": _ts(0)},
            "lineage_depth": 0,
        }]
        with (
            patch.object(recovery, "load_session_events", return_value=[]),
            patch.object(recovery, "LedgerEventIndex", side_effect=lambda events: object()),
            patch.object(recovery, "_lineage", return_value=fake_lineage),
            patch.object(recovery, "recover_case", side_effect=fake_recover_case),
        ):
            recovered, holds = recovery.recover_cases_independently(
                cursor, cases, max_history=max_history
            )
        return cursor, captured, recovered, holds

    def test_single_superset_query_filters_each_target_boundary(self):
        case_a, target_a = _target("case-a", 5, 10)
        case_b, target_b = _target("case-b", 8, 20)
        rows = [
            _message("m1", 2, 5),
            _message("m_turn_cutoff", 5, 8),
            _message("m_equal_time", 3, 10),
            _message("m2", 5, 12),
            _message("m3", 7, 18),
        ]
        cursor, captured, recovered, holds = self._run_recovery(
            [case_a, case_b], [target_a, target_b], rows
        )

        history_queries = [
            query for query, _ in cursor.queries if "LIMIT %s" in query
        ]
        self.assertEqual(len(history_queries), 1)
        self.assertEqual(
            [row["message_id"] for row in captured["case-a"]], ["m1"]
        )
        self.assertEqual(
            [row["message_id"] for row in captured["case-b"]],
            ["m1", "m_turn_cutoff", "m_equal_time", "m2", "m3"],
        )
        self.assertEqual(len(recovered), 2)
        self.assertEqual(holds, [])

    def test_invalid_row_holds_only_targets_whose_boundary_includes_it(self):
        case_a, target_a = _target("case-a", 5, 10)
        case_b, target_b = _target("case-b", 8, 20)
        invalid = _message("bad-row", 5, 12)
        invalid["role"] = "system"
        rows = [_message("m1", 2, 5), invalid]
        cursor, captured, recovered, holds = self._run_recovery(
            [case_a, case_b], [target_a, target_b], rows
        )

        self.assertEqual(
            [row["message_id"] for row in captured["case-a"]], ["m1"]
        )
        self.assertNotIn("case-b", captured)
        self.assertEqual([row["case_id"] for row in recovered], ["case-a"])
        self.assertEqual(
            holds, [{"case_id": "case-b", "reason_code": "HISTORY_MESSAGE_SHAPE_INVALID"}]
        )

    def test_oversized_superset_uses_original_per_case_fallback(self):
        case_a, target_a = _target("case-a", 5, 10)
        case_b, target_b = _target("case-b", 8, 20)
        rows = [
            _message("m1", 1, 1),
            _message("m2", 2, 2),
            _message("m3", 3, 3),
        ]
        cursor, captured, recovered, holds = self._run_recovery(
            [case_a, case_b], [target_a, target_b], rows, max_history=2
        )

        self.assertEqual(captured, {"case-a": None, "case-b": None})
        self.assertEqual(
            len([query for query, _ in cursor.queries if "LIMIT %s" in query]),
            1,
        )
        self.assertEqual(len(recovered), 2)
        self.assertEqual(holds, [])


if __name__ == "__main__":
    unittest.main()

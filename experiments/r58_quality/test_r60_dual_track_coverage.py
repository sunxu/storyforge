"""Synthetic guardrail tests for owner-scoped R60 metadata pilot."""
from __future__ import annotations

from unittest.mock import Mock

import pytest

from r60_dual_track_coverage import Hold, screen


def test_metadata_rows_not_promoted():
    def fake_fetch(story):
        return [("m1", "session-1", 12, "2026-11-07T01:00:00Z", 144, "completed")]
    rows = screen(fake_fetch, ["story-one"])
    assert len(rows) == 1
    assert rows[0]["actual_sent_payload_verified"] is False
    assert rows[0]["single_completion_verified"] is False
    assert rows[0]["strict_gold_admitted"] is False
    assert rows[0]["experimental_admitted"] is False


def test_no_text_payload_allowed():
    with pytest.raises(Hold, match="CANDIDATE_ROW_INVALID"):
        screen(lambda _: [("m", "s", 12, "timestamp", 144, "completed", "SECRET")], ["story-one"])


def test_per_story_limit():
    with pytest.raises(Hold, match="CANDIDATE_LIMIT_EXCEEDED"):
        screen(lambda _: [("m", "s", 12, "timestamp", 144, "completed")] * 21, ["story-one"])


def test_invalid_status():
    with pytest.raises(Hold, match="CANDIDATE_METADATA_INVALID"):
        screen(lambda _: [("m", "s", 12, "timestamp", 144, "streaming")], ["story-one"])


def test_duplicate_target():
    with pytest.raises(Hold, match="DUPLICATE_TARGET"):
        screen(lambda _: [("m", "s", 12, "timestamp", 144, "completed")] * 2, ["story-one"])


def test_guard_requires_non_bypass_reader():
    from r60_dual_track_coverage import assert_guard

    cur = Mock()
    cur.fetchone.side_effect = [
        ("supabase_read_only_user", "on", "on", True, False),
    ]
    with pytest.raises(Hold, match="DB_ROLE_OR_RLS_GUARD_FAILED"):
        assert_guard(cur)


def test_guard_rejects_bad_table_index():
    from r60_dual_track_coverage import assert_guard

    cur = Mock()
    cur.fetchone.side_effect = [
        ("r58_export_reader", "on", "on", False, False),
        ("v2_chat_messages", True, True, False),
    ]
    with pytest.raises(Hold, match="MESSAGE_TABLE_PERMISSION_OR_INDEX_HOLD"):
        assert_guard(cur)

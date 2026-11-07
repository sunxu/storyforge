"""Synthetic tests for R60 scoped target pairs (no production rows)."""
from __future__ import annotations

import json

import pytest
from r60_scoped_target_pairs import Hold, assert_owner_db_guard, parse_scope, select_targets


def test_pairs_strictly_adjacent_and_unadmitted():
    rows = [
        ("u1", "story", "session", 1, "user", "completed", "t1"),
        ("a2", "story", "session", 2, "assistant", "completed", "t2"),
        ("u3", "story", "session", 3, "user", "completed", "t3"),
        ("a4", "story", "session", 4, "assistant", "failed", "t4"),
        ("a5", "story", "session", 5, "assistant", "completed", "t5"),
    ]
    actual, counts = select_targets(rows, "story", "session")
    assert counts == {"messages": 5, "pairs": 1}
    assert len(actual) == 1
    assert actual[0]["assistant_message_id"] == "a2"
    assert actual[0]["provider_attempt_linked"] is False
    assert actual[0]["experimental_admitted"] is False


def test_cross_story_rejected():
    rows = [("a2", "other", "session", 2, "assistant", "completed", "t2")]
    with pytest.raises(Hold, match="MESSAGE_IDENTITY_HOLD"):
        select_targets(rows, "story", "session")


def test_duplicate_turn_rejected():
    rows = [
        ("u1", "story", "session", 1, "user", "completed", "t1"),
        ("u2", "story", "session", 1, "user", "completed", "t2"),
    ]
    with pytest.raises(Hold, match="DUPLICATE_TURN_HOLD"):
        select_targets(rows, "story", "session")


def test_scope_disallows_unapproved_and_r50():
    raw = json.dumps({
        "schema": "storyforge_r60_private_session_scope_v1",
        "approved_purpose": "PRIVATE_TRAINING_CANDIDATE_REVIEW_ONLY",
        "sessions": [{
            "story_id": "story",
            "session_id": "session",
            "owner_scope_confirmed": True,
            "r50_protected_scope_excluded": False,
        }],
    }).encode()
    with pytest.raises(Hold, match="PRIVATE_SCOPE_SESSION_HOLD"):
        parse_scope(raw)


def test_scope_accepts_owner_defined_approved_session():
    raw = json.dumps({
        "schema": "storyforge_r60_private_session_scope_v1",
        "approved_purpose": "PRIVATE_TRAINING_CANDIDATE_REVIEW_ONLY",
        "sessions": [{
            "story_id": "story",
            "session_id": "session",
            "owner_scope_confirmed": True,
            "r50_protected_scope_excluded": True,
        }],
    }).encode()
    assert len(parse_scope(raw)) == 1


def test_owner_mac_reader_guard_accepts_r58_only():
    assert_owner_db_guard(("r58_export_reader", "on", "on", False, False))
    for bad in (
        ("supabase_read_only_user", "on", "on", True, False),
        ("r58_export_reader", "on", "on", True, False),
        ("r58_export_reader", "on", "on", False, True),
        ("r58_export_reader", "off", "on", False, False),
    ):
        with pytest.raises(Hold, match="DATABASE_GUARD_HOLD"):
            assert_owner_db_guard(bad)

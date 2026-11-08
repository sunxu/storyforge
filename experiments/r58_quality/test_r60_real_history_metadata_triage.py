"""R60-REAL-01 的合成测试：不得访问真实 Supabase 或私有正文。"""
from __future__ import annotations

import json
import os
import uuid

import pytest

import r60_real_history_metadata_triage as triage
import r60_scoped_target_pairs as scoped


def pair(turn=2):
    return {
        "story_id": "story1",
        "session_id": "session1",
        "assistant_message_id": "00000000-0000-4000-8000-000000000002",
        "prior_user_message_id": "00000000-0000-4000-8000-000000000001",
        "assistant_turn": turn,
        "provenance": "DB_COMPLETED_MESSAGE_PAIR_ONLY",
        "experimental_admitted": False,
    }


def db_row(*, chars=450, user_chars=20, finish="stop", edited=False,
           original=False, warning=False, user_type="", meta_type="object"):
    x = pair()
    return (
        x["assistant_message_id"], x["prior_user_message_id"],
        x["story_id"], x["session_id"], x["assistant_turn"],
        "assistant", "completed", "user", "completed", x["story_id"],
        chars, user_chars, finish, edited, original, warning, user_type,
        meta_type,
    )


def test_technical_priority_is_not_train_admission():
    row = triage.classify(pair(), db_row())
    assert row["technical_tier"] == "TECHNICAL_PRIORITY"
    assert row["target_semantics"] == "DB_FINAL_DELIVERED_ASSISTANT_CANDIDATE"
    assert row["quality_review_status"] == "UNREVIEWED"
    assert row["experimental_admitted"] is False
    assert row["training_authorized"] is False
    assert row["r50_exclusion_status"] == "UNKNOWN_HOLD"


@pytest.mark.parametrize(
    ("alteration", "expected"),
    [
        ({"chars": 25}, "TARGET_SHORTER_THAN_300"),
        ({"user_chars": 0}, "EMPTY_OR_CONTINUE_USER"),
        ({"user_type": "continue"}, "EMPTY_OR_CONTINUE_USER"),
        ({"finish": "MAX_TOKENS"}, "FINISH_REASON_UNVERIFIED"),
        ({"edited": True}, "EDIT_METADATA_PRESENT"),
        ({"original": True}, "EDIT_METADATA_PRESENT"),
        ({"warning": True}, "PARSE_WARNING_KEY_PRESENT"),
        ({"meta_type": None}, "ASSISTANT_METADATA_UNAVAILABLE"),
    ],
)
def test_technical_risk_requires_manual_review(alteration, expected):
    row = triage.classify(pair(), db_row(**alteration))
    assert row["technical_tier"] == "MANUAL_REVIEW_HOLD"
    assert expected in row["technical_reason_codes"]
    assert row["experimental_admitted"] is False


def test_wrong_message_uuid_not_accepted():
    values = list(db_row())
    values[0] = str(uuid.uuid4())
    with pytest.raises(scoped.Hold, match="PAIR_DB_IDENTITY_MISMATCH"):
        triage.classify(pair(), tuple(values))


def test_unknown_pair_is_hold():
    with pytest.raises(scoped.Hold, match="EXACT_PAIR_NOT_FOUND"):
        triage.classify(pair(), None)


def test_summary_has_no_identifying_values():
    rows = [triage.classify(pair(), db_row()),
            triage.classify(pair(), db_row(warning=True))]
    safe = triage.safe_summary(rows)
    assert safe["technical_priority"] == 1
    assert safe["manual_review_hold"] == 1
    assert safe["strict_gold_admitted"] == 0
    assert safe["experimental_admitted"] == 0
    assert "story_id" not in json.dumps(safe)
    assert safe["r50_exclusion_verified"] == 0


def test_query_has_only_metadata_and_lengths():
    sql = triage.SQL.lower()
    assert "char_length" in sql
    assert "session_id = %s" in sql
    assert "turn_index = %s" in sql
    assert "select a.content" not in sql
    assert "select u.content" not in sql
    assert "metadata->>'finishreason'" in sql


def test_load_sources_accepts_one_provenanced_pair(tmp_path, monkeypatch):
    base = tmp_path / "private"
    base.mkdir(mode=0o700)
    parent = base / "g0"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(scoped, "BASE", base)
    import hashlib

    scope_obj = {
        "schema": scoped.LIMITED_SCOPE_SCHEMA,
        "approved_purpose": "G0_DISCOVERY_G1_LIMITED_PRIVATE_REVIEW",
        "owner_authorization_ref": scoped.LIMITED_AUTH_REF,
        "scope_pair_provenance": "R60_OWNER_LOCATOR_THREE_CASES_ONE_PAIR",
        "r50_scope_verification": "UNKNOWN_HOLD",
        "training_rights_verification": "UNVERIFIED_HOLD",
        "source_version_sha256": None,
        "sessions": [{
            "story_id": "story1", "session_id": "session1",
            "g0_g1_scope_authorized": True,
            "r50_protected_scope_excluded": None,
            "training_rights_verified": None,
        }],
    }
    scope = parent / "R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json"
    data = json.dumps(scope_obj).encode()
    scope.write_bytes(data)
    os.chmod(scope, 0o600)
    locators = parent / "R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl"
    locators.write_text(json.dumps(pair()) + "\n")
    os.chmod(locators, 0o600)
    safe = parent / "R60_TARGET_PAIR_SAFE.json"
    safe.write_text(json.dumps({
        "status": "SCOPED_TARGET_PAIR_LOCATORS_EXTRACTED_NOT_ADMITTED",
        "scope_sha256": hashlib.sha256(data).hexdigest(),
        "session_scope_count": 1,
        "adjacent_completed_pairs": 1,
        "strict_gold_admitted": 0,
        "experimental_admitted": 0,
    }))
    os.chmod(safe, 0o600)
    approved, pairs = triage.load_sources(scope, locators, safe)
    assert approved["session_id"] == "session1"
    assert len(pairs) == 1

    other = {**pair(), "session_id": "not_authorized"}
    locators.write_text(json.dumps(other) + "\n")
    with pytest.raises(scoped.Hold, match="PAIR_SCOPE_OR_STATUS_HOLD"):
        triage.load_sources(scope, locators, safe)


def test_scope_rejects_unverified_training_expansion(tmp_path, monkeypatch):
    base = tmp_path / "private"
    base.mkdir(mode=0o700)
    sub = base / "g0"
    sub.mkdir(mode=0o700)
    monkeypatch.setattr(scoped, "BASE", base)
    scope = sub / "scope.json"
    scope.write_text(json.dumps({
        "schema": "storyforge_r60_private_session_scope_v1",
        "approved_purpose": "PRIVATE_TRAINING_CANDIDATE_REVIEW_ONLY",
        "sessions": [{
            "story_id": "story1", "session_id": "session1",
            "owner_scope_confirmed": True,
            "r50_protected_scope_excluded": True,
        }],
    }))
    os.chmod(scope, 0o600)
    loc = sub / "R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl"
    safe = sub / "R60_TARGET_PAIR_SAFE.json"
    for p in (loc, safe):
        p.write_text("{}")
        os.chmod(p, 0o600)
    with pytest.raises(scoped.Hold, match="SINGLE_PAIR_AUTHORIZATION_REQUIRED"):
        triage.load_sources(scope, loc, safe)

"""Synthetic-only provenance dedup checks for 339 verified candidates."""
from __future__ import annotations

import pytest
import r60_real1000_candidate_identity_audit as audit


def fixture():
    cases = []
    entries = []
    for i in range(1, 1001):
        same_target = 1 if i in (1, 2) else i
        case = {
            "case_key": f"key-{i}",
            "assistant_target_sha256": f"target-{same_target}",
            "history_messages_sha256": f"history-{i}",
            "source": {
                "story_id": f"story-{(i - 1) // 3}",
                "session_id": f"session-{i}",
                "assistant_message_id": f"message-{i}",
            },
        }
        cases.append(case)
        if i <= 339:
            entries.append({
                "position": i,
                "case_key": case["case_key"],
                "assistant_target_sha256": case["assistant_target_sha256"],
                "history_messages_sha256": case["history_messages_sha256"],
            })
    return cases, {"candidate_count": 339, "entries": entries}


def test_reports_duplicate_content_without_false_world_claim():
    cases, report = fixture()
    out = audit.audit(cases, report)
    assert out["candidate_count"] == 339
    assert out["unique_case_keys"] == 339
    assert out["unique_assistant_message_ids"] == 339
    assert out["same_target_hash_groups"] == 1
    assert out["same_target_hash_extra_cases"] == 1
    assert out["same_history_and_target_hash_extra_cases"] == 0
    assert out["max_candidates_per_story"] == 3
    assert out["unique_story_count"] == 113
    assert out["train_admitted"] == 0
    assert out["r50_complete_exclusion_verified"] is False


def test_rejects_duplicate_source_message_and_case_position():
    cases, report = fixture()
    report["entries"][1]["position"] = 1
    with pytest.raises(audit.Hold, match="DUPLICATE_OR_INVALID_POSITION_HOLD"):
        audit.audit(cases, report)
    cases, report = fixture()
    cases[1]["source"]["assistant_message_id"] = "message-1"
    with pytest.raises(audit.Hold, match="DUPLICATE_CASE_OR_MESSAGE_HOLD"):
        audit.audit(cases, report)


def test_rejects_changed_target_sha():
    cases, report = fixture()
    cases[0]["assistant_target_sha256"] = "tampered"
    with pytest.raises(audit.Hold, match="CANDIDATE_SOURCE_IDENTITY_HOLD"):
        audit.audit(cases, report)


def test_distinguishes_exact_pair_from_text_only_repeat():
    cases, report = fixture()
    cases[1]["history_messages_sha256"] = cases[0]["history_messages_sha256"]
    report["entries"][1]["history_messages_sha256"] = (
        cases[1]["history_messages_sha256"]
    )
    out = audit.audit(cases, report)
    assert out["same_target_hash_groups"] == 1
    assert out["same_history_and_target_hash_groups"] == 1


def test_known_r50_five_story_overlap_is_partial_only():
    cases, report = fixture()
    known = sorted(audit.r50_known.KNOWN_R50_STORIES)
    cases[0]["source"]["story_id"] = known[0]
    cases[1]["source"]["story_id"] = known[0]
    cases[2]["source"]["story_id"] = known[1]
    result = audit.audit(cases, report)
    assert result["r50_known5_candidate_overlap_count"] == 3
    assert result["r50_known5_overlapping_story_count"] == 2
    assert result["r50_known5_reference_stories"] == 5
    assert result["r50_complete_exclusion_verified"] is False


def test_no_known_r50_overlap_does_not_claim_full_exclusion():
    cases, report = fixture()
    result = audit.audit(cases, report)
    assert result["r50_known5_candidate_overlap_count"] == 0
    assert result["r50_complete_exclusion_verified"] is False

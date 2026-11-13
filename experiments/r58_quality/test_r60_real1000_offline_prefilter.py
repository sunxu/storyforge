"""Synthetic-only coverage for frozen-pool structural prefilter."""
from __future__ import annotations

import copy

import pytest

import r60_real_private_batch as private
import r60_real1000_offline_prefilter as module


def make_case(i: int) -> dict:
    history = [
        {"role": "user", "content": f"previous user {i}"},
        {"role": "assistant", "content": f"previous assistant {i}"},
        {"role": "user", "content": f"current user {i}"},
    ]
    target = f"synthetic completed response {i}"
    return {
        "case_key": f"case-{i}",
        "source": {
            "story_id": f"story-{i}", "session_id": f"session-{i}",
            "assistant_message_id": f"target-message-{i}",
            "prior_user_message_id": f"current-user-message-{i}",
            "previous_assistant_message_id": f"previous-assistant-{i}",
            "previous_user_message_id": f"previous-user-message-{i}",
            "assistant_turn_index": 4,
        },
        "history_messages": history,
        "target_text": target,
        "history_messages_sha256": private.digest(history),
        "assistant_target_sha256": private.digest(target),
    }


def candidates():
    return [make_case(i) for i in range(1000)]


def retarget(case, new_target):
    case["target_text"] = new_target
    case["assistant_target_sha256"] = private.digest(new_target)


def test_clean_1000_complete_no_quality_promotion():
    rows = module.classify_cases(candidates())
    safe = module.summarize(rows)
    assert safe["structure_pass"] == 1000
    assert safe["excluded"] == safe["context_hold"] == 0
    assert safe["quality_reviewed"] == safe["train_admitted"] == 0
    assert all("target_text" not in row for row in rows)


def test_duplicate_target_excludes_only_later_record():
    cases = candidates()
    retarget(cases[1], cases[0]["target_text"])
    rows = module.classify_cases(cases)
    assert rows[0]["state"] == "STRUCTURE_PASS"
    assert rows[1]["reason_code"] == "EXACT_TARGET_DUPLICATE"
    assert module.summarize(rows)["excluded"] == 1


def test_exact_duplicate_record_excludes_later():
    cases = candidates()
    history = copy.deepcopy(cases[0]["history_messages"])
    cases[1]["history_messages"] = history
    cases[1]["history_messages_sha256"] = private.digest(history)
    retarget(cases[1], cases[0]["target_text"])
    assert module.classify_cases(cases)[1]["reason_code"] == (
        "EXACT_RECORD_DUPLICATE"
    )


def test_same_history_different_target_is_context_hold_not_reject():
    cases = candidates()
    history = copy.deepcopy(cases[0]["history_messages"])
    cases[1]["history_messages"] = history
    cases[1]["history_messages_sha256"] = private.digest(history)
    result = module.classify_cases(cases)
    assert result[1]["state"] == "CONTEXT_HOLD"
    assert module.summarize(result)["context_hold"] == 1


def test_empty_messages_are_excluded():
    cases = candidates()
    cases[4]["history_messages"][2]["content"] = " "
    cases[4]["history_messages_sha256"] = private.digest(
        cases[4]["history_messages"]
    )
    assert module.classify_cases(cases)[4]["reason_code"] == (
        "STRUCTURE_INVALID"
    )


def test_corrupted_source_digest_fails_whole_run():
    cases = candidates()
    cases[7]["assistant_target_sha256"] = "tampered"
    with pytest.raises(module.Hold):
        module.classify_cases(cases)


def test_duplicate_source_id_fails_closed():
    cases = candidates()
    cases[2]["source"]["assistant_message_id"] = (
        cases[1]["source"]["assistant_message_id"]
    )
    with pytest.raises(module.Hold):
        module.classify_cases(cases)


def test_cannot_pretend_25_is_full_1000():
    with pytest.raises(module.Hold):
        module.classify_cases(candidates()[:25])


def test_no_unverified_private_result_on_io_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(module.quality, "frozen_pool",
                        lambda path: (candidates(), "pool"))
    monkeypatch.setattr(module.private, "BASE", tmp_path)
    out = tmp_path / "r60-real1000-prefilter-synthetic"
    result = module.run(tmp_path, out)
    assert result["status"] == (
        "REAL1000_PREFILTER_COMPLETE__QUALITY_NOT_EVALUATED"
    )
    assert (out / module.OUTPUT).exists()
    assert (out / module.OUTPUT).stat().st_mode & 0o777 == 0o600
    assert module.run(tmp_path, out)["status"] == "REAL1000_PREFILTER_HOLD"

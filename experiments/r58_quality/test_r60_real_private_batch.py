"""Synthetic-only tests: no real DB, no R50 text or user content."""
import json
import os

import pytest
import r60_real_private_batch as batch


def synthetic_row(story="story-a", turn=10):
    return (
        story, "session-x", "a-id", "u-id", "p-id", "pu-id", turn,
        "此前的用户消息", "NPC 先行推动故事", "当前玩家消息", "中文故事正文" * 60,
    )


def review_for(case, flags=None, scores=None):
    flags = flags or {k: False for k in batch.SEVERE}
    scores = scores or {k: 5 for k in batch.FLOORS}
    return {
        "schema": batch.REVIEW_SCHEMA, "case_key": case["case_key"],
        "assistant_target_sha256": case["assistant_target_sha256"],
        "history_messages_sha256": case["history_messages_sha256"],
        "reviewers_independent_owner_attested": True,
        "reviews": [
            {"reviewer_key": k, "decision": "PASS", "private_evidence_ref": "private-ref",
             "severe_flags": flags, "scores": scores}
            for k in ("reviewer-a", "reviewer-b")
        ],
    }


def test_guard_rejects_bypass_rls_role():
    batch.assert_guard(("r58_export_reader", "on", "on", False, False))
    for row in [("supabase_read_only_user", "on", "on", True, False),
                ("r58_export_reader", "on", "on", True, False),
                ("r58_export_reader", "off", "on", False, False)]:
        with pytest.raises(batch.Hold, match="DATABASE_GUARD_HOLD"):
            batch.assert_guard(row)


def test_capture_provenance_and_no_future_leakage():
    c = batch.parse_rows([synthetic_row()])[0]
    assert c["history_messages"][-1]["role"] == "user"
    assert len(c["history_messages"]) == 3
    assert c["target_text"] not in [x["content"] for x in c["history_messages"]]
    assert c["target_semantics"] == "DB_FINAL_PERSISTED_ASSISTANT"
    assert c["r50_complete_exclusion_status"] == "UNKNOWN_HOLD"
    assert not c["train_admitted"]
    assert c["history_messages_sha256"] == batch.digest(c["history_messages"])


def test_duplicate_story_or_target_rejected():
    with pytest.raises(batch.Hold, match="DUPLICATE_STORY_OR_TARGET_HOLD"):
        batch.parse_rows([synthetic_row(), synthetic_row(turn=12)])


def test_invalid_short_target_rejected():
    row = list(synthetic_row())
    row[-1] = "太短"
    with pytest.raises(batch.Hold, match="SOURCE_ROW_CONTENT_OR_BOUND_HOLD"):
        batch.parse_rows([tuple(row)])


def test_insufficient_reviews_are_hold():
    cases = batch.parse_rows([synthetic_row()])
    safe = batch.review_receipt(cases, [])
    assert safe["review_decisions"] == {"PASS": 0, "HOLD": 1, "REJECT": 0}
    assert safe["train_admitted"] == 0


def test_duplicate_reviewer_is_hold():
    case = batch.parse_rows([synthetic_row()])[0]
    r = review_for(case)
    r["reviews"][1]["reviewer_key"] = "reviewer-a"
    status, code = batch.validated_review(r, case)
    assert (status, code) == ("HOLD", "REVIEWER_NOT_DISTINCT")


def test_severe_flag_rejects():
    case = batch.parse_rows([synthetic_row()])[0]
    r = review_for(case, flags={"serious_player_agency": True,
                                "hard_fact_or_ban": False,
                                "safety_exclusion": False})
    assert batch.validated_review(r, case)[0] == "REJECT"


def test_six_floors_are_enforced():
    case = batch.parse_rows([synthetic_row()])[0]
    scores = {k: 5 for k in batch.FLOORS}
    scores["npc_initiative"] = 2
    assert batch.validated_review(review_for(case, scores=scores), case) == (
        "HOLD", "BELOW_QUALITY_FLOOR")


def test_attested_review_can_pass_quality_but_cannot_admit_training():
    case = batch.parse_rows([synthetic_row()])[0]
    safe = batch.review_receipt([case], [review_for(case)])
    assert safe["review_decisions"]["PASS"] == 1
    assert safe["train_admitted"] == 0
    assert safe["reviewer_independence_independently_proven_by_script"] is False


def test_source_mutation_is_rejected():
    case = batch.parse_rows([synthetic_row()])[0]
    case["target_text"] += "变动"
    with pytest.raises(batch.Hold, match="CAPTURE_TAMPER_HOLD"):
        batch.review_receipt([case], [])


def test_review_source_digest_must_match():
    case = batch.parse_rows([synthetic_row()])[0]
    r = review_for(case)
    r["assistant_target_sha256"] = "0" * 64
    assert batch.validated_review(r, case) == ("HOLD", "REVIEW_SOURCE_MISMATCH")


def test_files_only_private_and_no_identifiers_in_safe(tmp_path, monkeypatch):
    home = tmp_path / "private"
    home.mkdir(mode=0o700)
    monkeypatch.setattr(batch, "BASE", home)
    monkeypatch.setattr(batch, "fetch", lambda dsn: batch.parse_rows([synthetic_row()]))
    where = home / "capture01"
    safe = batch.capture(where, "not-used")
    assert where.stat().st_mode & 0o777 == 0o700
    assert (where / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl").stat().st_mode & 0o777 == 0o600
    raw_safe = json.dumps(safe)
    assert "story-a" not in raw_safe
    assert "a-id" not in raw_safe
    assert safe["train_admitted"] == 0
    with pytest.raises(batch.Hold, match="OUTPUT_EXISTS_HOLD"):
        batch.capture(where, "not-used")
    with pytest.raises(batch.Hold, match="PRIVATE_DIR_GUARD_HOLD"):
        batch.private_dir(tmp_path / "bad", create=True)


def test_review_receipt_offline_private_files(tmp_path, monkeypatch):
    home = tmp_path / "private"
    home.mkdir(mode=0o700)
    monkeypatch.setattr(batch, "BASE", home)
    monkeypatch.setattr(batch, "fetch", lambda dsn: batch.parse_rows([synthetic_row()]))
    directory = home / "run01"
    batch.capture(directory, "not-used")
    case = json.loads((directory / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl").read_text().strip())
    f = directory / "reviews.jsonl"
    f.write_text(json.dumps(review_for(case)) + "\n")
    os.chmod(f, 0o600)
    safe = batch.review(directory, f)
    assert safe["review_decisions"]["PASS"] == 1
    assert safe["train_admitted"] == 0
    assert (directory / "R60_REAL_G1_REVIEW_SAFE.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        batch.review(directory, f)

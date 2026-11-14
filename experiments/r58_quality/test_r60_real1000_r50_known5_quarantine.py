"""Synthetic-only tests of R50 known-five quarantining."""
import json

import pytest
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private


def sample():
    cases = []
    entries = []
    known = sorted(quarantine.known.KNOWN_R50_STORIES)
    for i in range(1, 1001):
        source = {
            "story_id": known[0] if i in (1, 2, 3) else f"story-{i}",
            "session_id": f"session-{i}",
            "assistant_message_id": f"message-{i}",
        }
        row = {
            "case_key": f"case-{i}",
            "history_messages_sha256": f"history-{i}",
            "assistant_target_sha256": f"target-{i}",
            "source": source,
        }
        cases.append(row)
        if i <= 339:
            entries.append({
                "position": i,
                "case_key": row["case_key"],
                "history_messages_sha256": row["history_messages_sha256"],
                "assistant_target_sha256": row["assistant_target_sha256"],
                "v1_receipt_sha256": f"sha-{i}",
            })
    return cases, {"candidate_count": 339, "entries": entries}


def test_known5_is_quarantined_remaining_all_hold():
    cases, report = sample()
    result = quarantine.construct(cases, report, "synthetic-sha")
    assert len(result["excluded_known5"]) == 3
    assert len(result["remaining_full_r50_hold"]) == 336
    assert {e["position"] for e in result["excluded_known5"]} == {1, 2, 3}
    assert all(e["status"] == "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD"
               for e in result["remaining_full_r50_hold"])
    assert result["train_admitted"] == 0
    assert result["r50_complete_exclusion_verified"] is False
    assert all("story_id" not in item for item in result["excluded_known5"])


def test_private_writer_create_only_and_no_files_in_preflight(
        tmp_path, monkeypatch):
    monkeypatch.setattr(private, "BASE", tmp_path)
    cases, report = sample()
    monkeypatch.setattr(identity, "verified_cases_report",
                        lambda *args: (cases, report))
    monkeypatch.setattr(private, "read_private",
                        lambda *args: b"synthetic-private-report")
    dest = tmp_path / "r60-real1000-r50-known5-quarantine-test"

    def invoke(write):
        return quarantine.run(
            tmp_path / "old", tmp_path / "plan", tmp_path / "v2",
            tmp_path / "v3", tmp_path / "audit", dest, write=write)

    safe = invoke(False)
    assert safe["status"] == "R50_KNOWN5_QUARANTINE_PREFLIGHT__NO_FILES"
    assert safe["known5_excluded_count"] == 3
    assert not dest.exists()
    safe = invoke(True)
    assert safe["status"] == "R50_KNOWN5_QUARANTINE_SAVED__FULL_R50_HOLD"
    file = dest / quarantine.FILENAME
    assert file.is_file()
    assert file.stat().st_mode & 0o777 == 0o600
    stored = json.loads(file.read_text())
    assert len(stored["remaining_full_r50_hold"]) == 336
    with pytest.raises(quarantine.Hold,
                       match="QUARANTINE_OUTPUT_PATH_HOLD"):
        invoke(True)
    assert file.is_file()


def test_not_a_full_r50_exclusion_even_when_no_known5_overlap():
    cases, report = sample()
    for index in (0, 1, 2):
        cases[index]["source"]["story_id"] = f"new-story-{index}"
    result = quarantine.construct(cases, report, "sha")
    assert not result["excluded_known5"]
    assert len(result["remaining_full_r50_hold"]) == 339
    assert result["r50_complete_exclusion_verified"] is False

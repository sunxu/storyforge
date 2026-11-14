"""Synthetic 172-world scoped database locator; no database calls."""
import pytest
import r60_base336_story_db_locator_cpu as target
from test_r60_base_start_cpu336_template_audit import sample


def cohort():
    cases, manifest = sample()
    for item in manifest["remaining_full_r50_hold"]:
        pos = item["position"]
        cases[pos - 1]["source"]["story_id"] = f"w-{(pos - 4) % 172}"
    return cases, manifest


def test_only_336_held_rows_are_scoped():
    cases, manifest = cohort()
    scope = target.scoped_stories(cases, manifest)
    assert len(scope) == 172
    assert all(x.startswith("w-") for x in scope)


def test_aggregate_no_history_promotion():
    result = target.aggregate(
        [f"w-{i}" for i in range(172)],
        (150, 130, 90, 120, 140, 1), (148, 200, 150, 198))
    assert result["current_user_stories_matching_ids"] == 150
    assert result["historical_story_version_at_target_verified"] is False
    assert result["world_component_isolation_verified"] is False
    assert result["train_admitted"] == 0


def test_invalid_count_is_rejected():
    with pytest.raises(target.Hold, match="RESULT_BOUNDS_HOLD"):
        target.aggregate([f"w-{i}" for i in range(172)],
                         (130, 131, 90, 120, 130, 0), (120, 200, 150, 180))


def test_candidate_missing_world_is_rejected():
    cases, manifest = cohort()
    del cases[3]["source"]["story_id"]
    with pytest.raises(target.Hold, match="STORY_ID_HOLD"):
        target.scoped_stories(cases, manifest)


def test_known5_leak_rejected():
    cases, manifest = cohort()
    cases[3]["source"]["story_id"] = min(
        target.quarantine.known.KNOWN_R50_STORIES)
    with pytest.raises(target.Hold, match="R50_KNOWN5_LEAK_HOLD"):
        target.scoped_stories(cases, manifest)


def test_failed_connection_phase_does_not_publish_dsn(monkeypatch, capsys):
    def fake_run(args):
        args._phase = "DB_CONNECT"
        raise RuntimeError("secret-dsn-and-private-id")

    monkeypatch.setattr(target, "run", fake_run)
    monkeypatch.setattr("sys.argv", [
        "r60_base336_story_db_locator_cpu.py",
        "--old-dir", "/tmp/a", "--plan-dir", "/tmp/b",
        "--v2-dir", "/tmp/c", "--v3-dir", "/tmp/d",
        "--audit-dir", "/tmp/e", "--quarantine-dir", "/tmp/f",
        "--execute",
    ])
    assert target.main() == 42
    output = capsys.readouterr().out
    assert "DB_CONNECTION_HOLD" in output
    assert "secret-dsn" not in output
    assert "private-id" not in output

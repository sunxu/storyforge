"""Synthetic, CPU-only tests for create-only private eight-group roster."""
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import r60_base336_world_cross_split_private_roster_cpu as subject
from test_r60_base336_story_db_locator_cpu import cohort


def frozen():
    cases, manifest = cohort()
    stories = sorted({cases[r["position"] - 1]["source"]["story_id"]
                      for r in manifest["remaining_full_r50_hold"]})
    return cases, manifest, stories


def test_reject_incomplete_world_group_inventory():
    cases, manifest, stories = frozen()
    with pytest.raises(subject.Hold, match="ROW_COUNT_HOLD"):
        subject.compile_roster([], cases, manifest, stories)


def test_reject_story_outside_frozen_172():
    cases, manifest, stories = frozen()
    with pytest.raises(subject.Hold, match="ROW_IDENTITY_HOLD"):
        subject.compile_roster([
            (1, "outside-frozen-source", "train", True, [])
        ], cases, manifest, stories)


def test_reject_duplicate_group_story_row():
    cases, manifest, stories = frozen()
    story = stories[0]
    split = subject.equality.split_labels(stories)[0]
    row = (1, story, split, True, [])
    with pytest.raises(subject.Hold, match="DUPLICATE_MEMBER_HOLD"):
        subject.compile_roster([row, row], cases, manifest, stories)


def test_precheck_no_db_and_no_private_creation(monkeypatch, tmp_path):
    cases, manifest, stories = frozen()
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    output = private / "review"
    monkeypatch.setattr(subject.locator.private, "BASE", private)
    monkeypatch.setattr(subject.prior, "_frozen", lambda args: (cases, manifest))
    monkeypatch.setattr(subject.locator, "scoped_stories", lambda *_: stories)
    monkeypatch.setattr(subject, "fetch", lambda *_: pytest.fail("unexpected DB read"))
    args = SimpleNamespace(private_output_dir=output, execute=False)
    result = subject.execute(args)
    assert result["status"] == "BASE336_WORLD_REVIEW_ROSTER_PRECHECK__NO_DB"
    assert result["private_file_created"] is False
    assert not output.exists()


def test_unsafe_output_dir_rejected(monkeypatch, tmp_path):
    cases, manifest, stories = frozen()
    monkeypatch.setattr(subject.prior, "_frozen", lambda args: (cases, manifest))
    monkeypatch.setattr(subject.locator, "scoped_stories", lambda *_: stories)
    args = SimpleNamespace(private_output_dir=tmp_path / "review", execute=False)
    with pytest.raises(subject.Hold, match="PRIVATE_DESTINATION_HOLD"):
        subject.execute(args)


def test_create_only_0600_record_not_in_git(monkeypatch, tmp_path):
    cases, manifest, stories = frozen()
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    monkeypatch.setattr(subject.locator.private, "BASE", private)
    monkeypatch.setattr(subject.prior, "_frozen", lambda args: (cases, manifest))
    monkeypatch.setattr(subject.locator, "scoped_stories", lambda *_: stories)
    monkeypatch.setattr(subject, "fetch", lambda *_: [(1, "synthetic", "train", True, [])])
    dummy_payload = {"schema": subject.SCHEMA, "groups_PRIVATE": []}
    dummy_safe = {
        "schema": subject.SAFE_SCHEMA, "status": "SYNTHETIC_READY",
        "train_admitted": 0, "private_values_emitted": False,
    }
    monkeypatch.setattr(
        subject, "compile_roster", lambda *_: (dummy_payload, dummy_safe))
    args = SimpleNamespace(private_output_dir=private / "review", execute=True)
    result = subject.execute(args)
    path = args.private_output_dir / subject.FILENAME
    assert result["private_file_created"] is True
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    with pytest.raises(subject.Hold, match="PRIVATE_DESTINATION_HOLD"):
        subject.execute(args)

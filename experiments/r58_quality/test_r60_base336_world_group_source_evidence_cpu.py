"""Synthetic eight-group world evidence checks; no actual DB or private text."""
import json
import stat
from types import SimpleNamespace

import pytest
import r60_base336_world_group_source_evidence_cpu as target
from test_r60_base336_world_review_decisions_template_cpu import payload


def test_source_member_prefers_current_revision():
    group = {
        "members_PRIVATE": [
            {"story_id_PRIVATE": "v", "current_world_match": False,
             "archived_revision_ids_PRIVATE": [7]},
            {"story_id_PRIVATE": "c", "current_world_match": True,
             "archived_revision_ids_PRIVATE": []},
        ]
    }
    assert target.source_member(group)["story_id_PRIVATE"] == "c"


def test_snapshot_replay_mismatch_fail_closed():
    groups = payload()["groups_PRIVATE"]

    class Dummy:
        def execute(self, *_):
            pass

        def fetchall(self):
            return []

    with pytest.raises(target.Hold, match="ROSTER_SNAPSHOT_DRIFT_HOLD"):
        target.collect(Dummy(), [f"s-{i}" for i in range(172)], groups)


def test_db_row_normalization_rejects_shape():
    with pytest.raises(target.Hold, match="ROSTER_REPLAY_HOLD"):
        target.normalize_db_rows([(1, "a", "train")])


def test_precheck_does_not_access_db_or_write(monkeypatch, tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    folder = private / "evidence"
    folder.mkdir(mode=0o700)
    monkeypatch.setattr(target.private, "BASE", private)
    roster_doc = payload()
    roster_doc["groups_PRIVATE"] = payload()["groups_PRIVATE"]
    target.private.write_new(
        folder / target.roster.FILENAME,
        (json.dumps(roster_doc) + "\n").encode(),
    )
    from r60_base336_world_review_decisions_template_cpu import build_template

    template = build_template(
        target.decisions.validate(roster_doc),
        __import__("hashlib").sha256(
            (folder / target.roster.FILENAME).read_bytes()).hexdigest(),
    )
    target.private.write_new(
        folder / target.decisions.FILENAME,
        (json.dumps(template) + "\n").encode(),
    )
    cases = [{"source": {"story_id": f"s-{i % 38}"}} for i in range(1000)]
    monkeypatch.setattr(target.frozen, "_frozen", lambda *_: (cases, {}))
    monkeypatch.setattr(
        target.locator, "scoped_stories", lambda *_: (
            [f"s-{i}" for i in range(38)]
            + [f"extra-{i}" for i in range(134)]
        ),
    )
    monkeypatch.setattr(
        target, "fetch", lambda *_: pytest.fail("No DB during precheck"),
    )
    args = SimpleNamespace(roster_dir=folder, execute=False)
    result = target.run(args)
    assert result["status"] == "BASE336_WORLD_EVIDENCE_PRECHECK__NO_DB"
    assert not (folder / target.FILENAME).exists()


def test_private_file_is_create_only(monkeypatch, tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    folder = private / "roster"
    folder.mkdir(mode=0o700)
    monkeypatch.setattr(target.private, "BASE", private)
    doc = payload()
    source = folder / target.roster.FILENAME
    target.private.write_new(source, (json.dumps(doc) + "\n").encode())
    from r60_base336_world_review_decisions_template_cpu import build_template

    template = build_template(target.decisions.validate(doc),
                              __import__("hashlib").sha256(source.read_bytes()).hexdigest())
    target.private.write_new(
        folder / target.decisions.FILENAME,
        (json.dumps(template) + "\n").encode())
    monkeypatch.setattr(target.frozen, "_frozen", lambda *_: ([], {}))
    monkeypatch.setattr(target.locator, "scoped_stories",
                        lambda *_: [f"s-{i}" for i in range(38)]
                        + [f"extra-{i}" for i in range(134)])
    monkeypatch.setattr(target, "fetch", lambda *_: [
        {"group_ordinal": k, "world_value_PRIVATE": {"setting": "synthetic"},
         "reference_PRIVATE": {"source_kind": "current"},
         "source_field": "v2_data.world",
         "review_decision": "HOLD"}
        for k in range(1, 9)
    ])
    args = SimpleNamespace(roster_dir=folder, execute=True)
    assert target.run(args)["evidence_file_created"] is True
    assert stat.S_IMODE((folder / target.FILENAME).stat().st_mode) == 0o600
    with pytest.raises(target.Hold, match="OUTPUT_EXISTS_HOLD"):
        target.run(args)

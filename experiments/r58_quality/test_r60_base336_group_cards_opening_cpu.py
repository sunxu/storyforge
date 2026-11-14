"""No-real-DB tests for world-group role card/opening evidence capture."""
import json
import stat
from types import SimpleNamespace

import pytest
import r60_base336_group_cards_opening_cpu as audit
from test_r60_base336_world_review_decisions_template_cpu import payload


def test_row_shape_and_bounded_fields():
    row = audit.source_fields([
        ({"name": "fictional"}, [{"role": "player"}], {"openingText": "hello"}),
    ])
    assert set(row) == {"character_PRIVATE", "characters_PRIVATE", "opening_PRIVATE"}
    with pytest.raises(audit.Hold, match="SOURCE_ROW_HOLD"):
        audit.source_fields([])


def test_world_group_drift_prevents_content_queries():
    class FakeCursor:
        def execute(self, query, params):
            assert query == audit.roster.SQL

        def fetchall(self):
            return []

    with pytest.raises(audit.Hold, match="WORLD_GROUP_SNAPSHOT_DRIFT_HOLD"):
        audit.build(FakeCursor(), [f"story-{n}" for n in range(172)],
                    payload()["groups_PRIVATE"])


def test_one_field_size_limit():
    with pytest.raises(audit.Hold, match="FIELD_TOO_LARGE_HOLD"):
        audit.source_fields([({"huge": "x" * (audit.MAX_FIELD_BYTES + 1)}, [], {})])


def test_no_db_precheck_and_output_create_only(monkeypatch, tmp_path):
    priv = tmp_path / "private"
    priv.mkdir(mode=0o700)
    evidence_dir = priv / "roster"
    evidence_dir.mkdir(mode=0o700)
    monkeypatch.setattr(audit.private, "BASE", priv)
    source = evidence_dir / audit.roster.FILENAME
    p = payload()
    audit.private.write_new(source, (json.dumps(p) + "\n").encode())
    import hashlib
    from r60_base336_world_review_decisions_template_cpu import build_template

    template = build_template(audit.world.decisions.validate(p),
                              hashlib.sha256(source.read_bytes()).hexdigest())
    audit.private.write_new(
        evidence_dir / audit.world.decisions.FILENAME,
        (json.dumps(template) + "\n").encode())
    monkeypatch.setattr(audit.frozen, "_frozen", lambda args: ([], {}))
    monkeypatch.setattr(audit.locator, "scoped_stories", lambda *_: (
        [f"s-{n}" for n in range(38)] + [f"other-{n}" for n in range(134)]
    ))
    monkeypatch.setattr(audit, "capture", lambda *_: pytest.fail("DB called"))
    args = SimpleNamespace(
        roster_dir=evidence_dir, output_dir=priv / "cards", execute=False)
    result = audit.generate(args)
    assert result["status"] == "BASE336_CARD_OPENING_EVIDENCE_PRECHECK__NO_DB"
    assert not args.output_dir.exists()
    args.output_dir.mkdir(mode=0o700)
    with pytest.raises(audit.Hold, match="OUTPUT_DIR_GUARD_HOLD"):
        audit.generate(args)


def test_synthetic_capture_writes_eight_private_files(monkeypatch, tmp_path):
    priv = tmp_path / "private"
    priv.mkdir(mode=0o700)
    roster_dir = priv / "roster"
    roster_dir.mkdir(mode=0o700)
    monkeypatch.setattr(audit.private, "BASE", priv)
    p = payload()
    source = roster_dir / audit.roster.FILENAME
    audit.private.write_new(source, (json.dumps(p) + "\n").encode())
    import hashlib
    from r60_base336_world_review_decisions_template_cpu import build_template

    doc = build_template(audit.world.decisions.validate(p),
                         hashlib.sha256(source.read_bytes()).hexdigest())
    audit.private.write_new(
        roster_dir / audit.world.decisions.FILENAME,
        (json.dumps(doc) + "\n").encode())
    monkeypatch.setattr(audit.frozen, "_frozen", lambda args: ([], {}))
    monkeypatch.setattr(audit.locator, "scoped_stories", lambda *_: (
        [f"s-{n}" for n in range(38)] + [f"other-{n}" for n in range(134)]
    ))
    groups = [
        {"group_ordinal": i, "current_world_cross_split": i != 8,
         "matched_source_records_PRIVATE": [
             {"source_kind": "current", "story_id_PRIVATE": "s-0",
              "source_fields": {"character_PRIVATE": {"demo": "only-synthetic"}}}
         ]} for i in range(1, 9)
    ]
    monkeypatch.setattr(audit, "capture", lambda *_: groups)
    args = SimpleNamespace(
        roster_dir=roster_dir, output_dir=priv / "cards", execute=True)
    safe = audit.generate(args)
    assert safe["private_files_created"] == 8
    assert safe["train_admitted"] == 0
    assert all(stat.S_IMODE(f.stat().st_mode) == 0o600
               for f in args.output_dir.iterdir())

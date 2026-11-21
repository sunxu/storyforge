"""No-real-DB tests for world-group role card/opening evidence capture."""
import hashlib
import json
import stat
from types import SimpleNamespace

import pytest
import r60_base336_group_cards_opening_cpu as audit
from r60_base336_world_review_decisions_template_cpu import build_template
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


def test_diagnostic_hold_code_and_phase_are_fixed():
    assert audit.diagnosed("PACKAGE_BUILD", lambda: "ok") == "ok"

    def known_error():
        raise audit.Hold("FIELD_TOO_LARGE_HOLD")

    with pytest.raises(audit.DiagnosticHold) as known:
        audit.diagnosed("DB_WORLD_AND_FIELDS", known_error)
    assert known.value.failure_phase == "DB_WORLD_AND_FIELDS"
    assert known.value.reason_code == "FIELD_TOO_LARGE_HOLD"

    def private_exception():
        raise RuntimeError("private story-id=never-emit")

    with pytest.raises(audit.DiagnosticHold) as unknown:
        audit.diagnosed("DB_CONNECT", private_exception)
    assert unknown.value.failure_phase == "DB_CONNECT"
    assert unknown.value.reason_code == "UNEXPECTED_HOLD"
    assert "private" not in str(unknown.value)


def test_generate_reports_safe_phase_without_db(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.world, "load", lambda *_: (
        _ for _ in ()).throw(RuntimeError("private sample must not print")))
    args = SimpleNamespace(roster_dir=tmp_path, output_dir=tmp_path / "output",
                           execute=False)
    with pytest.raises(audit.DiagnosticHold) as failure:
        audit.generate(args)
    assert failure.value.failure_phase == "ROSTER_TEMPLATE"
    assert failure.value.reason_code == "UNEXPECTED_HOLD"

    monkeypatch.setattr(audit.world, "load", lambda *_: ({}, [], b""))
    monkeypatch.setattr(audit.frozen, "_frozen", lambda *_: (
        _ for _ in ()).throw(audit.Hold("FROZEN_SCOPE_HOLD")))
    with pytest.raises(audit.DiagnosticHold) as failure:
        audit.generate(args)
    assert failure.value.failure_phase == "FROZEN_INPUT"
    assert failure.value.reason_code == "FROZEN_SCOPE_HOLD"


def test_main_emits_only_safe_failure_fields(monkeypatch, capsys, tmp_path):
    import sys
    from unittest.mock import patch

    def fail(_args):
        raise audit.DiagnosticHold("DB_WORLD_AND_FIELDS", "FIELD_TOO_LARGE_HOLD")

    monkeypatch.setattr(audit, "generate", fail)
    with patch.object(sys, "argv", [
        "r60_base336_group_cards_opening_cpu.py",
        *[
            v for key in ("old", "plan", "v2", "v3", "audit", "quarantine")
            for v in ("--" + key + "-dir", str(tmp_path))
        ],
        "--roster-dir", str(tmp_path),
        "--output-dir", str(tmp_path / "out"),
        "--execute",
    ]):
        assert audit.main() == 42
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["failure_phase"] == "DB_WORLD_AND_FIELDS"
    assert emitted["reason_code"] == "FIELD_TOO_LARGE_HOLD"
    assert emitted["database_accessed"] is None
    assert emitted["private_values_emitted"] is False
    assert "private" not in json.dumps(emitted).lower().replace(
        '"private_values_emitted": false', ""
    )


def test_owner_field_size_boundary_64_kib():
    assert audit.MAX_FIELD_BYTES == 65536
    assert audit.MAX_GROUP_BYTES == 655360
    # Previously rejected: opening >24 KB; now preserved without truncation.
    opening = "x" * 51809
    fields = audit.source_fields([({}, [], opening)])
    assert fields["opening_PRIVATE"] == opening
    with pytest.raises(audit.Hold, match="FIELD_TOO_LARGE_HOLD"):
        audit.source_fields([({}, [], "x" * audit.MAX_FIELD_BYTES)])


def test_group_writer_beyond_shared_200kb_create_only(tmp_path):
    # Prove this tool doesn't inherit the unrelated private capture cap.
    path = tmp_path / "group.json"
    contents = b"x" * 575785
    audit.write_group_new(path, contents)
    assert path.stat().st_size == len(contents)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        audit.write_group_new(path, b"replacement")
    with pytest.raises(audit.Hold, match="OUTPUT_SIZE_HOLD"):
        audit.write_group_new(tmp_path / "oversized", b"x" * (audit.MAX_GROUP_BYTES + 1))
    assert not (tmp_path / "oversized").exists()

"""Synthetic-only tests for Owner-local P2/Base336 source evidence capture."""
from __future__ import annotations

import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r60_base336_p2_source_evidence_capture_cpu as audit


def p2_source(i: int) -> dict:
    return {
        "source_key": f"S{i:02d}",
        "story_id": f"p2-story-{i}",
        "public_content_revision": 7,
        "public_content_hash": "a" * 64,
        "submission_snapshot_sha256": "b" * 64,
        "world_json_md5": "c" * 32,
        "moderation_submission_id": f"submission-{i}",
        "permission_event_id": f"permission-{i}",
        "permission_kind": "ai",
        "permission_result": "ai_approved",
        "permission_submission_id": f"submission-{i}",
        "permission_submission_bound": True,
        "permission_to_visibility": "public",
        "snapshot_matches_current_public_v2": True,
        "snapshot_hash_matches_submission_sha256": True,
    }


def p2_doc() -> dict:
    return {
        "schema": audit.P2_MANIFEST_SCHEMA,
        "status": audit.P2_MANIFEST_STATUS,
        "rights_scope": (
            "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
            "NO_TRAINING_OR_REDISTRIBUTION"
        ),
        "selection": {
            "selected_stories": 8,
            "authors": 5,
            "distinct_world_json": 8,
            "created_before_gpu_run": 3,
            "created_after_gpu_run": 5,
            "private_session_bodies_read": False,
        },
        "sources": [p2_source(i) for i in range(1, 9)],
    }


def p2_rows(sources: list[dict]) -> list[tuple]:
    rows = []
    for source in sources:
        fields = {
            "world": {"worldSentence": "A public world"},
            "character": {"name": "A"},
            "characters": [{"name": "A"}],
            "opening": {"opening": "A beginning"},
        }
        rows.append((
            source["story_id"], source["public_content_revision"],
            source["public_content_hash"], fields,
            source["moderation_submission_id"], source["public_content_revision"],
            source["submission_snapshot_sha256"], fields, "public",
            source["permission_event_id"], source["permission_submission_id"],
            "public", source["permission_kind"], source["permission_result"],
            source["world_json_md5"],
        ))
    return rows


class SourceEvidenceCaptureTests(unittest.TestCase):
    def test_missing_psycopg_driver_gives_fixed_safe_reason(self):
        with patch.dict(sys.modules, {"psycopg": None}):
            with self.assertRaises(audit.Hold) as raised:
                audit.fetch("postgresql://never-used", ["synthetic-story"], [])
        self.assertEqual(str(raised.exception), "DB_DRIVER_IMPORT_HOLD")

    def test_db_connection_error_gives_fixed_safe_reason(self):
        class FakePsycopgError(Exception):
            pass

        def connect(*_args, **_kwargs):
            raise FakePsycopgError("private host or credential details")

        fake = SimpleNamespace(Error=FakePsycopgError, connect=connect)
        with patch.dict(sys.modules, {"psycopg": fake}):
            with self.assertRaises(audit.Hold) as raised:
                audit.fetch("postgresql://never-used", ["synthetic-story"], [])
        self.assertEqual(str(raised.exception), "DB_CONNECTION_HOLD")
        self.assertNotIn("private", str(raised.exception))

    def test_unexpected_post_query_failure_reports_only_safe_phase(self):
        def fail_after_source_fetch(args):
            args.failure_phase = "P2_RECORD_VALIDATION"
            raise RuntimeError("secret source text must not appear")

        args = ["tool"]
        for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
            args.extend([f"--{name}-dir", "/unused"])
        args.extend(["--p2-manifest", "/unused", "--output-dir", "/unused", "--execute"])
        stream = StringIO()
        with patch.object(sys, "argv", args), patch.object(audit, "run", fail_after_source_fetch):
            with redirect_stdout(stream):
                exit_code = audit.main()
        self.assertEqual(exit_code, 42)
        receipt = json.loads(stream.getvalue())
        self.assertEqual(receipt["failure_phase"], "P2_RECORD_VALIDATION")
        self.assertEqual(receipt["reason_code"], "SOURCE_CAPTURE_OR_RUNTIME_HOLD")
        self.assertNotIn("secret", stream.getvalue())
        self.assertIsNone(receipt["database_accessed"])

    def test_load_p2_manifest_accepts_exact_eight_source_contract(self):
        with self.subTest("private input"):
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as directory:
                path = Path(directory) / "manifest.json"
                path.write_text(json.dumps(p2_doc()), encoding="utf-8")
                os.chmod(path, 0o600)
                doc, raw, sources = audit.load_p2_manifest(path)
                self.assertEqual(doc["status"], audit.P2_MANIFEST_STATUS)
                self.assertGreater(len(raw), 0)
                self.assertEqual(len(sources), 8)

    def test_load_p2_manifest_rejects_duplicate_story_ids(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            doc = p2_doc()
            doc["sources"][1]["story_id"] = doc["sources"][0]["story_id"]
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            os.chmod(path, 0o600)
            with self.assertRaises(audit.Hold) as raised:
                audit.load_p2_manifest(path)
            self.assertEqual(str(raised.exception), "P2_SOURCE_DUPLICATE_HOLD")

    def test_p2_rows_require_exact_revision_snapshot_and_permission_binding(self):
        sources = [p2_source(i) for i in range(1, 9)]
        records, coverage = audit._p2_records(p2_rows(sources), sources)
        self.assertEqual(len(records), 8)
        self.assertEqual(coverage, {field: 8 for field in audit.FIELDS})

    def test_p2_rows_reject_snapshot_drift(self):
        sources = [p2_source(i) for i in range(1, 9)]
        rows = p2_rows(sources)
        first = list(rows[0])
        first[7] = {"world": {"worldSentence": "changed"}}
        rows[0] = tuple(first)
        with self.assertRaises(audit.Hold) as raised:
            audit._p2_records(rows, sources)
        self.assertEqual(str(raised.exception), "P2_SNAPSHOT_CURRENT_MISMATCH_HOLD")

    def test_p2_rows_reject_permission_submission_mismatch(self):
        sources = [p2_source(i) for i in range(1, 9)]
        rows = p2_rows(sources)
        first = list(rows[0])
        first[10] = "wrong-submission"
        rows[0] = tuple(first)
        with self.assertRaises(audit.Hold) as raised:
            audit._p2_records(rows, sources)
        self.assertEqual(str(raised.exception), "P2_REVISION_PERMISSION_BINDING_HOLD")

    def test_base_records_require_current_coverage_for_all_172_stories(self):
        stories = [f"base-story-{i}" for i in range(172)]
        rows = [
            ("current", story, None, "2026-11-19T00:00:00Z",
             {"world": "w"}, {"character": "c"}, [], {"opening": "o"}, "d" * 32)
            for story in stories
        ]
        records, stats = audit._base_records(rows, stories)
        self.assertEqual(len(records), 172)
        self.assertEqual(stats["current_rows"], 172)
        self.assertEqual(stats["archived_version_rows"], 0)
        self.assertEqual(stats["field_nonnull_counts"], {field: 172 for field in audit.FIELDS})

    def test_base_records_reject_missing_current_story(self):
        stories = [f"base-story-{i}" for i in range(172)]
        rows = [
            ("current", story, None, None, None, None, None, None, None)
            for story in stories[:-1]
        ]
        rows.append(("archived", stories[0], 1, None, None, None, None, None, None))
        with self.assertRaises(audit.Hold) as raised:
            audit._base_records(rows, stories)
        self.assertEqual(str(raised.exception), "BASE_CURRENT_COVERAGE_HOLD")

    def test_exact_field_matches_report_counts_without_emitting_values(self):
        p2 = [{
            "source_key_PRIVATE": "S01",
            "story_id_PRIVATE": "secret-p2-id",
            "source_fields_PRIVATE": {field: {"same": field} for field in audit.FIELDS},
        }]
        base = [{
            "source_kind": "current",
            "story_id_PRIVATE": "secret-base-id",
            "revision_id_PRIVATE": None,
            "source_fields_PRIVATE": {field: {"same": field} for field in audit.FIELDS},
        }]
        counts, pairs = audit.exact_field_matches(p2, base)
        self.assertTrue(all(counts[field]["p2_sources"] == 1 for field in audit.FIELDS))
        self.assertEqual(len(pairs), len(audit.FIELDS))
        safe = audit.safe_summary(
            {"current_rows": 172, "archived_version_rows": 0,
             "field_nonnull_counts": {field: 172 for field in audit.FIELDS}},
            {field: 8 for field in audit.FIELDS}, p2, 0, counts, 1234,
        )
        rendered = json.dumps(safe)
        self.assertNotIn("secret-p2-id", rendered)
        self.assertNotIn("secret-base-id", rendered)
        self.assertFalse(safe["historical_actual_sent_verified"])
        self.assertFalse(safe["reviewer_independence_verified"])
        self.assertEqual(safe["train_admitted"], 0)

    def test_output_target_is_create_only_and_private(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            base = Path(directory)
            os.chmod(base, 0o700)
            original = audit.private.BASE
            audit.private.BASE = base
            try:
                target = base / "new-output"
                audit.validate_output_target(target)
                target.mkdir(mode=0o700)
                with self.assertRaises(audit.Hold) as raised:
                    audit.validate_output_target(target)
                self.assertEqual(str(raised.exception), "OUTPUT_TARGET_HOLD")
            finally:
                audit.private.BASE = original

    def test_private_writer_uses_0600_and_refuses_overwrite(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            path = Path(directory) / "private.json"
            audit._write_new(path, b'{"private":true}')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                audit._write_new(path, b'{"private":false}')


if __name__ == "__main__":
    unittest.main()

"""R57 G2 offline exporter tests: synthetic dialogues and private sandbox only."""

import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "r57_source_index_export.py"
spec = importlib.util.spec_from_file_location("r57_source_index_export", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(override=None):
    dialogue = {
        "id": "synthetic-example",
        "metadata": {
            "source_story_id": "synthetic-story",
            "target_sha256": sha(b"synthetic assistant line"),
        },
        "messages": [
            {"role": "system", "content": "fabricated system constraint"},
            {"role": "user", "content": "fabricated player input"},
            {"role": "assistant", "content": "synthetic assistant line", "loss": True},
        ],
    }
    if override is not None:
        override(dialogue)
    return (json.dumps(dialogue, ensure_ascii=False) + "\n").encode() * 49


def plan(payload, alias_sha):
    return {
        "schema": mod.PLAN_FORMAT,
        "no_protected_evaluation_accessed": True,
        "training_authorized": False,
        "alias_map_sha256": alias_sha,
        "source_pins": {
            "R46_TRAIN": {
                "sha256": sha(payload),
                "metadata_world_field": "source_story_id",
            }
        },
    }


def alias():
    return {
        "schema": mod.ALIAS_FORMAT,
        "story_to_component": {"synthetic-story": "C_synthetic_component_0001"},
    }


class TestSourceExporter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.private = self.root / "owner-private"
        self.repo.mkdir()
        self.private.mkdir()
        (self.private / "r46").mkdir()
        self.raw = fixture()
        (self.private / "r46/train.jsonl").write_bytes(self.raw)

    def build(self, raw=None, mapping=None, props=None):
        payload = self.raw if raw is None else raw
        mapping = alias() if mapping is None else mapping
        serialized_alias = json.dumps(mapping).encode()
        obj = plan(payload, sha(serialized_alias))
        if props:
            props(obj)
        return mod.build_index(
            obj, mapping, repo_root=self.repo, private_root=self.private,
            read=lambda root, relative, limit: self.raw if relative == "r46/train.jsonl" else None,
            trusted_sha256={},  # isolated synthetic fixture; production CLI always uses frozen pins
        )

    def test_pinned_source_success_private_index_structure(self):
        result = self.build()
        self.assertEqual([x["id"] for x in result["sources"]], ["R46_TRAIN"])
        entry = result["sources"][0]["rows"][0]
        self.assertEqual(len(result["sources"][0]["rows"]), 49)
        self.assertEqual(entry["target_sha256"], sha(b"synthetic assistant line"))
        self.assertEqual(entry["world_component_token"], "C_synthetic_component_0001")
        self.assertNotIn("synthetic assistant line", json.dumps(result))

    def test_byte_hash_mismatch_blocks(self):
        with self.assertRaises(mod.ExportHold):
            self.build(props=lambda x: x["source_pins"]["R46_TRAIN"].update(sha256="0" * 64))

    def test_alias_map_absence_blocks(self):
        with self.assertRaises(mod.ExportHold):
            self.build(mapping={"schema": mod.ALIAS_FORMAT, "story_to_component": {"other": "C_other_component_0001"}})

    def test_unsafe_source_names_block(self):
        with self.assertRaises(mod.ExportHold):
            self.build(props=lambda x: x["source_pins"].update({"R50_FAKE": {"sha256": sha(self.raw),
                                 "metadata_world_field": "source_story_id"}}))

    def test_missing_target_hash_match_blocks(self):
        alt = fixture(lambda x: x["metadata"].update(target_sha256="0" * 64))
        self.raw = alt
        with self.assertRaises(mod.ExportHold):
            self.build(raw=alt)

    def test_wrong_target_role_blocks(self):
        alt = fixture(lambda x: x["messages"][-1].update(role="user"))
        self.raw = alt
        with self.assertRaises(mod.ExportHold):
            self.build(raw=alt)

    def test_missing_world_id_blocks(self):
        alt = fixture(lambda x: x["metadata"].pop("source_story_id"))
        self.raw = alt
        with self.assertRaises(mod.ExportHold):
            self.build(raw=alt)

    def test_source_count_mismatch_blocks(self):
        self.raw = self.raw.splitlines()[0] + b"\n"
        with self.assertRaises(mod.ExportHold):
            self.build(raw=self.raw)

    def test_canonical_projection_deterministic(self):
        msgs = [
            {"role": "user", "content": "same", "loss": False},
            {"role": "assistant", "content": "synthetic assistant line", "loss": True},
        ]
        a = mod._project_messages(msgs)
        self.assertNotIn("loss", a[-1])
        self.assertEqual(mod._projection_sha(a), mod._projection_sha(mod._project_messages(msgs)))

    def test_blob_identity_uses_git_nul_separator(self):
        data = b"test"
        canonical = hashlib.sha1(b"blob 4\x00test").hexdigest()
        self.assertEqual(mod._git_blob(data), canonical)

    def test_cli_rejects_wrong_frozen_trainer_sha(self):
        alias_raw = json.dumps(alias()).encode()
        (self.private / "R57_G2_ALIAS_GRAPH_PRIVATE.json").write_bytes(alias_raw)
        (self.private / "R57_G2_SOURCE_PINS_PRIVATE.json").write_text(
            json.dumps(plan(self.raw, sha(alias_raw))), encoding="utf-8"
        )
        result = subprocess.run([
            sys.executable, str(SCRIPT), "--repo-root", str(self.repo),
            "--private-root", str(self.private),
        ], text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("published compiled Trainer", result.stderr)
        self.assertFalse((self.private / "R57_G2_SOURCE_INDEX_PRIVATE.json").exists())

    def test_private_output_exclusive_write_and_perms(self):
        filename = "R57_G2_SOURCE_INDEX_PRIVATE.json"
        payload = b'{"synthetic":true}\\n'
        mod._put_private(self.private, filename, payload)
        index_path = self.private / filename
        self.assertEqual(index_path.read_bytes(), payload)
        if os.name == "posix":
            self.assertEqual(index_path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            mod._put_private(self.private, filename, b"OVERWRITE")
        self.assertEqual(index_path.read_bytes(), payload)

    def test_published_pin_names_are_exact_and_four(self):
        self.assertEqual(set(mod.HISTORICAL_TRAINER_SHA256), {
            "R46_TRAIN", "R46_VALIDATION", "R54_TRAIN", "R54_VALIDATION"
        })
        self.assertTrue(all(len(x) == 64 for x in mod.HISTORICAL_TRAINER_SHA256.values()))

    def test_symlink_source_rejected(self):
        orig = self.private / "r46/train.jsonl"
        alt = self.private / "r46/other.jsonl"
        orig.rename(alt)
        orig.symlink_to(alt)
        with self.assertRaises(mod.ExportHold):
            mod._read(self.private, "r46/train.jsonl", mod.MAX_SOURCE_BYTES)

    def test_protected_path_guard_before_read(self):
        with self.assertRaises(mod.ExportHold):
            mod._guard_path(self.private, "r50/some_private_file.jsonl")

    def test_no_unpinned_repo_data_replay(self):
        obj = plan(self.raw, sha(json.dumps(alias()).encode()))
        obj["source_pins"]["GOLD87"] = {"sha256": sha(self.raw),
                                            "metadata_world_field": "source_story_id"}
        with self.assertRaises(mod.ExportHold):
            mod.build_index(
                obj, alias(), repo_root=self.repo, private_root=self.private,
                read=lambda root, relative, limit: self.raw,
            )


if __name__ == "__main__":
    unittest.main()

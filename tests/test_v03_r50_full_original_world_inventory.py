"""Synthetic-only R50 old/full-world ZIP inventory tests; no private material."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"scripts"/"v03_r50_full_original_world_inventory.py"
spec=importlib.util.spec_from_file_location("r50_lfs_inventory",P)
assert spec and spec.loader
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def archive(files):
    data=BytesIO()
    with zipfile.ZipFile(data,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,blob in files.items():
            z.writestr(name,blob)
    return data.getvalue()

def record(i):
    return {"rank":i,"story":{"id":f"synthetic-{i}"},
        "messages":[{"role":"user","content":"synthetic sample "+("a"*160)+str(i)},
                    {"role":"assistant","content":"synthetic response "+("b"*130)+str(i)}]}

class FullSourceGateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.repo=self.root/"repo";self.repo.mkdir();(self.repo/".git").mkdir()
        raw14=archive({
            **{f"{i:02d}-raw.json":json.dumps(record(i)).encode()
               for i in range(1,15)},
            **{f"{i:02d}-raw.jsonl":json.dumps({
                **record(i), "export_format": "jsonl"
            }).encode() for i in range(1,15)},
            "02-notes.txt": b"synthetic non-conversation sidecar",
        })
        self.old14=self.root/"old14.zip";self.old14.write_bytes(raw14)
        zip15=archive({"15-original.json":json.dumps(record(15)).encode()})
        bundle=archive({"raw/15-original.zip":zip15})
        raw0615=archive({"sources/original-stories.zip":bundle})
        self.old0615=self.root/"06-15.zip";self.old0615.write_bytes(raw0615)
        original=m.ARCHIVES
        m.ARCHIVES={"old14":(hashlib.sha256(raw14).hexdigest(),len(raw14)),
                    "old06_15":(hashlib.sha256(raw0615).hexdigest(),len(raw0615))}
        self.addCleanup(lambda:setattr(m,"ARCHIVES",original))
        receipt=self.repo/m.RECEIPT;receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({
            "source_commit": m.SOURCE_COMMIT,
            "source_root": m.ROOT.as_posix(),
            "files": [{}] * 35,
            "worlds": [{
                "number": i, "folder": f"{i}-synthetic",
                "story_id": f"synthetic-{i}"
            } for i in range(16, 21)],
        }))
        for i in range(16,21):
            folder=self.repo/m.ROOT/f"{i}-synthetic";folder.mkdir(parents=True)
            row=record(i)
            (folder/(folder.name+".jsonl")).write_text(json.dumps(row)+"\n")
            (folder/"story-cards.json").write_text(json.dumps({
                "rank": i, "story_id": f"synthetic-{i}"
            }))

    def test_old14_equivalent_json_and_jsonl(self):
        rows = m.old14_data(self.old14)
        self.assertEqual(len(rows), 14)
        self.assertEqual(set(rows), set(range(1, 15)))
        self.assertEqual(rows[4]["story"]["id"], "synthetic-4")

    def test_old14_nonmatching_variants_hold(self):
        with zipfile.ZipFile(self.old14) as z:
            payloads = {info.filename: z.read(info) for info in z.infolist()}
        edited = record(4)
        edited["messages"][0]["content"] = "DIFFERENT SYNTHETIC USER CONTENT"
        payloads["04-raw.jsonl"] = json.dumps(edited).encode()
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        with self.assertRaisesRegex(ValueError, "OLD14_VARIANTS_DIVERGE"):
            m.screen(self.repo, self.old14, self.old0615)

    def test_old14_changed_variant_identity_hold(self):
        with zipfile.ZipFile(self.old14) as z:
            payloads = {info.filename: z.read(info) for info in z.infolist()}
        edited = record(4)
        edited["story"]["id"] = "synthetic-different-world"
        payloads["04-raw.jsonl"] = json.dumps(edited).encode()
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        with self.assertRaisesRegex(ValueError, "OLD14_VARIANT_ID_MISMATCH"):
            m.screen(self.repo, self.old14, self.old0615)

    def test_old14_uses_frozen_required_ranks_not_01_to_14(self):
        # A 14-export archive can contain an additional numbered story.
        # That alone must not be silently ignored or treated as a conflict.
        with zipfile.ZipFile(self.old14) as z:
            payloads = {info.filename: z.read(info) for info in z.infolist()}
        payloads["21-extra.json"] = json.dumps(record(21)).encode()
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        parsed = m.old14_data(self.old14)
        self.assertIn(21, parsed)
        report = m.screen(self.repo, self.old14, self.old0615)
        self.assertIn(21, report["extra_archive_ranks_outside_frozen_r45"])
        self.assertEqual(report["extra_archive_source_id_conflicts_with_r50"], 0)
        self.assertEqual(report["semantic_hidden_alias_and_world_component_closure"], "HOLD")

    def test_required_old14_rank_still_fail_closed(self):
        with zipfile.ZipFile(self.old14) as z:
            payloads = {info.filename: z.read(info) for info in z.infolist()
                        if not info.filename.startswith("14-")}
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        with self.assertRaisesRegex(ValueError, "OLD14_R45_REQUIRED_RANKS_MISSING"):
            m.screen(self.repo, self.old14, self.old0615)

    def test_out_of_scope_extra_story_identity_overlap_is_flagged(self):
        with zipfile.ZipFile(self.old14) as z:
            payloads = {info.filename: z.read(info) for info in z.infolist()}
        extra = record(21)
        extra["story"]["id"] = "synthetic-16"
        payloads["21-extra.json"] = json.dumps(extra).encode()
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        r = m.screen(self.repo, self.old14, self.old0615)
        self.assertEqual(r["extra_archive_source_id_conflicts_with_r50"], 1)
        self.assertEqual(r["screen_status"],
                         "LEXICAL_OR_IDENTITY_FLAGS_REQUIRE_AI_ADJUDICATION")

    def test_old15_cross_archive_divergence_is_rejected(self):
        with zipfile.ZipFile(self.old14) as z:
            payloads = {info.filename: z.read(info) for info in z.infolist()}
        payloads["15-extra.json"] = json.dumps(record(15)).encode()
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        r = m.screen(self.repo, self.old14, self.old0615)
        self.assertTrue(r["old15_checked_against_two_archives"])
        changed = record(15)
        changed["messages"][0]["content"] = "altered synthetic old15 text"
        payloads["15-extra.json"] = json.dumps(changed).encode()
        binary = archive(payloads)
        self.old14.write_bytes(binary)
        m.ARCHIVES["old14"] = (hashlib.sha256(binary).hexdigest(), len(binary))
        with self.assertRaisesRegex(ValueError,
                                    "OLD15_CROSS_ARCHIVE_TRANSCRIPT_MISMATCH"):
            m.screen(self.repo, self.old14, self.old0615)

    def test_finder_metadata_is_ignored_without_changing_world_count(self):
        root = self.repo / m.ROOT
        (root / ".DS_Store").write_bytes(b"synthetic Finder metadata")
        (root / ".localized").write_text("synthetic")
        (root / "._20-synthetic").write_bytes(b"synthetic AppleDouble")
        r = m.screen(self.repo, self.old14, self.old0615)
        self.assertEqual(r["source_pair_count"], 50)
        self.assertEqual(r["new_source_ranks_checked"], list(range(16, 21)))
        self.assertEqual(r["semantic_hidden_alias_and_world_component_closure"],
                         "HOLD")

    def test_unknown_root_file_fails_closed(self):
        (self.repo / m.ROOT / "unsafe.txt").write_text("synthetic")
        with self.assertRaisesRegex(ValueError,
                                    "R50_UNEXPECTED_SOURCE_ROOT_ENTRY"):
            m.new_data(self.repo)

    def test_unknown_world_directory_fails_closed(self):
        (self.repo / m.ROOT / "21-other").mkdir()
        with self.assertRaisesRegex(ValueError,
                                    "R50_UNEXPECTED_SOURCE_ROOT_ENTRY"):
            m.new_data(self.repo)

    def test_missing_frozen_world_directory_fails_closed(self):
        (self.repo / m.ROOT / "20-synthetic").rename(
            self.repo / "removed-source-outside-world-root"
        )
        with self.assertRaisesRegex(ValueError,
                                    "R50_EXPECTED_WORLD_FOLDER_MISSING"):
            m.new_data(self.repo)

    def test_sidecar_symlink_cannot_bypass_guard(self):
        root = self.repo / m.ROOT
        (root / ".DS_Store").symlink_to(self.repo / m.RECEIPT)
        with self.assertRaisesRegex(ValueError,
                                    "R50_SOURCE_ROOT_SYMLINK_HOLD"):
            m.new_data(self.repo)

    def test_modified_frozen_world_folder_name_is_rejected(self):
        receipt_path = self.repo / m.RECEIPT
        record = json.loads(receipt_path.read_text())
        record["worlds"][0]["folder"] = "16-another"
        receipt_path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,
                                    "R50_EXPECTED_WORLD_FOLDER_MISSING"):
            m.new_data(self.repo)

    def test_nested_old_15(self):
        self.assertEqual(m.identity(m.old15_data(self.old0615)),"synthetic-15")

    def test_full_10_by_5_still_semantic_hold(self):
        r=m.screen(self.repo,self.old14,self.old0615)
        self.assertEqual(r["source_pair_count"],50)
        self.assertEqual(r["old_source_ranks_checked"],sorted(m.OLD_RANKS))
        self.assertEqual(r["semantic_hidden_alias_and_world_component_closure"],"HOLD")
        self.assertEqual(r["same_story_id_pair_count"],0)
        self.assertNotIn("synthetic-2",json.dumps(r))

    def test_bad_lfs_hash_fails(self):
        with self.old14.open("ab") as f:f.write(b"tampered")
        with self.assertRaisesRegex(ValueError,"SIZE_MISMATCH"):
            m.screen(self.repo,self.old14,self.old0615)

    def test_missing_nested_old15_fails(self):
        broken=archive({"sources/archive.zip":archive({"raw/nope.zip":
                        archive({"14-original.json":b"{}"})})})
        self.old0615.write_bytes(broken)
        m.ARCHIVES["old06_15"]=(hashlib.sha256(broken).hexdigest(),len(broken))
        with self.assertRaisesRegex(ValueError,"OLD15_RAW_SOURCE_NOT_FOUND"):
            m.screen(self.repo,self.old14,self.old0615)

    def test_real_identity_overlap_flagged(self):
        folder=self.repo/m.ROOT/"20-synthetic"
        v=record(20);v["story"]["id"]="synthetic-2"
        (folder/(folder.name+".jsonl")).write_text(json.dumps(v)+"\n")
        (folder/"story-cards.json").write_text(json.dumps({
            "rank": 20, "story_id": "synthetic-2"
        }))
        r=m.screen(self.repo,self.old14,self.old0615)
        self.assertEqual(r["same_story_id_pair_count"],1)
        self.assertEqual(r["screen_status"],"LEXICAL_OR_IDENTITY_FLAGS_REQUIRE_AI_ADJUDICATION")

if __name__=="__main__": unittest.main()

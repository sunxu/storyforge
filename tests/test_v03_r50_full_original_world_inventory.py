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
        raw14=archive({f"{i:02d}-raw.json":json.dumps(record(i)).encode()
                       for i in range(1,15)})
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
        receipt.write_text(json.dumps({"source_commit":m.SOURCE_COMMIT,"files":[{}]*35}))
        for i in range(16,21):
            folder=self.repo/m.ROOT/f"{i}-synthetic";folder.mkdir(parents=True)
            row=record(i)
            (folder/(folder.name+".jsonl")).write_text(json.dumps(row)+"\n")
            (folder/"story-cards.json").write_text(json.dumps({"story_id":f"synthetic-{i}"}))

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
        (folder/"story-cards.json").write_text(json.dumps({"story_id":"synthetic-2"}))
        r=m.screen(self.repo,self.old14,self.old0615)
        self.assertEqual(r["same_story_id_pair_count"],1)
        self.assertEqual(r["screen_status"],"LEXICAL_OR_IDENTITY_FLAGS_REQUIRE_AI_ADJUDICATION")

if __name__=="__main__": unittest.main()

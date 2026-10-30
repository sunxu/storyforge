"""Synthetic-only tests for R58 G1 metadata filename discovery. No real protected data."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from autodiscover_g1_index_candidates import (
    SCOPES, ROOTS, Hold, find_candidates, draft_rows, run,
)

class TestG1AutoDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.root=self.base/"evidence"
        self.root.mkdir(mode=0o700)
        self.out=self.base/"private"
        self.out.mkdir(mode=0o700)
        os.chmod(self.out,0o700)
    def tearDown(self):
        self.temp.cleanup()
    def make_file(self,relative,content="SECRET_SOURCE_CANARY"):
        p=self.root/relative
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(content,encoding="utf-8")
        return p
    def test_finds_known_world_and_exposure_names_without_reading(self):
        self.make_file("r52/world_review/r52_world_alias_roster.json")
        self.make_file("r52/history_exposure_with_r45/r45_exposure_ledger.csv")
        hits=find_candidates(self.root)
        self.assertEqual(len(hits["semantic_world_graph"]),1)
        self.assertEqual(len(hits["prior_sft_exposure"]),1)
        self.assertEqual(hits["r50_protected_worlds"],[])
    def test_never_traverses_r50_directory(self):
        self.make_file("r57/private/r50/r50_protected_world_index.json")
        self.make_file("r52/world_review/r50_protected_world_index.csv")
        hits=find_candidates(self.root)
        self.assertEqual(hits["r50_protected_worlds"],[])
        self.assertEqual(hits["semantic_world_graph"],[])
    def test_never_traverses_raw_sources(self):
        self.make_file("r57/private/raw/r57_world_roster.json")
        self.make_file("r52/world_review/originals/sft_exposure_index.json")
        self.assertTrue(all(not x for x in find_candidates(self.root).values()))
    def test_rejects_jsonl_and_nonmetadata_filenames(self):
        self.make_file("r57/private/r57_world_messages.json")
        self.make_file("r57/private/r57_world_inventory.jsonl")
        self.make_file("r57/private/r57_world_prompt.md")
        self.assertTrue(all(not x for x in find_candidates(self.root).values()))
    def test_draft_never_claims_coverage(self):
        found={scope:[] for scope in SCOPES}
        found["semantic_world_graph"]=["/tmp/synthetic_safe_world_index.json"]
        draft=draft_rows(found)
        self.assertEqual(len(draft),5)
        self.assertEqual(draft[0]["coverage_status"],"UNKNOWN")
        self.assertEqual(draft[0]["independent_review_status"],"PENDING")
        self.assertEqual(draft[0]["private_source_reference"],
                         "/tmp/synthetic_safe_world_index.json")
    def test_ambiguous_source_never_autofills(self):
        found={scope:[] for scope in SCOPES}
        found["prior_sft_exposure"]=["/tmp/a.json","/tmp/b.csv"]
        self.assertEqual(draft_rows(found)[2]["private_source_reference"],"")
    def test_stdout_safe_and_file_modes(self):
        self.make_file("r52/world_isolation/synthetic_world_graph.json","PRIVATE_METADATA_CONTENT_CANARY")
        safe=run(self.root,self.out/"candidates_private.json",self.out/"inventory_draft_private.csv")
        text=json.dumps(safe)
        self.assertNotIn("PRIVATE_METADATA_CONTENT_CANARY",text)
        self.assertNotIn(str(self.root),text)
        self.assertFalse(safe["protected_r50_directories_scanned"])
        self.assertEqual(safe["g1_clearance"],"HOLD")
        self.assertEqual((self.out/"candidates_private.json").stat().st_mode & 0o777,0o600)
        self.assertEqual((self.out/"inventory_draft_private.csv").stat().st_mode & 0o777,0o600)
        private=(self.out/"candidates_private.json").read_text()
        self.assertIn("synthetic_world_graph.json",private)
        self.assertNotIn("PRIVATE_METADATA_CONTENT_CANARY",private)
    def test_existing_outputs_rejected_and_unchanged(self):
        self.make_file("r52/world_review/synthetic_world_roster.csv")
        p=self.out/"draft.csv"
        p.write_text("ORIGINAL_PRIVATE")
        with self.assertRaises(Hold):
            run(self.root,self.out/"candidates.json",p)
        self.assertEqual(p.read_text(),"ORIGINAL_PRIVATE")
    def test_symlinked_candidate_is_not_followed(self):
        target=self.make_file("r52/world_review/real_world_index.json")
        link=target.parent/"link_world_index.json"
        link.symlink_to(target)
        result=find_candidates(self.root)
        self.assertEqual(len(result["semantic_world_graph"]),1)
    def test_non_private_output_directory_holds(self):
        self.make_file("r52/world_review/synthetic_world_index.json")
        os.chmod(self.out,0o755)
        with self.assertRaises(Hold):
            run(self.root,self.out/"candidate.json",self.out/"draft.csv")
if __name__=="__main__":
    unittest.main()

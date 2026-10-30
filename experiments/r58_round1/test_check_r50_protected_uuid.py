"""Synthetic-only R58 G1 R50 protected UUID match tests; no R50 cases read."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from check_r50_protected_uuid import (
    OWNER_POLICY, Hold, protected_ids, evaluate, read_private_holds,
    write_private, run,
)

def uid(n):
    return f"00000000-0000-0000-0000-{n:012d}"

def source():
    return {
        "source_commit":"a197923e1e15344e8c98bd96e593e84781b68c83",
        "source_root":"evaluations/v0.2/source-archives/16-20",
        "file_count":35,
        "worlds":[{"number":16+i,"folder":"safe_metadata",
                   "story_id":uid(i+1),"session_id":uid(i+31)} for i in range(5)],
    }

def coverage():
    return {"source_world_count":5,"candidate_case_count":46,"excluded_case_count":4,
            "per_world":{f"W{i}":{} for i in range(16,21)}}

def ledger():
    rows=[]
    for i in range(5):
        x=uid(i+1)
        old=(i==0)
        rows.append({
            "story_id_PRIVATE":x,
            "historical_sft_exact_uuid_overlap":old,
            "status":("EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if old else
                      "HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING"),
        })
    return {
        "schema":"r58_round1_g1_prior_sft_exact_id_holds_private_v2",
        "owner_world_identity_policy":OWNER_POLICY,
        "namespace_equivalence_owner_confirmed":True,
        "expansion_allowed":False,
        "entries":rows,
    }

class TestR50ExactUUID(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        os.chmod(self.root,0o700)
    def tearDown(self):
        self.temp.cleanup()
    def holds(self,body=None):
        p=self.root/"v2_sft_holds.json"
        p.write_text(json.dumps(body or ledger()))
        os.chmod(p,0o600)
        return p
    def test_five_source_uuid_set(self):
        ids=protected_ids(source(),coverage())
        self.assertEqual(len(ids),5)
        self.assertIn(uid(4),ids)
    def test_reject_missing_world_or_duplicate(self):
        v=source()
        v["worlds"][4]["story_id"]=uid(4)
        with self.assertRaises(Hold):protected_ids(v,coverage())
    def test_reject_other_r50_rank_even_if_five(self):
        v=source();v["worlds"][0]["number"]=15
        with self.assertRaises(Hold):protected_ids(v,coverage())
    def test_reject_wrong_later_case_coverage(self):
        v=coverage();v["per_world"].pop("W20")
        with self.assertRaises(Hold):protected_ids(source(),v)
    def test_only_non_sft_exposed_four_are_counted(self):
        safe,private=evaluate(ledger(),{uid(1),uid(2),uid(3)})
        self.assertEqual(safe["historical_sft_exact_uuid_excluded"],1)
        self.assertEqual(safe["r50_exact_uuid_matches_among_remaining_four"],2)
        self.assertEqual(safe["remaining_without_sft_or_r50_exact_uuid_match"],2)
        self.assertEqual(sum(x["status"].startswith("EXCLUDED_") for x in private),3)
        self.assertEqual(safe["g1_clearance"],"HOLD")
        self.assertNotIn(uid(2),json.dumps(safe))
    def test_zero_r50_matches_only_clears_r50_exact_uuid(self):
        safe,_=evaluate(ledger(),{uid(100),uid(101),uid(102),uid(103),uid(104)})
        self.assertEqual(safe["r50_exact_uuid_matches_among_remaining_four"],0)
        self.assertEqual(safe["remaining_without_sft_or_r50_exact_uuid_match"],4)
        self.assertFalse(safe["r55_r57_dev_uuid_check_completed"])
        self.assertFalse(safe["other_protected_uuid_check_completed"])
        self.assertEqual(safe["train_admitted"],0)
    def test_reject_invalid_private_permission(self):
        p=self.holds()
        os.chmod(p,0o644)
        with self.assertRaises(Hold):read_private_holds(p)
    def test_safe_run_and_private_output_never_overwrite(self):
        p=self.holds()
        output=self.root/"r50_holds.json"
        def fake_blob(_repo,sha):
            return source() if sha.startswith("2d8623c1") else coverage()
        with patch("check_r50_protected_uuid.blob_json",side_effect=fake_blob):
            safe=run(self.root,p,output)
            self.assertEqual(safe["r50_exact_uuid_matches_among_remaining_four"],4)
            self.assertTrue(safe["private_case_level_r50_hold_written"])
            self.assertEqual(output.stat().st_mode & 0o777,0o600)
            self.assertNotIn(uid(1),json.dumps(safe))
            before=output.read_bytes()
            with self.assertRaises(Hold):run(self.root,p,output)
            self.assertEqual(output.read_bytes(),before)

if __name__=="__main__":
    unittest.main()

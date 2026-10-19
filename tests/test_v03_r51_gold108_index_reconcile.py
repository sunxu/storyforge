"""Purely synthetic R51 Gold108 index crosswalk tests."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

folder=Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0,str(folder))
spec=importlib.util.spec_from_file_location(
    "crosswalk",folder / "v03_r51_gold108_index_reconcile.py"
)
assert spec and spec.loader
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    import hashlib
    rows=[]
    index=[]
    for number,n in sorted(m.EXPECTED_BY_STORY.items()):
        for i in range(n):
            id_=f"SYNTHETIC_{number}_{i}"
            content=f"Synthetic target content {id_}"
            digest=hashlib.sha256(content.encode()).hexdigest()
            rows.append({
                "id":id_,
                "messages":[
                    {"role":"user","content":"test"},
                    {"role":"assistant","content":content},
                ],
                "metadata":{
                    "story_id":f"SYNTHETIC_STORY_{number}",
                    "story_number":int(number),
                    "target_message_id":f"SYNTHETIC_SOURCE_{number}_{i}",
                    "target_sha256":digest,
                    "training_admission":"PENDING_NOT_APPROVED",
                    "split":None,
                },
            })
            index.append({
                "candidate_id":id_,
                "story_number":number,
                "story_id":f"SYNTHETIC_STORY_{number}",
                "target_message_id":f"SYNTHETIC_SOURCE_{number}_{i}",
                "target_sha256":digest,
                "reviewer1_decision":"ACCEPT",
                "reviewer2_decision":"ACCEPT",
                "training_admission":"PENDING_NOT_APPROVED",
                "split":"",
            })
    return rows,index


class IndexReconcileTests(unittest.TestCase):
    def test_108_originals_and_index_verified_without_admission(self):
        a,b=fixture()
        result=m.reconcile(a,b)
        self.assertEqual(result["record_count"],108)
        self.assertEqual(result["verified_target_hash_against_original_reply"],108)
        self.assertEqual(result["training_admitted_by_reconciliation"],0)

    def test_missing_original_metadata_recovered_only_as_crosswalk(self):
        a,b=fixture()
        for k in ("story_id","target_sha256","story_number"):
            del a[0]["metadata"][k]
        r=m.reconcile(a,b)
        self.assertEqual(r["metadata_story_id_gaps_resolved_by_frozen_index"],1)
        self.assertEqual(r["metadata_target_hash_gaps_resolved_by_frozen_index"],1)
        self.assertEqual(r["metadata_story_number_gaps_resolved_by_frozen_index"],1)

    def test_target_hash_tamper_hard_fails(self):
        a,b=fixture()
        a[1]["messages"][-1]["content"]="tampered"
        with self.assertRaisesRegex(ValueError,"R51_REVIEW_INDEX_TARGET_SHA_MISMATCH"):
            m.reconcile(a,b)

    def test_forged_duplicate_id_rejected(self):
        a,b=fixture()
        b[1]["candidate_id"]=b[0]["candidate_id"]
        with self.assertRaisesRegex(ValueError,
                                    "R51_INDEX_CANDIDATE_ID_MISSING_OR_DUPLICATED"):
            m.reconcile(a,b)

    def test_story_identity_mismatch_rejected(self):
        a,b=fixture()
        a[0]["metadata"]["story_id"]="FORGED"
        with self.assertRaisesRegex(ValueError,"R51_STORY_ID_INDEX_CONFLICT"):
            m.reconcile(a,b)

    def test_duplicate_review_cannot_be_falsely_accepted(self):
        a,b=fixture()
        b[0]["reviewer2_decision"]="HOLD"
        with self.assertRaisesRegex(ValueError,
                                    "R51_NOT_DOUBLE_ACCEPTED_IN_FROZEN_REVIEW_INDEX"):
            m.reconcile(a,b)


if __name__=="__main__":
    unittest.main()

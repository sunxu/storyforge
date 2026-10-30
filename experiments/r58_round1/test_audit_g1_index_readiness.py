"""Synthetic-only readiness preflight tests; never access real protected indices."""
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest

from audit_g1_index_readiness import SCOPES, COLUMNS, Hold, input_inventory, readiness

def rows():
    return {
        key: {
            "scope":key,
            "private_source_reference":"",
            "source_revision":"",
            "coverage_status":"UNKNOWN",
            "world_identity_namespace":"",
            "independent_review_status":"PENDING",
        } for key in SCOPES
    }

class TestReadiness(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        os.chmod(self.root, 0o700)
    def tearDown(self):
        self.temp.cleanup()
    def inventory(self,data):
        p=self.root/"inventory.csv"
        with p.open("w", encoding="utf-8", newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(COLUMNS))
            w.writeheader();w.writerows(list(data.values()))
        os.chmod(p,0o600)
        return p

    def test_blank_inventory_all_missing(self):
        result=readiness(input_inventory(self.inventory(rows())))
        self.assertEqual(result["scope_count"],5)
        self.assertEqual(result["source_files_present_unopened"],0)
        self.assertEqual(result["independently_verified_complete_scopes"],0)
        self.assertEqual(result["g1_clearance"],"HOLD")

    def test_existing_file_only_is_unverified(self):
        data=rows()
        p=self.root/"synthetic_manifest.json"
        p.write_text('{"synthetic":"safe"}')
        data["r50_protected_worlds"]["private_source_reference"]=str(p)
        result=readiness(data)
        state=result["scope_readiness"]["r50_protected_worlds"]
        self.assertTrue(state["source_file_exists_unopened"])
        self.assertEqual(state["status"],"SOURCE_FOUND_REVISION_MISSING")
        self.assertFalse(state["actual_index_coverage_verified"])

    def test_owner_attestation_still_requires_independent_review(self):
        data=rows()
        p=self.root/"source_safe.json"
        p.write_text("{}")
        k="prior_sft_exposure"
        data[k].update({
            "private_source_reference":str(p),
            "source_revision":"synthetic-freeze-v1",
            "coverage_status":"OWNER_COVERAGE_ATTESTED",
            "world_identity_namespace":"synthetic-semantic-world-v1",
            "independent_review_status":"INDEPENDENT_VERIFIED",
        })
        state=readiness(data)["scope_readiness"][k]
        self.assertEqual(state["status"],"OWNER_COVERAGE_CLAIM_ONLY__INDEPENDENT_CHECK_PENDING")
        self.assertTrue(state["independent_review_claim_in_inventory"])
        self.assertFalse(state["independent_review_proven_by_this_tool"])

    def test_missing_source_not_promoted_by_claims(self):
        data=rows()
        data["r55_r57_dev_worlds"].update({
            "source_revision":"x",
            "coverage_status":"OWNER_COVERAGE_ATTESTED",
            "world_identity_namespace":"v1",
        })
        state=readiness(data)["scope_readiness"]["r55_r57_dev_worlds"]
        self.assertEqual(state["status"],"MISSING_SOURCE_REFERENCE")

    def test_rejects_symlink_source(self):
        data=rows()
        p=self.root/"real.json";p.write_text("{}")
        link=self.root/"link.json";link.symlink_to(p)
        data["semantic_world_graph"]["private_source_reference"]=str(link)
        state=readiness(data)["scope_readiness"]["semantic_world_graph"]
        self.assertEqual(state["status"],"SOURCE_REFERENCE_NOT_VERIFIED")

    def test_private_ids_and_paths_do_not_escape(self):
        data=rows()
        path=self.root/"PRIVATE-STORY-IDENTIFIER-source.json"
        path.write_text("SECRET_CANARY_CONTENT")
        data["semantic_world_graph"]["private_source_reference"]=str(path)
        text=json.dumps(readiness(data))
        self.assertNotIn("PRIVATE-STORY-IDENTIFIER",text)
        self.assertNotIn(str(self.root),text)
        self.assertNotIn("SECRET_CANARY_CONTENT",text)
        self.assertFalse(json.loads(text)["source_index_bytes_read"])

    def test_missing_scope_holds(self):
        data=rows()
        data.pop("r50_protected_worlds")
        with self.assertRaises(Hold):
            input_inventory(self.inventory(data))

    def test_duplicate_scope_holds(self):
        data=rows()
        data["prior_sft_exposure"]["scope"]="r50_protected_worlds"
        with self.assertRaises(Hold):
            input_inventory(self.inventory(data))

    def test_permissions_guard(self):
        path=self.inventory(rows())
        os.chmod(path,0o644)
        with self.assertRaises(Hold):
            input_inventory(path)

if __name__=="__main__":
    unittest.main()

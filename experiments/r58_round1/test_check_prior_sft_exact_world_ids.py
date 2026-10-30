"""Synthetic-only R58 exact prior SFT world-ID overlap tests."""
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from check_prior_sft_exact_world_ids import (
    SCHEMA, ALLOWED_ROSTER_TOP, ALLOWED_ROSTER_RECORD, Hold,
    parse_exposed_roster, discover_roster, check,
)

def sid(n):
    return f"00000000-0000-0000-0000-{n:012d}"

def roster():
    records=[]
    for n in range(1,30):
        records.append({
            "source_story_uuid_PRIVATE":sid(n),
            "source_row_counts":{},
            "gold_final_targets_without_previous_exact_match":0,
            "same_exact_uuid_seen_in_previous_sft":n<=27,
            "owner_declared_component_token_PRIVATE":None,
            "owner_alias_evidence_references_PRIVATE":[],
            "owner_alias_semantic_review_status":"PENDING_NOT_VERIFIED",
            "owner_signoff_status":"NOT_SIGNED",
            "dataset_v04_decision":"HOLD_NOT_REVIEWED",
        })
    return {
        "schema":"storyforge-r57-g2-owner-private-world-alias-review-roster-v1",
        "purpose":"OWNER_MANUAL_SEMANTIC_ALIAS_AND_WORLD_COMPONENT_EVIDENCE_REVIEW_ONLY",
        "sources_frozen_byte_identity_checked_by_cli":False,
        "independent_semantic_world_link_certified":False,
        "training_authorized":False,
        "v04_admitted_rows":0,
        "worlds":records,
    }

class TestExactOverlap(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.base=Path(self.tmp.name)
        self.root=self.base/"r57"/"private"
        self.root.mkdir(parents=True,mode=0o700)
        self.owner=self.base/"owner"
        self.owner.mkdir(mode=0o700)
        os.chmod(self.owner,0o700)
    def tearDown(self):
        self.tmp.cleanup()
    def private_json(self,path,data):
        path.write_text(json.dumps(data),encoding="utf-8")
        os.chmod(path,0o600)
        return path
    def queue(self,ids):
        path=self.owner/"queue.csv"
        keys=["story_id","source_type","review_state","world_component",
              "owner_world_graph_reviewed","r50_protected_clear",
              "prior_sft_clear","r55_r57_dev_clear","other_protected_clear",
              "evidence_reference"]
        with path.open("w",encoding="utf-8",newline="") as h:
            writer=csv.DictWriter(h,fieldnames=keys)
            writer.writeheader()
            for x in ids:
                row={k:"" for k in keys}
                row.update({"story_id":x,"source_type":"original",
                            "review_state":"G1_HOLD"})
                for gate in keys[4:9]:
                    row[gate]="false"
                writer.writerow(row)
        os.chmod(path,0o600)
        return path
    def discovery(self,candidates):
        return self.private_json(self.owner/"discovery.json",{
            "schema":"r58_g1_filename_candidates_private_v1",
            "candidate_paths_by_scope":{
                "semantic_world_graph":[str(p) for p in candidates],
                "r55_r57_dev_worlds":[],
            },
        })
    def roster_path(self,name="R57_G2_WORLD_ALIAS_REVIEW_20261030_210000_PRIVATE.json"):
        return self.root/name
    def test_exact_overlap_is_risk_not_admission(self):
        p=self.private_json(self.roster_path(),roster())
        result=check(self.queue([sid(1),sid(28),sid(29)]),self.discovery([p]),self.root)
        self.assertEqual(result["exact_identifier_overlap_count"],1)
        self.assertIn("OVERLAP_FOUND",result["status"])
        self.assertFalse(result["no_match_means_all_protected_sets_clear"])
        self.assertTrue(result["owner_attested_one_uuid_one_world"])
        self.assertFalse(result["cross_uuid_semantic_review_required"])
        self.assertEqual(result["train_admitted"],0)
    def test_zero_exact_overlap_not_clean(self):
        p=self.private_json(self.roster_path(),roster())
        result=check(self.queue([sid(28),sid(29)]),self.discovery([p]),self.root)
        self.assertEqual(result["exact_identifier_overlap_count"],0)
        self.assertIn("OTHER_PROTECTED_SET_HOLD",result["status"])
        self.assertEqual(result["candidate_id_namespace"],"OWNER_CONFIRMED_ROLEPLAY_STORY_UUID")
        self.assertEqual(result["g1_clearance"],"HOLD")
    def test_missing_roster_holds(self):
        result=check(self.queue([sid(1)]),self.discovery([]),self.root)
        self.assertIn("ROSTER_MISSING",result["status"])
        self.assertIsNone(result["exact_identifier_overlap_count"])
    def test_multiple_rosters_holds(self):
        a=self.private_json(self.roster_path(),roster())
        b=self.private_json(self.roster_path("R57_G2_WORLD_ALIAS_REVIEW_20261030_220000_PRIVATE.json"),roster())
        result=check(self.queue([sid(1)]),self.discovery([a,b]),self.root)
        self.assertIn("AMBIGUOUS",result["status"])
        self.assertFalse(result["r57_roster_schema_verified"])
    def test_unexpected_metadata_fields_fail_closed(self):
        v=roster()
        v["worlds"][0]["story_text"]="SECRET_STRING"
        with self.assertRaises(Hold):
            parse_exposed_roster(v)
    def test_wrong_historical_roster_size_holds(self):
        v=roster()
        v["worlds"].pop()
        with self.assertRaises(Hold):
            parse_exposed_roster(v)
    def test_symlink_roster_holds(self):
        a=self.private_json(self.roster_path("other.json"),roster())
        b=self.roster_path();b.symlink_to(a)
        with self.assertRaises(Hold):
            discover_roster({"schema":"r58_g1_filename_candidates_private_v1",
                             "candidate_paths_by_scope":{"semantic_world_graph":[str(b)],
                             "r55_r57_dev_worlds":[]}},self.root)
    def test_safe_json_does_not_echo_uuid_or_path(self):
        p=self.private_json(self.roster_path(),roster())
        result=check(self.queue([sid(1)]),self.discovery([p]),self.root)
        raw=json.dumps(result)
        self.assertNotIn(sid(1),raw)
        self.assertNotIn(str(self.root),raw)
        self.assertFalse(result["r50_protection_checked"])
        self.assertFalse(result["candidate_reply_text_accessed"])
    def test_private_hold_ledger_has_exactly_one_collision_and_four_hold(self):
        p=self.private_json(self.roster_path(),roster())
        ids=[sid(1),sid(28),sid(29),sid(30),sid(31)]
        queue=self.queue(ids)
        original=queue.read_bytes()
        out=self.owner/"g1_holds_private.json"
        result=check(queue,self.discovery([p]),self.root,out)
        self.assertTrue(result["private_five_story_hold_ledger_written"])
        self.assertEqual(result["private_ledger_case_count"],5)
        self.assertEqual(out.stat().st_mode & 0o777,0o600)
        private=json.loads(out.read_text())
        self.assertEqual(len(private["entries"]),5)
        self.assertEqual(sum(e["historical_sft_exact_uuid_overlap"]
                             for e in private["entries"]),1)
        self.assertEqual(sum(e["status"].startswith("EXCLUDED_") for e in private["entries"]),1)
        self.assertEqual(sum(e["status"].startswith("HOLD_") for e in private["entries"]),4)
        self.assertTrue(all(not e["train_admitted"] for e in private["entries"]))
        self.assertEqual(queue.read_bytes(),original)
        self.assertNotIn(ids[0],json.dumps(result))

    def test_private_hold_ledger_must_not_overwrite(self):
        p=self.private_json(self.roster_path(),roster())
        queue=self.queue([sid(1)])
        manifest=self.discovery([p])
        out=self.owner/"g1_holds_private.json"
        out.write_text("original private contents")
        with self.assertRaises(Hold):
            check(queue,manifest,self.root,out)
        self.assertEqual(out.read_text(),"original private contents")

    def test_missing_roster_does_not_create_private_hold_ledger(self):
        out=self.owner/"g1_holds_private.json"
        with self.assertRaises(Hold):
            check(self.queue([sid(1)]),self.discovery([]),self.root,out)
        self.assertFalse(out.exists())

    def test_unsafe_world_guard_stays_false_in_hold_ledger(self):
        p=self.private_json(self.roster_path(),roster())
        out=self.owner/"g1_holds_private.json"
        check(self.queue([sid(1),sid(28)]),self.discovery([p]),self.root,out)
        obj=json.loads(out.read_text())
        self.assertTrue(obj["namespace_equivalence_owner_confirmed"])
        self.assertFalse(obj["cross_uuid_semantic_world_review_required"])
        self.assertFalse(obj["expansion_allowed"])
        for entry in obj["entries"]:
            self.assertTrue(entry["owner_attested_distinct_semantic_world"])
            self.assertEqual(entry["owner_attested_world_component_UUID"],entry["story_id_PRIVATE"])
            self.assertFalse(entry["r50_protected_clear"])
            self.assertFalse(entry["prior_sft_clear"])
            self.assertFalse(entry["r55_r57_dev_clear"])
            self.assertFalse(entry["other_protected_clear"])

    def test_owner_uuid_policy_never_clears_r50_or_dev(self):
        p=self.private_json(self.roster_path(),roster())
        output=check(self.queue([sid(28),sid(29)]),self.discovery([p]),self.root)
        self.assertEqual(output["owner_attested_distinct_worlds_in_queue"],2)
        self.assertEqual(output["r57_roster_only_exact_id_nonoverlap_count"],2)
        self.assertFalse(output["cross_uuid_semantic_review_required"])
        self.assertFalse(output["r50_protection_checked"])
        self.assertFalse(output["other_protected_worlds_checked"])
        self.assertEqual(output["g1_clearance"],"HOLD")
        self.assertEqual(output["train_admitted"],0)

    def test_owner_policy_rejects_non_uuid_story_id(self):
        p=self.private_json(self.roster_path(),roster())
        with self.assertRaises(Hold):
            check(self.queue(["non-uuid-but-previously-valid"]),self.discovery([p]),self.root)

    def test_source_roster_field_contract(self):
        v=roster()
        self.assertEqual(set(v),ALLOWED_ROSTER_TOP)
        self.assertEqual(set(v["worlds"][0]),ALLOWED_ROSTER_RECORD)
        self.assertEqual(len(parse_exposed_roster(v)),27)

if __name__=="__main__":
    unittest.main()

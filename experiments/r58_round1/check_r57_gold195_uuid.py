#!/usr/bin/env python3
"""R58 G1: owner-local R57 Gold195 source-UUID overlap for four remaining stories.

Checks only the existing 29-row R57 metadata roster, v2 prior SFT UUID
ledger, and R50 private exclusion ledger. Does not read roleplay turns,
Gold replies, R50 examples, or old Dev20 contents. This does NOT certify
coverage of the R55/R57 20-case old Test Dev suite or other holdouts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from check_prior_sft_exact_world_ids import (
    OWNER_IDENTITY_POLICY,
    discover_roster,
    parse_exposed_roster,
    private_json,
)
from check_r50_protected_uuid import read_private_holds

SCHEMA="r58_round1_g1_r57_gold195_uuid_safe_v1"
UUID=re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$",re.IGNORECASE)
EXPECTED_SOURCES={"GOLD87","GOLD108","V01_TRAIN","V01_VALIDATION",
                  "R46_TRAIN","R46_VALIDATION","R54_TRAIN","R54_VALIDATION"}

class Hold(Exception):
    pass

def read_r50_private(path:Path,base:dict)->list[dict]:
    src=private_json(path,150000)
    if (not isinstance(src,dict)
        or src.get("schema")!="r58_round1_g1_r50_protection_private_v1"
        or src.get("status")!="NO_GLOBAL_G1_CLEARANCE"
        or src.get("owner_world_identity_policy")!=OWNER_IDENTITY_POLICY
        or src.get("expansion_allowed") is not False
        or not isinstance(src.get("entries"),list)
        or len(src["entries"])!=5):
        raise Hold("R50 private metadata ledger invalid")
    original={r["story_id_PRIVATE"].lower():r for r in base["entries"]}
    seen=set()
    for row in src["entries"]:
        if not isinstance(row,dict):raise Hold("R50 ledger record invalid")
        sid=row.get("story_id_PRIVATE")
        if not isinstance(sid,str) or not UUID.fullmatch(sid) or sid.lower() in seen:
            raise Hold("R50 ledger UUID duplicate or invalid")
        seen.add(sid.lower())
        prior=original.get(sid.lower())
        if prior is None or (row.get("historically_sft_exposed")
                            is not prior["historical_sft_exact_uuid_overlap"]):
            raise Hold("SFT/R50 ledger story mismatch")
        if row.get("r50_exact_story_uuid_match") is not False:
            # Current Owner report had 0 R50 exact overlaps across remaining 4;
            # historical exposed row may also overlap R50 but remains excluded.
            if not prior["historical_sft_exact_uuid_overlap"]:
                raise Hold("R50 protected story cannot advance to Gold stage")
    if seen!=set(original):
        raise Hold("R50 ledger does not cover fixed five")
    return src["entries"]

def r57_gold_ids(obj:dict)->set[str]:
    exposed=parse_exposed_roster(obj)
    worlds=obj["worlds"]
    gold=set()
    for row in worlds:
        sources=row.get("source_row_counts")
        if not isinstance(sources,dict) or set(sources)!=EXPECTED_SOURCES:
            raise Hold("R57 Gold source membership metadata incomplete")
        if any(type(v) is not int or v<0 for v in sources.values()):
            raise Hold("invalid Gold source membership count")
        sid=row["source_story_uuid_PRIVATE"].lower()
        if sources["GOLD87"]+sources["GOLD108"]>0:
            gold.add(sid)
    if len(gold)!=13 or len(gold-exposed)!=2:
        raise Hold("R57 Gold195 13 worlds / 2 previously-unexposed source UUIDs mismatch")
    return gold

def evaluate(private_sft:dict,r50_entries:list[dict],gold:set[str])->tuple[dict,list[dict]]:
    current={r["story_id_PRIVATE"].lower():r for r in r50_entries}
    out=[]; hit=0; pending=0
    for row in private_sft["entries"]:
        uid=row["story_id_PRIVATE"].lower()
        r50=current[uid]
        old=row["historical_sft_exact_uuid_overlap"]
        collision=uid in gold
        if not old and not r50["r50_exact_story_uuid_match"]:
            pending+=1
            hit+=int(collision)
        status=("EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if old
                else "EXCLUDED_R50_PROTECTED_STORY_UUID" if r50["r50_exact_story_uuid_match"]
                else "HOLD_R57_GOLD195_SOURCE_UUID_EXPOSURE" if collision
                else "HOLD_LEGACY_DEV20_OTHER_PROTECTED_AND_SFT_COVERAGE")
        out.append({
            "story_id_PRIVATE":uid,"historical_sft_uuid_exposed":old,
            "r50_protected_uuid_match":r50["r50_exact_story_uuid_match"],
            "r57_gold195_source_uuid_match":collision,"status":status,
            "train_admitted":False,"expansion_allowed":False,
        })
    if pending!=4:
        raise Hold("expected four non-SFT/non-R50 stories")
    safe={
        "schema":SCHEMA,
        "status":"R58_G1_R57_GOLD195_EXACT_UUID_CHECK_DONE__LEGACY_DEV_AND_OTHER_HOLD",
        "fixed_stories":5,
        "prior_sft_exposed_excluded":1,
        "r50_matched_among_remaining_four":0,
        "r57_gold195_source_story_uuids":len(gold),
        "r57_gold195_exact_uuid_matches_among_remaining_four":hit,
        "remaining_without_sft_r50_or_r57_gold_source_uuid_match":4-hit,
        "r57_gold_metadata_schema_validated":True,
        "legacy_r47_r48_r55_r57_dev20_uuid_index_covered":False,
        "other_protected_uuids_covered":False,
        "source_registry_complete":False,
        "candidate_story_content_accessed":False,
        "r50_protected_test_content_accessed":False,
        "g1_clearance":"HOLD",
        "train_admitted":0,"validation_admitted":0,"teacher_admitted":0,
        "expansion_allowed":False,
    }
    return safe,out

def save_private(path:Path,data:dict):
    parent=path.parent
    if (path.exists() or path.is_symlink() or not parent.is_dir()
        or parent.is_symlink() or parent.stat().st_mode & 0o077):
        raise Hold("private output unsafe or exists")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as h:
            json.dump(data,h,ensure_ascii=False,indent=2);h.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def run(sft_holds:Path,r50_holds:Path,discovery:Path,r57_root:Path,
        private_output:Path|None=None):
    sft=read_private_holds(sft_holds)
    r50=read_r50_private(r50_holds,sft)
    candidates=discover_roster(private_json(discovery,300000),r57_root)
    if len(candidates)!=1:
        raise Hold("R57 unique source world roster unavailable")
    gold=r57_gold_ids(private_json(candidates[0],400000))
    safe,rows=evaluate(sft,r50,gold)
    if private_output is not None:
        save_private(private_output,{
            "schema":"r58_round1_g1_r57_gold195_uuid_private_v1",
            "owner_uuid_world_policy":OWNER_IDENTITY_POLICY,
            "status":"PROTECTED_METADATA_ONLY__NOT_ADMITTED",
            "entries":rows,
            "legacy_dev20_and_other_protected_uuids_pending":True,
            "expansion_allowed":False,
        })
        safe["private_case_hold_ledger_written"]=True
    return safe

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--private-sft-holds",type=Path,required=True)
    p.add_argument("--private-r50-holds",type=Path,required=True)
    p.add_argument("--private-discovery",type=Path,required=True)
    p.add_argument("--r57-private-root",type=Path,
                   default=Path.home()/".local/share/storyforge/r57/private")
    p.add_argument("--private-output",type=Path)
    a=p.parse_args()
    try:
        print(json.dumps(run(a.private_sft_holds,a.private_r50_holds,
                             a.private_discovery,a.r57_private_root,a.private_output),
                         sort_keys=True,ensure_ascii=False,indent=2))
        return 0
    except (Hold,OSError,KeyError,TypeError,ValueError):
        print("R58_G1_R57_GOLD: HOLD (private metadata mismatch)",file=sys.stderr)
        return 42
if __name__=="__main__":
    raise SystemExit(main())

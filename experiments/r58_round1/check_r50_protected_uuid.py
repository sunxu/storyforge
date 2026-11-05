#!/usr/bin/env python3
"""R58 G1: R50 protected STORY UUID intersection using TWO pinned SAFE Git blobs.

No R50 cases, prompts, answers, test examples, or source archives read. The
Git blobs are R50 source-identity and admission-count SAFE receipts only.
Only 4 frozen non-SFT-exposed RolePlay stories are compared. Outputs SAFE
counts; optional private file stores case-level flags, never GitHub.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA="r58_round1_g1_r50_protected_uuid_safe_v1"
SOURCE_SHA="2d8623c17ef230d8eff5797a5eb29850e97e6ccb"
COVERAGE_SHA="20341c6c55bd4564140b05e8319cf66e572137c0"
OWNER_POLICY="OWNER_ATTESTED_ROLEPLAY_UUID_ONE_UUID_ONE_WORLD_V1"
UUID=re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$",re.IGNORECASE)

class Hold(ValueError):
    pass

def blob_json(repo:Path,sha:str)->dict:
    if not (repo/".git").exists():
        raise Hold("git checkout missing")
    try:
        proc=subprocess.run(
            ["git","-C",str(repo),"cat-file","blob",sha],
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=15,check=False,
        )
    except (OSError,subprocess.TimeoutExpired):
        raise Hold("frozen Git SAFE evidence unavailable")
    if proc.returncode or not (0<len(proc.stdout)<=100000):
        raise Hold("Git evidence blob missing or too large")
    try:
        item=json.loads(proc.stdout)
    except (ValueError,UnicodeError):
        raise Hold("invalid pinned SAFE receipt")
    if not isinstance(item,dict):
        raise Hold("invalid SAFE receipt structure")
    return item

def protected_ids(src:dict,coverage:dict)->set[str]:
    if (src.get("source_commit")!="a197923e1e15344e8c98bd96e593e84781b68c83"
        or src.get("source_root")!="evaluations/v0.2/source-archives/16-20"
        or src.get("file_count")!=35):
        raise Hold("R50 source identity mismatch")
    worlds=src.get("worlds")
    if not isinstance(worlds,list) or len(worlds)!=5:
        raise Hold("R50 source world list incomplete")
    ids=set()
    numbers=set()
    for row in worlds:
        if (not isinstance(row,dict)
            or set(row)!={"number","folder","story_id","session_id"}):
            raise Hold("R50 source metadata row not expected")
        raw=row["story_id"]
        if not isinstance(raw,str) or not UUID.fullmatch(raw):
            raise Hold("R50 protected story UUID invalid")
        if type(row["number"]) is not int or row["number"] in numbers:
            raise Hold("R50 source world rank duplicate")
        numbers.add(row["number"])
        ids.add(raw.lower())
    if len(ids)!=5 or numbers!=set(range(16,21)):
        raise Hold("R50 protected source world count mismatch")
    # The later 46-case receipt is a second, independent fixed blob.
    if (coverage.get("source_world_count")!=5
        or coverage.get("candidate_case_count")!=46
        or coverage.get("excluded_case_count")!=4
        or not isinstance(coverage.get("per_world"),dict)
        or set(coverage["per_world"])!={f"W{i}" for i in range(16,21)}):
        raise Hold("R50 later case-count coverage mismatch")
    return ids

def read_private_holds(path:Path)->dict:
    if not path.is_file() or path.is_symlink():
        raise Hold("private v2 hold ledger missing")
    st=path.stat()
    if st.st_mode & 0o077 or not (0<st.st_size<=150000):
        raise Hold("private hold ledger permissions/size")
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError,ValueError):
        raise Hold("private ledger invalid")
    if (not isinstance(obj,dict)
        or obj.get("schema")!="r58_round1_g1_prior_sft_exact_id_holds_private_v2"
        or obj.get("owner_world_identity_policy")!=OWNER_POLICY
        or obj.get("namespace_equivalence_owner_confirmed") is not True
        or obj.get("expansion_allowed") is not False):
        raise Hold("private UUID policy evidence mismatch")
    rows=obj.get("entries")
    if not isinstance(rows,list) or len(rows)!=5:
        raise Hold("private frozen pilot must have five records")
    seen=set(); exposed=0
    for row in rows:
        if not isinstance(row,dict):
            raise Hold("invalid private ledger row")
        id_=row.get("story_id_PRIVATE")
        if not isinstance(id_,str) or not UUID.fullmatch(id_) or id_.lower() in seen:
            raise Hold("invalid or duplicate private story UUID")
        seen.add(id_.lower())
        collision=row.get("historical_sft_exact_uuid_overlap")
        if type(collision) is not bool:
            raise Hold("historical exposure flag missing")
        if row.get("status") != (
            "EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if collision else
            "HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING"
        ):
            raise Hold("historical SFT status mismatch")
        exposed+=int(collision)
    if exposed!=1:
        raise Hold("frozen pilot exposure count changed")
    return obj

def evaluate(ledger:dict,protected:set[str])->tuple[dict,list[dict]]:
    original=ledger["entries"]
    remaining=[r for r in original if not r["historical_sft_exact_uuid_overlap"]]
    if len(remaining)!=4:
        raise Hold("current non-SFT-exposed count mismatch")
    hits=sum(row["story_id_PRIVATE"].lower() in protected for row in remaining)
    private_rows=[]
    for row in original:
        id_=row["story_id_PRIVATE"]
        old=bool(row["historical_sft_exact_uuid_overlap"])
        r50=id_.lower() in protected
        private_rows.append({
            "story_id_PRIVATE":id_,
            "historically_sft_exposed":old,
            "r50_exact_story_uuid_match":r50,
            "status":(
                "EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if old else
                "EXCLUDED_R50_PROTECTED_STORY_UUID" if r50 else
                "HOLD_R55_R57_DEV_OTHER_PROTECTED_AND_SOURCE_COVERAGE"
            ),
            "r55_r57_dev_clear":False,
            "other_protected_clear":False,
            "train_admitted":False,
        })
    safe={
        "schema":SCHEMA,
        "status":"R58_G1_R50_EXACT_UUID_INTERSECTION_DONE__OTHER_GATES_HOLD",
        "owner_identity_policy":OWNER_POLICY,
        "frozen_story_records":5,
        "historical_sft_exact_uuid_excluded":1,
        "non_sft_exposed_checked_for_r50":4,
        "r50_frozen_protected_story_uuids":5,
        "r50_source_blob_pin_verified":True,
        "r50_46_case_receipt_blob_pin_verified":True,
        "r50_exact_uuid_matches_among_remaining_four":hits,
        "remaining_without_sft_or_r50_exact_uuid_match":4-hits,
        "candidate_or_protected_test_text_accessed":False,
        "r50_original_test_content_accessed":False,
        "r55_r57_dev_uuid_check_completed":False,
        "other_protected_uuid_check_completed":False,
        "g1_clearance":"HOLD",
        "train_admitted":0,
        "validation_admitted":0,
        "teacher_admitted":0,
        "expansion_allowed":False,
    }
    return safe,private_rows

def write_private(path:Path,body:dict):
    parent=path.parent
    if (path.exists() or path.is_symlink() or not parent.is_dir()
        or parent.is_symlink() or parent.stat().st_mode & 0o077):
        raise Hold("private output exists or unsafe")
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(body,out,ensure_ascii=False,indent=2)
            out.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def run(repo:Path,holds:Path,private_output:Path|None=None)->dict:
    ledger=read_private_holds(holds)
    src=blob_json(repo,SOURCE_SHA)
    coverage=blob_json(repo,COVERAGE_SHA)
    protect=protected_ids(src,coverage)
    safe,private_rows=evaluate(ledger,protect)
    if private_output is not None:
        write_private(private_output,{
            "schema":"r58_round1_g1_r50_protection_private_v1",
            "source_blob_sha_PRIVATE":SOURCE_SHA,
            "coverage_blob_sha_PRIVATE":COVERAGE_SHA,
            "owner_world_identity_policy":OWNER_POLICY,
            "status":"NO_GLOBAL_G1_CLEARANCE",
            "entries":private_rows,
            "protected_set_gates_pending":["r55_r57_dev","other_protected","prior_sft_source_completeness"],
            "expansion_allowed":False,
        })
        safe["private_case_level_r50_hold_written"]=True
    return safe

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--private-sft-holds",type=Path,required=True)
    ap.add_argument("--private-output",type=Path)
    args=ap.parse_args()
    try:
        print(json.dumps(run(args.repo_root,args.private_sft_holds,args.private_output),
                         ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (Hold,OSError,TypeError,KeyError,ValueError):
        print("R58_G1_R50: HOLD (pinned SAFE source or private input)",file=sys.stderr)
        return 42

if __name__=="__main__":
    raise SystemExit(main())

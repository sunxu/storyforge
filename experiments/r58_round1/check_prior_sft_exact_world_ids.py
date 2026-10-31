#!/usr/bin/env python3
"""R58 G1: Owner-local exact-identifier exposure check for the FIVE fixed stories.

Only opens (1) the already-frozen private G1 metadata queue, (2) filename
discovery manifest, and (3) one explicitly schema-checked R57 private
world/alias UUID roster. Never opens messages, R50, or story content.
An exact match establishes historical UUID exposure under the Owner-confirmed RolePlay identity policy; a miss clears only the frozen R57 27-UUID set, never R50/dev/other protected sets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from audit_g1_structural_overlap import load_queue

SCHEMA="r58_round1_g1_prior_sft_exact_id_safe_v2"
OWNER_IDENTITY_POLICY="OWNER_ATTESTED_ROLEPLAY_UUID_ONE_UUID_ONE_WORLD_V1"
EXPECTED_ROSTER_SCHEMA="storyforge-r57-g2-owner-private-world-alias-review-roster-v1"
ROSTER_RE=re.compile(r"^R57_G2_WORLD_ALIAS_REVIEW_[0-9]{8}_[0-9]{6}_PRIVATE\.json$")
UUID=re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$",re.I)
ALLOWED_ROSTER_RECORD={
  "source_story_uuid_PRIVATE","source_row_counts",
  "gold_final_targets_without_previous_exact_match",
  "same_exact_uuid_seen_in_previous_sft",
  "owner_declared_component_token_PRIVATE",
  "owner_alias_evidence_references_PRIVATE",
  "owner_alias_semantic_review_status","owner_signoff_status",
  "dataset_v04_decision",
}
ALLOWED_ROSTER_TOP={
  "schema","purpose","sources_frozen_byte_identity_checked_by_cli",
  "independent_semantic_world_link_certified","training_authorized",
  "v04_admitted_rows","worlds",
}

class Hold(Exception):
    pass

def private_json(path:Path,maximum:int):
    if path.is_symlink() or not path.is_file():
        raise Hold("private evidence path invalid")
    st=path.stat()
    if (st.st_mode & 0o077) or not (0<st.st_size<=maximum):
        raise Hold("private evidence permission or size HOLD")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError,ValueError):
        raise Hold("private evidence JSON invalid")

def discover_roster(manifest,private_root:Path):
    if (not isinstance(manifest,dict) or
        manifest.get("schema")!="r58_g1_filename_candidates_private_v1"):
        raise Hold("private discovery manifest schema HOLD")
    groups=manifest.get("candidate_paths_by_scope")
    if not isinstance(groups,dict):
        raise Hold("private candidate groups invalid")
    items=[]
    for scope in ("semantic_world_graph","r55_r57_dev_worlds"):
        group=groups.get(scope)
        if not isinstance(group,list):
            raise Hold("private candidate category missing")
        for raw in group:
            if not isinstance(raw,str) or len(raw)>1024:
                raise Hold("invalid private candidate path")
            path=Path(raw)
            if ROSTER_RE.fullmatch(path.name):
                if (not path.is_absolute() or path.is_symlink()
                    or not path.resolve().is_relative_to(private_root.resolve())):
                    raise Hold("R57 roster path boundary HOLD")
                items.append(path)
    return sorted(set(items))

def parse_exposed_roster(obj):
    if not isinstance(obj,dict) or set(obj)!=ALLOWED_ROSTER_TOP:
        raise Hold("R57 private roster top-level schema mismatch")
    if obj.get("schema")!=EXPECTED_ROSTER_SCHEMA:
        raise Hold("R57 roster schema mismatch")
    worlds=obj.get("worlds")
    if not isinstance(worlds,list) or len(worlds)!=29:
        raise Hold("R57 roster expected 29 source UUID records")
    seen=set()
    exposed=set()
    for row in worlds:
        if not isinstance(row,dict) or set(row)!=ALLOWED_ROSTER_RECORD:
            raise Hold("R57 roster record schema mismatch")
        sid=row["source_story_uuid_PRIVATE"]
        if not isinstance(sid,str) or not UUID.fullmatch(sid):
            raise Hold("R57 world UUID format mismatch")
        sid=sid.lower()
        if sid in seen:
            raise Hold("duplicate historical story UUID")
        seen.add(sid)
        exp=row["same_exact_uuid_seen_in_previous_sft"]
        if type(exp) is not bool:
            raise Hold("historical exposure flag not boolean")
        if exp:
            exposed.add(sid)
    if len(exposed)!=27:
        raise Hold("historical SFT UUID roster count mismatch")
    return exposed

def save_private_holds(path:Path, ids:list[str], exposed:set[str],
                       source_roster:Path):
    """Immutable private case-level HOLD record; never returned to stdout."""
    parent=path.parent
    if (path.exists() or path.is_symlink() or not parent.is_dir()
        or parent.is_symlink() or (parent.stat().st_mode & 0o077)):
        raise Hold("private HOLD output path invalid or exists")
    entries=[]
    for sid in ids:
        collision=UUID.fullmatch(sid) is not None and sid.lower() in exposed
        entries.append({
            "story_id_PRIVATE":sid,
            "historical_sft_exact_uuid_overlap":collision,
            "status":("EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE"
                      if collision else
                      "HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING"),
            "owner_attested_world_component_UUID":sid.lower(),
            "owner_attested_distinct_semantic_world":True,
            "historical_sft_exact_uuid_set_nonoverlap":not collision,
            "r50_protected_clear":False,
            "prior_sft_clear":False,
            "r55_r57_dev_clear":False,
            "other_protected_clear":False,
            "train_admitted":False,
        })
    ledger={
        "schema":"r58_round1_g1_prior_sft_exact_id_holds_private_v2",
        "owner_world_identity_policy":OWNER_IDENTITY_POLICY,
        "status":"G1_FIVE_STORIES_HOLD_ONLY__NOT_ADMITTED",
        "roster_bytes_sha256_PRIVATE":hashlib.sha256(source_roster.read_bytes()).hexdigest(),
        "namespace_equivalence_owner_confirmed":True,
        "cross_uuid_semantic_world_review_required":False,
        "entries":entries,
        "frozen_queue_unmodified":True,
        "expansion_allowed":False,
    }
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            json.dump(ledger,handle,indent=2,ensure_ascii=False)
            handle.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return len(entries)


def check(queue:Path,discovery:Path,private_root:Path,
          private_hold_output:Path|None=None):
    ids=load_queue(queue)
    manifest=private_json(discovery,300000)
    matches=discover_roster(manifest,private_root)
    safe={
        "schema":SCHEMA,
        "status":"R58_G1_PRIOR_SFT_EXACT_ID_EVIDENCE_NOT_RESOLVED__HOLD",
        "frozen_candidate_stories_checked":len(ids),
        "candidate_id_namespace":"OWNER_CONFIRMED_ROLEPLAY_STORY_UUID",
        "owner_world_identity_policy":OWNER_IDENTITY_POLICY,
        "owner_attested_one_uuid_one_world":True,
        "cross_uuid_semantic_review_required":False,
        "r57_roster_candidates_found":len(matches),
        "r57_roster_schema_verified":False,
        "r57_historical_sft_uuid_count_verified":False,
        "exact_identifier_overlap_count":None,
        "no_match_means_all_protected_sets_clear":False,
        "r57_exact_uuid_no_match_counts_as_clear_for_r57_roster_only":True,
        "r50_protection_checked":False,
        "other_protected_worlds_checked":False,
        "private_story_text_accessed":False,
        "candidate_reply_text_accessed":False,
        "owner_attested_distinct_worlds_in_queue":len(ids),
        "independently_rechecked_semantic_worlds":0,
        "g1_clearance":"HOLD",
        "train_admitted":0,
        "validation_admitted":0,
        "teacher_admitted":0,
        "expansion_allowed":False,
    }
    if len(matches)!=1:
        if private_hold_output is not None:
            raise Hold("cannot generate private case ledger without a unique roster")
        safe["status"]=(
            "R58_G1_R57_ROSTER_MISSING__HOLD" if len(matches)==0
            else "R58_G1_R57_ROSTER_AMBIGUOUS__HOLD")
        return safe
    source=private_json(matches[0],400000)
    exposed=parse_exposed_roster(source)
    if any(not UUID.fullmatch(x) for x in ids):
        raise Hold("RolePlay candidate IDs must be canonical UUIDs")
    exact=sum(x.lower() in exposed for x in ids)
    if private_hold_output is not None:
        save_private_holds(private_hold_output,ids,exposed,matches[0])
        safe["private_five_story_hold_ledger_written"]=True
        safe["private_ledger_case_count"]=len(ids)
        safe["private_ledger_all_cases_hold"]=True
        safe["frozen_queue_unmodified"]=True
    safe.update({
        "r57_roster_schema_verified":True,
        "r57_historical_sft_uuid_count_verified":True,
        "exact_identifier_overlap_count":exact,
        "r57_roster_only_exact_id_nonoverlap_count":len(ids)-exact,
        "candidate_ids_in_uuid_syntax":sum(UUID.fullmatch(x) is not None for x in ids),
        "status":("R58_G1_PRIOR_SFT_EXACT_UUID_OVERLAP_FOUND__HOLD"
                  if exact else "R58_G1_NO_EXACT_UUID_OVERLAP__OTHER_PROTECTED_SET_HOLD"),
    })
    return safe

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--private-queue",type=Path,required=True)
    ap.add_argument("--private-discovery",type=Path,required=True)
    ap.add_argument("--r57-private-root",type=Path,default=Path.home()/".local/share/storyforge/r57/private")
    ap.add_argument("--private-hold-output",type=Path)
    args=ap.parse_args()
    try:
        print(json.dumps(check(args.private_queue,args.private_discovery,args.r57_private_root,args.private_hold_output),
                         sort_keys=True,ensure_ascii=False,indent=2))
        return 0
    except (Hold,OSError,ValueError,KeyError,TypeError):
        print("R58_G1_PRIOR_SFT: HOLD (metadata identity/source unavailable)",
              file=sys.stderr)
        return 42

if __name__=="__main__":
    raise SystemExit(main())

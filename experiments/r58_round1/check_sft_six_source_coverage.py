#!/usr/bin/env python3
"""R58 G1 six frozen SFT split source-world reconciliation (Owner Mac, no network).

Only metadata (world UUID, source counts, target SHA256 lists). Two pinned
compiled v0.3 train/validation Git blobs are parsed as raw structural bytes:
there is NO JSON decoding or export of any narrative. Does not open R50,
reviewer outputs, model data, HF jobs, or training logs. Always G1 HOLD.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import stat
import subprocess
import sys

SOURCE_PINS = {
    'V01_TRAIN': ('3e64c9932ca43fefa8ecfb200085fe718581b6f9', 65),
    'V01_VALIDATION': ('db0ae8b86038be1b372d547fdb2d6b0b7e33b54e', 15),
}
HISTORY_KEYS = {'r46_train':'R46_TRAIN', 'r46_val':'R46_VALIDATION',
                'r54_train':'R54_TRAIN', 'r54_val':'R54_VALIDATION'}
EXPECTED = {'R46_TRAIN':49, 'R46_VALIDATION':15,
            'R54_TRAIN':31, 'R54_VALIDATION':9}
SOURCES = ('GOLD87','GOLD108', 'V01_TRAIN','V01_VALIDATION',
           'R46_TRAIN','R46_VALIDATION','R54_TRAIN','R54_VALIDATION')
UUID = re.compile(r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$', re.I)
HEX64 = re.compile(r'^[0-9a-f]{64}$', re.I)
WORLD_TOKEN = re.compile(rb'"story_id"\s*:\s*"([0-9a-fA-F-]{36})"')
META_TOKEN = re.compile(rb'"metadata"\s*:\s*\{')
SAMPLE_TOKEN = re.compile(rb'"id"\s*:\s*"(sample-[0-9]{6})"')
ROSTER_SCHEMA = 'storyforge-r57-g2-owner-private-world-alias-review-roster-v1'
HISTORY_SCHEMA = 'storyforge-r56-source-world-exposure-v1'

class Hold(Exception):
    pass


def safe_uuid(s):
    if not isinstance(s,str) or UUID.fullmatch(s) is None:
        raise Hold('bad world UUID metadata')
    return s.lower()


def private_json(path: Path, limit: int) -> dict:
    if path.is_symlink() or not path.is_file():
        raise Hold('private metadata file unavailable')
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or not (0<st.st_size<=limit):
        raise Hold('private metadata size or mode invalid')
    try:
        obj = json.loads(path.read_bytes())
    except (UnicodeError, ValueError):
        raise Hold('private metadata invalid JSON')
    if not isinstance(obj,dict):
        raise Hold('private metadata root not object')
    return obj


def pinned_git_blob(repo:Path, blobsha:str) -> bytes:
    if not re.fullmatch('[a-f0-9]{40}',blobsha):
        raise Hold('invalid immutable blob identity')
    try:
        run = subprocess.run(['git','-C',str(repo),'cat-file','blob',blobsha],
                             capture_output=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Hold('frozen Git blob unavailable')
    if run.returncode or not 0<len(run.stdout)<=12_000_000:
        raise Hold('frozen Git blob missing or oversized')
    return run.stdout


def pinned_split_counts(blob:bytes, expected_rows:int) -> Counter:
    # Do not json.loads narrative-bearing test/train/validation records.
    lines=blob.splitlines()
    if len(lines)!=expected_rows or any(not x.strip() for x in lines):
        raise Hold('pinned v0.1 source row count mismatch')
    counts=Counter(); seen=set()
    for raw in lines:
        worlds=WORLD_TOKEN.findall(raw)
        samples=SAMPLE_TOKEN.findall(raw)
        if len(worlds)!=1 or len(samples)!=1 or len(META_TOKEN.findall(raw))!=1:
            raise Hold('pinned source metadata token ambiguous')
        try:
            uid=safe_uuid(worlds[0].decode('ascii'))
            sample=samples[0].decode('ascii')
        except UnicodeError:
            raise Hold('invalid source metadata encoding')
        if sample in seen:
            raise Hold('duplicate split sample ID')
        seen.add(sample); counts[uid]+=1
    return counts


def parse_historical(obj:dict) -> dict[str,Counter]:
    if (obj.get('schema')!=HISTORY_SCHEMA or obj.get('r50_read') is not False
        or not isinstance(obj.get('splits'),dict)
        or set(obj['splits'])!=set(HISTORY_KEYS)):
        raise Hold('R56 frozen historical index schema/split mismatch')
    output={}
    for old,source in HISTORY_KEYS.items():
        group=obj['splits'][old]
        if not isinstance(group,dict):
            raise Hold('R56 historical split invalid')
        counts=Counter(); digests=set()
        for raw_uid, hashes in group.items():
            uid=safe_uuid(raw_uid)
            if uid in counts:
                raise Hold('R56 duplicate UUID after canonicalization')
            if not isinstance(hashes,list) or not hashes:
                raise Hold('R56 invalid empty target group')
            for h in hashes:
                if not isinstance(h,str) or HEX64.fullmatch(h) is None:
                    raise Hold('R56 malformed target digest')
                if h in digests:
                    raise Hold('R56 duplicate target digest within split')
                digests.add(h)
            counts[uid]=len(hashes)
        if sum(counts.values())!=EXPECTED[source]:
            raise Hold('R56 historical split count mismatch')
        output[source]=counts
    return output


def reconcile(roster:dict, historical:dict, compiled:dict[str,bytes]) -> dict:
    if (roster.get('schema')!=ROSTER_SCHEMA or not isinstance(roster.get('worlds'),list)
        or len(roster['worlds'])!=29):
        raise Hold('R57 frozen roster schema/count mismatch')
    source_counts={key:Counter() for key in SOURCE_PINS}
    for key,(sha,n) in SOURCE_PINS.items():
        if key not in compiled:
            raise Hold('missing pinned compiled source')
        source_counts[key]=pinned_split_counts(compiled[key],n)
    source_counts.update(parse_historical(historical))
    expected_uids=set().union(*(set(c) for c in source_counts.values()))
    if len(expected_uids)!=27:
        raise Hold('six-source UUID union is not 27')
    roster_uids=set(); gold=set(); marked_exposed=set()
    for item in roster['worlds']:
        if not isinstance(item,dict):
            raise Hold('R57 roster row not object')
        uid=safe_uuid(item.get('source_story_uuid_PRIVATE'))
        if uid in roster_uids:
            raise Hold('duplicate R57 roster UUID')
        roster_uids.add(uid)
        rows=item.get('source_row_counts')
        if (not isinstance(rows,dict) or set(rows)!=set(SOURCES)
            or any(type(value) is not int or value<0 for value in rows.values())):
            raise Hold('R57 roster source count schema mismatch')
        for key in source_counts:
            if rows[key]!=source_counts[key].get(uid,0):
                raise Hold('R57 vs frozen six-source per-UUID count mismatch')
        if rows['GOLD87']+rows['GOLD108']:
            gold.add(uid)
        flag=item.get('same_exact_uuid_seen_in_previous_sft')
        if type(flag) is not bool or flag is not (uid in expected_uids):
            raise Hold('R57 historical SFT flag inconsistent with frozen splits')
        if flag:marked_exposed.add(uid)
    if (len(roster_uids)!=29 or not expected_uids<=roster_uids or
        len(marked_exposed)!=27 or len(gold)!=13 or len(gold-expected_uids)!=2):
        raise Hold('R57 six-source/Gold UUID universe mismatch')
    for key in source_counts:
        if sum(source_counts[key].values()) != (SOURCE_PINS[key][1] if key in SOURCE_PINS else EXPECTED[key]):
            raise Hold('source aggregate count drift')
    return {
        'schema':'r58_round1_g1_sft_six_source_reconciliation_safe_v1',
        'status':'R58_G1_KNOWN_SIX_FROZEN_SPLITS_RECONCILED__REMOTE_AND_OTHER_PROTECTED_HOLD',
        'known_frozen_sft_source_splits':6,
        'v01_train_rows':65,'v01_validation_rows':15,
        'r46_train_rows':49,'r46_validation_rows':15,
        'r54_train_rows':31,'r54_validation_rows':9,
        'known_six_source_total_rows':184,
        'known_six_source_unique_world_uuids':27,
        'r57_roster_source_worlds':29,
        'r57_roster_gold_source_worlds':13,
        'known_six_source_per_world_counts_equal':True,
        'known_six_source_exposure_flags_equal':True,
        'source_bytes_or_world_uuids_exported':False,
        'r50_protected_test_content_accessed':False,
        'remote_trainer_primary_inputs_verified':False,
        'all_actual_sft_runs_and_input_sources_proven_complete':False,
        'r56_non_gold_other_protected_index_covered':False,
        'source_registry_complete':False,
        'g1_clearance':'HOLD',
        'train_admitted':0,'validation_admitted':0,'teacher_admitted':0,
        'expansion_allowed':False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,required=True)
    p.add_argument('--r57-private-root',type=Path,default=Path.home()/'.local/share/storyforge/r57/private')
    p.add_argument('--r56-historical-exposure',type=Path,default=Path.home()/'.local/share/storyforge/r56/owner-full-replay-20261022-v1/toolkit/private/R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json')
    a=p.parse_args(argv)
    try:
        if (a.r57_private_root.is_symlink() or not a.r57_private_root.is_dir()
            or a.r56_historical_exposure.name!='R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json'):
            raise Hold('unexpected frozen source location')
        candidates=sorted(x for x in a.r57_private_root.glob('R57_G2_WORLD_ALIAS_REVIEW_*_PRIVATE.json')
            if re.fullmatch(r'R57_G2_WORLD_ALIAS_REVIEW_\d{8}_\d{6}_PRIVATE\.json',x.name))
        if len(candidates)!=1:
            raise Hold('missing or ambiguous R57 historical roster')
        r57=private_json(candidates[0],400_000)
        r56=private_json(a.r56_historical_exposure,400_000)
        compiled={key:pinned_git_blob(a.repo_root,sha) for key,(sha,n) in SOURCE_PINS.items()}
        safe=reconcile(r57,r56,compiled)
        print(json.dumps(safe,sort_keys=True,ensure_ascii=False,indent=2))
        return 0
    except (Hold,OSError,ValueError,KeyError,TypeError):
        print('R58_G1_SFT_SIX_SOURCE: HOLD (source metadata discrepancy or unavailable)',file=sys.stderr)
        return 42

if __name__=='__main__':
    raise SystemExit(main())

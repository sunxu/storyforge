#!/usr/bin/env python3
"""R56 scope preflight for existing UUID-triage CSV (metadata only; no source reads).

Read Owner-private CSV; fail closed for malformed files; emit private scope cues and
count-only safe JSON. UUID-only candidates ALWAYS remain HOLD. Never touches R50.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import os
from pathlib import Path
import re
import sys

UUID = re.compile(r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$', re.I)
SHA = re.compile(r'^[a-f0-9]{64}$', re.I)
GOLD = 'ALREADY_PRESENT_IN_GOLD195__NOT_NEW_WORLD'
HISTORY = 'KNOWN_HISTORICAL_UUID_OVERLAP__EXCLUDE'
POTENTIAL = 'POTENTIAL_NON_GOLD_WORLD__SEMANTIC_EXPOSURE_HOLD'
ALLOWED = {GOLD, HISTORY, POTENTIAL}
REQUIRED = {'story_uuid_PRIVATE', 'original_story_sha256_PRIVATE', 'original_source_path_PRIVATE', 'uuid_triage', 'formal_world_admitted'}
class Blocked(Exception): pass

def triage(csv_path: Path) -> tuple[dict, dict]:
    if not csv_path.is_file() or csv_path.is_symlink():
        raise Blocked('PRIVATE_TRIAGE_CSV_NOT_REGULAR_FILE')
    counts = collections.Counter()
    sources = set()
    uuids = set()
    all_known_gold = True
    all_old_root = True
    with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED <= set(reader.fieldnames):
            raise Blocked('REQUIRED_TRIAGE_FIELDS_MISSING')
        for row in reader:
            uid, sha, src, cls = ((row.get(k) or '').strip() for k in ('story_uuid_PRIVATE','original_story_sha256_PRIVATE','original_source_path_PRIVATE','uuid_triage'))
            if not UUID.fullmatch(uid) or not SHA.fullmatch(sha) or not src or cls not in ALLOWED:
                raise Blocked('INVALID_ROW_OR_UNKNOWN_TRIAGE')
            if (row.get('formal_world_admitted') or '').strip().upper() != 'NO':
                raise Blocked('FORMAL_ADMISSION_MUST_BE_NO')
            if uid in uuids or (uid,sha) in sources:
                raise Blocked('DUPLICATED_WORLD_UUID_IN_TRIAGE')
            uuids.add(uid);sources.add((uid,sha))
            counts['rows'] += 1
            counts[cls] += 1
            all_known_gold &= (cls == GOLD)
            normalized=src.replace('\\','/').lower()
            all_old_root &= '/evaluations/v0.2/source-archives/jsonl/' in normalized
    if counts['rows'] == 0:
        raise Blocked('EMPTY_TRIAGE_CSV')
    safe = {
        'schema': 'storyforge-r56-stage7-source-scope-preflight-counts-v1',
        'source_world_rows': counts['rows'],
        'gold_uuid_overlap': counts[GOLD],
        'historical_uuid_overlap': counts[HISTORY],
        'potential_new_uuid_only': counts[POTENTIAL],
        'old_gold_source_root_observed': all_old_root,
        'formal_world_admitted': 0,
        'official_test_admitted': 0,
        'r50_source_opened': False,
        'gpu_job_started': False,
        'training_performed': False,
        'next_scope_action': ('LOCATE_NON_GOLD_NON_R50_RAW_EXPORT_ROOT' if all_known_gold else 'REVIEW_PRIVATE_UUID_POTENTIALS_AND_SEMANTIC_EXPOSURE'),
        'status': ('GOLD_ONLY_SOURCE_SCOPE__NO_NEW_WORLDS__STOP_REPEAT' if all_known_gold else 'UUID_TRIAGE_ONLY__ALL_POTENTIAL_HOLD'),
        'explanation': 'Metadata gate only: source files were not opened. Exact UUID membership does not certify semantic isolation or unexposed new evaluation questions.'
    }
    private = {
        'schema': 'storyforge-r56-stage7-source-scope-preflight-private-v1',
        'input_csv_path_PRIVATE': str(csv_path.resolve()),
        'all_rows_gold195': all_known_gold,
        'old_gold_source_root_observed': all_old_root,
        'recommendation_private': ('The input is only historical Gold195 sources; choose a separate Owner-controlled, explicitly non-R50 directory of genuine original full-story exports, outside the 01–15 historical source archive.' if all_known_gold else 'Manually inspect all newly UUID-distinct originals, previous model/evaluation exposure and cross-story relationships. No test admission.'),
        'official_test_admitted': 0
    }
    return safe, private

def write(safe:dict, private:dict, out_dir:Path)->None:
    if out_dir.exists():raise Blocked('OUTPUT_EXISTS_NO_OVERWRITE')
    os.umask(0o077)
    out_dir.mkdir(parents=True,mode=0o700)
    (out_dir/'safe').mkdir(mode=0o700)
    (out_dir/'private').mkdir(mode=0o700)
    for sub,name,data in [('safe','R56_STAGE7_SCOPE_COUNTS_ONLY.json',safe),('private','R56_STAGE7_SCOPE_DIAGNOSTIC_PRIVATE.json',private)]:
        p=out_dir/sub/name
        with p.open('x', encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
        os.chmod(p,0o600)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--triage-csv',type=Path,required=True)
    ap.add_argument('--out-dir',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.out_dir.resolve()==args.triage_csv.resolve():raise Blocked('OUTPUT_EQUALS_INPUT')
        safe,private=triage(args.triage_csv)
        write(safe,private,args.out_dir)
        print(safe['status'])
        print('worlds=',safe['source_world_rows'],'gold_overlap=',safe['gold_uuid_overlap'],'potential=',safe['potential_new_uuid_only'],'official_test_admitted=0')
        return 0
    except (Blocked,OSError,UnicodeError,csv.Error,ValueError) as exc:
        print('R56_SCOPE_PREFLIGHT_BLOCKED:',str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())

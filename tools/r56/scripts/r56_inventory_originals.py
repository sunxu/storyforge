#!/usr/bin/env python3
"""R56 CPU-only original JSON/JSONL metadata inventory. No evaluation admission.

Only use explicitly isolated non-R50 source roots. Reject known sealed paths and
rank markers; filters cannot identify unknown aliases of sealed materials.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from collections import Counter

SEALED = re.compile(r'(^|[/_.\\-])r50($|[/_.\\-])|(^|[/_.\\-])(16-20|(?:16|17|18|19|20)-[^/\\]*)($|[/_.\\-])', re.I)
UUID = re.compile(r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$', re.I)
class Blocked(Exception): pass

def is_sealed(path): return bool(SEALED.search(str(path)))

def parse_export(path, max_bytes=150_000_000):
    if is_sealed(path): raise Blocked('SEALED_PATH')
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes: return None
    try:
        raw = path.read_bytes()
        obj = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError): return None
    if not isinstance(obj, dict): return None
    story, messages = obj.get('story'), obj.get('messages')
    if not isinstance(story, dict) or not isinstance(messages, list) or not messages: return None
    uid = story.get('id')
    if not isinstance(uid, str) or not UUID.fullmatch(uid): return None
    if str(obj.get('rank')) in {'16','17','18','19','20'}: raise Blocked('SEALED_RANK')
    if not all(isinstance(m, dict) and isinstance(m.get('id'), str) for m in messages): return None
    timestamp = story.get('created_at')
    return {'story_uuid_PRIVATE':uid,
            'original_story_sha256_PRIVATE':hashlib.sha256(raw).hexdigest(),
            'original_source_path_PRIVATE':str(path.resolve()),
            'earliest_creation_timestamp_PRIVATE':timestamp if isinstance(timestamp,str) else '',
            'provenance_evidence_private':'RAW_EXPORT_BYTE_SHA_ONLY__TARGET_TIME_CARD_UNVERIFIED',
            'original_message_count_PRIVATE':len(messages),
            'candidate_status_PRIVATE':'UUID_CANDIDATE_ONLY__SEMANTIC_HOLD__NO_ADMISSION'}

def inventory(roots, max_bytes=150_000_000, max_files=5000, max_depth=4):
    if max_files<=0 or max_depth<=0 or max_bytes<=0: raise Blocked('INVALID_LIMIT')
    items, stats, seen_paths = [],Counter(),set()
    for root in roots:
        if is_sealed(root) or root.is_symlink(): raise Blocked('SOURCE_ROOT_FORBIDDEN')
        if not root.exists(): raise Blocked('SOURCE_ROOT_MISSING')
        if root.is_file() and root.suffix.lower()=='.zip': raise Blocked('EXTRACT_NON_R50_ZIP_TO_PRIVATE_FOLDER_FIRST')
        paths = [root] if root.is_file() else sorted(root.rglob('*'))
        for p in paths:
            if p.is_symlink() or not p.is_file():continue
            if p.suffix.lower()=='.zip':
                stats['archives_skipped_extract_first']+=1;continue
            if p.suffix.lower() not in ('.json','.jsonl'):continue
            depth=len(p.relative_to(root).parts) if root.is_dir() else 1
            if depth>max_depth:stats['depth_skipped']+=1;continue
            if is_sealed(p):stats['sealed_path_skipped']+=1;continue
            if p.stat().st_size>max_bytes:stats['oversize_skipped']+=1;continue
            canonical=str(p.resolve())
            if canonical in seen_paths:continue
            seen_paths.add(canonical)
            stats['files_scanned']+=1
            if stats['files_scanned']>max_files: raise Blocked('MAX_FILES_EXCEEDED')
            try: row=parse_export(p,max_bytes)
            except Blocked as err:
                if str(err)=='SEALED_RANK':stats['sealed_rank_skipped']+=1;continue
                raise
            if row is None:stats['non_full_story_files']+=1
            else: items.append(row)
    by_uuid={}
    for row in items:by_uuid.setdefault(row['story_uuid_PRIVATE'],set()).add(row['original_story_sha256_PRIVATE'])
    conflicts={uid for uid,h in by_uuid.items() if len(h)>1}
    for row in items:
        if row['story_uuid_PRIVATE'] in conflicts:
            row['candidate_status_PRIVATE']='SOURCE_VERSION_CONFLICT__HOLD'
    stats['raw_original_exports']=len(items)
    stats['unique_world_uuids']=len(by_uuid)
    stats['world_uuids_with_version_conflict']=len(conflicts)
    return items,stats

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,action='append',required=True)
    ap.add_argument('--out-dir',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.out_dir.exists() or is_sealed(args.out_dir):raise Blocked('OUTPUT_FORBIDDEN_OR_EXISTS')
        for root in args.root:
            if root.is_dir() and root.resolve() in args.out_dir.resolve().parents:raise Blocked('OUTPUT_INSIDE_SOURCE_FORBIDDEN')
        rows,stats=inventory(args.root)
        os.umask(0o077)
        priv=args.out_dir/'private';safe=args.out_dir/'safe'
        priv.mkdir(parents=True,mode=0o700);safe.mkdir(mode=0o700)
        with (priv/'R56_AUTO_ORIGINAL_WORLD_INVENTORY_PRIVATE.jsonl').open('x',encoding='utf8') as f:
            for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
        result={'schema':'storyforge-r56-stage6-original-inventory-counts-v1',
            'status':'SOURCE_METADATA_ONLY__ALL_WORLDS_HOLD__NO_TEST_ADMISSION',**stats,
            'worlds_formally_admitted':0,'official_test_admitted':0,'r50_explicit_paths_and_ranks_filtered':True,
            'r50_owner_directory_isolation_still_required':True,'gpu_started':False,'gold_modified':False,
            'note':'No independence/semantic exposure proof; do not publish the private JSONL.'}
        (safe/'R56_AUTO_ORIGINAL_WORLD_COUNTS_ONLY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf8')
        print('R56_ORIGINAL_WORLD_INVENTORY_CREATED__NO_FORMAL_ADMISSION')
        print('sources_scanned:',stats['files_scanned'],'original_exports:',len(rows),'worlds:',stats['unique_world_uuids'])
        return 0
    except (Blocked,OSError,ValueError) as e:
        print('R56_SOURCE_DISCOVERY_BLOCKED:',str(e),file=sys.stderr)
        return 2
if __name__=='__main__': raise SystemExit(main())

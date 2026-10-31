#!/usr/bin/env python3
"""StoryForge R58 private offline shortlist / gate / content freeze. No network or inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

MAX_INPUT_BYTES = 50 * 1024 * 1024
DIGEST = re.compile(r'^[0-9a-f]{64}$')
SOURCE_KINDS = {'original_gold', 'teacher_rewrite', 'teacher_generated', 'human_edited'}
TRUE_STRINGS = {'true', 't', '1', 'yes'}


class Hold(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def check_digest(value, field):
    if not isinstance(value, str) or DIGEST.fullmatch(value) is None:
        raise Hold(f'{field}: invalid sha256')


def read_path(path: str) -> Path:
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise Hold('input is missing, not a regular file, or is a symlink')
    if p.stat().st_size > MAX_INPUT_BYTES:
        raise Hold('input too large; process a smaller private batch')
    return p


def load_jsonl(path):
    rows = []
    p = read_path(path)
    with p.open('r', encoding='utf-8') as f:
        for index, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise Hold(f'invalid JSON on line {index}') from exc
            if not isinstance(obj, dict):
                raise Hold(f'line {index}: expected object')
            rows.append(obj)
    return rows


def read_rows(path):
    p = read_path(path)
    if p.suffix.lower() == '.csv':
        with p.open('r', encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))
    return load_jsonl(path)


def private_write(path, data: bytes):
    p = Path(path)
    if not p.parent.is_dir() or p.parent.is_symlink() or p.exists() or p.is_symlink():
        raise Hold('private output must be a new path in a real existing directory')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(p, flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        try:
            p.unlink()
        except OSError:
            pass
        raise


def dumps_jsonl(rows) -> bytes:
    return b''.join(canon(row) + b'\n' for row in rows)


def boolfield(v):
    return v is True or isinstance(v, str) and v.strip().lower() in TRUE_STRINGS


def shortlist(args):
    rows = read_rows(args.input)
    seen = set()
    candidates = []
    for row in rows:
        story_id = row.get('story_id')
        if not isinstance(story_id, str) or not story_id or story_id in seen:
            raise Hold('blank or duplicated story id in inventory')
        seen.add(story_id)
        if row.get('story_type') != 'v2_sandbox' or not boolfield(row.get('not_deleted')):
            continue
        if row.get('moderation_status') not in ('approved', 'override_approved'):
            continue
        count = int(row.get('assistant_completed') or 0)
        if count < args.min_assistant_completed:
            continue
        if not all(boolfield(row.get(f)) for f in ('has_world','has_character','has_director','has_opening')):
            continue
        sessions = int(row.get('session_count') or 0)
        if sessions < 1:
            continue
        genre = str(row.get('genre') or '<UNKNOWN>')
        source = str(row.get('source_type') or '<UNKNOWN>')
        # Capped log makes popularity only a small tie-break, not a quality label.
        score = round(min(30.0, 10.0 * math.log10(max(1,count))), 3) + (5 if boolfield(row.get('has_characters')) else 0)
        candidates.append({'story_id': story_id, 'genre': genre, 'source_type': source,
                           'assistant_completed_rollup': count, 'session_count_rollup': sessions,
                           'heuristic_score': score, 'status': 'SHORTLIST_ONLY_WORLD_AND_QUALITY_UNVERIFIED'})
    candidates.sort(key=lambda r: (-r['heuristic_score'], sha256(r['story_id'].encode())))
    # Round-robin by genre, to avoid a single popular genre occupying whole batch.
    grouped = {}
    for candidate in candidates:
        grouped.setdefault(candidate['genre'], []).append(candidate)
    out = []
    genres = sorted(grouped, key=lambda x: (-len(grouped[x]), x))
    while len(out) < args.limit and genres:
        next_genres = []
        for genre in genres:
            group = grouped[genre]
            if group and len(out) < args.limit:
                out.append(group.pop(0))
            if group:
                next_genres.append(genre)
        genres = next_genres
    private_write(args.output, dumps_jsonl(out))
    print(json.dumps({'status':'SHORTLIST_ONLY','inventory_rows':len(rows), 'eligible_heuristic':len(candidates),
                      'selected_story_count':len(out), 'quality_admitted':0,'story_ids_printed':False},ensure_ascii=False))


def decide(row):
    cid = row.get('case_id')
    if not isinstance(cid, str) or not cid:
        raise Hold('case_id missing')
    kind = row.get('source_kind')
    if kind not in SOURCE_KINDS:
        return 'HOLD', 'UNKNOWN_SOURCE_KIND'
    for field in ('input_messages_sha256','assistant_target_sha256','source_bytes_sha256', 'world_graph_certificate_sha256'):
        if not isinstance(row.get(field), str) or DIGEST.fullmatch(row[field]) is None:
            return 'HOLD', 'MISSING_PROVENANCE_SHA'
    if not isinstance(row.get('world_component_id'), str) or not row['world_component_id']:
        return 'HOLD', 'WORLD_UNRESOLVED'
    if row.get('split') not in ('train','validation'):
        return 'HOLD', 'SPLIT_UNRESOLVED'
    if row.get('split') == 'validation' and kind in ('teacher_rewrite','teacher_generated'):
        return 'HOLD', 'TEACHER_TARGET_NOT_ALLOWED_IN_VALIDATION'
    reviews = row.get('reviews')
    if not isinstance(reviews, list) or len(reviews)<2:
        return 'HOLD','TWO_REVIEWS_REQUIRED'
    keys = [r.get('reviewer_key') for r in reviews if isinstance(r,dict)]
    if len(keys)!=len(reviews) or any(not isinstance(k,str) or not k for k in keys) or len(set(keys))<2:
        return 'HOLD','REVIEWER_INDEPENDENCE_NOT_DECLARED'
    if any(r.get('decision')=='REJECT' for r in reviews):
        return 'REJECT','REVIEWER_REJECT'
    if any(r.get('decision')!='PASS' or not r.get('evidence_ref') for r in reviews):
        return 'HOLD','REVIEW_EVIDENCE_MISSING'
    required = ('source_bytes_verified','history_replay_verified','target_time_canon_verified',
                'world_graph_verified','protected_overlap_verified','reviewer_independence_declared','privacy_filtered','owner_approved')
    if any(row.get(k) is not True for k in required):
        return 'HOLD','ADMISSION_EVIDENCE_INCOMPLETE'
    if row.get('protected_test_exposed') is not False:
        return 'HOLD','PROTECTED_TEST_UNRESOLVED'
    if kind in ('teacher_rewrite','teacher_generated'):
        if not row.get('teacher_model') or not row.get('teacher_recipe_sha256') or not row.get('parent_target_sha256'):
            return 'HOLD','TEACHER_LINEAGE_MISSING'
        for k in ('teacher_recipe_sha256','parent_target_sha256'):
            if DIGEST.fullmatch(str(row.get(k,''))) is None:
                return 'HOLD','TEACHER_LINEAGE_BAD_DIGEST'
    if kind=='human_edited' and DIGEST.fullmatch(str(row.get('parent_target_sha256',''))) is None:
        return 'HOLD','EDIT_LINEAGE_MISSING'
    return 'PASS','ALL_DECLARED_GATES_PASS'


def gate(args):
    rows = load_jsonl(args.input)
    if not rows:
        raise Hold('no candidate rows')
    seen = set()
    out = []
    counts = {'PASS':0,'HOLD':0,'REJECT':0}
    for row in rows:
        cid = row.get('case_id')
        if cid in seen:
            raise Hold('duplicate case_id')
        seen.add(cid)
        decision, reason = decide(row)
        counts[decision] += 1
        out.append({'case_id':cid,'decision':decision,'reason':reason,
                    'input_messages_sha256':row.get('input_messages_sha256'),
                    'assistant_target_sha256':row.get('assistant_target_sha256'),
                    'world_component_id':row.get('world_component_id'),
                    'split':row.get('split'), 'source_kind':row.get('source_kind')})
    # All validation before writes; refuse both existing outputs.
    for name in (args.output,args.safe_output):
        p = Path(name)
        if p.exists() or p.is_symlink():
            raise Hold('output already exists')
    if Path(args.output).resolve()==Path(args.safe_output).resolve():
        raise Hold('output paths must differ')
    private_write(args.output,dumps_jsonl(out))
    private_write(args.safe_output,canon({'schema':'r58-gate-safe-v1','cases':len(rows),
                                         'counts':counts,'contains_story_text':False,'owner_admission_proven':False})+b'\n')
    print(json.dumps({'status':'DECLARED_METADATA_GATE_ONLY','cases':len(rows),'counts':counts},ensure_ascii=False))


def freeze(args):
    check_digest(args.world_graph_sha,'world_graph_sha')
    candidates = load_jsonl(args.input)
    decisions = load_jsonl(args.decision)
    approved={}
    for d in decisions:
        cid=d.get('case_id')
        if not cid or cid in approved:
            raise Hold('duplicate or missing decision case_id')
        approved[cid]=d
    if not candidates:
        raise Hold('no freeze candidates')
    seen_cases=set()
    seen_inputs=set()
    seen_targets=set()
    split_components={}
    written={'train':[],'validation':[]}
    private_manifest=[]
    synthetic=0
    for row in candidates:
        cid=row.get('case_id')
        if not cid or cid in seen_cases:
            raise Hold('duplicate or missing candidate case_id')
        seen_cases.add(cid)
        dec=approved.get(cid)
        if not dec or dec.get('decision')!='PASS':
            raise Hold('freeze case has no PASS decision')
        messages=row.get('messages')
        target=row.get('target_text')
        split=row.get('split')
        world=row.get('world_component_id')
        kind=row.get('source_kind')
        if (not isinstance(messages,list) or len(messages)<2 or
            not isinstance(target,str) or not target.strip() or split not in written or
            not isinstance(world,str) or not world or kind not in SOURCE_KINDS):
            raise Hold('invalid target, split, world or messages')
        if not isinstance(messages[0],dict) or not isinstance(messages[-1],dict) or messages[0].get('role')!='system' or messages[-1].get('role')!='user':
            raise Hold('messages must begin with system and end with user')
        if any(not isinstance(m,dict) or m.get('role') not in ('system','user','assistant') or
               not isinstance(m.get('content'),str) or not m['content'].strip() or
               (i>0 and m.get('role')=='system') for i,m in enumerate(messages)):
            raise Hold('invalid role/content or extra system message')
        input_digest=sha256(canon(messages))
        target_digest=sha256(target.encode('utf-8'))
        for digest,field in ((input_digest,'input_messages_sha256'),(target_digest,'assistant_target_sha256')):
            if row.get(field)!=digest or dec.get(field)!=digest:
                raise Hold('input or target SHA does not match gate decision')
        if dec.get('world_component_id')!=world or dec.get('split')!=split or dec.get('source_kind')!=kind:
            raise Hold('world/split/kind changed after gate')
        if split=='validation' and kind in ('teacher_rewrite','teacher_generated'):
            raise Hold('teacher output not permitted as validation gold')
        if input_digest in seen_inputs or target_digest in seen_targets:
            raise Hold('exact duplicate input or target in frozen cohort')
        seen_inputs.add(input_digest)
        seen_targets.add(target_digest)
        if world in split_components and split_components[world]!=split:
            raise Hold('semantic world component crosses train/validation')
        split_components[world]=split
        if kind.startswith('teacher_'):
            synthetic += 1
        written[split].append({'messages':messages+[{'role':'assistant','content':target}]})
        private_manifest.append({'case_id':cid,'world_component_id':world,'split':split,
                                 'source_kind':kind,'input_messages_sha256':input_digest,
                                 'assistant_target_sha256':target_digest})
    if not written['train'] or not written['validation']:
        raise Hold('both train and validation splits required')
    if synthetic/len(candidates)>args.max_teacher_share:
        raise Hold('Teacher share above frozen experimental ceiling')
    p=Path(args.output_dir)
    if p.exists() or p.is_symlink() or not p.parent.is_dir() or p.parent.is_symlink():
        raise Hold('output directory must not exist and parent must be real directory')
    # All content validations complete before creating directory.
    p.mkdir(mode=0o700)
    output_hashes={}
    for split in ('train','validation'):
        data=dumps_jsonl(written[split])
        private_write(p/f'{split}.jsonl',data)
        output_hashes[f'{split}.jsonl']=sha256(data)
    private_write(p/'private_manifest.jsonl',dumps_jsonl(private_manifest))
    safe={'schema':'r58-frozen-content-safe-v1','status':'CONTENT_FREEZE_ONLY__HF_CPU_PREFLIGHT_PENDING',
          'train_count':len(written['train']),'validation_count':len(written['validation']),
          'world_component_counts':{split:len({x['world_component_id'] for x in private_manifest if x['split']==split}) for split in ('train','validation')},
          'teacher_case_count':synthetic,'world_graph_certificate_sha256':args.world_graph_sha,
          'file_sha256':output_hashes,'contains_raw_text':False}
    private_write(p/'safe_manifest.json',canon(safe)+b'\n')
    print(json.dumps({'status':safe['status'],'train_count':safe['train_count'],
                      'validation_count':safe['validation_count'],'teacher_case_count':synthetic},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='stage',required=True)
    s=sub.add_parser('shortlist')
    s.add_argument('--input',required=True)
    s.add_argument('--output',required=True)
    s.add_argument('--limit',type=int,default=30)
    s.add_argument('--min-assistant-completed',type=int,default=50)
    s.set_defaults(func=shortlist)
    s=sub.add_parser('gate')
    s.add_argument('--input',required=True)
    s.add_argument('--output',required=True)
    s.add_argument('--safe-output',required=True)
    s.set_defaults(func=gate)
    s=sub.add_parser('freeze')
    s.add_argument('--input',required=True)
    s.add_argument('--decision',required=True)
    s.add_argument('--output-dir',required=True)
    s.add_argument('--world-graph-sha',required=True)
    s.add_argument('--max-teacher-share',type=float,default=0.20)
    s.set_defaults(func=freeze)
    args=parser.parse_args()
    try:
        if getattr(args,'limit',1)<1 or getattr(args,'min_assistant_completed',0)<0 or not (0<=getattr(args,'max_teacher_share',0)<=1):
            raise Hold('invalid numeric argument')
        args.func(args)
    except (Hold,ValueError,TypeError,KeyError,OverflowError) as exc:
        print(f'HOLD: {exc}',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    sys.exit(main())

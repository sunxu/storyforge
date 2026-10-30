#!/usr/bin/env python3
"""R58 Round-1 metadata-only private pilot shortlist; never reads chat text."""
import argparse
import csv
import json
import os
from pathlib import Path
import sys

STORY_FIELDS = {'story_id','source_type','not_deleted','moderation_status',
                'story_type','assistant_completed','session_count','has_world',
                'has_character','has_characters','has_opening'}
GUARD_FIELDS = {'story_id','world_component','owner_world_graph_reviewed',
                'r50_protected_clear','prior_sft_clear','r55_r57_dev_clear',
                'other_protected_clear','evidence_reference'}
CATEGORIES = {'original':3,'dice_cocreate':1,'ai_assisted':1}
OWNER_WORLD_IDENTITY_POLICY = 'OWNER_ATTESTED_ROLEPLAY_UUID_ONE_UUID_ONE_WORLD_V1'

class Hold(Exception):
    pass

def private_csv(path, mandatory):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 5_000_000:
        raise Hold('bad private CSV')
    with p.open('r', encoding='utf-8-sig', newline='') as handle:
        reader=csv.DictReader(handle)
        if not reader.fieldnames or not mandatory <= set(reader.fieldnames):
            raise Hold('CSV schema invalid')
        return list(reader)

def boolish(x):
    """Accept PostgreSQL psql CSV booleans (t/f) and explicit textual forms.

    Unknown non-empty tokens HOLD rather than silently rejecting all stories.
    Empty values are treated as false so absent protection attestations block.
    """
    token = str(x if x is not None else '').strip().lower()
    if token in {'t', 'true', '1', 'yes'}:
        return True
    if token in {'f', 'false', '0', 'no', ''}:
        return False
    raise Hold('unexpected boolean CSV token')

def positive_int(x):
    try:
        v=int(str(x).strip())
    except (ValueError,TypeError):
        raise Hold('numeric metadata invalid')
    if v<0: raise Hold('negative count')
    return v

PARSER_VERSION = 'R58_ROUND1_CSV_GATE_DIAGNOSTIC_V2'

GATE_NAMES = (
    'story_type_v2_sandbox', 'moderation_approved', 'not_deleted',
    'assistant_completed_50plus', 'session_count_2plus',
    'has_world', 'has_character_or_characters', 'has_opening',
    'recognized_source_type',
)


def safe_gate_diagnostics(rows):
    """Aggregate only fixed-condition counts. Never emit CSV values or story IDs."""
    individual = {name: 0 for name in GATE_NAMES}
    cumulative = {name: 0 for name in GATE_NAMES}
    for r in rows:
        checks = (
            r['story_type'].strip() == 'v2_sandbox',
            r['moderation_status'].strip() in ('approved', 'override_approved'),
            boolish(r['not_deleted']),
            positive_int(r['assistant_completed']) >= 50,
            positive_int(r['session_count']) >= 2,
            boolish(r['has_world']),
            boolish(r['has_character']) or boolish(r['has_characters']),
            boolish(r['has_opening']),
            r['source_type'].strip() in CATEGORIES,
        )
        surviving = True
        for name, passed in zip(GATE_NAMES, checks):
            individual[name] += int(passed)
            surviving = surviving and passed
            cumulative[name] += int(surviving)
    return {
        'individual_pass_counts': individual,
        'cumulative_survivor_counts': cumulative,
        'parser_psql_true_supported': boolish('t'),
        'parser_psql_false_supported': not boolish('f'),
        'parsed_rows': len(rows),
    }


def discover(rows):
    found=[]; seen=set()
    for r in rows:
        story=r['story_id'].strip()
        if not story or story in seen: raise Hold('missing or duplicated story ID')
        seen.add(story)
        replies=positive_int(r['assistant_completed'])
        sessions=positive_int(r['session_count'])
        if (r['story_type'].strip()=='v2_sandbox'
            and r['moderation_status'].strip() in ('approved','override_approved')
            and boolish(r['not_deleted'])
            and replies>=50 and sessions>=2
            and boolish(r['has_world'])
            and (boolish(r['has_character']) or boolish(r['has_characters']))
            and boolish(r['has_opening'])
            and r['source_type'].strip() in CATEGORIES):
            found.append({'story_id':story,'source_type':r['source_type'].strip(),
                          'assistant_completed':replies,'session_count':sessions})
    return found

def select(inventory, guards):
    approved={}
    for r in guards:
        story=r['story_id'].strip()
        if not story or story in approved: raise Hold('bad guard ID uniqueness')
        approved[story]=r
    pool=[]
    for story in inventory:
        g=approved.get(story['story_id'])
        if not g: continue
        # Owner attests one RolePlay story UUID = one independent semantic world.
        # Keep legacy owner_world_graph_reviewed/world_component CSV columns
        # for compatibility; they are not separate semantic approval gates.
        keys=['r50_protected_clear','prior_sft_clear',
              'r55_r57_dev_clear','other_protected_clear']
        if not all(boolish(g[k]) for k in keys): continue
        if not g['evidence_reference'].strip(): continue
        # RolePlay story UUID itself is the canonical world component.
        pool.append({**story,'world_component':story['story_id'].strip().lower(),
                     'evidence_reference':g['evidence_reference'].strip()})
    selected=[]; worlds=set()
    for source_type, cap in CATEGORIES.items():
        subset=sorted((x for x in pool if x['source_type']==source_type),
                       key=lambda x:(-x['session_count'],-x['assistant_completed'],x['story_id']))
        for item in subset:
            if sum(s['source_type']==source_type for s in selected)>=cap: break
            if item['world_component'] in worlds: continue
            selected.append(item); worlds.add(item['world_component'])
    return selected, pool

def write_private(path, data):
    p=Path(path); parent=p.parent
    if p.exists() or p.is_symlink() or parent.is_symlink() or not parent.is_dir():
        raise Hold('private destination must be new file in existing directory')
    if parent.stat().st_mode & 0o077:
        raise Hold('private output directory must be mode 0700')
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as h:
            json.dump(data,h,ensure_ascii=False,indent=2);h.write('\n')
    except BaseException:
        p.unlink(missing_ok=True)
        raise

def audit(args):
    input_rows=private_csv(args.inventory, STORY_FIELDS)
    discovered=discover(input_rows)
    diagnostics=safe_gate_diagnostics(input_rows)
    if diagnostics['cumulative_survivor_counts']['recognized_source_type'] != len(discovered):
        raise Hold('diagnostic and discovery count mismatch')
    by_source={source:sum(x['source_type']==source for x in discovered)
               for source in CATEGORIES}
    safe={'schema':'r58_round1_pilot_safe_v1',
          'parser_version':PARSER_VERSION,
          'condition_diagnostics':diagnostics,
          'status':'R58_ROUND1_DISCOVERY_ONLY__WORLD_GUARD_HOLD',
          'inventory_rows':len(input_rows),'metadata_eligible':len(discovered),
          'metadata_eligible_by_source':by_source,
          'max_semantic_worlds':5,'max_reply_targets_planned':20,
          'owner_world_identity_policy':OWNER_WORLD_IDENTITY_POLICY,
          'cross_uuid_semantic_review_required':False,
          'candidate_reply_text_accessed':False,'train_admitted':0,
          'validation_admitted':0,'teacher_admitted':0,
          'expansion_allowed':False,'owner_expansion_approval':'REQUIRED'}
    if len(input_rows) >= 100 and not discovered:
        safe['status'] = 'R58_ROUND1_UNEXPECTED_ZERO__CSV_GATE_HOLD'
        return safe
    if args.guards:
        if not args.private_output: raise Hold('private output required for guarded selection')
        guards=private_csv(args.guards, GUARD_FIELDS)
        picked, cleared=select(discovered,guards)
        safe['guard_registry_rows']=len(guards)
        safe['owner_claimed_cleared_count']=len(cleared)
        safe['picked_story_count']=len(picked)
        safe['picked_by_source']={k:sum(r['source_type']==k for r in picked) for k in CATEGORIES}
        safe['status']=('R58_ROUND1_PRIVATE_SHORTLIST_READY__PROTECTED_SET_REVIEW_PENDING'
                         if picked else 'R58_ROUND1_WORLD_GUARD_HOLD__NO_SELECTION')
        if picked:
            private={'schema':'r58_round1_pilot_private_v1',
                     'status':'SHORTLIST_ONLY__NOT_ADMITTED',
                     'selected':picked,
                     'cap_reply_targets':20,
                     'requires_world_review':False,
                     'owner_world_identity_policy':OWNER_WORLD_IDENTITY_POLICY,
                     'requires_protected_set_evidence_review':True,
                     'requires_owner_confirmation_before_expansion':True}
            write_private(args.private_output,private)
    return safe

def main():
    ap=argparse.ArgumentParser(description='R58 Round1 owner-private discovery and pilot selector')
    ap.add_argument('--inventory',required=True)
    ap.add_argument('--guards')
    ap.add_argument('--private-output')
    ap.add_argument('--safe-output')
    args=ap.parse_args()
    try:
        result=audit(args)
        body=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        if args.safe_output:
            target=Path(args.safe_output)
            if target.exists() or target.is_symlink() or not target.parent.is_dir():
                raise Hold('safe output must be a new file')
            target.write_text(body,encoding='utf-8')
        print(body,end='')
        return 0
    except (Hold, OSError,ValueError,KeyError,TypeError):
        print('R58_ROUND1_PILOT: HOLD (private input / world guard / output)',file=sys.stderr)
        return 42

if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""R58 G1 five-story metadata-only collision signals; never clears any guard.

Owner-local: story IDs pass only through local PostgreSQL stdin, not argv/logs.
Only an aggregate JSON result is emitted. Protected sets and chat text untouched.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCHEMA='r58_round1_g1_structural_overlap_safe_v1'
EXPECTED_CSV={'story_id','source_type','review_state','world_component',
              'owner_world_graph_reviewed','r50_protected_clear',
              'prior_sft_clear','r55_r57_dev_clear','other_protected_clear',
              'evidence_reference'}
GUARDS=['owner_world_graph_reviewed','r50_protected_clear',
        'prior_sft_clear','r55_r57_dev_clear','other_protected_clear']
ID_RE=re.compile(r'^[A-Za-z0-9_-]{1,128}$')

class Hold(Exception):
    pass

def load_queue(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>100000:
        raise Hold('invalid owner-private review queue')
    if path.stat().st_mode & 0o077:
        raise Hold('review queue must be mode 0600')
    with path.open('r',encoding='utf-8-sig',newline='') as h:
        reader=csv.DictReader(h)
        if not reader.fieldnames or not EXPECTED_CSV <= set(reader.fieldnames):
            raise Hold('G1 queue columns missing')
        rows=list(reader)
    ids=[]
    for row in rows:
        sid=row['story_id']
        if not ID_RE.fullmatch(sid):
            raise Hold('story identifier format HOLD')
        if any(row[g].strip().lower() not in {'false','f','0','no',''} for g in GUARDS):
            raise Hold('review queue must still have all guards false')
        if row['world_component'].strip() or row['evidence_reference'].strip():
            raise Hold('unexpected pre-certification of world or evidence')
        if row['review_state']!='G1_HOLD':
            raise Hold('review state must be G1_HOLD')
        ids.append(sid)
    if not 1<=len(ids)<=5 or len(set(ids))!=len(ids):
        raise Hold('queue size or uniqueness HOLD')
    return ids

def build_sql(ids):
    if not ids or len(ids)>5 or any(not ID_RE.fullmatch(x) for x in ids):
        raise Hold('unsafe bounded identifiers')
    obj=json.dumps([{'story_id':v} for v in ids],separators=(',',':'),ensure_ascii=True)
    # Validated identifiers cannot contain quotes, semicolons or SQL metacharacters.
    return """BEGIN READ ONLY;
WITH selected AS (
  SELECT x.story_id FROM jsonb_to_recordset('""" + obj + """'::jsonb)
     AS x(story_id text)
),
  story AS (
    SELECT s.story_id, t.id AS matched_id, t.author_id,
           NULLIF(lower(btrim(t.title)),'') AS norm_title,
           NULLIF(btrim(t.world_setting),'') AS world_setting,
           t.v2_data->'world' AS world_json
    FROM selected s LEFT JOIN public.user_stories t ON t.id=s.story_id
  ),
  pair_flags AS (
    SELECT
      (a.author_id IS NOT NULL AND a.author_id=b.author_id) AS same_author,
      (a.norm_title IS NOT NULL AND a.norm_title=b.norm_title) AS same_title,
      (a.world_setting IS NOT NULL AND a.world_setting=b.world_setting) AS same_world_setting,
      (a.world_json IS NOT NULL AND b.world_json IS NOT NULL AND
       a.world_json <> '{}'::jsonb AND a.world_json=b.world_json) AS same_world_json
    FROM story a JOIN story b ON a.story_id < b.story_id
  )
SELECT jsonb_build_object(
  'transaction_read_only',current_setting('transaction_read_only'),
  'reader_role_correct',current_user='r58_export_reader',
  'selected_count',(SELECT count(*) FROM selected),
  'matched_count',(SELECT count(*) FROM story WHERE matched_id IS NOT NULL),
  'compared_pairs',(SELECT count(*) FROM pair_flags),
  'same_author_pairs',(SELECT count(*) FROM pair_flags WHERE same_author),
  'same_title_pairs',(SELECT count(*) FROM pair_flags WHERE same_title),
  'same_world_setting_pairs',(SELECT count(*) FROM pair_flags WHERE same_world_setting),
  'same_v2_world_exact_pairs',(SELECT count(*) FROM pair_flags WHERE same_world_json)
)::text;
COMMIT;
"""

def project(data, size):
    if (not isinstance(data,dict) or data.get('reader_role_correct') is not True
        or data.get('transaction_read_only')!='on'):
        raise Hold('reader identity / transaction HOLD')
    keys=['selected_count','matched_count','compared_pairs','same_author_pairs',
          'same_title_pairs','same_world_setting_pairs','same_v2_world_exact_pairs']
    if any(type(data.get(k)) is not int for k in keys):
        raise Hold('unexpected SQL aggregate schema')
    if data['selected_count']!=size or data['matched_count']!=size:
        raise Hold('source row mapping mismatch')
    possible=size*(size-1)//2
    if data['compared_pairs']!=possible:
        raise Hold('pair count mismatch')
    if any(not 0<=data[k]<=possible for k in keys[3:]):
        raise Hold('pair counts outside known bounds')
    return {
        'schema':SCHEMA,
        'status':'R58_ROUND1_G1_STRUCTURAL_SIGNALS_ONLY__PROTECTION_AND_WORLD_HOLD',
        'metadata_story_rows_checked':size,
        'pairwise_comparisons':possible,
        'same_author_pairs':data['same_author_pairs'],
        'same_title_pairs':data['same_title_pairs'],
        'same_world_setting_pairs':data['same_world_setting_pairs'],
        'same_v2_world_exact_pairs':data['same_v2_world_exact_pairs'],
        'interpretation':'Only possible overlaps; zero matching pairs does not certify semantic independence.',
        'world_components_certified':0,
        'r50_protection_checked':False,
        'prior_sft_exposure_checked':False,
        'r55_r57_dev_checked':False,
        'candidate_reply_text_accessed':False,
        'training_admitted':0,
        'expansion_allowed':False,
    }

def run(queue,plan_only):
    ids=load_queue(queue)
    if plan_only:
        return {'schema':SCHEMA,'status':'PLAN_ONLY__NO_DB_ACCESS',
                'queue_size':len(ids),'will_query_metadata_only':True,
                'world_clearance':'HOLD','expansion_allowed':False}
    if not os.environ.get('PGUSER','').startswith('r58_export_reader.'):
        raise Hold('dedicated read-only PGUSER required')
    if not os.environ.get('PGHOST'):
        raise Hold('PGHOST missing')
    env=dict(os.environ)
    env['PGOPTIONS']='-c default_transaction_read_only=on -c statement_timeout=45000'
    try:
        p=subprocess.run(['psql','-X','-w','-q','-A','-t','-v','ON_ERROR_STOP=1'],
             input=build_sql(ids),capture_output=True,text=True,
             timeout=60,env=env,check=False)
    except (subprocess.TimeoutExpired,OSError):
        raise Hold('read-only SQL execution unavailable')
    # NEVER surface stderr: PostgreSQL errors may echo a private SQL expression.
    if p.returncode!=0:
        raise Hold('read-only SQL HOLD')
    lines=[line.strip() for line in p.stdout.splitlines() if line.strip()]
    if len(lines)!=1:
        raise Hold('unexpected SQL stdout')
    try:
        return project(json.loads(lines[0]),len(ids))
    except (json.JSONDecodeError,ValueError,TypeError):
        raise Hold('invalid SQL JSON output')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--private-queue',type=Path,required=True)
    p.add_argument('--plan-only',action='store_true')
    args=p.parse_args()
    try:
        print(json.dumps(run(args.private_queue,args.plan_only),
              ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (Hold,OSError,KeyError,ValueError,TypeError):
        print('R58_G1_STRUCTURAL_SIGNALS: HOLD; no private details emitted',file=sys.stderr)
        return 42

if __name__=='__main__':
    raise SystemExit(main())

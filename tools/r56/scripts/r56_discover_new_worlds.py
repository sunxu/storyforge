#!/usr/bin/env python3
"""R56 Stage2 metadata-only triage of NON-Gold original story sources.

Never opens original story content or R50. An output row is only a candidate for
independent world review, never proof of independence/test admission.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,pathlib,re,subprocess,sys

PINS={
 'evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl':'a2038e18bee8ddef96b93bb6746270a462f9a6e4',
 'evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl':'eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90',
 'data/compiled/v0.3/train.jsonl':'3e64c9932ca43fefa8ecfb200085fe718581b6f9',
 'data/compiled/v0.3/validation.jsonl':'db0ae8b86038be1b372d547fdb2d6b0b7e33b54e',
 'data/compiled/v0.3/test.jsonl':'c17f225967b6b2f8cbaf3d82fadac1b4031d0654'}
R50_PATTERN=re.compile(r'(^|[/_.\\-])r50([/_.\\-]|$)',re.I)
HEX64=re.compile('^[a-f0-9]{64}$')
class Block(Exception):pass

def require(cond,s):
 if not cond:raise Block(s)

def read_jsonl(p):
 require(p.is_file(),'INPUT_NOT_FOUND');raw=p.read_text(encoding='utf-8').splitlines()
 require(raw and all(x.strip() for x in raw),'EMPTY_OR_BLANK_JSONL')
 return [json.loads(x) for x in raw]

def sid(x):
 m=x.get('metadata') or {};return m.get('story_id') or m.get('source_story_id')

def pinned_world_ids(repo):
 gold,prior=set(),set()
 for rel,expected in PINS.items():
  file=repo/rel;require(file.is_file(),'MISSING_PINNED_FILE')
  p=subprocess.run(['git','hash-object','--',str(file)],capture_output=True,text=True,check=True)
  require(p.stdout.strip()==expected,'PINNED_BLOB_MISMATCH')
  for r in read_jsonl(file):
   uuid=sid(r);require(isinstance(uuid,str) and uuid,'MISSING_WORLD_UUID_IN_FROZEN_SOURCE')
   (gold if rel.startswith('evaluations/') else prior).add(uuid)
 return gold,prior

def parse_historical(p):
 data=json.loads(p.read_text(encoding='utf-8'))
 require(data.get('schema')=='storyforge-r56-source-world-exposure-v1','HISTORICAL_SCHEMA_BAD')
 require(data.get('r50_read') is False,'HISTORICAL_R50_FLAG')
 require(set(data.get('splits',{}))=={'r46_train','r46_val','r54_train','r54_val'},'SPLIT_SET_BAD')
 splits=data['splits'];expected={'r46_train':49,'r46_val':15,'r54_train':31,'r54_val':9}
 for k,n in expected.items():
  require(sum(len(v) for v in splits[k].values())==n,'HISTORIC_SPLIT_COUNT_BAD')
  require(all(isinstance(v,list) and all(isinstance(h,str) and HEX64.fullmatch(h) for h in v) for v in splits[k].values()),'HISTORIC_TARGET_HASH_BAD')
 return set().union(*(set(v) for v in splits.values()))

def triage(inventory,gold,prior):
 seen=set();rows=[]
 for r in inventory:
  require(isinstance(r,dict),'INVENTORY_NOT_OBJECT')
  uuid=r.get('story_uuid_PRIVATE');digest=r.get('original_story_sha256_PRIVATE');loc=r.get('original_source_path_PRIVATE','')
  require(isinstance(uuid,str) and uuid.strip() and uuid not in seen,'DUPLICATE_OR_MISSING_WORLD_UUID')
  require(isinstance(digest,str) and HEX64.fullmatch(digest),'BAD_ORIGINAL_SOURCE_SHA256')
  require(isinstance(loc,str),'BAD_SOURCE_LOCATOR')
  # This script opens only the inventory JSONL, the frozen Git files, and
  # the R46/R54 historical manifest: never resolves the source locators.
  require(not any(R50_PATTERN.search(str(v)) for v in r.values() if isinstance(v,str)),'R50_REFERENCE_FORBIDDEN')
  seen.add(uuid)
  if uuid in gold:state='ALREADY_PRESENT_IN_GOLD195__NOT_NEW_WORLD'
  elif uuid in prior:state='KNOWN_HISTORICAL_UUID_OVERLAP__EXCLUDE'
  else:state='POTENTIAL_NON_GOLD_WORLD__SEMANTIC_EXPOSURE_HOLD'
  rows.append({'story_uuid_PRIVATE':uuid,'original_story_sha256_PRIVATE':digest,
    'original_source_path_PRIVATE':loc,'earliest_creation_timestamp_PRIVATE':r.get('earliest_creation_timestamp_PRIVATE',''),
    'provenance_evidence_private':r.get('provenance_evidence_private',''),
    'uuid_triage':state,'world_semantic_reviewer':'NOT_RUN',
    'target_time_story_card_gate':'HOLD','case_source_history_gate':'HOLD','train_eval_semantic_gate':'HOLD',
    'shared_character_setting_plot_gate':'HOLD','formal_world_admitted':'NO'})
 return rows

def write_csv(p,rows):
 import io
 fields=['story_uuid_PRIVATE','original_story_sha256_PRIVATE','original_source_path_PRIVATE','earliest_creation_timestamp_PRIVATE',
  'provenance_evidence_private','uuid_triage','world_semantic_reviewer','target_time_story_card_gate','case_source_history_gate',
  'train_eval_semantic_gate','shared_character_setting_plot_gate','formal_world_admitted']
 b=io.StringIO();w=csv.DictWriter(b,fieldnames=fields);w.writeheader();w.writerows(rows)
 with p.open('x',encoding='utf-8',newline='') as f:f.write(b.getvalue())
 os.chmod(p,0o600)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--repo',required=True,type=pathlib.Path)
 p.add_argument('--historical',required=True,type=pathlib.Path)
 p.add_argument('--inventory',required=True,type=pathlib.Path)
 p.add_argument('--out-dir',required=True,type=pathlib.Path)
 a=p.parse_args();os.umask(0o077)
 try:
  require(not a.out_dir.exists(),'OUTPUT_EXISTS_NO_OVERWRITE')
  # Read only metadata inventory; refuse any R50 path or named R50 reference.
  require(not R50_PATTERN.search(str(a.inventory)),'R50_INVENTORY_PATH_FORBIDDEN')
  gold,prior=pinned_world_ids(a.repo)
  prior|=parse_historical(a.historical)
  require(len(gold)==13,'FROZEN_GOLD_WORLD_COUNT_NOT13')
  inventory=read_jsonl(a.inventory)
  rows=triage(inventory,gold,prior)
  a.out_dir.mkdir(mode=0o700,parents=True);pr=a.out_dir/'private';pr.mkdir(mode=0o700)
  write_csv(pr/'R56_NON_GOLD_WORLD_METADATA_TRIAGE_PRIVATE.csv',rows)
  counts={'schema':'storyforge-r56-stage2-new-world-discovery-count-only-v1','status':'NON_GOLD_METADATA_TRIAGE_ONLY__ZERO_WORLDS_ADMITTED',
    'inventory_world_rows':len(rows),'gold_uuid_overlap':sum(x['uuid_triage'].startswith('ALREADY') for x in rows),
    'historical_uuid_overlap':sum(x['uuid_triage'].startswith('KNOWN') for x in rows),
    'potential_new_uuid_only':sum(x['uuid_triage'].startswith('POTENTIAL') for x in rows),
    'independently_proven_worlds':0,'official_test_admitted':0,'r50_read':False,
    'gpu_job_started':False,'training_performed':False,'model_promoted':False,
    'note':'Potential count is a UUID-only triage, not semantic disjointness, historical evaluation exposure clearance, or eligible world count.'}
  (a.out_dir/'R56_NON_GOLD_INVENTORY_COUNTS_ONLY.json').write_text(json.dumps(counts,indent=2,sort_keys=True)+'\n',encoding='utf-8')
  print('R56_INVENTORY_TRIAGE_COUNT_ONLY__ALL_POTENTIAL_HOLD')
  return 0
 except (Block,OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.CalledProcessError) as e:
  print('R56_NEW_WORLD_DISCOVERY_BLOCKED:',str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

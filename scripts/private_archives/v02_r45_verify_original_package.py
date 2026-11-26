#!/usr/bin/env python3
"""Fail-closed R45 candidate package integrity check. Optional full 14-source replay."""
from pathlib import Path
import hashlib,json,sys,zipfile,argparse,csv
p=argparse.ArgumentParser();p.add_argument('--raw-14',type=Path);a=p.parse_args()
D=Path(__file__).resolve().parent
h=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
for line in (D/'SHA256SUMS.txt').read_text().splitlines():
 digest,name=line.split('  ',1);assert h(D/name)==digest, 'checksum mismatch '+name
G=json.loads((D/'R45_PHASE1_CONTENT_AND_CANDIDATE_FREEZE_GATE.json').read_text())
assert G['review_window']==G['scope_accepted_rows']+G['all_holds']==82
assert G['r45_new_holds']==7 and G['all_holds']==18
assert G['approved_for_train']==G['approved_for_validation']==G['approved_for_test']==0
assert not G['gpu_authorized'] and not G['gpu_started'] and not G['training_performed']
assert G['fresh_external_heldout_received']==0 and not G['full_hidden_world_alias_certified']
assert G['experimental_candidate_freeze_status']=='FROZEN_FOR_FUTURE_ADMISSION_REVIEW_ONLY'
R=json.loads((D/'R43_HF_RUNTIME_REPORT_PRIVATE_v2.json').read_text())
assert h(D/'R43_HF_RUNTIME_REPORT_PRIVATE_v2.json')==G['r43_actual_cpu_report_sha256']
ids=set();splitid={};n=0
for split,count in [('train',49),('validation',15)]:
 f=D/f'R45_{split.upper()}_FROZEN_CANDIDATE_{count}_NOT_APPROVED.jsonl';assert h(f)==G[split+'_sha256']
 rows=[json.loads(s)for s in f.read_text().splitlines() if s.strip()];assert len(rows)==count
 rh={x['sample_id']:x for x in R['datasets'][split]['rows']}
 group=set()
 for r in rows:
  assert r['id'] not in ids;ids.add(r['id']);n+=1;group.add(r['metadata']['source_story_id'])
  assert r['metadata']['dataset_admission']=='NOT_APPROVED'
  m=r['messages'];assert m[0]['role']=='system' and m[-2]['role']=='user' and m[-1]['role']=='assistant'
  assert all(x.get('loss') is False for x in m[:-1]) and m[-1].get('loss') is True
  assert hashlib.sha256(m[-1]['content'].encode()).hexdigest()==r['metadata']['target_sha256']
  assert rh[r['id']]['status']=='PASS' and len(rh[r['id']]['labels_sha256'])==64
 splitid[split]=group
assert n==64 and not splitid['train']&splitid['validation']
route=list(csv.DictReader((D/'R45_82_FINAL_PILOT_ROUTE_PRIVATE.csv').open()))
assert len(route)==82 and len({x['sample_id'] for x in route})==82
assert sum(x['r45_pilot_decision']=='NEW_LONG_RANGE_PERSONA_PROMISE_HOLD'for x in route)==7
assert sum(x['r45_pilot_decision']=='PRIOR_CONSERVATIVE_HOLD'for x in route)==11
assert set(x['sample_id']for x in route if x['r45_pilot_decision']=='SCOPED_SEMANTIC_ACCEPTED_CANDIDATE_ONLY')==ids
if a.raw_14:
 assert h(a.raw_14)==G['original_source_14_zip_sha256']
 source={}
 with zipfile.ZipFile(a.raw_14) as z:
  for name in z.namelist():
   if len(name)>3 and name[:2].isdigit() and name[2]=='-':source[int(name[:2])]=json.loads(z.read(name))
 for evidence in map(json.loads,(D/'R45_71_EXACT_SOURCE_AND_SCOPED_DECISIONS_PRIVATE.jsonl').read_text().splitlines()):
  row=source[evidence['source_story_rank']]['messages'][evidence['source_target_index']]
  assert hashlib.sha256(row['content'].encode()).hexdigest()==evidence['target_sha256']
 print('R45_RAW14_ORIGINAL_TARGETS_71_PASS')
print('R45_PHASE1_SCOPE_FREEZE_49_15_PASS__TRAINING_NOT_APPROVED__NO_GPU')

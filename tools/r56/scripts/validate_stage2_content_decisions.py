#!/usr/bin/env python3
"""Validate private R56 Stage2 single-visible-content review against uploaded task ZIP.
Only reads local files, requires full HOLD and no other source/material.
"""
import argparse,csv,hashlib,io,json,pathlib,zipfile,sys
H=lambda b:hashlib.sha256(b).hexdigest()
def jb(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
def verify(task_zip,dir):
 p=pathlib.Path(dir);safe=p/'safe/R56_STAGE2_CONTENT_REVIEW_COUNTS_ONLY.json'
 s=json.loads(safe.read_text(encoding='utf8'))
 assert s['schema']=='storyforge-r56-stage2-single-content-review-safe-counts-v1'
 assert s['status']=='32_OF_32_VISIBLE_ONLY_CONTENT_REVIEWS_COMPLETE__ALL24_PROVISIONAL_HOLD__NO_FORMAL_ADMISSION'
 assert s['official_test_admitted']==0 and s['provisional24_all_still_hold']==24
 assert s['target_sha256_local_verified']==s['frozen_history_sha256_local_verified']==32
 assert s['target_time_card_versions_verified']==s['independent_human_content_reviewer_signoffs']==0
 assert not any(s[x] for x in ('r50_read','gpu_job_started','training_performed','model_promoted'))
 with zipfile.ZipFile(task_zip) as z:
  assert z.testzip() is None
  tasks=[json.loads(x) for x in z.read('private/R56_GOLD32_CONTENT_AUDITOR_TASKS_PRIVATE.jsonl').decode().splitlines() if x.strip()]
  blanks=list(csv.DictReader(io.StringIO(z.read('private/R56_GOLD32_INDEPENDENT_CONTENT_DECISION_BLANK_PRIVATE.csv').decode())))
 records=[json.loads(x) for x in (p/'private/R56_GOLD32_CONTENT_AUDITOR_DECISIONS_SINGLE_REVIEW_PRIVATE.jsonl').read_text('utf8').splitlines() if x.strip()]
 with (p/'private/R56_GOLD32_CONTENT_AUDITOR_DECISIONS_SINGLE_REVIEW_PRIVATE.csv').open(encoding='utf8',newline='') as f: csvs=list(csv.DictReader(f))
 assert len(tasks)==len(records)==len(csvs)==len(blanks)==32
 ids=set();counters={'03':0,'05':0};provisional=0
 for task,rec,row,blank in zip(tasks,records,csvs,blanks):
  cid=task['candidate_id_PRIVATE'];assert cid not in ids;ids.add(cid)
  assert row['candidate_id_PRIVATE']==blank['candidate_id_PRIVATE']==rec['candidate_id_PRIVATE']==cid
  assert task['story_slot_PRIVATE']==row['story_slot_PRIVATE']==rec['story_slot_PRIVATE']
  assert task['target_original_sha256_PRIVATE']==row['target_sha256_PRIVATE']==rec['target_original_sha256_PRIVATE']
  assert task['source_original_sha256_PRIVATE']==row['source_sha256_PRIVATE']==rec['source_original_sha256_PRIVATE']
  assert H(task['gold_target_for_content_review_only_PRIVATE']['content'].encode('utf8'))==row['target_sha256_PRIVATE']
  assert H(jb(task['visible_history_as_frozen_in_gold87_PRIVATE']))==rec['history_sha256_PRIVATE']==task['history_sha256_PRIVATE']
  assert rec['source_original_bytes_verified'] is False and rec['target_utf8_sha256_verified'] and rec['history_sha256_verified']
  assert rec['final_test_admission']==row['final_test_admission']=='HOLD_NOT_TEST_ADMITTED'
  assert rec['reviewer_decision']==row['reviewer_decision']=='HOLD_EVIDENCE_INSUFFICIENT__NO_TEST_ADMISSION'
  assert rec['reviewer_id_PRIVATE']==row['reviewer_id_PRIVATE']=='R56_CONTENT_REVIEW_ASSISTANT_SINGLE_20261022'
  assert row['reviewer_rationale_PRIVATE'] and len(row['reviewer_rationale_PRIVATE'])>110
  assert task['source_message_ids_PRIVATE'][-2]==rec['last_user_source_message_id_PRIVATE']
  assert H(task['visible_history_as_frozen_in_gold87_PRIVATE'][-1]['content'].encode('utf8'))==rec['last_user_sha256_PRIVATE']
  assert row['reviewer_evidence_sha256_PRIVATE']==rec['reviewer_evidence_sha256_PRIVATE']
  assert all(row[g+'_gate']==rec['gate_statuses'][g] for g in rec['gate_statuses'])
  assert all(not row[g+'_gate'].startswith('PASS_FORMAL') for g in rec['gate_statuses'])
  # Rebuild the exact per-case evidence bytes and hash
  evidence={'source_story_uuid_PRIVATE':rec['story_uuid_PRIVATE'], 'source_original_sha256_PRIVATE_AS_DECLARED':rec['source_original_sha256_PRIVATE'],
   'source_json_pointer_PRIVATE':rec['source_json_pointer_PRIVATE'],'source_message_ids_PRIVATE':task['source_message_ids_PRIVATE'],
   'target_turn':rec['target_turn'],'target_original_sha256_PRIVATE':rec['target_original_sha256_PRIVATE'],
   'history_sha256_PRIVATE':rec['history_sha256_PRIVATE'],'last_visible_user_source_message_id_PRIVATE':rec['last_user_source_message_id_PRIVATE'],
   'last_visible_user_sha256_PRIVATE':rec['last_user_sha256_PRIVATE'],'gate_decisions':{g+'_gate':rec['gate_statuses'][g] for g in rec['gate_statuses']},
   'rationale':row['reviewer_rationale_PRIVATE'],'reviewer_decision':row['reviewer_decision'],
   'reviewer_scope':'LOCAL_VISIBLE_CONTENT_SINGLE_ASSISTANT_REVIEW_NOT_INDEPENDENT_HUMAN_SIGNOFF'}
  assert H(jb(evidence))==row['reviewer_evidence_sha256_PRIVATE'],cid
  provisional+=bool(task['provisional24']);counters[rec['story_slot_PRIVATE']]+=1
 assert counters=={'03':14,'05':18} and provisional==24
 assert s['private_csv_sha256']==H((p/'private/R56_GOLD32_CONTENT_AUDITOR_DECISIONS_SINGLE_REVIEW_PRIVATE.csv').read_bytes())
 assert s['private_jsonl_sha256']==H((p/'private/R56_GOLD32_CONTENT_AUDITOR_DECISIONS_SINGLE_REVIEW_PRIVATE.jsonl').read_bytes())
 manifest=json.loads((p/'SHA256SUMS.json').read_text('utf8'))
 for rel,dig in manifest['files'].items():assert H((p/rel).read_bytes())==dig,(rel,'manifest sha mismatch')
 assert 'SHA256SUMS.json' not in manifest['files']
 return {'status':'R56_STAGE2_SINGLE_VISIBLE_CONTENT_REVIEW_REHASH_PASS__ALL32_HOLD','rows':32,'provisional_hold':24,'story_counts':counters,'evidence_digest_verified':32,'official_test_admitted':0}
if __name__=='__main__':
 ar=argparse.ArgumentParser();ar.add_argument('--tasks',required=True);ar.add_argument('--review-root',required=True);ar.add_argument('--out-safe');args=ar.parse_args()
 try:
  result=verify(args.tasks,args.review_root)
  if args.out_safe:pathlib.Path(args.out_safe).write_bytes(jb(result))
  print(json.dumps(result,ensure_ascii=False,sort_keys=True))
 except Exception as e:print('FAIL_VALIDATION',type(e).__name__,str(e)[:200],file=sys.stderr);sys.exit(1)

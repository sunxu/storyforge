#!/usr/bin/env python3
"""R56 Stage2: prepare PRIVATE independent Gold03/05 content-audit packets, all HOLD.

No access to R50; no model inference / training / data rewrites. Never upload
private packets, reference assistant targets, source IDs, or reviewer notes.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,pathlib,re,subprocess,sys

GOLD87_REL='evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl'
GOLD87_BLOB='a2038e18bee8ddef96b93bb6746270a462f9a6e4'
VERIFIED_STATUS='OWNER_REPLAY_REFERENCED_FILES_VERIFIED__ALL24_HOLD__NO_ADMISSION'
RECEIPT_SHA='7624d321b14dbbd633d379e56894afe7ad606da566ffc03c419b39b3c95f80ce'
GATES=['source_original_exact','target_time_card_and_canon','full_model_visible_history','characters_and_aliases','age_and_consent_at_target','content_boundaries','player_agency','character_rule_consistency','story_continuity','prior_train_eval_semantic_exposure','cross_world_independence']

class Block(Exception): pass

def require(ok,reason):
 if not ok:raise Block(reason)

def sha(b):return hashlib.sha256(b).hexdigest()

def json_bytes(obj):return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')

def verify_report(report):
 require(report.get('schema')=='storyforge-r56-owner-receipt-verification-v1','WRONG_VERIFIED_SCHEMA')
 require(report.get('status')==VERIFIED_STATUS,'OWNER_REFERENCE_NOT_VERIFIED')
 require(report.get('receipt_sha256')==RECEIPT_SHA,'WRONG_FROZEN_OWNER_RECEIPT')
 for k in ('five_pinned_blobs_reverified_locally','original_output_sha256_verified','deep_output_sha256_verified','both_unittest_logs_verified','private_case_sheet_structural_check','reconstructed_expected_deep_summary_sha256_matches','reconstructed_expected_safe_summary_sha256_matches'):
  require(report.get(k) is True,'UNVERIFIED_'+k)
 for k in ('r50_read','gpu_job_started','training_performed','model_promoted'):
  require(report.get(k) is False,'FORBIDDEN_'+k)
 require(report.get('official_test_admitted')==0 and report.get('additional_independent_worlds_missing')==2,'PREMATURE_ADMISSION')
 require(report.get('independent_case_content_gate')=='HOLD_NOT_REVIEWED','NONHOLD_CONTENT')
 require(report.get('source_exposure_semantic_gate')=='HOLD_NOT_REVIEWED','NONHOLD_EXPOSURE')
 require(report.get('cross_world_independence')=='HOLD_NOT_PROVEN','NONHOLD_WORLD')

def rows_from_csv(path):
 with path.open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def verify_case_rows(rows):
 require(len(rows)==32,'NOT_32_CASE_ROWS')
 require(len({r['candidate_id_PRIVATE'] for r in rows})==32,'DUP_CASE_ID')
 require(sum(r['selected24_provisional']=='YES' for r in rows)==24,'NOT_24_PROVISIONAL')
 for code,n,k in [('03',14,12),('05',18,12)]:
  sub=[r for r in rows if r['story_code']==code]
  require(len(sub)==n and sum(r['selected24_provisional']=='YES' for r in sub)==k,'CASE_WORLD_COUNT_MISMATCH')
 for r in rows:
  require(r['status']=='HOLD_NOT_TEST_ADMITTED','CASE_NOT_HOLD')
  require(r.get('gold_independent_review')=='NOT_RUN','FAKE_INDEPENDENT_REVIEW')
  require(r.get('target_time_card_recorded')=='ABSENT','UNEXPECTED_CARD_STATE')

def verify_frozen_gold(repo):
 src=repo/GOLD87_REL
 require(src.is_file(),'GOLD87_SOURCE_NOT_FOUND')
 cmd=subprocess.run(['git','hash-object','--',str(src)],capture_output=True,text=True,check=True)
 require(cmd.stdout.strip()==GOLD87_BLOB,'GOLD87_GIT_BLOB_SHA_MISMATCH')
 records=[]
 for line in src.read_text(encoding='utf-8').splitlines():
  require(line.strip(),'GOLD87_EMPTY_JSONL_LINE');records.append(json.loads(line))
 require(len(records)==87,'GOLD87_ROW_COUNT_WRONG')
 return {r['id']:r for r in records}

def verified_record(row,gold):
 rid=row['candidate_id_PRIVATE'];require(rid in gold,'CANDIDATE_ID_NOT_IN_PINNED_GOLD87')
 r=gold[rid];m=r['metadata'];msgs=r['messages']
 require(len(msgs)>=2 and msgs[-1]['role']=='assistant' and msgs[-2]['role']=='user','ROLE_CYCLE_BAD')
 require(m['context_message_count']==len(msgs)-1,'CONTEXT_LENGTH_BAD')
 require(str(m['target_turn_index'])==row['target_turn'],'TURN_MISMATCH')
 require(str(m['context_message_count'])==row['context_message_count'],'CONTEXT_COUNT_MISMATCH')
 tg=sha(msgs[-1]['content'].encode('utf-8'))
 require(tg==m.get('target_sha256_utf8'),'GOLD_TARGET_DIGEST_MISMATCH')
 require(tg==row['gold_target_sha256_PRIVATE'],'SHEET_TARGET_DIGEST_MISMATCH')
 require(m.get('source_sha256')==row['source_snapshot_sha256_PRIVATE'],'SHEET_ORIGINAL_DIGEST_MISMATCH')
 require(m.get('story_card_version_id') is None,'STORY_CARD_VERSION_STATE_CHANGED')
 ids=m.get('source_message_ids');turns=m.get('source_turn_indices')
 require(isinstance(ids,list) and len(ids)==len(msgs) and len(set(map(str,ids)))==len(ids),'SOURCE_IDS_BAD')
 require(isinstance(turns,list) and len(turns)==len(msgs) and all(type(x) is int for x in turns) and turns==sorted(set(turns)),'SOURCE_TURNS_BAD')
 require(turns[-1]==m['target_turn_index'],'TARGET_TURN_NOT_LAST')
 require(all(isinstance(x.get('content'),str) and x['content'].strip() for x in msgs),'EMPTY_MESSAGE')
 return r,tg

def content_packet(row,gold):
 r,digest=verified_record(row,gold);m=r['metadata']; msgs=r['messages']
 # A content-audit packet is intentionally NOT a blind model evaluation prompt.
 # Gold target is present for independent CONTENT reviewer and never sent to a model.
 return {'schema':'storyforge-r56-stage2-private-gold-content-audit-task-v1',
  'task_use':'INDEPENDENT_SOURCE_AND_CONTENT_AUDIT_ONLY__NOT_MODEL_EVAL',
  'story_slot_PRIVATE':row['story_code'],'story_uuid_PRIVATE':m['story_id'],
  'candidate_id_PRIVATE':r['id'],'provisional24':row['selected24_provisional']=='YES',
  'target_turn':m['target_turn_index'],'source_file_PRIVATE':m.get('source_file'),
  'source_json_pointer_PRIVATE':m.get('source_json_pointer'),
  'source_original_sha256_PRIVATE':m['source_sha256'],
  'target_original_sha256_PRIVATE':digest,
  'source_message_ids_PRIVATE':m['source_message_ids'],
  'source_turn_indices_PRIVATE':m['source_turn_indices'],
  'visible_history_as_frozen_in_gold87_PRIVATE':msgs[:-1],
  'history_sha256_PRIVATE':sha(json_bytes(msgs[:-1])),
  'gold_target_for_content_review_only_PRIVATE':msgs[-1],
  'evidence_insufficiency_flags':['TARGET_TIME_CARD_VERSION_NOT_VERIFIED','PRE_TARGET_FULL_SYSTEM_RULES_NOT_PROVEN',
   'NO_INDEPENDENT_CONTENT_VERDICT','EXPOSURE_SEMANTICS_NOT_PROVEN','ALIAS_WORLD_ISOLATION_NOT_PROVEN'],
  'model_prompt_is_certified_complete':False,
  'original_gold_unchanged':True,
  'gate_statuses':{x:'HOLD_REVIEW_NEEDED' for x in GATES},
  'reviewer_id_PRIVATE':'','reviewer_evidence_sha256_PRIVATE':'','reviewer_rationale_PRIVATE':'',
  'final_test_admission':'HOLD_NOT_TEST_ADMITTED'}

def write_private(path,payload):
 # chmod sensitive files after write, with umask 077 from CLI.
 with path.open('xb') as f:f.write(payload)
 os.chmod(path,0o600)

def run(repo,verified_report,sheet,out):
 require(not out.exists(),'OUTPUT_EXISTS_NO_OVERWRITE')
 verify_report(json.loads(verified_report.read_text(encoding='utf-8')))
 rows=rows_from_csv(sheet);verify_case_rows(rows)
 gold=verify_frozen_gold(repo)
 tasks=[content_packet(r,gold) for r in rows]
 require(len(tasks)==32 and len({r['candidate_id_PRIVATE'] for r in tasks})==32,'TASK_COUNT_FAIL')
 out.mkdir(parents=True,mode=0o700)
 priv=out/'private';safe=out/'safe';priv.mkdir(mode=0o700);safe.mkdir(mode=0o700)
 packed=((''.join(json.dumps(t,ensure_ascii=False,sort_keys=True)+'\n' for t in tasks)).encode('utf-8'))
 write_private(priv/'R56_GOLD32_CONTENT_AUDITOR_TASKS_PRIVATE.jsonl',packed)
 blank=[]
 for t in tasks:
  a={'story_slot_PRIVATE':t['story_slot_PRIVATE'],'candidate_id_PRIVATE':t['candidate_id_PRIVATE'],
     'target_sha256_PRIVATE':t['target_original_sha256_PRIVATE'],'source_sha256_PRIVATE':t['source_original_sha256_PRIVATE'],
     'reviewer_id_PRIVATE':'','reviewer_evidence_sha256_PRIVATE':'','reviewer_rationale_PRIVATE':'',
     'reviewer_decision':'HOLD_NOT_REVIEWED','final_test_admission':'HOLD_NOT_TEST_ADMITTED'}
  for gate in GATES:a[gate+'_gate']='HOLD_NEEDS_SOURCE_EVIDENCE'
  blank.append(a)
 import io
 h=io.StringIO();writer=csv.DictWriter(h,fieldnames=list(blank[0]));writer.writeheader();writer.writerows(blank)
 write_private(priv/'R56_GOLD32_INDEPENDENT_CONTENT_DECISION_BLANK_PRIVATE.csv',h.getvalue().encode('utf-8'))
 output={'schema':'storyforge-r56-stage2-content-auditor-packet-count-only-v1',
  'status':'32_AUDITOR_PACKETS_PREPARED__24_PROVISIONAL_HOLD__NO_FORMAL_ADMISSION',
  'verified_owner_report_sha256':sha(verified_report.read_bytes()),
  'frozen_gold87_blob_sha1':GOLD87_BLOB,
  'story03_tasks':14,'story05_tasks':18,'total_content_auditor_tasks':32,
  'provisional24_tasks':24,'completed_independent_content_reviews':0,
  'independent_worlds_confirmed':0,'additional_worlds_required':2,
  'target_time_story_card_versions_verified':0,
  'formal_test_admission':0,'r50_read':False,'gpu_job_started':False,
  'training_performed':False,'model_promoted':False,
  'note':'Contains Gold target in private CONTENT reviewer packets; these are NOT blind model evaluation tasks. Human independent review and full time-point evidence still pending.'}
 (safe/'R56_STAGE2_AUDITOR_PACKET_COUNTS_ONLY.json').write_bytes(json_bytes(output))
 return output

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--repo',type=pathlib.Path,required=True)
 ap.add_argument('--verified-report',type=pathlib.Path,required=True)
 ap.add_argument('--case-sheet',type=pathlib.Path,required=True)
 ap.add_argument('--out-dir',type=pathlib.Path,required=True)
 args=ap.parse_args();os.umask(0o077)
 try:
  result=run(args.repo,args.verified_report,args.case_sheet,args.out_dir)
  print(result['status']);print('SAFE_COUNTS_ONLY:',args.out_dir/'safe/R56_STAGE2_AUDITOR_PACKET_COUNTS_ONLY.json')
  return 0
 except (Block,KeyError,TypeError,ValueError,OSError,subprocess.CalledProcessError,json.JSONDecodeError) as e:
  print('R56_STAGE2_BLOCKED:',str(e),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())

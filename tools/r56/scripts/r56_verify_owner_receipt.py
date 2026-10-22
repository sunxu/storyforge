#!/usr/bin/env python3
"""StoryForge R56: fail-closed CPU-only verification of Owner's reported Mac replay.

Never reads R50, calls models, runs GPU, changes Gold, or uploads private data.
May be invoked with --receipt alone (attestation only) or --owner-root (actual
SHA256 and output cross-check); optional --repo pins the five source Git blobs.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, pathlib, re, subprocess, sys

REPORT_SCHEMA = 'storyforge-r56-owner-local-CPU-actual-repo-receipt-v1'
REPORT_STATUS = 'LOCAL_R56_REAL_GOLD195_PRESCREEN_PASS__ALL24_HOLD'
SUMMARY_SCHEMA = 'storyforge-r56-gold195-eligibility-prescreen-v1'
DEEP_SCHEMA = 'storyforge-r56-deep-preflight-count-only-v1'
SOURCE_PINS = {
 'evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl': 'a2038e18bee8ddef96b93bb6746270a462f9a6e4',
 'evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl': 'eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90',
 'data/compiled/v0.3/train.jsonl': '3e64c9932ca43fefa8ecfb200085fe718581b6f9',
 'data/compiled/v0.3/validation.jsonl': 'db0ae8b86038be1b372d547fdb2d6b0b7e33b54e',
 'data/compiled/v0.3/test.jsonl': 'c17f225967b6b2f8cbaf3d82fadac1b4031d0654',
}
SUMMARY_COUNTS = {
 'gold_total': 195, 'gold87':87, 'gold108':108, 'gold_target_sha256_unique':195,
 'gold_worlds':13, 'worlds_with_historical_story_overlap':11,
 'historical_uuid_overlap_rows':163,'no_known_uuid_overlap_worlds':2,
 'no_known_uuid_overlap_rows':32,'provisional_selected':24, 'provisional_worlds':2,
 'target_official_questions':24,'target_independent_worlds':4,'independent_world_shortfall':2,
 'formally_admitted_independent_test_rows':0,
}
DEEP_COUNTS = {
 'review_pool_03':14,'review_pool_05':18,'history_ge5_03':14,'history_ge5_05':13,
 'review_pool_total':32, 'provisional_selected_03':12,'provisional_selected_05':12,
 'total_provisional_hold':24, 'all_pool_reviewed_for_content':0,
 'target_time_card_verified':0, 'independent_gold_reviews_completed_for_pool':0,
 'distinct_worlds_represented':2,'additional_independent_worlds_missing':2,
 'official_test_admitted':0,
}
# Fully deterministic safe summary templates based on the exact frozen R56 tools.
# Matching these hashes proves receipt/report consistency, NOT independent access
# to the Owner Mac output files or their execution provenance.
FROZEN_SUMMARY = dict(SUMMARY_COUNTS, schema=SUMMARY_SCHEMA,
 status='GOLD195_UUID_AND_TARGET_PRESCREEN_PASS__24_PROVISIONAL_HOLD__NO_FRESH_HELDOUT_ADMISSION',
 r50_read=False,gpu_used=False,training_performed=False,model_promoted=False,
 warning='Hash/UUID nonoverlap does NOT imply semantic world independence. Gold quality != independent test readiness.')
FROZEN_DEEP = dict(DEEP_COUNTS,schema=DEEP_SCHEMA,
 status='STRUCTURAL_PREFLIGHT__NO_FORMAL_HELDOUT_ADMISSION',
 verification='local pinned-Git-blob read; human semantic review NOT completed',
 gold87_source_blob_sha1=SOURCE_PINS['evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl'],
 gold108_source_blob_sha1=SOURCE_PINS['evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl'],
 r50_opened=False,gpu_started=False,training_performed=False,model_promoted=False,
 note='03 and 05 only have UUID-level preliminary separation; provisional 12+12 must be RESELECTED as 6 per world if 4-world plan proceeds.')

def deterministic_safe_hash(obj):
 data=(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')
 return hashlib.sha256(data).hexdigest()

HEX40=re.compile(r'^[0-9a-f]{40}$'); HEX64=re.compile(r'^[0-9a-f]{64}$')

class GateError(Exception): pass

def require(ok,reason):
 if not ok: raise GateError(reason)

def read_json(path):
 require(path.is_file(),'MISSING_FILE:'+path.name)
 return json.loads(path.read_text(encoding='utf-8'))

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def check_fields(obj, expected, prefix):
 for k,v in expected.items():
  require(type(obj.get(k)) is type(v) and obj.get(k)==v,f'{prefix}_{k}_MISMATCH')

def verify_receipt(receipt):
 require(receipt.get('schema')==REPORT_SCHEMA,'BAD_RECEIPT_SCHEMA')
 require(receipt.get('result')==REPORT_STATUS,'BAD_RESULT')
 require(isinstance(receipt.get('repo_head'),str) and HEX40.fullmatch(receipt['repo_head']),'BAD_REPO_HEAD')
 for key in ('safe_summary_sha256','deep_count_only_sha256'):
  require(isinstance(receipt.get(key),str) and HEX64.fullmatch(receipt[key]),'BAD_'+key)
 require(receipt['safe_summary_sha256']==deterministic_safe_hash(FROZEN_SUMMARY),'PRESCREEN_EXPECTED_SAFE_DIGEST_MISMATCH')
 require(receipt['deep_count_only_sha256']==deterministic_safe_hash(FROZEN_DEEP),'DEEP_EXPECTED_SAFE_DIGEST_MISMATCH')
 require(type(receipt.get('old_unit_tests')) is int and receipt['old_unit_tests']==11,'BAD_OLD_TEST_COUNT')
 require(type(receipt.get('official_test_admitted')) is int and receipt['official_test_admitted']==0,'BAD_TEST_ADMISSION')
 for key in ('r50_read','gpu_job_started','training_performed','model_promoted'):
  require(receipt.get(key) is False,'FORBIDDEN_ACTION_REPORTED_'+key)
 return {'schema':'storyforge-r56-owner-receipt-verification-v1',
 'status':'RECEIPT_STRUCTURALLY_VALID__REFERENCED_EVIDENCE_NOT_YET_RECHECKED',
 'receipt_sha256':None,'report_schema_verified':True,
 'reported_real_mac_replay':True, 'reported_old_tests':11,
 'five_pinned_blobs_reverified_locally':False,
 'reconstructed_expected_safe_summary_sha256_matches':True,
 'reconstructed_expected_deep_summary_sha256_matches':True,
 'original_output_sha256_verified':False,'deep_output_sha256_verified':False,
 'both_unittest_logs_verified':False,'private_case_sheet_structural_check':False,
 'source_exposure_semantic_gate':'HOLD_NOT_REVIEWED',
 'independent_case_content_gate':'HOLD_NOT_REVIEWED',
 'cross_world_independence':'HOLD_NOT_PROVEN',
 'official_test_admitted':0,'additional_independent_worlds_missing':2,
 'r50_read':False,'gpu_job_started':False,'training_performed':False,'model_promoted':False}

def validate_origin(out,receipt,result):
 original_path=out/'original_prescreen/R56_GOLD195_ELIGIBILITY_AUDIT.json'
 deep_path=out/'deep_preflight/safe/R56_DEEP_PREFLIGHT_COUNTS_ONLY.json'
 require(digest(original_path)==receipt['safe_summary_sha256'],'PRESCREEN_SUMMARY_SHA_MISMATCH')
 require(digest(deep_path)==receipt['deep_count_only_sha256'],'DEEP_SUMMARY_SHA_MISMATCH')
 a=read_json(original_path); d=read_json(deep_path)
 require(a.get('schema')==SUMMARY_SCHEMA and d.get('schema')==DEEP_SCHEMA,'SUMMARY_SCHEMA_MISMATCH')
 require(a.get('status')=='GOLD195_UUID_AND_TARGET_PRESCREEN_PASS__24_PROVISIONAL_HOLD__NO_FRESH_HELDOUT_ADMISSION','ORIGINAL_STATUS_MISMATCH')
 require(d.get('status')=='STRUCTURAL_PREFLIGHT__NO_FORMAL_HELDOUT_ADMISSION','DEEP_STATUS_MISMATCH')
 check_fields(a,SUMMARY_COUNTS,'PRESCREEN'); check_fields(d,DEEP_COUNTS,'DEEP')
 for k in ('r50_read','gpu_used','training_performed','model_promoted'):
  require(a.get(k) is False,'PRESCREEN_FORBIDDEN_'+k)
 for k in ('r50_opened','gpu_started','training_performed','model_promoted'):
  require(d.get(k) is False,'DEEP_FORBIDDEN_'+k)
 result['original_output_sha256_verified']=True
 result['deep_output_sha256_verified']=True


def validate_logs(out,result):
 for path,n in ((out/'ORIGINAL_11_TESTS.log',11),(out/'NEW_TESTS.log',7)):
  data=path.read_text(encoding='utf-8')
  require(re.search(r'Ran\s+'+str(n)+r'\s+tests?', data),'MISSING_TEST_COUNT_'+str(n))
  require(re.search(r'(?m)^OK\s*$',data),'UNITTEST_LOG_FAILED_'+str(n))
  require(not re.search(r'(?m)^FAILED|^ERROR:',data),'UNITTEST_FAILURE_'+str(n))
 result['both_unittest_logs_verified']=True


def validate_private_sheets(out,result):
 base=out/'deep_preflight/private'
 for path,total,sel in ((base/'R56_GOLD32_CASE_GATE_REVIEW_PRIVATE.csv',32,24),
                        (base/'R56_GOLD24_PROVISIONAL_GATE_REVIEW_PRIVATE.csv',24,24)):
  with path.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
  require(len(rows)==total,'BAD_CASE_SHEET_COUNT')
  require(len({r['candidate_id_PRIVATE'] for r in rows})==total,'DUP_CASE_SHEET_ID')
  require(sum(r.get('selected24_provisional')=='YES' for r in rows)==sel,'BAD_CASE_SHEET_SELECTED_COUNT')
  require(all(r.get('status')=='HOLD_NOT_TEST_ADMITTED' for r in rows),'NON_HOLD_CASE_SHEET')
  for r in rows:
   require(r.get('story_code') in ('03','05'),'UNEXPECTED_STORY_CODE')
   require(r.get('gold_independent_review')=='NOT_RUN','INDEPENDENT_REVIEW_CLAIM_CHANGE')
  require(sum(r['story_code']=='03' for r in rows)==(14 if total==32 else 12),'BAD_03_CASE_COUNT')
  require(sum(r['story_code']=='05' for r in rows)==(18 if total==32 else 12),'BAD_05_CASE_COUNT')
 result['private_case_sheet_structural_check']=True


def verify_git(repo,head,result):
 for rel,expect in SOURCE_PINS.items():
  path=repo/rel
  require(path.is_file(),'MISSING_SOURCE_GIT_BLOB')
  r=subprocess.run(['git','-C',str(repo),'hash-object','--',str(path)],capture_output=True,text=True,check=True)
  require(r.stdout.strip()==expect,'FROZEN_GIT_BLOB_SHA1_MISMATCH')
 r=subprocess.run(['git','-C',str(repo),'cat-file','-t',head],capture_output=True,text=True,check=True)
 require(r.stdout.strip()=='commit','GIT_REPO_HEAD_NOT_A_COMMIT')
 result['five_pinned_blobs_reverified_locally']=True


def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--receipt',required=True,type=pathlib.Path)
 p.add_argument('--owner-root',type=pathlib.Path,help='Real Mac replay output folder, containing original_prescreen and deep_preflight')
 p.add_argument('--repo',type=pathlib.Path,help='Optional owner storyforge repo for exact five Git blob verification')
 p.add_argument('--out',type=pathlib.Path,help='Write count-only safe status JSON, refuse overwrite')
 args=p.parse_args(argv)
 try:
  require(args.owner_root is not None or args.repo is None,'REPO_REQUIRES_OWNER_ROOT')
  if args.out: require(not args.out.exists(),'OUTPUT_EXISTS_NO_OVERWRITE')
  a=read_json(args.receipt)
  r=verify_receipt(a); r['receipt_sha256']=digest(args.receipt)
  if args.owner_root is not None:
   root=args.owner_root
   validate_origin(root,a,r)
   validate_logs(root,r)
   validate_private_sheets(root,r)
   if args.repo: verify_git(args.repo,a['repo_head'],r)
   r['status']='OWNER_REPLAY_REFERENCED_FILES_VERIFIED__ALL24_HOLD__NO_ADMISSION'
  if args.out:
   args.out.parent.mkdir(parents=True,exist_ok=True)
   with args.out.open('x',encoding='utf-8') as f:
    json.dump(r,f,ensure_ascii=False,sort_keys=True,indent=2); f.write('\n')
  print(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2))
  return 0
 except (GateError,KeyError,OSError,ValueError,TypeError,subprocess.CalledProcessError,json.JSONDecodeError) as e:
  print('R56_OWNER_RECEIPT_VERIFICATION_BLOCKED:',str(e),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())

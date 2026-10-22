#!/usr/bin/env python3
"""R56 local read-only Gold03/05 structural preflight. CPU only. All candidates HOLD.
Does not open R50, run models, approve training, or modify Gold source.
Private outputs never belong on GitHub.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,pathlib,re,subprocess,sys
from itertools import combinations

BLOBS={
 'gold87':'a2038e18bee8ddef96b93bb6746270a462f9a6e4',
 'gold108':'eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90',
}
PATHS={
 'gold87':'evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl',
 'gold108':'evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl',
}
GATES=['target_time_card','story_canon_character_consistency','age_at_target','consent_and_content_boundary',
       'player_agency','history_visibility','cross_world_alias_and_entities',
       'historical_eval_semantic_exposure','source_replay_provenance','independent_review']
HOLD='HOLD_NOT_TEST_ADMITTED'


def require(ok,msg):
 if not ok: raise ValueError(msg)

def sha(b): return hashlib.sha256(b).hexdigest()

def verify_blob(path,expected):
 p=subprocess.run(['git','hash-object','--',str(path)],capture_output=True,text=True,check=True)
 require(p.stdout.strip()==expected,'GIT_BLOB_PIN_MISMATCH: '+str(path))

def read_jsonl(p):
 txt=p.read_text(encoding='utf-8');lines=txt.splitlines()
 require(all(x.strip() for x in lines),'BLANK_JSONL_LINE')
 return [json.loads(s) for s in lines]

def check_row(r):
 m=r['metadata']; msgs=r['messages']; sid=r.get('id')
 require(isinstance(sid,str) and sid,'BAD_ROW_ID')
 require(isinstance(msgs,list) and len(msgs)>1,'BAD_MESSAGES')
 require(msgs[-1].get('role')=='assistant','BAD_FINAL_ROLE')
 require(all(x.get('role') in ('system','user','assistant','tool') and isinstance(x.get('content'),str) and x.get('content').strip() for x in msgs),'BAD_MESSAGE_ROLE_OR_CONTENT')
 target_digest=sha(msgs[-1]['content'].encode('utf-8'))
 require(m.get('target_sha256_utf8',m.get('target_sha256'))==target_digest,'TARGET_SHA256_MISMATCH '+sid)
 ctx=m.get('context_message_count')
 require(type(ctx) is int and ctx==len(msgs)-1,'CONTEXT_LENGTH_MISMATCH '+sid)
 require(msgs[-2].get('role')=='user','LAST_CONTEXT_NOT_USER '+sid)
 src_ids=m.get('source_message_ids'); turns=m.get('source_turn_indices')
 src_ids_ok=isinstance(src_ids,list) and len(src_ids)==len(msgs) and len(src_ids)==len(set(map(str,src_ids)))
 turns_ok=isinstance(turns,list) and len(turns)==len(msgs) and all(type(x) is int for x in turns) and turns==sorted(set(turns))
 require(src_ids_ok and turns_ok,'BAD_SOURCE_PROVENANCE '+sid)
 require(turns[-1]==m.get('target_turn_index'),'BAD_TARGET_TURN '+sid)
 require(isinstance(m.get('source_sha256'),str) and re.fullmatch('[0-9a-f]{64}',m['source_sha256']),'BAD_SOURCE_SHA '+sid)
 return target_digest

def max_context_overlap(r,others):
 ids=set(map(str,r['metadata']['source_message_ids'][:-1]))
 return round(max((len(ids & set(map(str,o['metadata']['source_message_ids'][:-1])))/
                  len(ids | set(map(str,o['metadata']['source_message_ids'][:-1])))
                  for o in others if o['id']!=r['id']),default=0),4)

def make_rows(gold87,selection,eligibility):
 require(len(gold87)==87,'GOLD87_COUNT_MISMATCH')
 require(eligibility.get('official_independent_test_admitted')==0,'PRESCREEN_STATUS_NOT_HOLD')
 require(eligibility.get('planned_provisional_count')==24,'PRESCREEN_TARGET_CHANGED')
 require(eligibility.get('source_eligible_world_counts')=={'03':14,'05':18},'PRESCREEN_WORLD_COUNTS_CHANGED')
 require(selection.get('status')=='24_PROVISIONAL_HOLD__NOT_FRESH_HELDOUT__NO_GPU','SELECTION_STATUS_CHANGED')
 known={}
 for r in gold87:
  check_row(r)
  require(r['id'] not in known,'DUPLICATE_GOLD87_ID')
  known[r['id']]=r
 selected=selection['ids_by_story']
 require(set(selected)=={'03','05'} and all(len(v)==12 for v in selected.values()),'PROPOSED_SELECTION_NOT_12_PLUS_12')
 uuid_by_code={}; selected_ids=set()
 for code,ids in selected.items():
  require(all(isinstance(x,str) and x in known for x in ids),'MISSING_SELECTED_ID '+code)
  require(len(set(ids))==12,'DUPLICATE_SELECTED_ID '+code)
  uuid={known[x]['metadata']['story_id'] for x in ids}
  require(len(uuid)==1,'CROSS_WORLD_SELECTED_ID '+code)
  uuid_by_code[code]=next(iter(uuid)); selected_ids.update(ids)
 require(len(selected_ids)==24 and len(set(uuid_by_code.values()))==2,'SHARED_WORLD_UUID_OR_BAD_SELECTION')
 pool={c: sorted([r for r in gold87 if r['metadata']['story_id']==uuid],
                 key=lambda r:(r['metadata']['target_turn_index'],r['id'])) for c,uuid in uuid_by_code.items()}
 require({k:len(v) for k,v in pool.items()}=={'03':14,'05':18},'GOLD_POOL_COUNT_MISMATCH')
 rows=[]
 for code,records in pool.items():
  for r in records:
   m=r['metadata']; rid=r['id']; selected_flag=rid in selected_ids
   require(not selected_flag or m['context_message_count']>=5,'SELECTED_HISTORY_LT5 '+rid)
   obj={
    'story_code':code,'story_uuid_PRIVATE':m['story_id'],'candidate_id_PRIVATE':rid,
    'selected24_provisional': 'YES' if selected_flag else 'NO',
    'target_turn':m['target_turn_index'],'context_message_count':m['context_message_count'],
    'gold_target_sha256_PRIVATE':check_row(r),'source_snapshot_sha256_PRIVATE':m['source_sha256'],
    'source_message_ids_count':len(m['source_message_ids']),
    'max_context_source_id_jaccard_in_world':max_context_overlap(r,records),
    'gold_independent_review':str(m.get('independent_gold_review','NOT_RECORDED')),
    'target_time_card_recorded':str(m.get('story_card_version_id') or 'ABSENT'),
    'target_time_card_status':str(m.get('story_card_status') or 'NOT_RECORDED'),
    'owner_original_rights_attestation':'ON_FILE_NOT_CASE_VERIFICATION',
    'owner_adult_characters_attestation':'ON_FILE_NOT_TARGET_TIME_VERIFICATION',
    'local_player_agency_label':str(m.get('player_agency_check','NOT_RECORDED')),
    'metadata_target_hash_gate':'PASS_SOURCE_ORIGINAL_GOLD87',
    'context_and_source_id_shape_gate':'PASS_STRUCTURAL_ONLY',
    'story_uuid_overlap_gate':'NO_KNOWN_UUID_OVERLAP__NOT_WORLD_PROOF',
    'all_gate_evidence_sha256_PRIVATE':'',
    'reviewer_decision_and_rationale_PRIVATE':'',
    'status':HOLD,
   }
   for gate in GATES: obj[gate+'_gate']='HOLD_NEEDS_INDEPENDENT_EVIDENCE'
   rows.append(obj)
 return rows,pool,uuid_by_code

def write_csv(p,records):
 require(records,'EMPTY_CSV')
 with p.open('x',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)

def main(argv=None):
 ap=argparse.ArgumentParser()
 ap.add_argument('--repo',type=pathlib.Path,required=True)
 ap.add_argument('--selection',type=pathlib.Path,required=True)
 ap.add_argument('--eligibility',type=pathlib.Path,required=True)
 ap.add_argument('--out-dir',type=pathlib.Path,required=True)
 a=ap.parse_args(argv)
 try:
  require(not a.out_dir.exists(),'OUTPUT_EXISTS_NO_OVERWRITE')
  data={}
  for k,p in PATHS.items():
   path=a.repo/p;require(path.is_file(),'MISSING_PINNED_GOLD_FILE '+str(path))
   verify_blob(path,BLOBS[k]);data[k]=read_jsonl(path)
  require(len(data['gold108'])==108,'GOLD108_COUNT_MISMATCH')
  # Gold108 may have a distinct provenance schema; the original R56 screen validates
  # its 108 targets. Verify independent minimum role/target integrity here only.
  for r in data['gold108']:
   msgs=r.get('messages',[]);m=r.get('metadata',{})
   require(isinstance(msgs,list) and msgs and msgs[-1].get('role')=='assistant','GOLD108_BAD_FINAL_ROLE')
   txt=msgs[-1].get('content')
   require(isinstance(txt,str) and txt.strip(),'GOLD108_EMPTY_TARGET')
   h=m.get('target_sha256_utf8',m.get('target_sha256'))
   if h is not None:require(h==sha(txt.encode('utf-8')),'GOLD108_TARGET_SHA_MISMATCH')
  sel=json.loads(a.selection.read_text(encoding='utf-8'))
  el=json.loads(a.eligibility.read_text(encoding='utf-8'))
  rows,pool,uuids=make_rows(data['gold87'],sel,el)
  require(len(rows)==32 and sum(r['selected24_provisional']=='YES' for r in rows)==24,'ROW_INVARIANT_FAIL')
  world_profile=[]
  for code in ('03','05','NEW_WORLD_A','NEW_WORLD_B'):
   exists=code in uuids
   world_profile.append({'slot':code,'uuid_PRIVATE':uuids.get(code,''),'source_story_sha256_PRIVATE':'',
    'source_canon_at_target_SHA256_PRIVATE':'','role_alias_entity_table_sha256_PRIVATE':'',
    'first_training_exposure_date_private':'','train_val_and_development_exposure_crosscheck':'HOLD',
    'historical_eval_semantic_overlap':'HOLD','age_consent_source_check':'HOLD',
    'world_independence':'HOLD_NOT_PROVEN' if exists else 'MISSING_WORLD',
    'owner_or_reviewer_evidence_ref_PRIVATE':'','admitted_to_4_world_test':'NO'})
  pairs=[]
  for a1,a2 in combinations([p['slot'] for p in world_profile],2):
   pairs.append({'world_a':a1,'world_b':a2,
     'shared_named_characters_aliases':'NOT_CHECKED',
     'shared_organisations_locations_rules':'NOT_CHECKED',
     'shared_plot_or_parent_world':'NOT_CHECKED',
     'source_hashes_evidence_PRIVATE':'','reviewer_rationale_PRIVATE':'',
     'independent_world_pair':'HOLD_NOT_PROVEN'})
  public={'schema':'storyforge-r56-deep-preflight-count-only-v1','status':'STRUCTURAL_PREFLIGHT__NO_FORMAL_HELDOUT_ADMISSION',
   'verification':'local pinned-Git-blob read; human semantic review NOT completed',
   'gold87_source_blob_sha1':BLOBS['gold87'],'gold108_source_blob_sha1':BLOBS['gold108'],
   'review_pool_03':14,'review_pool_05':18,'history_ge5_03':sum(r['metadata']['context_message_count']>=5 for r in pool['03']),
   'history_ge5_05':sum(r['metadata']['context_message_count']>=5 for r in pool['05']),
   'review_pool_total':len(rows),'provisional_selected_03':12,'provisional_selected_05':12,
   'total_provisional_hold':24,'all_pool_reviewed_for_content':0,
   'target_time_card_verified':0,'independent_gold_reviews_completed_for_pool':0,
   'distinct_worlds_represented':2,'additional_independent_worlds_missing':2,
   'official_test_admitted':0,'r50_opened':False,'gpu_started':False,'training_performed':False,'model_promoted':False,
   'note':'03 and 05 only have UUID-level preliminary separation; provisional 12+12 must be RESELECTED as 6 per world if 4-world plan proceeds.'}
  a.out_dir.mkdir(parents=True)
  private=a.out_dir/'private';private.mkdir()
  safe=a.out_dir/'safe';safe.mkdir()
  write_csv(private/'R56_GOLD32_CASE_GATE_REVIEW_PRIVATE.csv',rows)
  write_csv(private/'R56_GOLD24_PROVISIONAL_GATE_REVIEW_PRIVATE.csv',[r for r in rows if r['selected24_provisional']=='YES'])
  write_csv(private/'R56_WORLD4_PROFILE_GATES_PRIVATE.csv',world_profile)
  write_csv(private/'R56_WORLD6_PAIR_GATES_PRIVATE.csv',pairs)
  p=safe/'R56_DEEP_PREFLIGHT_COUNTS_ONLY.json';p.write_text(json.dumps(public,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
  files=sorted(p for p in a.out_dir.rglob('*') if p.is_file())
  hashes={str(p.relative_to(a.out_dir)):sha(p.read_bytes()) for p in files}
  (a.out_dir/'SHA256SUMS_ALL_LOCAL.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')
  print('R56_DEEP_PREFLIGHT_32_POOL__24_HOLD__2_WORLD_GAP__0_ADMITTED')
  print(json.dumps(public,ensure_ascii=False,sort_keys=True))
 except (ValueError,AssertionError,KeyError,TypeError,OSError,subprocess.CalledProcessError,json.JSONDecodeError) as e:
  print('R56_DEEP_PREFLIGHT_BLOCKED:',str(e),file=sys.stderr);return 2
 return 0

if __name__=='__main__':sys.exit(main())

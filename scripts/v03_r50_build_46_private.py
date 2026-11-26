#!/usr/bin/env python3
"""Deterministic, private R50 50->46 selection; audit only, NEVER final heldout seal.
Does not mutate any input or contact network/GPU; no in-repo output.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re, stat, unicodedata, zipfile
from pathlib import Path, PurePosixPath

ORIGINAL_HASHES={
 'R50_FRESH_HELDOUT_50.jsonl':'8dbb66aeb47fd1fec34718d31b228c0378a79f43b7b847eb3e403752d8139781',
 'R50_CASE_PROVENANCE_50.jsonl':'9306af53c6a53fbe46a6675c50e5fac4753162a5c19d6f3c1a0072919306b280',
 'R50_AUTHORING_REPORT.md':'7d0862300d8a729f893f66c092dfa74a6e2adb75d85eae0cfe2276e105bdf8bd',
}
TRAIN='R45_TRAIN_FROZEN_CANDIDATE_49_NOT_APPROVED.jsonl'
VAL='R45_VALIDATION_FROZEN_CANDIDATE_15_NOT_APPROVED.jsonl'
R45_HASHES={TRAIN:'e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742',VAL:'5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963'}
EXCLUDE={
 'SFH50-W16-005':('HOLD','unresolved spirit pact state/timing'),
 'SFH50-W18-003':('FAIL','holding hands action continuity'),
 'SFH50-W19-003':('FAIL','vacuum field/third party timeline'),
 'SFH50-W19-010':('FAIL','completed instrument test timeline reset'),
}
SRC_NAMES=('R50_FRESH_HELDOUT_50.jsonl','R50_CASE_PROVENANCE_50.jsonl')
EXPECTED_STATUS_SHA='1e6f390b4d0493d883903b4628eae4c89175a4ff8affc8387038b8038c6e24c3'

def h(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def read_lines(p:Path)->list[bytes]:
 b=p.read_bytes();assert b.endswith(b'\n') and b.count(b'\n')==50, f'invalid raw lines {p}'
 return b.splitlines(keepends=True)
def parse_lines(l:list[bytes])->list[dict]:return [json.loads(x) for x in l]
def norm(s:str)->str:return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s).casefold()).strip()
def all_windows(s:str):
 for i in range(max(0,len(s)-120+1)):
  yield hashlib.blake2b(s[i:i+120].encode(),digest_size=16).digest()
def long_hash(s:str):return hashlib.blake2b(s.encode(),digest_size=16).digest()
def write_once(path:Path,b:bytes):
 with path.open('xb') as f:f.write(b)
 path.chmod(0o600)
def jbytes(o)->bytes:return (json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')
def in_repo(folder:Path)->bool:
 return any((node/'.git').exists() for node in (folder,*folder.parents))

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--frozen-dir',type=Path,required=True)
 ap.add_argument('--status-map',type=Path,required=True)
 ap.add_argument('--r45-zip',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True)
 a=ap.parse_args()
 out=a.output.resolve();assert not in_repo(out),'refusing private outputs inside git';out.mkdir(mode=0o700,parents=True,exist_ok=False)
 for name,expected in ORIGINAL_HASHES.items():assert h((a.frozen_dir/name).read_bytes())==expected,f'{name} frozen original mismatch'
 status_raw=a.status_map.read_bytes();assert h(status_raw)==EXPECTED_STATUS_SHA,'status map mismatch'
 status=json.loads(status_raw)['status_by_case_id'];assert len(status)==50
 raw_c,raw_p=[read_lines(a.frozen_dir/n) for n in SRC_NAMES]
 cc,pp=map(parse_lines,(raw_c,raw_p))
 ids=[x['case_id'] for x in cc];assert len(set(ids))==50 and ids==[x['case_id'] for x in pp]==list(status),'out of sync original/states'
 assert collections.Counter(status.values())=={'PASS':46,'HOLD':1,'FAIL':3}
 assert set(EXCLUDE)=={i for i,s in status.items() if s!='PASS'}
 for ident,(v,_) in EXCLUDE.items():assert status[ident]==v
 keep=[i for i,x in enumerate(cc) if x['case_id'] not in EXCLUDE];assert len(keep)==46
 selected=[cc[i] for i in keep];selected_prov=[pp[i] for i in keep]
 assert all(len(x['history'])==len(p['history_message_ids']) for x,p in zip(selected,selected_prov))
 assert all(x['world_id']==f"sfh50-w{p['story_number']}" for x,p in zip(selected,selected_prov))
 history_n=sum(len(x['history']) for x in selected)
 assert history_n==364,f'expected 364 source messages got {history_n}'
 world_counts=dict(sorted(collections.Counter(x['world_id'] for x in selected).items()))
 assert list(world_counts.values())==[9,10,9,8,10],world_counts
 proposed_case_bytes=b''.join(raw_c[i] for i in keep)
 proposed_prov_bytes=b''.join(raw_p[i] for i in keep)
 out_case='R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl'
 out_prov='R50_PROVENANCE_46_PRESEAL_PRIVATE.jsonl'
 write_once(out/out_case,proposed_case_bytes);write_once(out/out_prov,proposed_prov_bytes)
 src_ids=set(p['source_story_id'] for p in selected_prov)
 assert len(src_ids)==5
 # Check R45 original bytes & original System identity across all 64 rows.
 with zipfile.ZipFile(a.r45_zip) as z:
  rows=[]
  for name,n in ((TRAIN,49),(VAL,15)):
   names=[p for p in z.namelist() if PurePosixPath(p).name==name]
   assert len(names)==1
   b=z.read(names[0]);assert h(b)==R45_HASHES[name]
   batch=[json.loads(x) for x in b.decode('utf-8-sig').splitlines() if x.strip()]
   assert len(batch)==n
   rows.extend(batch)
 r45ids={r['metadata']['source_story_id'] for r in rows}
 assert len(r45ids)==9
 system_set={r['messages'][0]['content'] for r in rows if r['messages'][0]['role']=='system'}
 assert len(system_set)==1 and len(rows)==64
 system=next(iter(system_set));system_bytes=system.encode('utf-8')
 assert h(system_bytes)=='5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83'
 sys_file='R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt'
 write_once(out/sys_file,system_bytes)
 # Scope is 46 cases' included history, prompt, compact cards/rules only.
 # NOT five complete source narratives, and NOT manual alias review.
 hist_exact=set();hist_windows=set()
 for r in rows:
  for m in r['messages']:
   t=m.get('content')
   if not isinstance(t,str) or not t.strip():continue
   s=norm(t)
   if len(s)>=80:hist_exact.add(long_hash(s))
   hist_windows.update(all_windows(s))
 categories=collections.Counter();hits=collections.Counter()
 for x in selected:
  groups={'history':[m['content'] for m in x['history']], 'new_user':[x['user_input']], 'world_card':[x['world_card']], 'long_term_rules':x['long_term_rules']}
  for label,strings in groups.items():
   for raw in strings:
    if not isinstance(raw,str) or not raw.strip():continue
    categories[label]+=1
    s=norm(raw)
    if len(s)>=80 and long_hash(s) in hist_exact:hits[label+'_exact']+=1
    for w in all_windows(s):
     if w in hist_windows:hits[label+'_windows']+=1
 collisions=len(r45ids&src_ids)
 # Static input constructor option A, not an approved evaluation contract.
 static=[]
 for x in selected:
  assert all(m['role'] in ('user','assistant') and isinstance(m['content'],str) for m in x['history'])
  assert isinstance(x['world_card'],str) and all(isinstance(z,str) for z in x['long_term_rules'])
  composed=system+'\n\n[STORY_WORLD_CARD]\n'+x['world_card']+'\n[/STORY_WORLD_CARD]'+'\n\n[STORY_LONG_TERM_RULES]\n'+'\n'.join(x['long_term_rules'])+'\n[/STORY_LONG_TERM_RULES]'
  model_messages=[{'role':'system','content':composed}]+[{'role':m['role'],'content':m['content']} for m in x['history']]+[{'role':'user','content':x['user_input']}]
  assert model_messages[1:-1]==x['history']
  assert 'focus_tags' not in json.dumps(model_messages,ensure_ascii=False)
  is_double=(len(model_messages)>=3 and model_messages[-2]['role']=='user')
  static.append({'case_id':x['case_id'],'history_count':len(x['history']),'last_historical_role':x['history'][-1]['role'], 'consecutive_user_before_generation':is_double, 'draft_input_messages_sha256':h(json.dumps(model_messages,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())})
 # Histological case-level duplicate source historical IDs (post filtering).
 by_id=collections.defaultdict(set)
 for p in selected_prov:
  for mid in p['history_message_ids']:by_id[mid].add(p['case_id'])
 duplicates=sum(1 for v in by_id.values() if len(v)>1)
 # Independent world groups are not claimed: just distinct source story IDs.
 manifest={
 'schema':'storyforge-r50-46-selection-preseal-manifest-v1','created_on':'2026-10-16',
 'decision':'OWNER_EXCLUDE_4_EXPLICIT','candidate_stage':'CONTENT_PASS_ONLY__FULL_ADMISSION_HOLD',
 'original_sha256':ORIGINAL_HASHES,'original_case_count':50,
 'filtered_files_sha256':{out_case:h(proposed_case_bytes),out_prov:h(proposed_prov_bytes)},
 'derived_file_policy':'byte-exact subset of unmodified original JSONL lines, same order, IDs unchanged',
 'selected_case_count':46,'selected_history_messages':history_n,'selected_world_counts':world_counts,
 'excluded_cases':[{'case_id':i,'prior_review':s,'scope':'EXCLUDED_FROM_NEW_46_SELECTION','reason':r} for i,(s,r) in EXCLUDE.items()],
 'selected_parent_line_numbers_1_based':[i+1 for i in keep],
 'case_source_line_sha256':{cc[i]['case_id']:h(raw_c[i]) for i in keep},
 'provenance_source_line_sha256':{pp[i]['case_id']:h(raw_p[i]) for i in keep},
 'ai_only_policy':True,'owner_exclusion_authorized':True,
 'source_replay':'PRIOR_RECORDED_50_50_392_392_50_50__NOT_REEXECUTED',
 'full_five_world_source_check':'PENDING','semantic_alias_review':'PENDING','actual_qwen_tokenizer':'PENDING',
 'four_arm_evaluation_contract':'DRAFT_NOT_APPROVED',
 'final_heldout_seal':'NOT_PERFORMED','model_generation':False,'paid_gpu':False,'model_promotion':False,
 }
 screen={'schema':'storyforge-r50-46-r45-original-exact-subset-screen-v1',
  'r45_original_train_sha256':R45_HASHES[TRAIN],'r45_original_validation_sha256':R45_HASHES[VAL],
  'verified_r45_samples':64,'r45_distinct_world_source_ids':len(r45ids),'r50_distinct_world_source_ids':len(src_ids),
  'exact_source_id_collisions':collisions,'tested_scope':'46 selected candidate records only; NO full 16-20 source transcript replay',
  'r45_normalized_exact_long_message_digests':len(hist_exact),
  'r45_normalized_all_offset_120char_digests':len(hist_windows),
  'r50_fields_screened_counts':dict(categories), 'r45_matches_by_field':dict(hits),
  'min_exact_normalized_chars':80,'window_normalized_codepoints':120,'window_step':1,
  'normalization':'NFKC+casefold+whitespace collapse',
  'semantic_alias_paraphrase_screen':'PENDING',
  'full_original_five_source_story_screen':'PENDING',
  'result':'SUBSET_EXACT_SCREEN_NO_HITS' if collisions==0 and not hits else 'SUBSET_EXACT_SCREEN_HAS_HITS_REVIEW_REQUIRED',
  'no_source_text_in_report':True,'no_gpu':True}
 static_report={'schema':'storyforge-r50-46-static-builder-v1','case_count':len(static), 'history_message_count':history_n,
  'consecutive_user_count':sum(int(s['consecutive_user_before_generation']) for s in static),
  'draft_system_sha256':h(system_bytes),'draft_system_source':'R45 Train49/Val15 identical 64/64, NOT preregistered for R56',
  'draft_builder':'System+world+rules delim, preserve history roles/order, append user',
  'case_input_receipts':static,'actual_tokenizer_not_run':True,'four_arm_runtime_equality_not_run':True,
  'status':'STATIC_ONLY__QWEN_TOKENIZER_PENDING__EVAL_CONTRACT_NOT_APPROVED'}
 for name,obj in [('R50_46_PRESEAL_SELECTION_MANIFEST_PRIVATE.json',manifest),('R50_46_R45_ORIGINAL_EXACT_SUBSET_SCREEN.json',screen),('R50_46_STATIC_INPUT_PREFLIGHT_PRIVATE.json',static_report)]:write_once(out/name,jbytes(obj))
 print(json.dumps({'case_count':len(selected),'history':history_n,'worlds':world_counts,'candidate_sha256':h(proposed_case_bytes),'provenance_sha256':h(proposed_prov_bytes),'r45_subset_result':screen['result'],'r45_hits':dict(hits),'r45_source_id_collisions':collisions,'consecutive_user':static_report['consecutive_user_count'],'r45_system_sha256':h(system_bytes),'full_admission':'HOLD'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Privacy-preserving 40/64-character screen + same-world context-overlap audit.

Not a semantic near-duplicate verdict and not the full five-story source gate.
Only aggregate/pseudonymous case IDs are written, no text or hashes of substrings.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,os,re,unicodedata,zipfile
from pathlib import Path

TRAIN_HASH='e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742'
VAL_HASH='5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963'
CAND_HASH='109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2'
EXCLUDED={'SFH50-W16-005','SFH50-W18-003','SFH50-W19-003','SFH50-W19-010'}

def norm(s:str)->str:return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s).casefold()).strip()
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def r45(zip_path:Path):
    with zipfile.ZipFile(zip_path) as z:
        for part,suffix,target,expected in [('train','R45_TRAIN_FROZEN_CANDIDATE_49_NOT_APPROVED.jsonl',49,TRAIN_HASH),('validation','R45_VALIDATION_FROZEN_CANDIDATE_15_NOT_APPROVED.jsonl',15,VAL_HASH)]:
            names=[n for n in z.namelist() if n.endswith('/'+suffix)]
            if len(names)!=1:raise ValueError('R45 original missing')
            data=z.read(names[0])
            if sha(data)!=expected:raise ValueError('R45 byte mismatch')
            rows=[json.loads(x) for x in data.splitlines()]
            if len(rows)!=target:raise ValueError('R45 row mismatch')
            for row in rows:
                for msg in row['messages']:
                    content=msg.get('content','')
                    if isinstance(content,str) and content.strip():yield norm(content)

def windows(s:str,n:int):
    for i in range(len(s)-n+1):yield s[i:i+n]

def run(candidates:Path,zip_path:Path):
    raw=candidates.read_bytes()
    if sha(raw)!=CAND_HASH:raise ValueError('expected frozen 46 candidates SHA256')
    cases=[json.loads(l) for l in raw.splitlines()]
    if len(cases)!=46 or len({c['case_id'] for c in cases})!=46 or EXCLUDED.intersection(c['case_id'] for c in cases):raise ValueError('bad 46 selection')
    historic=list(r45(zip_path)); source=[(c['case_id'],c['world_id'],c) for c in cases]
    results={}; universe={}
    for n in (40,64):
        olds=set()
        for content in historic:olds.update(windows(content,n))
        hits_per_type=collections.Counter();cases_hit=set();worlds_hit=set();hit_windows=0
        for cid,wid,row in source:
            fields=[('history',m['content']) for m in row['history']] + [('user_input',row['user_input']),('world_card',row['world_card'])] + [('long_term_rule',r) for r in row['long_term_rules']]
            for typ,value in fields:
                for w in windows(norm(value),n):
                    if w in olds:
                        hits_per_type[typ]+=1;cases_hit.add(cid);worlds_hit.add(wid);hit_windows+=1
        results[str(n)]={'historic_normalized_window_count':len(olds),'hit_window_occurrences':hit_windows,'cases_with_hits':len(cases_hit),'worlds_with_hits':len(worlds_hit),'hits_by_input_field':dict(hits_per_type),'status':'NO_HITS_WITHIN_CHECKED_FIELDS' if hit_windows==0 else 'CANDIDATE_HITS_NEED_PRIVATE_MANUAL_AUDIT'}
    # Same-world shared historical messages are not leakage but can inflate precision.
    groups=collections.defaultdict(list)
    for cid,wid,row in source:
        pieces=[hashlib.sha256((m['role']+'\0'+m['content']).encode()).digest() for m in row['history']]
        groups[wid].append((cid,pieces))
    shared=[]; edge=collections.defaultdict(set)
    for wid,rows in groups.items():
        for i,(a,aa) in enumerate(rows):
            for b,bb in rows[i+1:]:
                same=len(set(aa)&set(bb)); denom=min(len(aa),len(bb))
                if same:
                    shared.append({'world_id':wid,'case_a':a,'case_b':b,'exact_shared_history_messages':same,'smaller_context_fraction':round(same/denom,4) if denom else 0})
                if same>=3:
                    edge[a].add(b);edge[b].add(a)
    comps=[];seen=set()
    for cid in sorted(edge):
        if cid in seen:continue
        todo=[cid]; cc=[]
        while todo:
            x=todo.pop()
            if x in seen:continue
            seen.add(x);cc.append(x);todo.extend(edge[x]-seen)
        comps.append(sorted(cc))
    return {'schema':'storyforge-r50-46-short-fragment-and-cluster-audit-v1',
        'candidate_sha256':CAND_HASH,'source_r45_train_and_validation_sha256_match':True,
        'scope':'R45_49_15_ORIGINAL_MESSAGES_VS_46_HELDOUT_VISIBLE_FIELDS_ONLY',
        'case_count':46,'r45_train_validation_count':64,
        'normalized_exact_window_screen':results,
        'within_world_case_history_shared_pairs':len(shared),
        'pairs_with_any_exact_shared_history':sorted(shared,key=lambda r:(r['world_id'],r['case_a'],r['case_b'])),
        'clusters_with_three_or_more_shared_history_messages':comps,
        'limitations':['Not full 5-story source comparison','Not paraphrase or hidden-alias detection','Case clusters are for variance/correlation handling, not exclusion by themselves','No content admission promotion'],
        'no_raw_text_or_fragment_hashes_written':True,'no_model_or_gpu':True,'no_final_heldout_seal':True}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates',type=Path,required=True)
    p.add_argument('--r45-zip',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise SystemExit('HOLD: output exists')
    res=run(a.candidates,a.r45_zip)
    a.output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(a.output,os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(res,f,ensure_ascii=False,indent=2);f.write('\n')
    print('R50_SHORT_FRAGMENT_SCREEN_COMPLETED_NO_GPU')
    for k,v in res['normalized_exact_window_screen'].items():print(f'{k} codepoints: {v["status"]}; candidate hits={v["hit_window_occurrences"]}')
    print(f'Cases with exact shared history edges: {res["within_world_case_history_shared_pairs"]} pairs')
if __name__=='__main__':main()

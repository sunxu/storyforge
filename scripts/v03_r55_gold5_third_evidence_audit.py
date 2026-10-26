#!/usr/bin/env python3
"""R55 Gold5: independently blind third evidence audit after 2 frozen reviews.

Owner-only preparation revalidates the exact first and second sources/decisions
and the second validated receipts. Select every *category* for which first==HOLD
or first!=second; select corresponding unique candidates, then ask third auditor
for both categories with NEW tokens and NO original opinions/model identities.

Never automatically claim final violations, change initial files, touch R50,
or promote a model. All outputs private, outside Git, and non-overwriting.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

import v03_r55_gold5_second_evidence_audit as second
import v03_r55_gold5_event_arbitration as first
import v03_r55_gold5_review_freeze as fr

PREFIX='R55_GOLD5_THIRD_EVIDENCE_AUDIT'
SCHEMA='storyforge-r55-gold5-third-evidence-audit-v1'
PINNED_SECOND_BLIND='e2dc0d4fcd2d86aa0a8acab91941e6c2a3abfff23d1cfba8b7cd44cf8e1f252b'
PINNED_SECOND_DECISIONS='db4233d59fd59a0fb85c3df7ced80ec3a974f7ea0bef5ae7bff3975185c925ee'
EXPECTED_SECOND_ITEMS=68
EXPECTED_SECOND_CATEGORIES=136
EXPECTED_TERTIARY_CATEGORY_COUNT=59
CATS=first.CATEGORIES
VERDICTS=first.VERDICTS
FIELDS=second.SOURCE_KEYS


def require(cond:bool, label:str)->None:
    if not cond:raise fr.Hold(label)


def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()


def read_obj(p:Path,label:str)->dict:
    fr.valid_private(p,label)
    try: obj=json.loads(p.read_text(encoding='utf-8'))
    except (UnicodeError,ValueError) as exc: raise fr.Hold(label+'_INVALID_JSON') from exc
    require(isinstance(obj,dict),label+'_NOT_OBJECT')
    return obj


def by_token(items:list,label:str,expected:int)->dict:
    require(isinstance(items,list) and len(items)==expected,label+'_COUNT_MISMATCH')
    require(all(isinstance(x,dict) and isinstance(x.get('candidate_token'),str) and x['candidate_token'] for x in items),label+'_BAD_TOKEN')
    out={x['candidate_token']:x for x in items}
    require(len(out)==expected,label+'_DUPLICATE_TOKEN')
    return out


def write_private(p:Path,obj)->None:
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as h:
        json.dump(obj,h,sort_keys=True,indent=2,ensure_ascii=False);h.write('\n')


def ensure_new_out(out:Path)->Path:
    out=out.expanduser().resolve()
    fr.outside_git(out)
    require(not out.exists() and not out.is_symlink(),'OUTPUT_ALREADY_EXISTS')
    return out


def checked_twice(first_pack:Path,first_decisions:Path,first_safe:Path,
                  second_pack:Path,second_decisions:Path,second_validated:Path)->dict:
    """Re-execute both locally-saved validators before any selection."""
    state=second.checked_first(first_pack,first_decisions,first_safe)
    second_pack=second_pack.expanduser().resolve()
    fr.valid_private(second_decisions,'SECOND_DECISIONS')
    require(digest(second_decisions.read_bytes())==PINNED_SECOND_DECISIONS,'PINNED_SECOND_DECISIONS_SHA_MISMATCH')
    source=second_pack/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json'
    index=second_pack/'coordinator/R55_GOLD5_SECOND_AUDIT_INDEX_PRIVATE.json'
    prepar=second_pack/'safe/R55_GOLD5_SECOND_AUDIT_PREP_SAFE_COUNT_ONLY.json'
    require(digest(source.read_bytes())==PINNED_SECOND_BLIND,'PINNED_SECOND_BLIND_SHA_MISMATCH')
    prep=read_obj(prepar,'SECOND_PREP')
    require(prep.get('selected_candidate_count')==EXPECTED_SECOND_ITEMS
            and prep.get('selected_category_judgments_required')==EXPECTED_SECOND_CATEGORIES
            and prep.get('blind_packet_sha256')==PINNED_SECOND_BLIND
            and prep.get('first_decisions_sha256')==second.PINNED_FIRST_DECISIONS
            and prep.get('r50_accessed') is False,'SECOND_PREP_INVALID')
    second_validated=second_validated.expanduser().resolve()
    safe_file=second_validated/'R55_GOLD5_SECOND_AUDIT_SAFE_COUNT_ONLY.json'
    cmp_file=second_validated/'R55_GOLD5_SECOND_AUDIT_COMPARISON_PRIVATE.json'
    safe=read_obj(safe_file,'SECOND_VALIDATED_SAFE')
    cmp=read_obj(cmp_file,'SECOND_VALIDATED_COMPARISON')
    require(safe.get('schema')==second.SCHEMA+'-safe-validated-v1'
            and safe.get('status')=='R55_GOLD5_SECOND_AUDIT_VERDICTS_VALIDATED__NO_AUTO_PROMOTION__NO_R50'
            and safe.get('r50_accessed') is False
            and safe.get('second_decisions_sha256')==PINNED_SECOND_DECISIONS
            and safe.get('blind_packet_sha256')==PINNED_SECOND_BLIND
            and safe.get('selected_candidate_count')==EXPECTED_SECOND_ITEMS
            and safe.get('second_category_decisions_validated')==EXPECTED_SECOND_CATEGORIES
            and safe.get('first_HOLD_or_disagreement_needs_tertiary_count')==EXPECTED_TERTIARY_CATEGORY_COUNT,
            'SECOND_VALIDATED_SAFE_NOT_PINNED')
    require(cmp.get('schema')==second.SCHEMA+'-private-comparison-v1','SECOND_COMPARISON_WRONG_SCHEMA')
    # The second validator is reused directly to recalculate the real second
    # count-only receipt and private compare from frozen source/decision bytes.
    with tempfile.TemporaryDirectory(prefix='r55-third-verify-') as tmp:
        regen_dir=Path(tmp)/'replay'
        regenerated=second.validate_second(second_pack,second_decisions,regen_dir)
        require(regenerated==safe,'SECOND_SAFE_REPLAY_MISMATCH')
        require(digest((regen_dir/'R55_GOLD5_SECOND_AUDIT_COMPARISON_PRIVATE.json').read_bytes())
                ==digest(cmp_file.read_bytes()),'SECOND_COMPARISON_REPLAY_MISMATCH')
    tasks=by_token(read_obj(source,'SECOND_BLIND')['items'],'SECOND_BLIND',EXPECTED_SECOND_ITEMS)
    idx=by_token(read_obj(index,'SECOND_INDEX')['records'],'SECOND_INDEX',EXPECTED_SECOND_ITEMS)
    judgments=by_token(read_obj(second_decisions,'SECOND_DECISIONS')['items'],'SECOND_DECISIONS',EXPECTED_SECOND_ITEMS)
    comp=by_token(cmp['items'],'SECOND_COMPARISON',EXPECTED_SECOND_ITEMS)
    require(set(tasks)==set(idx)==set(judgments)==set(comp),'SECOND_TOKENS_DIFFER')
    chosen=[]; focus_count=Counter(); statuses=Counter()
    for tok,t in tasks.items():
        row=idx[tok]; c=comp[tok]
        old_tok=row['original_candidate_token_private']
        original=state['task_by'].get(old_tok)
        require(original is not None,'ORIGINAL_CANDIDATE_NOT_PRESENT')
        require(row['source_arm_private']==c['source_arm_private']
                and c['original_candidate_token_private']==old_tok,'SECOND_PRIVATE_MAP_MISMATCH')
        require(row['response_sha256']==digest(t['匿名候选回复'].encode('utf-8')),'SECOND_REPLY_CHANGED')
        for field in FIELDS:
            require(t[field]==original[field],'CANDIDATE_OR_CONTEXT_CHANGED')
        require(row['first_verdict_private']=={cat:state['dec_by'][old_tok][cat]['verdict'] for cat in CATS},
                'FIRST_VERDICTS_MISMATCH')
        unresolved=[]
        for cat in CATS:
            f=row['first_verdict_private'][cat]
            s=judgments[tok][cat]['verdict']
            require(c['categories'][cat]['first_verdict_private']==f
                    and c['categories'][cat]['second_verdict']==s,'SECOND_COMPARISON_VERDICT_MISMATCH')
            flag=(f!=s or f=='HOLD_INSUFFICIENT_EVIDENCE')
            expected='NEEDS_TERTIARY_OR_EVIDENCE' if flag else 'MATCH'
            require(c['categories'][cat]['review_status']==expected,'SECOND_COMPARISON_STATUS_MISMATCH')
            if flag:
                unresolved.append(cat)
                focus_count[cat]+=1
                statuses[f+'__TO__'+s]+=1
        if unresolved:
            chosen.append({'token':tok,'source':t,'private':row,'original':original,
                           'unresolved':unresolved,'first':row['first_verdict_private'],
                           'second':{cat:judgments[tok][cat]['verdict'] for cat in CATS}})
    require(sum(focus_count.values())==EXPECTED_TERTIARY_CATEGORY_COUNT,'TERTIARY_CATEGORY_COUNT_MISMATCH')
    require(len(chosen)>=1,'NO_TERTIARY_SUBJECTS')
    return {'chosen':chosen,'focus':dict(focus_count),'statuses':dict(statuses),
            'second_safe_hash':digest(safe_file.read_bytes()),
            'second_comparison_hash':digest(cmp_file.read_bytes()),
            'second_prep_hash':digest(prepar.read_bytes()),
            'first_decision_hash':digest(first_decisions.read_bytes()),
            'second_decision_hash':digest(second_decisions.read_bytes())}


def prepare(state:dict,out:Path)->dict:
    out=ensure_new_out(out)
    blind=[]; mapping=[];new_case_tokens={}
    for cand in state['chosen']:
        old_case=cand['source']['case_token']
        if old_case not in new_case_tokens:new_case_tokens[old_case]='C'+secrets.token_hex(9)
        token='T'+secrets.token_hex(13)
        blind.append({'candidate_token':token,'case_token':new_case_tokens[old_case],
                      **{field:cand['source'][field] for field in FIELDS},
                      'must_evaluate_both_categories':list(CATS),
                      'instructions':'Independently judge both categories from the visible source. Do not infer or request model identities, prior outcomes, reviewer scores, selection criteria.'})
        mapping.append({'candidate_token':token,
                        'original_second_candidate_token_private':cand['token'],
                        'original_first_candidate_token_private':cand['private']['original_candidate_token_private'],
                        'source_arm_private':cand['private']['source_arm_private'],
                        'response_sha256':cand['private']['response_sha256'],
                        'first_verdict_private':cand['first'],
                        'second_verdict_private':cand['second'],
                        'unresolved_categories_private':cand['unresolved']})
    require(len(set(x['candidate_token'] for x in blind))==len(blind),'RANDOM_DUPLICATE_TOKENS')
    secrets.SystemRandom().shuffle(blind)
    blank=[{'candidate_token':x['candidate_token'],**{
        cat:{'verdict':'','candidate_quote':'','context_quote':'','rationale':''} for cat in CATS}} for x in blind]
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    for folder in ('reviewers','coordinator','safe'):(out/folder).mkdir(mode=0o700)
    source=out/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json'
    template=out/'reviewers/R55_GOLD5_THIRD_AUDIT_DECISIONS_BLANK_PRIVATE.json'
    coord=out/'coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json'
    write_private(source,{'schema':SCHEMA+'-blind-items-v1','items':blind,'status':'THIRD_AUDIT_PENDING'})
    write_private(template,{'schema':SCHEMA+'-decisions-v1','items':blank})
    write_private(coord,{'schema':SCHEMA+'-coordinator-index-v1','records':mapping,
                         'second_validated_safe_sha256':state['second_safe_hash'],
                         'warning':'OWNER ONLY: first/second verdicts, original tokens, model identity. NEVER SEND TO THIRD REVIEWER.'})
    rec={'schema':SCHEMA+'-safe-prep-v1',
         'status':'R55_GOLD5_THIRD_AUDIT_PRIVATE_BLIND_PACK_PREPARED__NO_NEW_VERDICTS__NO_R50',
         'source_second_candidate_count':EXPECTED_SECOND_ITEMS,
         'source_second_category_count':EXPECTED_SECOND_CATEGORIES,
         'category_disagreements_or_first_hold_selected':EXPECTED_TERTIARY_CATEGORY_COUNT,
         'selected_unique_candidates':len(blind),
         'required_third_category_judgments':len(blind)*len(CATS),
         'original_second_blind_sha256':PINNED_SECOND_BLIND,
         'first_decisions_sha256':state['first_decision_hash'],
         'second_decisions_sha256':state['second_decision_hash'],
         'second_validated_safe_sha256':state['second_safe_hash'],
         'second_private_comparison_sha256':state['second_comparison_hash'],
         'blind_packet_sha256':digest(source.read_bytes()),
         'blank_template_sha256':digest(template.read_bytes()),
         'private_mapping_sha256':digest(coord.read_bytes()),
         'prior_verdicts_sent_to_third_review':False,
         'model_identity_sent_to_third_review':False,
         'private_case_or_story_text_in_safe_receipt':False,
         'old_exposed_development_only':True,'r50_accessed':False,
         'gpu_job_started':False,'training':False,'model_promoted':False,
         'automatic_final_adjudication':False}
    write_private(out/'safe/R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json',rec)
    return rec


def validate(pack:Path,submitted:Path,out:Path)->dict:
    pack=pack.expanduser().resolve();out=ensure_new_out(out)
    pfile=pack/'safe/R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json'
    prep=read_obj(pfile,'THIRD_PREP')
    require(prep.get('schema')==SCHEMA+'-safe-prep-v1'
            and prep.get('status')=='R55_GOLD5_THIRD_AUDIT_PRIVATE_BLIND_PACK_PREPARED__NO_NEW_VERDICTS__NO_R50'
            and prep.get('category_disagreements_or_first_hold_selected')==EXPECTED_TERTIARY_CATEGORY_COUNT
            and prep.get('original_second_blind_sha256')==PINNED_SECOND_BLIND
            and prep.get('first_decisions_sha256')==second.PINNED_FIRST_DECISIONS
            and prep.get('second_decisions_sha256')==PINNED_SECOND_DECISIONS
            and prep.get('r50_accessed') is False,'THIRD_PREP_RECEIPT_NOT_PINNED')
    source=pack/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json'
    template=pack/'reviewers/R55_GOLD5_THIRD_AUDIT_DECISIONS_BLANK_PRIVATE.json'
    index=pack/'coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json'
    for p,key in ((source,'blind_packet_sha256'),(template,'blank_template_sha256'),(index,'private_mapping_sha256')):
        fr.valid_private(p,key)
        require(digest(p.read_bytes())==prep.get(key),key+'_MISMATCH')
    src=read_obj(source,'THIRD_SOURCE');tmpl=read_obj(template,'THIRD_TEMPLATE')
    idx=read_obj(index,'THIRD_MAPPING');done=read_obj(submitted,'THIRD_DECISIONS')
    n=prep.get('selected_unique_candidates')
    require(type(n) is int and 1<=n<=EXPECTED_SECOND_ITEMS,'THIRD_COUNT_NOT_PLAUSIBLE')
    require(src.get('schema')==SCHEMA+'-blind-items-v1'
            and tmpl.get('schema')==done.get('schema')==SCHEMA+'-decisions-v1'
            and idx.get('schema')==SCHEMA+'-coordinator-index-v1'
            and idx.get('second_validated_safe_sha256')==prep.get('second_validated_safe_sha256'),
            'THIRD_SCHEMAS_INVALID')
    tasks=by_token(src.get('items'),'THIRD_SOURCE',n)
    blanks=by_token(tmpl.get('items'),'THIRD_TEMPLATE',n)
    mapper=by_token(idx.get('records'),'THIRD_INDEX',n)
    answers=by_token(done.get('items'),'THIRD_DECISIONS',n)
    require(set(tasks)==set(blanks)==set(mapper)==set(answers),'THIRD_TOKEN_MISMATCH')
    count=Counter();by_arm=defaultdict(Counter);private=[];diff_count=0
    for token,task in tasks.items():
        m=mapper[token]
        require(m['response_sha256']==digest(task['匿名候选回复'].encode('utf-8')),'THIRD_SOURCE_REPLY_TAMPERED')
        require(task.get('must_evaluate_both_categories')==list(CATS),'THIRD_TASK_CATEGORY_CHANGED')
        require(set(answers[token])=={'candidate_token',*CATS},'THIRD_ANSWER_FIELDS_CHANGED')
        require(set(blanks[token])=={'candidate_token',*CATS},'THIRD_TEMPLATE_FIELDS_CHANGED')
        require(set(m['first_verdict_private'])==set(CATS)
                and set(m['second_verdict_private'])==set(CATS),'THIRD_PRIOR_CATEGORIES_BAD')
        require(m['source_arm_private'] in ('base','gold','v01','v02','v03'),'THIRD_ARM_BAD')
        require(set(m['unresolved_categories_private']).issubset(set(CATS)),
                'THIRD_UNRESOLVED_CATEGORY_BAD')
        context='\n'.join(task[k] for k in FIELDS[:-1]); decisions={}
        for cat in CATS:
            d=answers[token][cat]
            require(isinstance(d,dict) and set(d)=={'verdict','candidate_quote','context_quote','rationale'},
                    'THIRD_VERDICT_STRUCTURE_CHANGED')
            v=d.get('verdict');f=m['first_verdict_private'][cat];s=m['second_verdict_private'][cat]
            require(v in VERDICTS and f in VERDICTS and s in VERDICTS,
                    'THIRD_UNFILLED_VERDICT')
            require(isinstance(d['rationale'],str) and len(d['rationale'].strip())>=12,
                    'THIRD_MISSING_REASON')
            if v=='CONFIRMED':
                require(isinstance(d['candidate_quote'],str) and len(d['candidate_quote'].strip())>=2
                        and d['candidate_quote'] in task['匿名候选回复']
                        and isinstance(d['context_quote'],str) and len(d['context_quote'].strip())>=2
                        and d['context_quote'] in context,'THIRD_QUOTE_NOT_EXACT')
            else:
                require(isinstance(d['candidate_quote'],str) and isinstance(d['context_quote'],str),
                        'THIRD_OPTIONAL_QUOTE_BAD')
            unresolved=f!=s or f=='HOLD_INSUFFICIENT_EVIDENCE'
            require(unresolved==(cat in m['unresolved_categories_private']),
                    'THIRD_UNRESOLVED_SELECTION_INVALID')
            diff_count+=int(unresolved)
            count[v]+=1
            by_arm[(cat,m['source_arm_private'])][f+'__'+s+'__'+v]+=1
            decisions[cat]={'first_private':f,'second_private':s,'third':v,
                            'third_reason_private':d['rationale'],
                            'third_candidate_quote_private':d['candidate_quote'],
                            'third_context_quote_private':d['context_quote'],
                            'originally_needed_third':unresolved}
        private.append({'candidate_token':token,'source_arm_private':m['source_arm_private'],
                        'original_first_candidate_token_private':m['original_first_candidate_token_private'],
                        'categories':decisions})
    require(diff_count==EXPECTED_TERTIARY_CATEGORY_COUNT,'THIRD_UNRESOLVED_CATEGORY_TOTAL_MISMATCH')
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    write_private(out/'R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json',
                  {'schema':SCHEMA+'-owner-triage-private-v1','items':private,
                   'warning':'OWNER ONLY. Three reviewers, unverified semantic correctness. NO AUTOMATIC MAJORITY FINAL.'})
    safe={'schema':SCHEMA+'-safe-validated-v1',
          'status':'R55_GOLD5_THIRD_AUDIT_VERDICTS_QUOTATIONS_VALIDATED__NO_AUTO_RESOLUTION__NO_R50',
          'third_candidate_count':n,'third_category_decisions':n*len(CATS),
          'original_unresolved_category_count':diff_count,
          'third_verdict_counts':dict(count),
          'first_second_third_triage_by_arm_category':{
              cat:{arm:dict(by_arm[(cat,arm)]) for arm in ('base','v01','v02','v03','gold')} for cat in CATS},
          'third_decisions_sha256':digest(submitted.read_bytes()),
          'third_blind_sha256':prep['blind_packet_sha256'],
          'third_private_comparison_sha256':digest((out/'R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json').read_bytes()),
          'r50_accessed':False,'gpu_job_started':False,'training':False,
          'model_promoted':False,'automatic_final_adjudication':False,
          'verdict_semantics_not_automatically_certified':True,
          'third_reviewer_independence_not_technically_verified':True,
          'no_raw_private_text_in_safe_report':True}
    write_private(out/'R55_GOLD5_THIRD_AUDIT_SAFE_COUNT_ONLY.json',safe)
    return safe


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=('prepare','validate'),required=True)
    ap.add_argument('--first-pack',type=Path)
    ap.add_argument('--first-decisions',type=Path)
    ap.add_argument('--first-safe',type=Path)
    ap.add_argument('--second-pack',type=Path)
    ap.add_argument('--second-decisions',type=Path)
    ap.add_argument('--second-validated-dir',type=Path)
    ap.add_argument('--pack',type=Path,help='third blinded pack for validate')
    ap.add_argument('--decisions',type=Path,help='third filled decisions for validate')
    ap.add_argument('--out-dir',required=True,type=Path)
    args=ap.parse_args()
    try:
        if args.mode=='prepare':
            require(all((args.first_pack,args.first_decisions,args.first_safe,
                         args.second_pack,args.second_decisions,args.second_validated_dir)),
                    'MISSING_PRIOR_FROZEN_SOURCES')
            st=checked_twice(args.first_pack,args.first_decisions,args.first_safe,
                             args.second_pack,args.second_decisions,args.second_validated_dir)
            result=prepare(st,args.out_dir)
            outpath=args.out_dir/'safe/R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json'
        else:
            require(args.pack is not None and args.decisions is not None,'MISSING_THIRD_SOURCE_OR_DECISIONS')
            result=validate(args.pack,args.decisions,args.out_dir)
            outpath=args.out_dir/'R55_GOLD5_THIRD_AUDIT_SAFE_COUNT_ONLY.json'
        print(result['status']);print(PREFIX+'_SAFE_RECEIPT='+str(outpath))
    except (fr.Hold,OSError,ValueError,TypeError,KeyError,AssertionError) as exc:
        code=str(exc) if isinstance(exc,fr.Hold) else type(exc).__name__
        print(PREFIX+'_HOLD__'+code,file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""R55 Gold5: independent *second* semantic audit of frozen arbitration verdicts.

Prepare: pin original 76-item blinded packet, original signed-off decision bytes,
coordinator index and count-only decision receipt; prepare a fresh, re-tokenized,
blind second-review packet without first verdicts, reviewer annotations or arms.

Selection: all first CONFIRMED or HOLD category subjects plus a reproducible,
per-source-arm/per-category ceil(20%) sample of first REJECTED category subjects.
Each selected candidate must independently receive BOTH category judgments.

Validate: check second reviewer result and exact citations, then privately compare
independent category verdicts. Never auto-relabel original scores or promote a model.
Pure stdlib, no GPU, no R50, no network; private data must remain outside Git.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import sys

import v03_r55_gold5_event_arbitration as first
import v03_r55_gold5_review_freeze as fr

PREFIX = 'R55_GOLD5_SECOND_EVIDENCE_AUDIT'
SCHEMA = 'storyforge-r55-gold5-second-evidence-audit-v1'
PINNED_BLIND = 'b97e743ba3901561dc5745f9f50a47e52d1199c7c60f106ad9d011604c741f65'
PINNED_INDEX = '3b0400a5629b6673c2317248f061b63e1a30c26d6486da81f7eb0636d7638e9a'
PINNED_FIRST_DECISIONS = 'ee573b1d86d5ad2c8e807f69306006addc86d968ad85e1918d524de0d9b7d621'
EXPECTED_FIRST_VERDICTS = {'CONFIRMED':57, 'HOLD_INSUFFICIENT_EVIDENCE':22, 'REJECTED':73}
SAMPLE_DENOMINATOR = 5  # fixed: per (source arm, category), ceil(n/5) of rejected
CATS = first.CATEGORIES
VERDICTS = first.VERDICTS
SOURCE_KEYS = ('故事背景与系统规则', '历史对话', '当前用户输入', '匿名候选回复')


def require(ok: bool, code: str) -> None:
    if not ok:
        raise fr.Hold(code)


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_object(path: Path, name: str) -> dict:
    fr.valid_private(path, name)
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, ValueError) as exc:
        raise fr.Hold(name+'_INVALID_JSON') from exc
    require(isinstance(obj, dict), name+'_NOT_OBJECT')
    return obj


def checked_first(original_pack: Path, original_decisions: Path, validated_safe: Path) -> dict:
    """Read and cross-check actual frozen evidence, with Owner-provided fixed pins."""
    original_pack = original_pack.expanduser().resolve()
    source_file = original_pack/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json'
    index_file = original_pack/'coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json'
    prep_file = original_pack/'safe/R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json'
    for fp, label in ((source_file,'BLIND_ITEMS'),(index_file,'SOURCE_INDEX'),
                      (prep_file,'PREP_RECEIPT'),(original_decisions,'FIRST_DECISIONS'),
                      (validated_safe,'VALIDATED_FIRST_RECEIPT')):
        fr.valid_private(fp,label)
    require(digest(source_file.read_bytes())==PINNED_BLIND,'PINNED_BLIND_PACKET_SHA_MISMATCH')
    require(digest(index_file.read_bytes())==PINNED_INDEX,'PINNED_INDEX_SHA_MISMATCH')
    require(digest(original_decisions.read_bytes())==PINNED_FIRST_DECISIONS,
            'PINNED_FIRST_DECISIONS_SHA_MISMATCH')
    src=load_object(source_file,'BLIND_ITEMS')
    idx=load_object(index_file,'SOURCE_INDEX')
    prep=load_object(prep_file,'PREP_RECEIPT')
    decided=load_object(original_decisions,'FIRST_DECISIONS')
    safe=load_object(validated_safe,'VALIDATED_FIRST_RECEIPT')
    require(prep.get('schema')==first.SCHEMA+'-safe-prep-v1'
            and prep.get('scope')=='flagged' and prep.get('arbitration_items')==76
            and prep.get('blind_items_sha256')==PINNED_BLIND
            and prep.get('coordinator_index_sha256')==PINNED_INDEX
            and prep.get('r50_accessed') is False,'PREP_RECEIPT_NOT_PINNED')
    require(src.get('schema')==first.SCHEMA+'-blind-items-v1'
            and idx.get('schema')==first.SCHEMA+'-coordinator-index-v1'
            and decided.get('schema')==first.SCHEMA+'-adjudicator-decisions-v1',
            'FIRST_SCHEMAS_DIFFER')
    require(safe.get('schema')==first.SCHEMA+'-safe-decision-count-v1'
            and safe.get('status')=='R55_GOLD5_ARBITRATION_DECISIONS_SYNTAX_AND_EXACT_QUOTES_VALIDATED__DEV_ONLY__NO_R50'
            and safe.get('scope')=='flagged' and safe.get('adjudication_items_checked')==76
            and safe.get('blind_items_sha256')==PINNED_BLIND
            and safe.get('decisions_sha256')==PINNED_FIRST_DECISIONS
            and safe.get('r50_accessed') is False and safe.get('model_promoted') is False,
            'FIRST_SAFE_RECEIPT_MISMATCH')
    tasks=src.get('items'); metas=idx.get('records'); entries=decided.get('items')
    require(all(isinstance(z,list) and len(z)==76 for z in (tasks,metas,entries)),
            'FIRST_ITEMS_NOT_76')
    def mapping(rows, label):
        require(all(isinstance(r,dict) and isinstance(r.get('candidate_token'),str) for r in rows),label+'_BAD_ROWS')
        mp={r['candidate_token']:r for r in rows}
        require(len(mp)==76,label+'_DUPLICATE_TOKENS')
        return mp
    task_by=mapping(tasks,'BLIND'); meta_by=mapping(metas,'INDEX'); dec_by=mapping(entries,'FIRST')
    require(set(task_by)==set(meta_by)==set(dec_by),'FIRST_TOKEN_SET_MISMATCH')
    counts=Counter()
    by_arm=defaultdict(Counter)
    for tok,task in task_by.items():
        meta=meta_by[tok];entry=dec_by[tok]
        require(task['case_token']==meta['case_token'],'SOURCE_CASE_TOKEN_MISMATCH')
        require(digest(task['匿名候选回复'].encode('utf-8'))==meta['response_sha256'],
                'REPLY_HASH_NOT_FROZEN')
        require(meta['source_arm_private'] in ('base','v01','v02','v03','gold'),
                'UNKNOWN_SOURCE_ARM')
        require(set(entry)=={'candidate_token',*CATS},'FIRST_DECISION_STRUCTURE_CHANGED')
        context='\n'.join(task[k] for k in SOURCE_KEYS[:-1])
        for c in CATS:
            d=entry[c]
            require(isinstance(d,dict) and set(d)=={'verdict','candidate_quote','context_quote','rationale'},
                    'FIRST_VERDICT_STRUCTURE_CHANGED')
            v=d['verdict']
            require(v in VERDICTS and isinstance(d['rationale'],str)
                    and len(d['rationale'].strip())>=12,'FIRST_INCOMPLETE_VERDICT')
            if v=='CONFIRMED':
                require(isinstance(d['candidate_quote'],str) and len(d['candidate_quote'].strip())>=2
                        and d['candidate_quote'] in task['匿名候选回复']
                        and isinstance(d['context_quote'],str) and len(d['context_quote'].strip())>=2
                        and d['context_quote'] in context,'FIRST_QUOTE_NOT_EXACT')
            counts[v]+=1
            by_arm[(c,meta['source_arm_private'])][v]+=1
    require(dict(counts)==EXPECTED_FIRST_VERDICTS, 'FIRST_DECISION_COUNTS_NOT_PINNED')
    report=safe.get('verdict_counts_by_category_and_arm')
    require(isinstance(report,dict),'FIRST_COUNT_TABLE_MISSING')
    for c in CATS:
        for arm in ('base','v01','v02','v03','gold'):
            require(report.get(c,{}).get(arm,{})==dict(by_arm[(c,arm)]),
                    'FIRST_COUNT_TABLE_DOES_NOT_MATCH_DECISIONS')
    return {'task_by':task_by,'meta_by':meta_by,'dec_by':dec_by,
            'original_pack':original_pack,'safe_hash':digest(validated_safe.read_bytes()),
            'source_prep_hash':digest(prep_file.read_bytes())}


def rejected_samples(state: dict) -> set[tuple[str,str]]:
    """Precommitted deterministic, stratified 20% first-REJECTED audit sample."""
    strata=defaultdict(list)
    for tok, dec in state['dec_by'].items():
        arm=state['meta_by'][tok]['source_arm_private']
        for c in CATS:
            if dec[c]['verdict']=='REJECTED':
                strata[(arm,c)].append(tok)
    chosen=set()
    for (arm, c), toks in sorted(strata.items()):
        ranked=sorted(toks, key=lambda tok:digest(
            ('r55-gold5-v2-second-audit-rejected-v1|'+PINNED_FIRST_DECISIONS+'|'+arm+'|'+c+'|'+tok).encode('utf-8')))
        n=math.ceil(len(ranked)/SAMPLE_DENOMINATOR)
        chosen.update((tok,c) for tok in ranked[:n])
    require(len(chosen)>=1,'NO_REJECTED_SAMPLE')
    return chosen


def private_write(path: Path, obj: object) -> None:
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False)
        f.write('\n')


def prepare(state: dict, out: Path) -> dict:
    out=out.expanduser().resolve()
    fr.outside_git(out)
    require(not out.exists() and not out.is_symlink(),'SECOND_OUTPUT_ALREADY_EXISTS')
    samples=rejected_samples(state)
    include=set()
    for tok, row in state['dec_by'].items():
        if any(row[c]['verdict']!='REJECTED' for c in CATS):
            include.add(tok)
    include.update(tok for tok,c in samples)
    require(len(include)<=76 and len(include)>=1,'INVALID_SELECTION_SIZE')
    new_cases={}
    items=[]; links=[]
    used=set()
    for tok in sorted(include):
        src=state['task_by'][tok]; meta=state['meta_by'][tok]
        old_case=src['case_token']
        if old_case not in new_cases:
            new_cases[old_case]='W'+secrets.token_hex(7)
        newtok='S'+secrets.token_hex(12)
        require(newtok not in used,'RANDOM_TOKEN_COLLISION')
        used.add(newtok)
        items.append({'candidate_token':newtok,'case_token':new_cases[old_case],
                      **{k:src[k] for k in SOURCE_KEYS},
                      'must_evaluate_both_categories':list(CATS),
                      'instructions':'Review BOTH categories independently. Prior opinions, source identity, reasons for selection and model standings are not available. Use exact source quotes. Do not infer provenance.'})
        links.append({'candidate_token':newtok,'original_candidate_token_private':tok,
                      'original_case_token_private':old_case,'source_arm_private':meta['source_arm_private'],
                      'response_sha256':meta['response_sha256'],
                      'first_verdict_private':{c:state['dec_by'][tok][c]['verdict'] for c in CATS},
                      'sampled_rejected_category_private':[c for c in CATS if (tok,c) in samples]})
    secrets.SystemRandom().shuffle(items)
    blanks=[{'candidate_token':it['candidate_token'],
             **{c:{'verdict':'','candidate_quote':'','context_quote':'','rationale':''} for c in CATS}}
            for it in items]
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name in ('reviewers','coordinator','safe'):
        (out/name).mkdir(mode=0o700)
    srcfile=out/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json'
    blankfile=out/'reviewers/R55_GOLD5_SECOND_AUDIT_DECISIONS_BLANK_PRIVATE.json'
    idxfile=out/'coordinator/R55_GOLD5_SECOND_AUDIT_INDEX_PRIVATE.json'
    private_write(srcfile,{'schema':SCHEMA+'-blind-items-v1','items':items,
                           'status':'UNSCORED__SECOND_INDEPENDENT_AUDIT'})
    private_write(blankfile,{'schema':SCHEMA+'-second-decisions-v1','items':blanks})
    private_write(idxfile,{'schema':SCHEMA+'-coordinator-index-v1','records':links,
                           'first_decisions_sha256':PINNED_FIRST_DECISIONS,
                           'first_validated_safe_sha256':state['safe_hash'],
                           'original_blind_sha256':PINNED_BLIND,
                           'warning':'PRIVATE FIRST ARBITER VERDICTS AND ARM IDENTITY. NEVER SEND TO AUDITOR.'})
    rec={'schema':SCHEMA+'-safe-prep-v1',
         'status':'R55_GOLD5_SECOND_AUDIT_BLIND_PACK_PREPARED__NO_NEW_JUDGMENTS__NO_R50',
         'source_first_case_candidates':76,'source_first_category_decisions':152,
         'source_first_verdict_count_only':dict(EXPECTED_FIRST_VERDICTS),
         'selected_candidate_count':len(items),
         'selected_category_judgments_required':len(items)*2,
         'rejected_category_stratified_samples_selected':len(samples),
         'selection':'all_first_CONFIRMED_or_HOLD_by_category_union_plus_stratified_ceil_20pct_first_REJECTED_categories;judge_both_categories',
         'all_first_confirmed_and_hold_categories_included':True,
         'blind_packet_sha256':digest(srcfile.read_bytes()),
         'blank_template_sha256':digest(blankfile.read_bytes()),
         'private_coordinator_index_sha256':digest(idxfile.read_bytes()),
         'original_blind_sha256':PINNED_BLIND,
         'first_decisions_sha256':PINNED_FIRST_DECISIONS,
         'first_validated_safe_sha256':state['safe_hash'],
         'model_arm_exposure_to_second_auditor':False,
         'first_arbiter_verdict_exposure_to_second_auditor':False,
         'old_development_only':True,'r50_accessed':False,'gpu_job_started':False,
         'model_promoted':False,'adjudication_complete':False,
         'no_private_case_text_or_tokens_in_safe_receipt':True}
    private_write(out/'safe/R55_GOLD5_SECOND_AUDIT_PREP_SAFE_COUNT_ONLY.json',rec)
    return rec


def validate_second(pack: Path, submitted: Path, out: Path) -> dict:
    pack=pack.expanduser().resolve()
    prepfile=pack/'safe/R55_GOLD5_SECOND_AUDIT_PREP_SAFE_COUNT_ONLY.json'
    rec=load_object(prepfile,'SECOND_PREP_RECEIPT')
    require(rec.get('schema')==SCHEMA+'-safe-prep-v1'
            and rec.get('status')=='R55_GOLD5_SECOND_AUDIT_BLIND_PACK_PREPARED__NO_NEW_JUDGMENTS__NO_R50'
            and rec.get('first_decisions_sha256')==PINNED_FIRST_DECISIONS
            and rec.get('original_blind_sha256')==PINNED_BLIND
            and rec.get('r50_accessed') is False,'SECOND_PREP_MISMATCH')
    sourcefile=pack/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json'
    blankfile=pack/'reviewers/R55_GOLD5_SECOND_AUDIT_DECISIONS_BLANK_PRIVATE.json'
    indexfile=pack/'coordinator/R55_GOLD5_SECOND_AUDIT_INDEX_PRIVATE.json'
    for f,label,field in ((sourcefile,'SECOND_SOURCE','blind_packet_sha256'),
                          (blankfile,'SECOND_BLANK','blank_template_sha256'),
                          (indexfile,'SECOND_INDEX','private_coordinator_index_sha256')):
        fr.valid_private(f,label)
        require(digest(f.read_bytes())==rec.get(field),label+'_HASH_MISMATCH')
    src=load_object(sourcefile,'SECOND_SOURCE')
    blank=load_object(blankfile,'SECOND_BLANK')
    index=load_object(indexfile,'SECOND_INDEX')
    done=load_object(submitted,'SECOND_SUBMITTED')
    require(src.get('schema')==SCHEMA+'-blind-items-v1'
            and blank.get('schema')==done.get('schema')==SCHEMA+'-second-decisions-v1'
            and index.get('schema')==SCHEMA+'-coordinator-index-v1',
            'SECOND_SCHEMAS_CHANGED')
    tasks=src.get('items'); templates=blank.get('items'); records=index.get('records'); answers=done.get('items')
    n=rec['selected_candidate_count']
    require(all(isinstance(z,list) and len(z)==n for z in (tasks,templates,records,answers)),
            'SECOND_ITEMS_COUNT_MISMATCH')
    def mapped(rows,label):
        require(all(isinstance(r,dict) and isinstance(r.get('candidate_token'),str) for r in rows),label+'_BAD')
        mp={r['candidate_token']:r for r in rows}
        require(len(mp)==n,label+'_DUPLICATES')
        return mp
    tasks_by=mapped(tasks,'TASKS'); template_by=mapped(templates,'TEMPLATES')
    index_by=mapped(records,'INDEX'); answers_by=mapped(answers,'ANSWERS')
    require(set(tasks_by)==set(template_by)==set(index_by)==set(answers_by),
            'SECOND_TOKENS_CHANGED')
    by_arm=defaultdict(Counter)
    by_transition=defaultdict(Counter)
    first_selected=Counter(); second_all=Counter(); disagreements=0
    unresolved=0; independent_confirmed=0
    private=[]
    for token, task in tasks_by.items():
        meta=index_by[token]
        require(meta['response_sha256']==digest(task['匿名候选回复'].encode('utf-8')),
                'SECOND_SOURCE_RESPONSE_HASH_MISMATCH')
        require(set(answers_by[token])=={'candidate_token',*CATS},'SECOND_FIELDS_CHANGED')
        ctx='\n'.join(task[k] for k in SOURCE_KEYS[:-1]); resulting={}
        for cat in CATS:
            d=answers_by[token][cat]
            require(isinstance(d,dict) and set(d)=={'verdict','candidate_quote','context_quote','rationale'},
                    'SECOND_VERDICT_FIELDS_CHANGED')
            v=d['verdict']
            require(v in VERDICTS and isinstance(d['rationale'],str) and len(d['rationale'].strip())>=12,
                    'SECOND_UNFILLED_VERDICT')
            if v=='CONFIRMED':
                require(isinstance(d['candidate_quote'],str) and len(d['candidate_quote'].strip())>=2
                        and d['candidate_quote'] in task['匿名候选回复'],'SECOND_UNGROUNDED_CANDIDATE_QUOTE')
                require(isinstance(d['context_quote'],str) and len(d['context_quote'].strip())>=2
                        and d['context_quote'] in ctx,'SECOND_UNGROUNDED_CONTEXT_QUOTE')
            else:
                require(isinstance(d['candidate_quote'],str) and isinstance(d['context_quote'],str),
                        'SECOND_BAD_OPTIONAL_QUOTES')
            orig=meta['first_verdict_private'][cat]
            require(orig in VERDICTS,'SECOND_FIRST_VERDICT_INVALID')
            first_selected[orig]+=1;second_all[v]+=1
            by_arm[(cat,meta['source_arm_private'])][v]+=1
            by_transition[(cat,meta['source_arm_private'])][orig+'__TO__'+v]+=1
            if orig!=v:disagreements+=1
            if orig=='CONFIRMED' and v=='CONFIRMED':independent_confirmed+=1
            if orig!=v or orig=='HOLD_INSUFFICIENT_EVIDENCE':unresolved+=1
            resulting[cat]={'first_verdict_private':orig,'second_verdict':v,
                            'second_rationale_private':d['rationale'],
                            'second_candidate_quote_private':d['candidate_quote'],
                            'second_context_quote_private':d['context_quote'],
                            'review_status':'MATCH' if orig==v and orig!='HOLD_INSUFFICIENT_EVIDENCE' else 'NEEDS_TERTIARY_OR_EVIDENCE'}
        private.append({'candidate_token':token,
                        'original_candidate_token_private':meta['original_candidate_token_private'],
                        'source_arm_private':meta['source_arm_private'],
                        'categories':resulting})
    require(sum(first_selected.values())==n*2,'SECOND_VERDICT_COUNT_MISMATCH')
    out=out.expanduser().resolve()
    fr.outside_git(out)
    require(not out.exists() and not out.is_symlink(),'SECOND_VALIDATION_OUTPUT_EXISTS')
    out.mkdir(parents=True,mode=0o700,exist_ok=False)
    private_write(out/'R55_GOLD5_SECOND_AUDIT_COMPARISON_PRIVATE.json',
                  {'schema':SCHEMA+'-private-comparison-v1',
                   'warning':'PRIVATE FIRST+SECOND JUDGMENTS AND MODEL ARMS. OWNER ONLY.',
                   'items':private})
    rec2={'schema':SCHEMA+'-safe-validated-v1',
          'status':'R55_GOLD5_SECOND_AUDIT_VERDICTS_VALIDATED__NO_AUTO_PROMOTION__NO_R50',
          'selected_candidate_count':n,'second_category_decisions_validated':n*2,
          'first_selected_category_verdicts':dict(first_selected),
          'second_category_verdicts':dict(second_all),
          'same_verdict_count':n*2-disagreements,
          'disagreement_category_count':disagreements,
          'first_HOLD_or_disagreement_needs_tertiary_count':unresolved,
          'both_arbiters_CONFIRMED_category_count':independent_confirmed,
          'per_arm_category_verdict_counts':{
              cat:{arm:dict(by_arm[(cat,arm)]) for arm in ('base','v01','v02','v03','gold')}
              for cat in CATS},
          'per_arm_category_transition_counts':{
              cat:{arm:dict(by_transition[(cat,arm)]) for arm in ('base','v01','v02','v03','gold')}
              for cat in CATS},
          'blind_packet_sha256':rec['blind_packet_sha256'],
          'first_decisions_sha256':PINNED_FIRST_DECISIONS,
          'second_decisions_sha256':digest(submitted.read_bytes()),
          'reviewer_independence_unverified':True,
          'verdict_semantics_not_automatically_certified':True,
          'selected_sample_not_population_error_rate':True,
          'r50_accessed':False,'gpu_job_started':False,
          'training':False,'model_promoted':False,'no_raw_private_text_in_safe_report':True}
    private_write(out/'R55_GOLD5_SECOND_AUDIT_SAFE_COUNT_ONLY.json',rec2)
    return rec2


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',required=True,choices=('prepare','validate'))
    ap.add_argument('--pack',type=Path,required=True,help='original event-arbitration-v1 for prepare; second pack for validate')
    ap.add_argument('--first-decisions',type=Path,help='first arbiter completed JSON (prepare only)')
    ap.add_argument('--first-safe',type=Path,help='first arbiter validated count-only JSON (prepare only)')
    ap.add_argument('--decisions',type=Path,help='second arbiter completed JSON (validate only)')
    ap.add_argument('--out-dir',type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.mode=='prepare':
            require(args.first_decisions is not None and args.first_safe is not None,
                    'MISSING_FIRST_DECISIONS_OR_SAFE')
            state=checked_first(args.pack,args.first_decisions,args.first_safe)
            result=prepare(state,args.out_dir)
            print(result['status'])
            print(PREFIX+'_SAFE_PREP='+str(args.out_dir/'safe/R55_GOLD5_SECOND_AUDIT_PREP_SAFE_COUNT_ONLY.json'))
        else:
            require(args.decisions is not None,'MISSING_SECOND_DECISIONS')
            result=validate_second(args.pack,args.decisions,args.out_dir)
            print(result['status'])
            print(PREFIX+'_SAFE_RESULT='+str(args.out_dir/'R55_GOLD5_SECOND_AUDIT_SAFE_COUNT_ONLY.json'))
    except (fr.Hold,OSError,TypeError,ValueError,KeyError,AssertionError) as exc:
        code=str(exc) if isinstance(exc,fr.Hold) else type(exc).__name__
        print(PREFIX+'_HOLD__'+code,file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())

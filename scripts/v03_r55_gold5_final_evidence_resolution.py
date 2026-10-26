#!/usr/bin/env python3
"""R55 Gold5: Owner-only final evidence docket, no automatic majority adjudication.

Replays and verifies three rounds of arbitration against frozen user-reported
pins; prepares all 76 flagged candidate subjects x 2 categories. Prioritizes
59 first/second disputes or first HOLDs + six agreed-C contradicted by third.
Optional staged validation checks 65 priority judgments, then all 152.
Does not read R50, retrain or promote any model. Private materials stay outside Git.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import v03_r55_gold5_third_evidence_audit as third
import v03_r55_gold5_second_evidence_audit as second
import v03_r55_gold5_event_arbitration as first
import v03_r55_gold5_review_freeze as fr

PREFIX = 'R55_GOLD5_FINAL_EVIDENCE'
SCHEMA = 'storyforge-r55-gold5-final-evidence-resolution-v1'
PINNED_THIRD_BLIND = '78c156763f79eaf1406b0f1788b18e014bb738497bce634fa64e3bb4c55920e1'
PINNED_THIRD_DECISIONS = 'c31ff03eaf12f6f3907b5db7e6fc1880be57af8ff425b9dd993dc76896abf9b2'
PINNED_THIRD_COMPARISON = '06ba8f879e3ed51b5f86869e5362bd98d0f080acbcc56a3ba6a9f2f7843ea2d4'
EXPECTED_FIRST_CANDIDATES=76
EXPECTED_TOTAL_CATEGORIES=152
EXPECTED_ORIGINAL_DISPUTES=59
EXPECTED_ADDITIONAL_CONTRADICTIONS=6
EXPECTED_THIRD_CANDIDATES=46
EXPECTED_THIRD_CATEGORY_SLOTS=92
EXPECTED_PRIORITY=65
CATS=first.CATEGORIES
VERDICTS=first.VERDICTS
SOURCE_KEYS=second.SOURCE_KEYS
ARMS=('base','gold','v01','v02','v03')


def require(cond:bool,code:str)->None:
    if not cond: raise fr.Hold(code)


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def read(path:Path,label:str)->dict:
    fr.valid_private(path,label)
    try: val=json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,UnicodeError) as exc: raise fr.Hold(label+'_INVALID_JSON') from exc
    require(isinstance(val,dict),label+'_NOT_OBJECT')
    return val


def by_token(items:list,label:str,count:int)->dict:
    require(isinstance(items,list) and len(items)==count,label+'_COUNT')
    require(all(isinstance(x,dict) and isinstance(x.get('candidate_token'),str)
                and x['candidate_token'] for x in items),label+'_STRUCTURE')
    mp={x['candidate_token']:x for x in items}
    require(len(mp)==count,label+'_DUPLICATE_TOKEN')
    return mp


def write(path:Path,val:object)->None:
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        json.dump(val,stream,sort_keys=True,ensure_ascii=False,indent=2)
        stream.write('\n')


def new_output(path:Path)->Path:
    p=path.expanduser().resolve()
    fr.outside_git(p)
    require(not p.exists() and not p.is_symlink(),'OUTPUT_ALREADY_EXISTS')
    return p


def checked_all(first_pack:Path,first_decisions:Path,first_safe:Path,
                second_pack:Path,second_decisions:Path,second_validated_dir:Path,
                third_pack:Path,third_decisions:Path,third_validated_dir:Path)->dict:
    # Re-derive original frozen first and second sources. Refuse even correctly
    # formatted reports which no longer agree with the underlying materials.
    selected=third.checked_twice(first_pack,first_decisions,first_safe,
                                second_pack,second_decisions,second_validated_dir)
    state=second.checked_first(first_pack,first_decisions,first_safe)
    third_pack=third_pack.expanduser().resolve()
    third_validated_dir=third_validated_dir.expanduser().resolve()
    third_blind=third_pack/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json'
    third_map=third_pack/'coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json'
    third_prep=third_pack/'safe/R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json'
    safe_path=third_validated_dir/'R55_GOLD5_THIRD_AUDIT_SAFE_COUNT_ONLY.json'
    compare_path=third_validated_dir/'R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json'
    for f,label in ((third_blind,'THIRD_BLIND'),(third_map,'THIRD_MAP'),
                    (third_decisions,'THIRD_DECISIONS'),(third_prep,'THIRD_PREP'),
                    (safe_path,'THIRD_SAFE'),(compare_path,'THIRD_COMPARE')):
        fr.valid_private(f,label)
    require(sha(third_blind.read_bytes())==PINNED_THIRD_BLIND,'THIRD_BLIND_PIN_MISMATCH')
    require(sha(third_decisions.read_bytes())==PINNED_THIRD_DECISIONS,'THIRD_DECISIONS_PIN_MISMATCH')
    require(sha(compare_path.read_bytes())==PINNED_THIRD_COMPARISON,'THIRD_COMPARE_PIN_MISMATCH')
    safe=read(safe_path,'THIRD_SAFE')
    prep=read(third_prep,'THIRD_PREP')
    require(safe.get('schema')==third.SCHEMA+'-safe-validated-v1'
            and safe.get('status')=='R55_GOLD5_THIRD_AUDIT_VERDICTS_QUOTATIONS_VALIDATED__NO_AUTO_RESOLUTION__NO_R50'
            and safe.get('third_candidate_count')==EXPECTED_THIRD_CANDIDATES
            and safe.get('third_category_decisions')==EXPECTED_THIRD_CATEGORY_SLOTS
            and safe.get('original_unresolved_category_count')==EXPECTED_ORIGINAL_DISPUTES
            and safe.get('third_decisions_sha256')==PINNED_THIRD_DECISIONS
            and safe.get('third_blind_sha256')==PINNED_THIRD_BLIND
            and safe.get('third_private_comparison_sha256')==PINNED_THIRD_COMPARISON
            and safe.get('r50_accessed') is False,'THIRD_VALIDATED_SAFE_MISMATCH')
    require(prep.get('blind_packet_sha256')==PINNED_THIRD_BLIND
            and prep.get('required_third_category_judgments')==EXPECTED_THIRD_CATEGORY_SLOTS
            and prep.get('selected_unique_candidates')==EXPECTED_THIRD_CANDIDATES
            and prep.get('private_mapping_sha256')==sha(third_map.read_bytes())
            and prep.get('second_validated_safe_sha256')==selected['second_safe_hash']
            and prep.get('r50_accessed') is False,'THIRD_PREP_MISMATCH')
    # third.validate() owns independent schema, exact quotation, token, source
    # hash and unresolved-selection checks. We also verify its byte-exact outputs.
    with tempfile.TemporaryDirectory(prefix='r55-final-verify-') as tmp:
        target=Path(tmp)/'third-replay'
        regen=third.validate(third_pack,third_decisions,target)
        require(regen==safe,'THIRD_SAFE_REPLAY_MISMATCH')
        require(sha((target/'R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json').read_bytes())
                ==PINNED_THIRD_COMPARISON,'THIRD_PRIVATE_REPLAY_MISMATCH')
    tasks=by_token(read(third_blind,'THIRD_BLIND')['items'],'THIRD_TASKS',EXPECTED_THIRD_CANDIDATES)
    idx=by_token(read(third_map,'THIRD_MAPPING')['records'],'THIRD_INDEX',EXPECTED_THIRD_CANDIDATES)
    answers=by_token(read(third_decisions,'THIRD_DECISIONS')['items'],'THIRD_ANSWERS',EXPECTED_THIRD_CANDIDATES)
    require(set(tasks)==set(idx)==set(answers),'THIRD_TOKEN_SET_MISMATCH')
    second_pack=second_pack.expanduser().resolve()
    sb=by_token(read(second_pack/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json',
                     'SECOND_BLIND')['items'],'SECOND_BLIND',third.EXPECTED_SECOND_ITEMS)
    si=by_token(read(second_pack/'coordinator/R55_GOLD5_SECOND_AUDIT_INDEX_PRIVATE.json',
                     'SECOND_INDEX')['records'],'SECOND_INDEX',third.EXPECTED_SECOND_ITEMS)
    sd=by_token(read(second_decisions,'SECOND_ANSWERS')['items'],'SECOND_ANSWERS',third.EXPECTED_SECOND_ITEMS)
    sec_by_original={v['original_candidate_token_private']:(k,v) for k,v in si.items()}
    require(len(sec_by_original)==third.EXPECTED_SECOND_ITEMS,'SECOND_ORIGINAL_DUPLICATE')
    tri_by_original={}
    for token,meta in idx.items():
        old=meta['original_first_candidate_token_private']
        sec_token=meta['original_second_candidate_token_private']
        require(old in state['task_by'] and sec_token in sb and sec_token in si and sec_token in sd,
                'THIRD_LINK_NOT_IN_FIRST_SECOND')
        require(si[sec_token]['original_candidate_token_private']==old
                and meta['source_arm_private']==si[sec_token]['source_arm_private']
                and meta['response_sha256']==state['meta_by'][old]['response_sha256'],
                'THIRD_LINK_ARM_OR_REPLY_BAD')
        require(all(tasks[token][k]==state['task_by'][old][k]==sb[sec_token][k]
                    for k in SOURCE_KEYS),'THIRD_SOURCE_TEXT_CHANGED')
        require(old not in tri_by_original,'THIRD_ORIGINAL_DUPLICATE')
        tri_by_original[old]=(token,meta)
    # Candidate is a (case, reply). Each of its 2 categories is a separate
    # evidentiary question; candidate counts cannot be substituted for events.
    items=[]; priority=Counter(); followups=Counter(); first_counts=Counter()
    for token,original in state['task_by'].items():
        arm=state['meta_by'][token]['source_arm_private']
        require(arm in ARMS,'ORIGINAL_ARM_INVALID')
        sec=sec_by_original.get(token)
        third_item=tri_by_original.get(token)
        require(sec is None or sec[0] in sd,'SECOND_DECISION_MISSING')
        categories={}
        for cat in CATS:
            f=state['dec_by'][token][cat]
            s=sd[sec[0]][cat] if sec else None
            t=answers[third_item[0]][cat] if third_item else None
            fv=f['verdict'];sv=s['verdict'] if s else None;tv=t['verdict'] if t else None
            if sec and (fv!=sv or fv=='HOLD_INSUFFICIENT_EVIDENCE'):
                require(third_item is not None,'ORIGINAL_DISPUTE_NOT_THIRD_REVIEWED')
                require(cat in third_item[1]['unresolved_categories_private'],
                        'THIRD_FOCUS_MISSING')
                reason='P0_FIRST_SECOND_DISPUTE_OR_HOLD'
            elif sec and fv==sv=='CONFIRMED' and tv=='REJECTED':
                reason='P0_DOUBLE_CONFIRMED_THIRD_REJECTED'
            elif t is not None:
                require(s is not None and fv==sv==tv,'THIRD_NON_PRIORITY_UNEXPECTED_DIFFERENCE')
                reason='P1_THREE_UNANIMOUS'
            elif s is not None:
                require(fv==sv and fv!='HOLD_INSUFFICIENT_EVIDENCE',
                        'SECOND_NON_PRIORITY_UNRESOLVED')
                reason='P1_TWO_AGREE_UNREVIEWED_THIRD'
            else:
                require(fv=='REJECTED','FIRST_ONLY_NOT_REJECTED')
                reason='P1_FIRST_ONLY_NOT_SAMPLED'
            priority[reason]+=1
            first_counts[fv]+=1
            categories[cat]={'priority_reason':reason,
                             'first':f,
                             'second':s,
                             'third':t,
                             'original_dispute':reason=='P0_FIRST_SECOND_DISPUTE_OR_HOLD'}
        items.append({'candidate_token':token,'case_token':original['case_token'],
                      'source_arm_PRIVATE':arm,
                      'original_candidate_response_sha256':state['meta_by'][token]['response_sha256'],
                      **{k:original[k] for k in SOURCE_KEYS},
                      'categories':categories})
    require(len(items)==EXPECTED_FIRST_CANDIDATES,'FINAL_CANDIDATE_COUNT_MISMATCH')
    require(sum(priority.values())==EXPECTED_TOTAL_CATEGORIES,'FINAL_CATEGORIES_NOT_152')
    require(priority['P0_FIRST_SECOND_DISPUTE_OR_HOLD']==EXPECTED_ORIGINAL_DISPUTES,
            'ORIGINAL_59_DISPUTES_MISMATCH')
    require(priority['P0_DOUBLE_CONFIRMED_THIRD_REJECTED']==EXPECTED_ADDITIONAL_CONTRADICTIONS,
            'EXTRA_6_CONTRADICTIONS_MISMATCH')
    require(sum(v for k,v in priority.items() if k.startswith('P0_'))==EXPECTED_PRIORITY,
            'PRIORITY_65_MISMATCH')
    require(dict(first_counts)==second.EXPECTED_FIRST_VERDICTS,'FIRST_VERDICTS_NOT_FROZEN')
    items.sort(key=lambda item:(0 if any(item['categories'][c]['priority_reason'].startswith('P0_')
                                      for c in CATS) else 1,item['case_token'],item['candidate_token']))
    pins={'first_decisions_sha256':sha(first_decisions.read_bytes()),
          'second_decisions_sha256':sha(second_decisions.read_bytes()),
          'third_decisions_sha256':sha(third_decisions.read_bytes()),
          'third_safe_sha256':sha(safe_path.read_bytes()),
          'third_compare_sha256':sha(compare_path.read_bytes()),
          'third_pack_sha256':sha(third_blind.read_bytes())}
    return {'items':items,'priority_counts':dict(priority),'pins':pins,
            'safe_previous':safe,'selected_third':selected}


def prepare(state:dict,out:Path)->dict:
    out=new_output(out)
    out.mkdir(parents=True,mode=0o700,exist_ok=False)
    owner=out/'owner';safe=out/'safe'
    owner.mkdir(mode=0o700);safe.mkdir(mode=0o700)
    docket=owner/'R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json'
    template=owner/'R55_GOLD5_FINAL_EVIDENCE_DECISIONS_BLANK_PRIVATE.json'
    write(docket,{'schema':SCHEMA+'-owner-docket-v1','items':state['items'],
                  'warning':'OWNER ONLY. Includes private source arm, story text and 3 arbiters evidence. NOT for Git or independent blind reviewer.'})
    blank=[{'candidate_token':r['candidate_token'],**{cat:{
        'final_verdict':'',
        'issue_subtype':'',
        'candidate_quote':'',
        'context_quote':'',
        'rationale':'',
        'evidence_gap':'',
        'final_decider_id':''} for cat in CATS}} for r in state['items']]
    write(template,{'schema':SCHEMA+'-owner-decisions-v1','items':blank})
    rec={'schema':SCHEMA+'-safe-prep-v1',
         'status':'R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PREPARED__NO_AUTO_DECISION__NO_R50',
         'source_flagged_candidates':EXPECTED_FIRST_CANDIDATES,
         'source_category_slots':EXPECTED_TOTAL_CATEGORIES,
         'priority_category_slots':EXPECTED_PRIORITY,
         'priority_breakdown':state['priority_counts'],
         'priority_is_provisional_not_confirmed_events':True,
         'prior_receipt_pins':state['pins'],
         'owner_docket_sha256':sha(docket.read_bytes()),
         'blank_template_sha256':sha(template.read_bytes()),
         'contains_private_text':False,'not_population_error_rate':True,
         'automatically_resolved':False,'semantic_certification':False,
         'r50_accessed':False,'training':False,'gpu_job_started':False,'model_promoted':False}
    write(safe/'R55_GOLD5_FINAL_EVIDENCE_PREP_SAFE_COUNT_ONLY.json',rec)
    return rec


def _complete_judgment(j:dict,task:dict,category:str)->None:
    require(isinstance(j,dict) and set(j)=={'final_verdict','issue_subtype','candidate_quote',
            'context_quote','rationale','evidence_gap','final_decider_id'},'FINAL_FIELDS_INVALID')
    v=j.get('final_verdict')
    require(v in VERDICTS,'FINAL_VERDICT_NOT_FILLED')
    require(isinstance(j['rationale'],str) and len(j['rationale'].strip())>=24,
            'FINAL_RATIONALE_TOO_SHORT')
    require(isinstance(j['final_decider_id'],str) and len(j['final_decider_id'].strip())>=3,
            'FINAL_DECIDER_ID_MISSING')
    require(all(isinstance(j[k],str) for k in ('candidate_quote','context_quote',
                                                'evidence_gap','issue_subtype')),
            'FINAL_TEXT_FIELD_INVALID')
    if v=='CONFIRMED':
        require(len(j['candidate_quote'].strip())>=2 and
                j['candidate_quote'] in task['匿名候选回复'],
                'FINAL_CANDIDATE_QUOTE_NOT_EXACT')
        ctx='\n'.join(task[k] for k in SOURCE_KEYS[:-1])
        require(len(j['context_quote'].strip())>=2 and
                j['context_quote'] in ctx,'FINAL_CONTEXT_QUOTE_NOT_EXACT')
        require(not j['evidence_gap'].strip(),'FINAL_CONFIRMED_CANNOT_HAVE_EVIDENCE_GAP')
        if category=='hard_fact_or_ban':
            require(j['issue_subtype'] in ('explicit_banned_phrase','hard_fact_mismatch','both'),
                    'FINAL_HARD_FACT_MISSING_SUBTYPE')
        else:
            require(j['issue_subtype']=='not_applicable','FINAL_AGENCY_SUBTYPE_INVALID')
    elif v=='HOLD_INSUFFICIENT_EVIDENCE':
        require(len(j['evidence_gap'].strip())>=16,'FINAL_HOLD_MISSING_EVIDENCE_GAP')
        require(j['issue_subtype']=='undetermined','FINAL_HOLD_SUBTYPE_UNDETERMINED')
    else:
        require(j['issue_subtype']=='not_applicable','FINAL_REJECTED_SUBTYPE_INVALID')
        require(not j['evidence_gap'].strip(),'FINAL_REJECTED_EVIDENCE_GAP_UNEXPECTED')


def validate(pack:Path,submitted:Path,out:Path,*,priority_only:bool)->dict:
    pack=pack.expanduser().resolve();out=new_output(out)
    receipt_file=pack/'safe/R55_GOLD5_FINAL_EVIDENCE_PREP_SAFE_COUNT_ONLY.json'
    docket_file=pack/'owner/R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json'
    template_file=pack/'owner/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_BLANK_PRIVATE.json'
    safe=read(receipt_file,'FINAL_PREP_RECEIPT')
    require(safe.get('schema')==SCHEMA+'-safe-prep-v1'
            and safe.get('status')=='R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PREPARED__NO_AUTO_DECISION__NO_R50'
            and safe.get('source_flagged_candidates')==EXPECTED_FIRST_CANDIDATES
            and safe.get('source_category_slots')==EXPECTED_TOTAL_CATEGORIES
            and safe.get('priority_category_slots')==EXPECTED_PRIORITY
            and safe.get('r50_accessed') is False,'FINAL_SAFE_PREP_INVALID')
    require(sha(docket_file.read_bytes())==safe['owner_docket_sha256'],
            'FINAL_DOCKET_HASH_MISMATCH')
    require(sha(template_file.read_bytes())==safe['blank_template_sha256'],
            'FINAL_BLANK_HASH_MISMATCH')
    docket=read(docket_file,'FINAL_DOCKET')
    template=read(template_file,'FINAL_BLANK')
    submission=read(submitted,'FINAL_COMPLETED')
    require(docket.get('schema')==SCHEMA+'-owner-docket-v1'
            and template.get('schema')==submission.get('schema')==SCHEMA+'-owner-decisions-v1',
            'FINAL_SCHEMA_CHANGED')
    tasks=by_token(docket.get('items'),'FINAL_DOCKET',EXPECTED_FIRST_CANDIDATES)
    blank=by_token(template.get('items'),'FINAL_BLANK',EXPECTED_FIRST_CANDIDATES)
    done=by_token(submission.get('items'),'FINAL_COMPLETED',EXPECTED_FIRST_CANDIDATES)
    require(set(tasks)==set(blank)==set(done),'FINAL_TOKENS_MISMATCH')
    require(all(set(x)=={'candidate_token',*CATS} for x in done.values()),
            'FINAL_CANDIDATE_FIELDS_CHANGED')
    verified=0;skipped=0;verdicts=Counter();by_arm=defaultdict(Counter);priority_counts=Counter()
    private=[]
    for tok,task in tasks.items():
        row=done[tok]
        rec={'candidate_token':tok,'source_arm_private':task['source_arm_PRIVATE'],'categories':{}}
        require(task['source_arm_PRIVATE'] in ARMS,'FINAL_DOCKET_ARM_INVALID')
        require(sha(task['匿名候选回复'].encode('utf-8'))==task['original_candidate_response_sha256'],
                'FINAL_DOCKET_REPLY_HASH_MISMATCH')
        for cat in CATS:
            tier=task['categories'][cat]['priority_reason']
            require(isinstance(tier,str) and tier.startswith(('P0_','P1_')),
                    'FINAL_PRIORITY_TIER_INVALID')
            j=row[cat]
            if priority_only and tier.startswith('P1_'):
                # P1 rows may be blank, but if filled, do not claim they were
                # validated, counted or endorsed in priority-only mode.
                skipped+=1
                continue
            _complete_judgment(j,task,cat)
            verified+=1
            verdicts[j['final_verdict']]+=1
            by_arm[(task['source_arm_PRIVATE'],cat)][j['final_verdict']]+=1
            priority_counts[tier]+=1
            rec['categories'][cat]={'verdict':j['final_verdict'],
                                    'subtype':j['issue_subtype'],
                                    'rationale_private':j['rationale'],
                                    'evidence_gap_private':j['evidence_gap'],
                                    'final_decider_id_private':j['final_decider_id'],
                                    'source_quote_private':j['candidate_quote'],
                                    'context_quote_private':j['context_quote'],
                                    'source_sha256':task['original_candidate_response_sha256']}
        if rec['categories']:private.append(rec)
    require(verified==(EXPECTED_PRIORITY if priority_only else EXPECTED_TOTAL_CATEGORIES),
            'FINAL_VALIDATED_COUNT_UNEXPECTED')
    require(skipped==(EXPECTED_TOTAL_CATEGORIES-EXPECTED_PRIORITY if priority_only else 0),
            'FINAL_SKIPPED_COUNT_UNEXPECTED')
    out.mkdir(parents=True,mode=0o700,exist_ok=False)
    write(out/'R55_GOLD5_FINAL_EVIDENCE_VERIFIED_PRIVATE.json',{
        'schema':SCHEMA+'-private-validated-v1', 'items':private,
        'warning':'OWNER ONLY. Form/quote validation is not semantic certification.'})
    result={'schema':SCHEMA+'-safe-validated-v1',
            'status':('R55_GOLD5_FINAL_EVIDENCE_PRIORITY_65_FORMAT_VERIFIED__NOT_FINAL__NO_R50'
                      if priority_only else
                      'R55_GOLD5_FINAL_EVIDENCE_ALL_152_FORMAT_VERIFIED__NOT_SEMANTIC_CERTIFIED__NO_R50'),
            'scope':('priority65' if priority_only else 'all152'),
            'verified_category_judgments':verified,
            'not_reviewed_in_this_validation':skipped,
            'verdict_counts':dict(verdicts),
            'verdict_counts_by_category_and_arm':{
                cat:{arm:dict(by_arm[(arm,cat)]) for arm in ARMS} for cat in CATS},
            'HOLD_categories_still_unresolved':verdicts.get('HOLD_INSUFFICIENT_EVIDENCE',0),
            'original_selected_case_candidates':EXPECTED_FIRST_CANDIDATES,
            'selection':'originally_review-flagged,not_random',
            'final_verdicts_are_human_owner_decisions_not_automated_vote_aggregation':True,
            'semantic_correctness_not_automatically_certified':True,
            'not_unbiased_model_error_rate':True,
            'source_final_docket_sha256':safe['owner_docket_sha256'],
            'completed_owner_decisions_sha256':sha(submitted.read_bytes()),
            'private_verified_result_sha256':sha((out/'R55_GOLD5_FINAL_EVIDENCE_VERIFIED_PRIVATE.json').read_bytes()),
            'r50_accessed':False,'gpu_job_started':False,'training':False,'model_promoted':False}
    write(out/'R55_GOLD5_FINAL_EVIDENCE_SAFE_COUNT_ONLY.json',result)
    return result


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=('prepare','validate-priority','validate-all'),required=True)
    for name in ('first-pack','first-decisions','first-safe','second-pack','second-decisions',
                 'second-validated-dir','third-pack','third-decisions','third-validated-dir'):
        ap.add_argument('--'+name,type=Path)
    ap.add_argument('--pack',type=Path,help='Owner final docket directory when validating')
    ap.add_argument('--decisions',type=Path,help='Completed Owner final decisions JSON when validating')
    ap.add_argument('--out-dir',type=Path,required=True)
    arg=ap.parse_args()
    try:
        if arg.mode=='prepare':
            names=('first_pack','first_decisions','first_safe','second_pack','second_decisions',
                   'second_validated_dir','third_pack','third_decisions','third_validated_dir')
            require(all(getattr(arg,n) is not None for n in names),'MISSING_FROZEN_SOURCES')
            state=checked_all(*(getattr(arg,n) for n in names))
            report=prepare(state,arg.out_dir)
            report_path=arg.out_dir/'safe/R55_GOLD5_FINAL_EVIDENCE_PREP_SAFE_COUNT_ONLY.json'
        else:
            require(arg.pack is not None and arg.decisions is not None,'MISSING_FINAL_OWNER_FILES')
            report=validate(arg.pack,arg.decisions,arg.out_dir,
                            priority_only=(arg.mode=='validate-priority'))
            report_path=arg.out_dir/'R55_GOLD5_FINAL_EVIDENCE_SAFE_COUNT_ONLY.json'
        print(report['status'])
        print(PREFIX+'_SAFE_RECEIPT='+str(report_path))
    except (fr.Hold,OSError,ValueError,TypeError,KeyError,AssertionError) as exc:
        code=str(exc) if isinstance(exc,fr.Hold) else type(exc).__name__
        print(PREFIX+'_HOLD__'+code,file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':raise SystemExit(main())

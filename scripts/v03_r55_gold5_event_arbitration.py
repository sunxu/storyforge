#!/usr/bin/env python3
"""R55 Gold5: Owner-only, no-job, independent blind event adjudication pipeline.

- Reads ONLY the previously-frozen exposed 20-case R55 Pair/Four/Five reviews.
- Refuses stale/replaced receipts, mapping or CSVs through the existing verifier.
- Groups provisional flags at (case, reply, category), never declares an event proven.
- Gives a NEW adjudicator source text / context without model name or old ratings.
- Keeps unblinded reviewer comments and source mapping COORDINATOR ONLY.
- Validates exact quotations before treating decisions as CONFIRMED.
- Never reads R50; produces only PRIVATE packets and safe aggregate counts.
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

import v03_r55_gold5_owner_unblind as ub
import v03_r55_gold5_review_freeze as fr

CATEGORIES = ('agency', 'hard_fact_or_ban')
VERDICTS = ('CONFIRMED', 'REJECTED', 'HOLD_INSUFFICIENT_EVIDENCE')
SCHEMA = 'storyforge-r55-gold5-event-arbitration-v1'


def must(ok: bool, code: str) -> None:
    if not ok:
        raise fr.Hold(code)


def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def private_write(path: Path, value: object) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write('\n')


def json_file(path: Path, label: str) -> dict:
    fr.valid_private(path, label)
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise fr.Hold(label + '_JSON_BAD') from exc
    must(isinstance(obj, dict), label + '_NOT_OBJECT')
    return obj


def common_source(row: dict) -> dict:
    return {k:row[k] for k in ('故事背景与系统规则','历史对话','当前用户输入')}


def groups_from_frozen(state: dict, maps: list[dict], *, scope: str = 'flagged') -> tuple[list[dict], list[dict], dict]:
    """Construct a one-time random anonymous review with a separate private index.

    `flagged` selects union of arm×case provisional flags across *all three*
    review rounds, NOT automatic factual event dedup. `all` inspects all 100.
    """
    must(scope in ('flagged', 'all'), 'INVALID_SCOPE')
    must(len(maps) == 20, 'MUST_BE_20_CASES')
    observations = defaultdict(list)
    arm_counts = Counter()
    for mode in ub.ROUND_NAMES:
        cfg = {'pair':'pairwise_mapping', 'four':'four_model_mapping', 'five':'five_way_mapping'}[mode]
        agency_col, hard_col = fr.MODES[mode][3:5]
        for idx in range(20):
            mapping = maps[idx][cfg]
            for ri in range(3):
                row = state['rows'][mode][ri][idx]
                for category, col in zip(CATEGORIES,(agency_col,hard_col)):
                    for arm in ub.decode_flag(row[col], mapping, mode):
                        observations[(idx,arm)].append({
                            'category':category,
                            'source_round':mode,
                            'reviewer':ri+1,
                            'evidence_location':f'{mode}:Reviewer_{ri+1:02d}:row_{idx+2}',
                            'verbatim_reviewer_evidence':row['逐事件严重问题证据'],
                            'verbatim_preference_reason':row['偏好理由与可见原文证据'],
                        })
                        arm_counts[(arm,category)]+=1
    if scope == 'all':
        selected = [(i,a) for i in range(20) for a in ub.ALL_ARMS]
    else:
        selected = sorted(observations, key=lambda k:(k[0],ub.ALL_ARMS.index(k[1])))
    must(bool(selected), 'NO_FLAGGED_GROUPS_TO_REVIEW')

    # All 3 rounds must carry the same story rules, dialogue and user input
    # before we may associate their Reviewer flags to a shared response.
    for i in range(20):
        expected = common_source(state['clean']['five'][0][i])
        for mode in ub.ROUND_NAMES:
            for ri in range(3):
                must(common_source(state['clean'][mode][ri][i]) == expected,
                     'CROSS_ROUND_SOURCE_CONTEXT_MISMATCH')

    items=[]
    coordinator=[]
    case_tokens={i:'W'+secrets.token_hex(7) for i in range(20)}
    used=set()
    for idx, arm in selected:
        source=common_source(state['clean']['five'][0][idx])
        five_label=next(lab for lab, src in maps[idx]['five_way_mapping'].items() if src == arm)
        response=state['clean']['five'][0][idx]['回复'+five_label]
        must(hash_bytes(response.encode('utf-8')) == maps[idx]['source_reply_sha256'][arm],
             'REPLY_SHA_NOT_MATCH_FROZEN_KEY')
        token='K'+secrets.token_hex(12)
        must(token not in used, 'TOKEN_COLLISION')
        used.add(token)
        items.append({
            'candidate_token':token,
            'case_token':case_tokens[idx],
            '故事背景与系统规则':source['故事背景与系统规则'],
            '历史对话':source['历史对话'],
            '当前用户输入':source['当前用户输入'],
            '匿名候选回复':response,
            'must_evaluate_both_categories':list(CATEGORIES),
            'instructions':'Ignore any previous rankings. Judge only visible context and candidate reply. Do not guess model/reference identity. Evidence quotes must be exact substrings.',
        })
        coordinator.append({
            'candidate_token':token,
            'case_token':case_tokens[idx],
            'case_index_private':idx,
            'source_sample_id_private':maps[idx]['sample_id'],
            'source_arm_private':arm,
            'response_sha256':hash_bytes(response.encode('utf-8')),
            'flag_observations_UNADJUDICATED':observations.get((idx,arm),[]),
        })
    must(len({e['candidate_token'] for e in items})==len(items), 'DUPLICATE_TOKEN')
    safe={
        'schema':SCHEMA+'-safe-prep-v1',
        'status':'R55_GOLD5_ADJUDICATION_PRIVATE_PACK_PREPARED__NO_CONFIRMED_EVENTS__NO_R50',
        'scope':scope,
        'source_unique_cases':20,
        'stories_exposed':2,
        'arbitration_items':len(items),
        'flagged_case_arm_groups':len(observations),
        'flagged_reviewer_case_arm_category_marks':sum(arm_counts.values()),
        'selected_items_with_preexisting_flags':sum((i,a) in observations for i,a in selected),
        'model_source_reveal_to_arbitrator':False,
        'original_gold_is_not_a_model':True,
        'old_development_set_only':True,
        'r50_accessed':False,
        'gpu_job_started':False,
        'training':False,
        'model_promoted':False,
        'adjudication_completed':False,
        'no_case_identifiers_or_story_text_in_safe_receipt':True,
    }
    return items,coordinator,safe


def prepare(state: dict, output_dir: Path, scope: str = 'flagged', *, pins: dict | None = ub.OWNER_PINS) -> dict:
    maps,digest=ub.validate_key(state,pins=pins)
    items,coordinator,safe=groups_from_frozen(state,maps,scope=scope)
    output_dir=output_dir.expanduser().resolve()
    fr.outside_git(output_dir)
    must(not output_dir.exists() and not output_dir.is_symlink(), 'OUTPUT_DIR_ALREADY_EXISTS')
    output_dir.mkdir(parents=True,mode=0o700,exist_ok=False)
    (output_dir/'reviewers').mkdir(mode=0o700)
    (output_dir/'coordinator').mkdir(mode=0o700)
    (output_dir/'safe').mkdir(mode=0o700)
    # List order is unpredictable independent of case/model order.
    secrets.SystemRandom().shuffle(items)
    private_write(output_dir/'reviewers'/'R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json',{
        'schema':SCHEMA+'-blind-items-v1',
        'status':'UNSCORED__SOURCE_IDENTITIES_HIDDEN',
        'items':items,
    })
    private_write(output_dir/'coordinator'/'R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json',{
        'schema':SCHEMA+'-coordinator-index-v1',
        'source_key_sha256':digest,
        'source_prep_sha256':state['prep_hash'],
        'source_freeze_receipt_sha256':state['receipt_hashes'],
        'records':coordinator,
        'warning':'Private model identity mapping and verbatim reviewer evidence. Never distribute to adjudicators or Git.',
    })
    blank=[]
    for it in items:
        blank.append({
            'candidate_token':it['candidate_token'],
            'agency':{'verdict':'','candidate_quote':'','context_quote':'','rationale':''},
            'hard_fact_or_ban':{'verdict':'','candidate_quote':'','context_quote':'','rationale':''},
        })
    private_write(output_dir/'reviewers'/'R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json',{
        'schema':SCHEMA+'-adjudicator-decisions-v1',
        'items':blank,
    })
    b=output_dir/'reviewers'/'R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json'
    c=output_dir/'coordinator'/'R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json'
    safe['blind_items_sha256']=hash_bytes(b.read_bytes())
    safe['coordinator_index_sha256']=hash_bytes(c.read_bytes())
    safe['owner_unblind_source_prep_sha256']=state['prep_hash']
    safe['original_freeze_receipt_sha256']=state['receipt_hashes']
    private_write(output_dir/'safe'/'R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json',safe)
    return safe


def verify_decisions(pack: Path, submitted_path: Path, out: Path) -> dict:
    pack=pack.expanduser().resolve()
    receipt=json_file(pack/'safe'/'R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json','ADJ_PREP_SAFE')
    must(receipt.get('schema')==SCHEMA+'-safe-prep-v1'
         and receipt.get('status')=='R55_GOLD5_ADJUDICATION_PRIVATE_PACK_PREPARED__NO_CONFIRMED_EVENTS__NO_R50'
         and receipt.get('r50_accessed') is False
         and receipt.get('adjudication_completed') is False,'ADJ_PREP_STATUS_INVALID')
    items_file=pack/'reviewers'/'R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json'
    coord_file=pack/'coordinator'/'R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json'
    fr.valid_private(items_file, 'BLIND_SOURCE')
    fr.valid_private(coord_file, 'COORD_SOURCE')
    must(hash_bytes(items_file.read_bytes())==receipt.get('blind_items_sha256'),'ARBITER_PACKET_HASH_MISMATCH')
    must(hash_bytes(coord_file.read_bytes())==receipt.get('coordinator_index_sha256'),'COORDINATOR_INDEX_HASH_MISMATCH')
    src=json_file(items_file,'BLIND_SOURCE')
    idx=json_file(coord_file,'COORD_SOURCE')
    decisions=json_file(submitted_path,'ARBITER_DECISIONS')
    must(src.get('schema')==SCHEMA+'-blind-items-v1'
         and idx.get('schema')==SCHEMA+'-coordinator-index-v1'
         and decisions.get('schema')==SCHEMA+'-adjudicator-decisions-v1','DECISION_SCHEMAS_CHANGED')
    items=src.get('items')
    records=idx.get('records')
    entries=decisions.get('items')
    must(isinstance(items,list) and isinstance(records,list) and isinstance(entries,list)
         and len(items)==len(records)==len(entries)==receipt['arbitration_items'], 'DECISION_COUNTS_DIFFER')
    items_by_token={it['candidate_token']:it for it in items}
    records_by_token={it['candidate_token']:it for it in records}
    must(len(items_by_token)==len(items) and len(records_by_token)==len(records), 'DUPLICATE_SOURCE_TOKENS')
    must(set(items_by_token)==set(records_by_token),'SOURCE_INDEX_TOKEN_SET_DIFFERS')
    decisions_by_token={e['candidate_token']:e for e in entries}
    must(len(decisions_by_token)==len(entries)
         and set(decisions_by_token)==set(items_by_token),'DECISION_TOKEN_SET_MISMATCH')
    decisions_by_arm=defaultdict(lambda:Counter())
    private_results=[]
    for token,task in items_by_token.items():
        meta=records_by_token[token]
        must(task['case_token']==meta['case_token'], 'SOURCE_CASE_TOKEN_MISMATCH')
        must(hash_bytes(task['匿名候选回复'].encode('utf-8'))==meta['response_sha256'], 'SOURCE_REPLY_HASH_MISMATCH')
        case_context='\n'.join(task[k] for k in ('故事背景与系统规则','历史对话','当前用户输入'))
        decision=decisions_by_token[token]
        must(set(decision)=={'candidate_token',*CATEGORIES}, 'DECISION_FIELDS_CHANGED')
        decisions_out={}
        for category in CATEGORIES:
            d=decision[category]
            must(isinstance(d,dict) and set(d)=={'verdict','candidate_quote','context_quote','rationale'},'VERDICT_FIELDS_CHANGED')
            v=d['verdict']
            must(v in VERDICTS, 'UNFILLED_OR_INVALID_VERDICT')
            must(isinstance(d['rationale'],str) and len(d['rationale'].strip())>=12,'MISSING_VERDICT_REASON')
            if v=='CONFIRMED':
                must(isinstance(d['candidate_quote'],str) and len(d['candidate_quote'].strip())>=2
                     and d['candidate_quote'] in task['匿名候选回复'],'CONFIRMED_CANDIDATE_QUOTE_NOT_SOURCE_EXACT')
                must(isinstance(d['context_quote'],str) and len(d['context_quote'].strip())>=2
                     and d['context_quote'] in case_context,'CONFIRMED_CONTEXT_QUOTE_NOT_SOURCE_EXACT')
            else:
                must(isinstance(d['candidate_quote'],str) and isinstance(d['context_quote'],str), 'INVALID_OPTIONAL_QUOTES')
            decisions_by_arm[(category,meta['source_arm_private'])][v]+=1
            decisions_out[category]=d
        private_results.append({**{k:meta[k] for k in ('candidate_token','case_token','case_index_private','source_sample_id_private','source_arm_private','response_sha256')}, 'decisions':decisions_out})
    # This is a targeted flagged-source audit; denominators are selected items,
    # not per-model population error rates unless scope=all and all 100 inspected.
    safe={
        'schema':SCHEMA+'-safe-decision-count-v1',
        'status':'R55_GOLD5_ARBITRATION_DECISIONS_SYNTAX_AND_EXACT_QUOTES_VALIDATED__DEV_ONLY__NO_R50',
        'adjudication_items_checked':len(items),
        'categories_per_item':2,
        'scope':receipt['scope'],
        'verdict_counts_by_category_and_arm':{
            cat:{arm:dict(decisions_by_arm[(cat,arm)]) for arm in ub.ALL_ARMS}
            for cat in CATEGORIES},
        'not_certified_reviewer_independence':True,
        'verdict_semantic_correctness_not_automatically_verified':True,
        'do_not_treat_targeted_counts_as_unbiased_error_rates':True,
        'model_promoted':False,
        'r50_accessed':False,
        'gpu_job_started':False,
        'training':False,
        'private_contents_in_safe_report':False,
        'blind_items_sha256':receipt['blind_items_sha256'],
        'decisions_sha256':hash_bytes(submitted_path.read_bytes()),
    }
    out=out.expanduser().resolve()
    fr.outside_git(out)
    must(not out.exists() and not out.is_symlink(),'OUTPUT_DIR_ALREADY_EXISTS')
    out.mkdir(parents=True,mode=0o700,exist_ok=False)
    private_write(out/'R55_GOLD5_ARBITRATION_DECISIONS_PRIVATE.json',{'schema':SCHEMA+'-validated-decisions-private-v1','items':private_results})
    private_write(out/'R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json',safe)
    return safe


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=('prepare','validate'),required=True)
    ap.add_argument('--pack',type=Path,required=True,help='owner-pack-v2 for prepare; prepared arbitration pack for validate')
    ap.add_argument('--pair-dir',type=Path)
    ap.add_argument('--four-dir',type=Path)
    ap.add_argument('--five-dir',type=Path)
    ap.add_argument('--decisions',type=Path)
    ap.add_argument('--scope',choices=('flagged','all'),default='flagged')
    ap.add_argument('--out-dir',type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.mode=='prepare':
            must(all((args.pair_dir,args.four_dir,args.five_dir)), 'MISSING_FROZEN_ROUND_DIRS')
            verified=ub.verify(args.pack,{'pair':args.pair_dir,'four':args.four_dir,'five':args.five_dir})
            report=prepare(verified,args.out_dir,args.scope)
            print(report['status'])
            print('R55_GOLD5_ARBITRATION_SAFE_COUNT_ONLY='+str(args.out_dir/'safe'/'R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json'))
        else:
            must(args.decisions is not None, 'MISSING_DECISIONS')
            safe=verify_decisions(args.pack,args.decisions,args.out_dir)
            print(safe['status'])
            print('R55_GOLD5_ARBITRATION_SAFE_COUNT_ONLY='+str(args.out_dir/'R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json'))
    except (fr.Hold, OSError, TypeError, ValueError, KeyError, AssertionError) as exc:
        code=str(exc) if isinstance(exc,fr.Hold) else type(exc).__name__
        print('R55_GOLD5_ARBITRATION_HOLD__'+code,file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())

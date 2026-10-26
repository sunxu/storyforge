#!/usr/bin/env python3
"""Owner-only R55 DEV Gold5 v2 post-freeze unblind: 3 distinct comparisons.

Stdlib, CPU-only, read-only source inputs; does not contact networks, HF or R50.
Validate all 9 scored CSVs against pristine sources, freeze receipts, and
Owner-reported digests BEFORE accessing a private identity key.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys

import v03_r55_gold5_review_freeze as fr

ROUND_NAMES = ('pair', 'four', 'five')
MODEL_ARMS = ('base', 'v01', 'v02', 'v03')
ALL_ARMS = ('gold', *MODEL_ARMS)
KEY_NAME = 'R55_GOLD5_COORDINATOR_KEY_V2_PRIVATE.json'
SCHEMA = 'storyforge-r55-gold5-v2-owner-unblind-aggregate-v1'

# Frozen values read directly from Owner count-only receipts in this conversation.
# No prompt, response, private case identifier, or identity mapping is embedded.
OWNER_PINS = {
    'prep': '6476da25e7d6b043a7bec3d413bfc75885c8571c188f318e3a4eb523888bdaa4',
    'key': 'fc328688fac957c849d822d82db841479105afb0c885b48b381b1a270f9f3334',
    'pair': (
        '00fb53854b364aeed7c7036e64e999543c329503758a40a2761b8ffea87601de',
        'e7de4f91ea21fce5a190ac70d7bd552e59e70db68857d2151f6ace3fcdb20d54',
        'f800281f9567d50f8c9d5bc9e88f809ba88a99d5a8e13207af8e622cea6cdef6',
    ),
    'four': (
        '12d483503101804eee2bad9bedc1c10d779c203a391c9da9a00eff5f7d3bc21b',
        '8bcb9544bc6f4ea4c30b64986f4a87cc34035dc39ed0cb37c28f220226a7add0',
        '1eb51a10d5aa53dc70f7e3d145c1d1ec19974b69d2e34779565d2d24857b3db6',
    ),
    'five': (
        '3ac83edc576c3c2fa2956b2ea4e611bb6ae9772bf074a50de91418c579e48606',
        '9e47b51167ad8b45b6a844e612d6acd42ef4574022a711961ce2095a60ec8be4',
        'b6bca635c9bded309b1234989d7f59cecb5ec4dc22b555c678afdc5610c44bfe',
    ),
    'flag_presence': {'pair': 32, 'four': 50, 'five': 50},
}


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def must(ok: bool, code: str) -> None:
    if not ok:
        raise fr.Hold(code)


def read_json_file(path: Path, label: str) -> dict:
    fr.valid_private(path, label)
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise fr.Hold(f'{label}_INVALID_JSON') from exc
    must(isinstance(value, dict), f'{label}_NOT_OBJECT')
    return value


def review_filename(round_name: str, i: int) -> str:
    return f'R55_GOLD5_{round_name.upper()}_V2_Reviewer_{i:02d}_FROZEN_PRIVATE.csv'


def pristine_filename(round_name: str, i: int) -> str:
    return f'R55_GOLD5_{round_name.upper()}_V2_Reviewer_{i:02d}_PRIVATE.csv'


def verify(pack: Path, frozen: dict[str, Path], *, pins: dict | None = OWNER_PINS):
    pack = pack.expanduser().resolve()
    dirs = {n: Path(frozen[n]).expanduser().resolve() for n in ROUND_NAMES}
    prep_file = pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json'
    prep = fr.check_prep(pack)
    prep_hash = h(prep_file.read_bytes())
    if pins is not None:
        must(prep_hash == pins['prep'], 'OWNER_PREP_SHA_MISMATCH')
    clean_rows = {k: [] for k in ROUND_NAMES}
    scored_rows = {k: [] for k in ROUND_NAMES}
    receipts, receipt_hashes = {}, {}
    case_ids = None
    expected_counts = {'pair': 720, 'four': 1440, 'five': 1800}
    for mode in ROUND_NAMES:
        directory = dirs[mode]
        must(directory.is_dir() and not directory.is_symlink(), 'FROZEN_DIR_MISSING_OR_SYMLINK')
        rp = directory/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
        receipt = read_json_file(rp, 'FREEZE_RECEIPT')
        receipts[mode] = receipt
        receipt_hashes[mode] = h(rp.read_bytes())
        must(receipt.get('schema') == 'storyforge-r55-gold5-v2-round-freeze-count-only-v1'
             and receipt.get('status') == f'R55_GOLD5_V2_{mode.upper()}_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50'
             and receipt.get('round') == mode and receipt.get('case_count') == 20
             and receipt.get('reviewer_count') == 3
             and receipt.get('ratings_verified') == expected_counts[mode]
             and receipt.get('expected_rating_cells') == expected_counts[mode]
             and receipt.get('source_prep_receipt_sha256') == prep_hash
             and receipt.get('unblinding_performed') is False
             and receipt.get('r50_accessed') is False
             and receipt.get('development_only') is True
             and receipt.get('gpu_job') is False
             and receipt.get('model_promotion') is False,
             f'{mode.upper()}_FREEZE_METADATA_MISMATCH')
        flags = 0
        for ri in range(1, 4):
            original = pack/'reviewers'/pristine_filename(mode, ri)
            target = directory/review_filename(mode, ri)
            fr.valid_private(original, 'PRISTINE')
            fr.valid_private(target, 'FROZEN_REVIEW')
            pristine = original.read_bytes()
            completed = target.read_bytes()
            must(h(pristine) == prep['reviewer_private_csv_sha256'].get(original.name),
                 f'{mode.upper()}_PRISTINE_SHA_MISMATCH')
            expected_digest = receipt.get('reviewer_scored_sha256', {}).get(f'Reviewer_{ri:02d}')
            must(h(completed) == expected_digest, f'{mode.upper()}_FREEZE_CSV_SHA_MISMATCH')
            if pins is not None:
                must(h(completed) == pins[mode][ri-1], f'{mode.upper()}_OWNER_SCORED_SHA_MISMATCH')
            n, v = fr.check_scored_file(pristine, completed, mode)
            must(n == 20 * len(fr.MODES[mode][1]) * len(fr.DIMS),
                 f'{mode.upper()}_RATING_COUNT_MISMATCH')
            flags += v
            _, p_rows = fr.parse_csv(pristine)
            _, d_rows = fr.parse_csv(completed)
            pristine_ids = tuple(row['样本编号'] for row in p_rows)
            if case_ids is None:
                case_ids = pristine_ids
            must(pristine_ids == case_ids, 'CASE_ORDER_MISMATCH_BETWEEN_ROUNDS')
            clean_rows[mode].append(p_rows)
            scored_rows[mode].append(d_rows)
        must(flags == receipt.get('reviewer_case_flag_presence_count'),
             f'{mode.upper()}_FLAG_PRESENCE_COUNT_MISMATCH')
        if pins is not None:
            must(flags == pins['flag_presence'][mode], f'{mode.upper()}_OWNER_FLAG_PRESENCE_MISMATCH')
    return {'pack':pack, 'prep_hash':prep_hash, 'prep':prep,
            'rows': scored_rows, 'clean': clean_rows, 'receipts': receipts,
            'receipt_hashes':receipt_hashes, 'case_ids':case_ids,
            'frozen_dirs':dirs}


def validate_key(verified: dict, *, pins: dict | None = OWNER_PINS):
    file = verified['pack']/'coordinator'/'private'/KEY_NAME
    fr.valid_private(file, 'PRIVATE_IDENTITY_KEY')
    raw = file.read_bytes()
    digest = h(raw)
    must(digest == verified['prep'].get('coordinator_private_key_sha256'),
         'COORDINATOR_KEY_PREP_SHA_MISMATCH')
    if pins is not None:
        must(digest == pins['key'], 'COORDINATOR_KEY_OWNER_SHA_MISMATCH')
    try:
        key = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise fr.Hold('COORDINATOR_KEY_INVALID_JSON') from exc
    must(key.get('schema') == 'storyforge-r55-gold5-v2-coordinator-v1'
         and key.get('source_cases') == 20
         and key.get('model_generation') is False
         and key.get('r50_accessed') is False, 'COORDINATOR_KEY_METADATA_MISMATCH')
    maps = key.get('identity_maps')
    must(isinstance(maps,list) and len(maps)==20, 'COORDINATOR_KEY_WRONG_CASES')
    for i, mapping in enumerate(maps):
        must(mapping.get('sample_id') == verified['case_ids'][i], 'KEY_CASE_ORDER_MISMATCH')
        source = mapping.get('source_reply_sha256')
        must(isinstance(source,dict) and set(source)==set(ALL_ARMS), 'KEY_SOURCE_RESPONSE_HASH_SET_MISMATCH')
        cfg = {
            'pair': ('pairwise_mapping',('v02','v03')),
            'four': ('four_model_mapping',MODEL_ARMS),
            'five': ('five_way_mapping',ALL_ARMS),
        }
        for mode,(key_field, arms) in cfg.items():
            expected_labels = fr.MODES[mode][1]
            arm_map = mapping.get(key_field)
            must(isinstance(arm_map,dict) and set(arm_map) == set(expected_labels)
                 and sorted(arm_map.values()) == sorted(arms), f'KEY_{mode.upper()}_ARM_MAP_INVALID')
            for j in range(3):
                row = verified['clean'][mode][j][i]
                for label, arm in arm_map.items():
                    text_hash = h(row[f'回复{label}'].encode('utf-8'))
                    must(text_hash == source[arm], f'KEY_{mode.upper()}_SOURCE_REPLY_SHA_MISMATCH')
        must(isinstance(mapping.get('prompt_sha256'),str)
             and len(mapping['prompt_sha256'])==64, 'KEY_PROMPT_SHA_FORMAT_BAD')
    return maps, digest


def decode_flag(raw: str, label_map: dict[str,str], mode: str) -> tuple[str, ...]:
    raw = raw.strip()
    if raw == 'NONE':
        return ()
    labels = ('LEFT','RIGHT') if mode=='pair' and raw=='BOTH' else raw.split(',') if mode!='pair' else (raw,)
    return tuple(label_map[l] for l in labels)


def tally(verified: dict, key_maps: list[dict]):
    summary, private_cases = {}, []
    cfg = {'pair':'pairwise_mapping','four':'four_model_mapping','five':'five_way_mapping'}
    for mode in ROUND_NAMES:
        prefcol=fr.MODES[mode][2]
        flag1,flag2=fr.MODES[mode][3:]
        dims=fr.DIMS
        preference_votes=Counter()
        case_best=Counter()
        totals=defaultdict(lambda: defaultdict(int))
        denom=defaultdict(lambda: defaultdict(int))
        flagged_reviewer_arms={'agency':Counter(),'hard_fact_or_ban':Counter()}
        case_flaggers={'agency':defaultdict(set),'hard_fact_or_ban':defaultdict(set)}
        details=[]
        for i in range(20):
            mapping=key_maps[i][cfg[mode]]
            per_case=Counter()
            case_record={'sample_id':key_maps[i]['sample_id'],'reviews':[]}
            for ri in range(3):
                row=verified['rows'][mode][ri][i]
                label=row[prefcol].strip()
                arm=mapping.get(label,'TIE') if label!='TIE' else 'TIE'
                per_case[arm]+=1
                preference_votes[arm]+=1
                for dim in dims:
                    for letter, source in mapping.items():
                        score=int(row[f'{dim}·{letter}'])
                        totals[source][dim]+=score
                        denom[source][dim]+=1
                agency=decode_flag(row[flag1],mapping,mode)
                hard=decode_flag(row[flag2],mapping,mode)
                for name, items in [('agency',agency),('hard_fact_or_ban',hard)]:
                    for source in items:
                        flagged_reviewer_arms[name][source]+=1
                        case_flaggers[name][source].add(i)
                case_record['reviews'].append({
                    'reviewer':ri+1, 'best':arm,
                    'agency_flagged_arms':sorted(agency),
                    'hard_fact_or_ban_flagged_arms':sorted(hard),
                    'scores_by_arm':{source:{dim:int(row[f'{dim}·{letter}']) for dim in dims}
                                     for letter,source in mapping.items()},
                    'evidence_location':f'{mode}:Reviewer_{ri+1:02d}:row_{i+2}',
                })
            leaders=[a for a,n in per_case.items() if n>=2]
            decision=leaders[0] if len(leaders)==1 else 'SPLIT_NO_MAJORITY'
            case_best[decision]+=1
            case_record['majority']=decision
            details.append(case_record)
        means={arm:{dim:round(totals[arm][dim]/denom[arm][dim],6) for dim in dims}
               for arm in sorted(totals)}
        overall={arm:round(sum(totals[arm].values())/sum(denom[arm].values()),6) for arm in sorted(totals)}
        total_reviewer_arm_flags={name:dict(sorted(counts.items())) for name,counts in flagged_reviewer_arms.items()}
        provisional_case_flags={name:{arm:len(ids) for arm,ids in sorted(v.items())}
                               for name,v in case_flaggers.items()}
        summary[mode]={
            'reviewer_preference_votes_including_ties':dict(sorted(preference_votes.items())),
            'twenty_case_majority_or_split':dict(sorted(case_best.items())),
            'six_axis_means_1_to_5':means,
            'overall_mean_six_1_to_5':overall,
            'UNADJUDICATED_flagged_reviewer_case_arm_marks':total_reviewer_arm_flags,
            'UNADJUDICATED_cases_with_any_reviewer_flag_by_arm':provisional_case_flags,
        }
        private_cases.append({'round':mode,'case_results':details})
    p=summary['pair']; m=p['twenty_case_majority_or_split']; pair_non_tie=m.get('v02',0)+m.get('v03',0)
    p['per_case_v03_win_fraction_excluding_all_ties_and_splits']=(
        round(m.get('v03',0)/pair_non_tie,6) if pair_non_tie else None)
    p['non_tie_case_majority_denominator']=pair_non_tie
    return summary, private_cases


def safe_write(path: Path, payload: dict) -> None:
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(payload,f,ensure_ascii=False,indent=2,sort_keys=True)
        f.write('\n')


def unblind(verified: dict, out: Path, *, pins: dict | None = OWNER_PINS):
    maps,key_digest=validate_key(verified,pins=pins)
    rounds,cases=tally(verified,maps)
    out=out.expanduser().resolve()
    fr.outside_git(out)
    must(not out.exists() and not out.is_symlink(), 'OUTPUT_DIR_ALREADY_EXISTS')
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={
        'schema':SCHEMA,
        'status':'R55_GOLD5_V2_OWNER_ONLY_UNBLIND_AGGREGATED__DEVELOPMENT_ONLY__NO_R50',
        'case_count':20,'world_count_historical':2,'reviewer_count':3,
        'round_rating_cells':{'pair':720,'four':1440,'five':1800},
        'total_verified_rating_cells':3960,
        'source_prep_receipt_sha256':verified['prep_hash'],
        'freeze_receipt_sha256':verified['receipt_hashes'],
        'frozen_csv_sha256':{mode:dict(verified['receipts'][mode]['reviewer_scored_sha256']) for mode in ROUND_NAMES},
        'coordinator_key_sha256_verified':key_digest,
        'results':rounds,
        'status_constraints':{
            'old_exposed_development_questions_only':True,
            'reviewer_votes_are_not_independent_test_cases':True,
            'flag_markings_are_NOT_confirmed_errors':True,
            'adjudication_complete':False,
            'reviewer_independence_human_attested_not_technically_proven':False,
            'model_promoted':False,'r50_accessed':False,
            'gpu_job_started':False,'model_inference_executed':False,
            'no_raw_private_text_or_case_ids_in_safe_report':True,
        },
        'decision':'CANDIDATE_GO_NO_GO_REVIEW_PENDING_HARD_EVENT_ADJUDICATION',
    }
    safe_write(out/'R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json',report)
    safe_write(out/'R55_GOLD5_V2_OWNER_UNBLIND_CASE_PRIVATE.json',{
        'schema':'storyforge-r55-gold5-v2-owner-private-case-review-v1',
        'warning':'Private per-case identifiers; do NOT commit or share in ordinary channels',
        'rounds':cases,
        'source_aggregate_sha256':h((out/'R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json').read_bytes()),
    })
    return report


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pack',type=Path,required=True)
    for mode in ROUND_NAMES:
        ap.add_argument('--'+mode+'-dir',type=Path,required=True)
    ap.add_argument('--mode',choices=['verify','unblind'],required=True)
    ap.add_argument('--out-dir',type=Path,required=True)
    a=ap.parse_args()
    try:
        state=verify(a.pack,{mode:getattr(a,mode+'_dir') for mode in ROUND_NAMES})
        if a.mode=='verify':
            print('R55_GOLD5_V2_ALL_3_ROUNDS_3960_RATINGS_VERIFIED__KEY_NOT_READ__NO_R50')
        else:
            report=unblind(state,a.out_dir)
            print(report['status'])
            print('R55_GOLD5_V2_OWNER_SAFE_AGGREGATE='+str(a.out_dir/'R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json'))
            print('R55_GOLD5_V2_CASE_LEVEL_OUTPUT_STAYS_PRIVATE')
    except (fr.Hold, OSError, ValueError, TypeError, KeyError, AssertionError, ZeroDivisionError) as e:
        code=str(e) if isinstance(e,fr.Hold) else type(e).__name__
        print('R55_GOLD5_V2_OWNER_UNBLIND_HOLD__'+code,file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())

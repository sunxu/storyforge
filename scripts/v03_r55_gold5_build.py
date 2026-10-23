#!/usr/bin/env python3
"""R55: fail-closed five-answer blind DEV pack, original Gold + 4 frozen models.

Stdlib only; uses existing R47/R48 canonical validators, no R50, no model calls.
All generated tasks, prompts, answer map, and per-case hashes are PRIVATE.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

# Reuse two audited, Git-versioned source validators verbatim.
try:
    from v02_r47_eval_validate import validate_prompts, validate_responses
    from v02_r48_four_arm_build import check_r47, read_gold, sha, CANONICAL_TEST_SHA256
except ImportError as ex:
    raise SystemExit("HOLD_R55_GOLD5_ORIGINAL_R47_R48_VALIDATORS_MISSING") from ex

MODEL_ARMS = ("base", "v01", "v02", "v03")
ALL_ARMS = ("gold", *MODEL_ARMS)
R55_OUTPUT_SHA256 = "80586435b4b8dbe361d2e76d746a1e0e88154d08525d63720562810efa186557"
R55_REPORT_SHA256 = "924404daa12ed5886a879e4445b7995350228f559995f646d480859f76c4fd64"
EXPECTED_PROMPTS_BLOB = "ac301a61d4130369a83dc67ac02aa2d8dda9e82b"
EXPECTED_MANIFEST_BLOB = "f4e39196c6aa0a87b095d7de5cae4acd8b2fca63"
DIMS = ("剧情连续性", "角色一致性", "指令遵循", "文学表现力", "互动推进", "玩家自主权")

class Hold(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Hold(reason)


def hash_text(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def ensure_regular(p, label):
    require(p.is_file() and not p.is_symlink(), "MISSING_OR_SYMLINK_"+label)


def ensure_outside_git(path):
    out = path.expanduser().resolve()
    for p in (out, *out.parents):
        require(not (p / '.git').exists(), "PRIVATE_OUTPUT_WITHIN_GIT_REPO")


def git_blob_sha(data):
    head = b'blob ' + str(len(data)).encode() + b'\0'
    return hashlib.sha1(head + data).hexdigest()


def role_context(msgs):
    background = '\n\n'.join(f"【{m['role']}】\n{m['content']}" for m in msgs if m['role'] in ('system','developer'))
    history = '\n\n'.join(f"【{m['role']}】\n{m['content']}" for m in msgs[:-1] if m['role'] not in ('system','developer'))
    return background, history, msgs[-1]['content']


def load_exact_sources(a):
    inputs = {
        'compiled_test': a.compiled_test, 'prompts': a.prompts,
        'manifest': a.manifest, 'r47_report': a.r47_report,
        'base': a.base, 'v01': a.v01, 'v02': a.v02,
        'v03': a.v03, 'r55_report': a.r55_report,
    }
    for label, p in inputs.items():
        ensure_regular(p, label.upper())
    require(sha(a.compiled_test) == CANONICAL_TEST_SHA256, 'CANONICAL_GOLD_TEST_SHA_MISMATCH')
    require(git_blob_sha(a.prompts.read_bytes()) == EXPECTED_PROMPTS_BLOB, 'GIT_PROMPTS_BLOB_MISMATCH')
    require(git_blob_sha(a.manifest.read_bytes()) == EXPECTED_MANIFEST_BLOB, 'GIT_MANIFEST_BLOB_MISMATCH')
    require(sha(a.v03) == R55_OUTPUT_SHA256, 'FROZEN_R55_V03_RESPONSES_SHA_MISMATCH')
    require(sha(a.r55_report) == R55_REPORT_SHA256, 'FROZEN_R55_REPORT_SHA_MISMATCH')
    # R55 report hash is pinned, so cannot silently replace the legacy output.
    prompts, entries = validate_prompts(a.prompts, a.manifest)
    require(len(prompts) == 20 and len(entries) == 20, 'NOT_20_PROMPTS')
    gold = read_gold(a.compiled_test, prompts)
    require(len(gold) == 20, 'NOT_20_GOLD_MATCHES')
    r47 = check_r47(
        a.r47_report, a.prompts, a.manifest,
        {'base': a.base, 'v01': a.v01, 'v02': a.v02},
        prompts
    )
    v03 = validate_responses(a.v03, prompts)
    require(len(v03) == 20, 'NOT_20_V03_RESPONSES')
    texts = {'gold': gold, **r47, 'v03': v03}
    require(set(texts) == set(ALL_ARMS), 'WRONG_FIVE_ARM_SET')
    require(all(len(texts[k]) == 20 for k in ALL_ARMS), 'WRONG_ARM_RESPONSE_COUNT')
    for i in range(20):
        require(all(isinstance(texts[k][i], str) and texts[k][i].strip() for k in ALL_ARMS),
                'EMPTY_OR_INVALID_RESPONSE')
    return prompts, entries, texts, inputs


def private_csv(path, fields, rows):
    # All generated filenames are PRIVATE, including reviewer CSV.
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(path, 0o600)


def private_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    os.chmod(path, 0o600)


def make_package(prompts, entries, answers, inputs, output):
    require(len(prompts) == len(entries) == 20, 'WRONG_SOURCE_LENGTH')
    require(set(answers) == set(ALL_ARMS), 'WRONG_FIVE_ARM_SET')
    # Fail closed before creating folders, never overwrite.
    ensure_outside_git(output)
    require(not output.exists() and not output.is_symlink(), 'PRIVATE_OUTPUT_ALREADY_EXISTS')
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    reviewers = output / 'reviewers'
    private = output / 'coordinator' / 'private'
    reviewers.mkdir(mode=0o700)
    private.mkdir(parents=True, mode=0o700)
    five_rows, pair_rows, case_keys = [], [], []
    for i, (prompt, meta) in enumerate(zip(prompts, entries, strict=True)):
        all_order = list(ALL_ARMS)
        secrets.SystemRandom().shuffle(all_order)
        five_map = dict(zip('ABCDE', all_order, strict=True))
        porder = ['v02', 'v03']
        secrets.SystemRandom().shuffle(porder)
        pmap = dict(zip(('LEFT','RIGHT'), porder, strict=True))
        sample_id = meta['sample_id']
        b, h, user = role_context(prompt['messages'])
        common = {'样本编号': sample_id, '故事背景与系统规则': b,
                  '历史对话': h, '当前用户输入': user}
        five = {**common, **{f'回复{letter}': answers[arm][i]
                             for letter,arm in five_map.items()}}
        pair = {**common, '回复LEFT': answers[pmap['LEFT']][i],
                '回复RIGHT': answers[pmap['RIGHT']][i]}
        five_rows.append(five)
        pair_rows.append(pair)
        case_keys.append({
            'sample_id': sample_id, 'prompt_sha256': meta['prompt_sha256'],
            'five_way_mapping': five_map, 'pairwise_mapping': pmap,
            'source_reply_sha256': {arm: hash_text(answers[arm][i]) for arm in ALL_ARMS},
        })
    cf = ('样本编号', '故事背景与系统规则', '历史对话', '当前用户输入')
    five_source = (*cf, *(f'回复{x}' for x in 'ABCDE'))
    pair_source = (*cf, '回复LEFT', '回复RIGHT')
    five_fields = (*five_source, '整体最佳(A/B/C/D/E/TIE)',
                   '四模型最佳(请填写对应匿名字母或TIE)',
                   '偏好理由与可见原文证据',
                   '严重玩家自主权问题(可多字母/NONE)',
                   '明确禁句或硬事实问题(可多字母/NONE)',
                   '逐事件严重问题证据',
                   *(f'{dim}·{x}' for dim in DIMS for x in 'ABCDE'))
    pair_fields = (*pair_source, '偏好(LEFT/RIGHT/TIE)',
                   '偏好理由与可见原文证据',
                   '严重玩家自主权问题(LEFT/RIGHT/BOTH/NONE)',
                   '明确禁句或硬事实问题(LEFT/RIGHT/BOTH/NONE)',
                   '逐事件严重问题证据',
                   *(f'{dim}·{x}' for dim in DIMS for x in ('LEFT','RIGHT')))
    # Different reviewers get IDENTICAL answer assignments per item: no key drift,
    # but distinct reviewer scores freeze separately. Pairwise first recommended.
    for i in range(1,4):
        private_csv(reviewers/f'R55_GOLD5_PAIR_Reviewer_{i:02d}_PRIVATE.csv', pair_fields, pair_rows)
        private_csv(reviewers/f'R55_GOLD5_FIVE_Reviewer_{i:02d}_PRIVATE.csv', five_fields, five_rows)
    private_json(private/'R55_GOLD5_COORDINATOR_KEY_PRIVATE.json', {
        'schema':'storyforge-r55-gold5-dev-coordinator-v1',
        'scope':'EXPOSED_20_TWO_WORLDS_DEVELOPMENT_ONLY',
        'source_cases':20, 'identity_maps':case_keys,
        'no_model_generation':True, 'r50_accessed':False,
    })
    src_hashes = {k:sha(path) for k,path in inputs.items()}
    pub = {
        'schema':'storyforge-r55-gold5-dev-count-only-prep-v1',
        'status':'R55_GOLD5_20_EXPOSED_CASES_EXACT_SOURCE_ALIGNED__PRIVATE_BLIND_PACK_CREATED__NO_R50',
        'case_count':20, 'world_count_historical':2,
        'model_reply_count':80, 'original_gold_reply_count':20,
        'five_way_response_count':100,
        'three_reviewers_prepared':3,
        'source_sha256':src_hashes,
        'private_five_key_sha256':sha(private/'R55_GOLD5_COORDINATOR_KEY_PRIVATE.json'),
        'reviewer_private_csv_sha256':{
            file.name:sha(file) for file in sorted(reviewers.glob('*.csv'))},
        'reviews_completed':0, 'new_heldout':False,
        'r50_accessed':False, 'gpu_inference':False,
        'training':False, 'model_promoted':False,
        'original_gold_is_non_model_reference':True,
        'final_seal':False,
        'private_contents_in_receipt':False,
    }
    private_json(output/'R55_GOLD5_PREP_SAFE_COUNT_ONLY.json', pub)
    return pub


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiled-test',type=Path, required=True)
    p.add_argument('--prompts',type=Path, required=True)
    p.add_argument('--manifest',type=Path, required=True)
    p.add_argument('--r47-report',type=Path, required=True)
    for name in MODEL_ARMS:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--r55-report',type=Path, required=True)
    p.add_argument('--output-dir',type=Path, required=True)
    p.add_argument('--mode',choices=('preflight','build'),default='preflight')
    a=p.parse_args()
    try:
        prompts,entries,texts,inputs=load_exact_sources(a)
        if a.mode=='build':
            outcome=make_package(prompts,entries,texts,inputs,a.output_dir)
            print(outcome['status'])
            print('R55_GOLD5_COUNT_ONLY='+str(a.output_dir/'R55_GOLD5_PREP_SAFE_COUNT_ONLY.json'))
            print('R55_GOLD5_PRIVATE_REVIEWERS_STAY_ON_OWNER_MAC')
        else:
            print('R55_GOLD5_20_CASE_FIVE_SOURCE_EXACT_ALIGNMENT_PASS__NO_OUTPUT__NO_GPU')
            print('R55_GOLD5_FROZEN_PROMPT_AND_GOLD_AND_MODEL_BYTES_MATCHED')
    except (Hold,ValueError,OSError,TypeError,KeyError,AssertionError) as err:
        # Do not display exception text from an upstream validator: may contain private paths.
        reason = str(err) if isinstance(err,Hold) else type(err).__name__
        print('R55_GOLD5_HOLD__'+reason,file=sys.stderr)
        raise SystemExit(2) from None

if __name__=='__main__':
    main()

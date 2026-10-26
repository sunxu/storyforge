#!/usr/bin/env python3
"""R55 Gold5 v2: independent blind pair, model-only four, all-five tasks.

Import unchanged v1 strict source checks. Pure stdlib; no GPU/network/model;
new private output directory only, and never read R50.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

import v03_r55_gold5_build as legacy

MODEL_ARMS = legacy.MODEL_ARMS
ALL_ARMS = legacy.ALL_ARMS
DIMS = legacy.DIMS


def make_review_v2(prompts, entries, answers, inputs, output):
    legacy.require(len(prompts) == len(entries) == 20, 'WRONG_SOURCE_LENGTH')
    legacy.require(set(answers) == set(ALL_ARMS), 'WRONG_FIVE_ARM_SET')
    legacy.require(all(len(answers[k]) == 20 for k in ALL_ARMS), 'WRONG_REPLY_COUNT')
    for i in range(20):
        legacy.require(all(isinstance(answers[k][i], str) and answers[k][i].strip()
                           for k in ALL_ARMS), 'EMPTY_RESPONSE')

    output = Path(output).expanduser().resolve()
    legacy.ensure_outside_git(output)
    legacy.require(not output.exists() and not output.is_symlink(), 'PRIVATE_OUTPUT_ALREADY_EXISTS')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    review = output / 'reviewers'
    key_dir = output / 'coordinator' / 'private'
    review.mkdir(mode=0o700)
    key_dir.mkdir(mode=0o700, parents=True)

    pair_rows, four_rows, five_rows, mappings = [], [], [], []
    for i, (prompt, meta) in enumerate(zip(prompts, entries, strict=True)):
        # Each review task uses an independent shuffle. Gold is never in FOUR.
        shuffled_pair = list(('v02', 'v03'))
        shuffled_four = list(MODEL_ARMS)
        shuffled_five = list(ALL_ARMS)
        for group in (shuffled_pair, shuffled_four, shuffled_five):
            secrets.SystemRandom().shuffle(group)
        pair_map = dict(zip(('LEFT', 'RIGHT'), shuffled_pair, strict=True))
        four_map = dict(zip('ABCD', shuffled_four, strict=True))
        five_map = dict(zip('ABCDE', shuffled_five, strict=True))
        bg, history, current = legacy.role_context(prompt['messages'])
        shared = {
            '样本编号': meta['sample_id'], '故事背景与系统规则': bg,
            '历史对话': history, '当前用户输入': current,
        }
        pair_rows.append({**shared, **{f'回复{label}': answers[arm][i]
                                           for label, arm in pair_map.items()}})
        four_rows.append({**shared, **{f'回复{label}': answers[arm][i]
                                           for label, arm in four_map.items()}})
        five_rows.append({**shared, **{f'回复{label}': answers[arm][i]
                                           for label, arm in five_map.items()}})
        mappings.append({
            'sample_id': meta['sample_id'],
            'prompt_sha256': meta['prompt_sha256'],
            'pairwise_mapping': pair_map,
            'four_model_mapping': four_map,
            'five_way_mapping': five_map,
            'source_reply_sha256': {arm: legacy.hash_text(answers[arm][i])
                                    for arm in ALL_ARMS},
        })

    common = ('样本编号', '故事背景与系统规则', '历史对话', '当前用户输入')
    def scores(labels):
        return tuple(f'{d}·{letter}' for d in DIMS for letter in labels)

    pair_cols = (*common, '回复LEFT', '回复RIGHT',
                 '偏好(LEFT/RIGHT/TIE)', '偏好理由与可见原文证据',
                 '严重玩家自主权问题(LEFT/RIGHT/BOTH/NONE)',
                 '明确禁句或硬事实问题(LEFT/RIGHT/BOTH/NONE)',
                 '逐事件严重问题证据', *scores(('LEFT', 'RIGHT')))
    four_cols = (*common, *(f'回复{x}' for x in 'ABCD'),
                 '整体最佳(A/B/C/D/TIE)', '偏好理由与可见原文证据',
                 '严重玩家自主权问题(字母集合/NONE)',
                 '明确禁句或硬事实问题(字母集合/NONE)',
                 '逐事件严重问题证据', *scores('ABCD'))
    five_cols = (*common, *(f'回复{x}' for x in 'ABCDE'),
                 '整体最佳(A/B/C/D/E/TIE)', '偏好理由与可见原文证据',
                 '严重玩家自主权问题(字母集合/NONE)',
                 '明确禁句或硬事实问题(字母集合/NONE)',
                 '逐事件严重问题证据', *scores('ABCDE'))
    assert '四模型最佳' not in ''.join(five_cols)

    for reviewer in range(1, 4):
        legacy.private_csv(review / f'R55_GOLD5_PAIR_V2_Reviewer_{reviewer:02d}_PRIVATE.csv',
                           pair_cols, pair_rows)
        legacy.private_csv(review / f'R55_GOLD5_FOUR_V2_Reviewer_{reviewer:02d}_PRIVATE.csv',
                           four_cols, four_rows)
        legacy.private_csv(review / f'R55_GOLD5_FIVE_V2_Reviewer_{reviewer:02d}_PRIVATE.csv',
                           five_cols, five_rows)

    private_key = key_dir / 'R55_GOLD5_COORDINATOR_KEY_V2_PRIVATE.json'
    legacy.private_json(private_key, {
        'schema': 'storyforge-r55-gold5-v2-coordinator-v1',
        'scope': 'EXPOSED_R47_R48_R55_SAME_20_TWO_WORLDS_DEV_ONLY',
        'identity_maps': mappings, 'source_cases': 20,
        'model_generation': False, 'r50_accessed': False,
    })
    receipt = {
        'schema': 'storyforge-r55-gold5-v2-safe-prep-v1',
        'status': 'R55_GOLD5_V2_THREE_DISTINCT_BLIND_TASKS_PREPARED__DEV_ONLY__NO_R50',
        'source_sha256': {key: legacy.sha(path) for key, path in inputs.items()},
        'case_count': 20, 'world_count_historical': 2,
        'model_reply_count': 80, 'original_gold_reply_count': 20,
        'pairwise_task_count': 20, 'four_model_task_count': 20,
        'five_way_task_count': 20, 'reviewer_count': 3,
        'reviewer_csv_count': 9,
        'reviewer_private_csv_sha256': {p.name: legacy.sha(p) for p in sorted(review.glob('*.csv'))},
        'coordinator_private_key_sha256': legacy.sha(private_key),
        'reviewers_completed': 0,
        'three_distinct_blind_tasks': True,
        'five_way_reviewer_cannot_be_asked_to_identify_gold': True,
        'gold_is_reference_not_fifth_model': True,
        'new_heldout': False, 'r50_accessed': False,
        'gpu_inference': False, 'training': False, 'model_promoted': False,
        'final_seal': False, 'contains_private_source_text': False,
    }
    safe_path = output / 'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json'
    legacy.private_json(safe_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('compiled-test', 'prompts', 'manifest', 'r47-report', 'base', 'v01',
                'v02', 'v03', 'r55-report', 'output-dir'):
        parser.add_argument('--' + arg, type=Path, required=True)
    parser.add_argument('--mode', choices=('preflight', 'build'), default='preflight')
    a = parser.parse_args()
    try:
        prompts, entries, outputs, paths = legacy.load_exact_sources(a)
        if a.mode == 'preflight':
            print('R55_GOLD5_V2_20_EXACT_SOURCES_PASS__NO_OUTPUT__NO_JOB')
        else:
            receipt = make_review_v2(prompts, entries, outputs, paths, a.output_dir)
            print(receipt['status'])
            print('R55_GOLD5_V2_SAFE_RECEIPT=' + str(a.output_dir / 'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json'))
    except (legacy.Hold, ValueError, OSError, TypeError, KeyError, AssertionError) as exc:
        reason = str(exc) if isinstance(exc, legacy.Hold) else type(exc).__name__
        print('R55_GOLD5_V2_HOLD__' + reason, file=sys.stderr)
        raise SystemExit(2) from None

if __name__ == '__main__':
    main()

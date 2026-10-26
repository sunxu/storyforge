#!/usr/bin/env python3
"""R55 Gold5 v2: Owner-local, no-model, fail-closed freeze of 3 scored CSVs.

Verify each reviewer has NOT edited the frozen prompt/answer columns and has
completed every response rating. Copy verified bytes to a NEW private folder.
No R50 or identity map is opened. Only count/hash data appears in stdout/receipt.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys

MODES = {
    'pair': ('PAIR', ('LEFT', 'RIGHT'), '偏好(LEFT/RIGHT/TIE)',
             '严重玩家自主权问题(LEFT/RIGHT/BOTH/NONE)',
             '明确禁句或硬事实问题(LEFT/RIGHT/BOTH/NONE)'),
    'four': ('FOUR', tuple('ABCD'), '整体最佳(A/B/C/D/TIE)',
             '严重玩家自主权问题(字母集合/NONE)',
             '明确禁句或硬事实问题(字母集合/NONE)'),
    'five': ('FIVE', tuple('ABCDE'), '整体最佳(A/B/C/D/E/TIE)',
             '严重玩家自主权问题(字母集合/NONE)',
             '明确禁句或硬事实问题(字母集合/NONE)'),
}
DIMS = ('剧情连续性', '角色一致性', '指令遵循', '文学表现力', '互动推进', '玩家自主权')
COMMON = ('样本编号', '故事背景与系统规则', '历史对话', '当前用户输入')
NOTES = ('偏好理由与可见原文证据', '逐事件严重问题证据')
EXPECTED_STATUS = 'R55_GOLD5_V2_THREE_DISTINCT_BLIND_TASKS_PREPARED__DEV_ONLY__NO_R50'

class Hold(Exception):
    """Safe, privacy-preserving status codes only."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def valid_private(path: Path, label: str) -> None:
    require(path.is_file() and not path.is_symlink(), f'{label}_MISSING_OR_SYMLINK')


def outside_git(path: Path) -> None:
    node = path.expanduser().resolve()
    require(not any((parent/'.git').exists() for parent in (node, *node.parents)), 'PRIVATE_OUTPUT_INSIDE_GIT')


def parse_csv(b: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        src = b.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(src, newline=''))
        header = list(reader.fieldnames or [])
        require(bool(header) and len(set(header)) == len(header), 'BAD_DUPLICATE_OR_EMPTY_HEADER')
        rows = list(reader)
        require(all(None not in r and all(isinstance(v, str) for v in r.values())
                    for r in rows), 'BAD_ROW_CSV_SHAPE')
        return header, rows
    except UnicodeDecodeError as exc:
        raise Hold('INVALID_UTF8_CSV') from exc
    except csv.Error as exc:
        raise Hold('INVALID_CSV') from exc


def check_flag(value: str, labels: tuple[str, ...], is_pair: bool) -> bool:
    v = value.strip()
    if is_pair:
        return v in ('LEFT','RIGHT','BOTH','NONE')
    if v == 'NONE':
        return True
    parts = v.split(',')
    return bool(parts) and len(parts) == len(set(parts)) and all(p in labels for p in parts)


def check_scored_file(blank_bytes: bytes, done_bytes: bytes, mode: str) -> tuple[int, int]:
    _, labels, preference, agency, forbidden = MODES[mode]
    pristine_header, pristine = parse_csv(blank_bytes)
    done_header, done = parse_csv(done_bytes)
    require(pristine_header == done_header, 'SCORING_COLUMNS_CHANGED')
    require(len(pristine) == len(done) == 20, 'NOT_EXACTLY_20_ROWS')
    fixed = (*COMMON, *(f'回复{x}' for x in labels))
    rating_cols = tuple(f'{d}·{x}' for d in DIMS for x in labels)
    scoring = (preference, *NOTES, agency, forbidden, *rating_cols)
    require(set(pristine_header) == set((*fixed, *scoring)), 'UNEXPECTED_CSV_SCHEMA')
    total = 0
    violations = 0
    for original, reviewed in zip(pristine, done, strict=True):
        require(all(original[col] == reviewed[col] for col in fixed), 'FROZEN_SOURCE_OR_ORDER_MODIFIED')
        require(all(not original[col].strip() for col in scoring), 'PRISTINE_ALREADY_SCORED')
        require(bool(original['样本编号'].strip()), 'EMPTY_CASE_ID')
        require(reviewed[preference].strip() in (*labels, 'TIE'), 'INVALID_PREFERENCE')
        require(bool(reviewed['偏好理由与可见原文证据'].strip()), 'MISSING_REASON')
        require(check_flag(reviewed[agency], labels, mode == 'pair'), 'INVALID_AGENCY_FLAG')
        require(check_flag(reviewed[forbidden], labels, mode == 'pair'), 'INVALID_FORBIDDEN_FLAG')
        any_flag = (reviewed[agency].strip() != 'NONE' or reviewed[forbidden].strip() != 'NONE')
        require(not any_flag or bool(reviewed['逐事件严重问题证据'].strip()), 'MISSING_VIOLATION_EVIDENCE')
        violations += int(any_flag)
        for col in rating_cols:
            require(reviewed[col].strip() in ('1','2','3','4','5'), 'INVALID_OR_MISSING_RATING')
            total += 1
    require(len({r['样本编号'] for r in pristine}) == 20, 'DUPLICATE_CASE_ID')
    return total, violations


def check_prep(pack: Path) -> dict:
    path = pack / 'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json'
    valid_private(path, 'PREP_RECEIPT')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise Hold('BAD_PREP_RECEIPT') from exc
    require(isinstance(data, dict), 'BAD_PREP_RECEIPT_ROOT')
    checks = (
        data.get('schema') == 'storyforge-r55-gold5-v2-safe-prep-v1',
        data.get('status') == EXPECTED_STATUS,
        data.get('case_count') == 20,
        data.get('reviewer_count') == 3,
        data.get('reviewer_csv_count') == 9,
        data.get('reviewers_completed') == 0,
        data.get('new_heldout') is False,
        data.get('r50_accessed') is False,
        data.get('gpu_inference') is False,
        data.get('training') is False,
        data.get('model_promoted') is False,
        data.get('three_distinct_blind_tasks') is True,
    )
    require(all(checks), 'PREP_RECEIPT_GATES_CHANGED')
    require(isinstance(data.get('reviewer_private_csv_sha256'), dict)
            and len(data['reviewer_private_csv_sha256']) == 9, 'PREP_CSV_HASH_MAP_INVALID')
    return data


def freeze_round(pack: Path, mode: str, completed: tuple[Path, ...], output: Path,
                 prior_pair: Path | None = None, prior_four: Path | None = None) -> dict:
    require(mode in MODES, 'INVALID_ROUND')
    pack = pack.expanduser().resolve()
    output = output.expanduser().resolve()
    outside_git(output)
    require(not output.exists() and not output.is_symlink(), 'FREEZE_DIR_ALREADY_EXISTS')
    require(len(completed) == 3, 'REQUIRES_3_REVIEWERS')
    if mode in ('four','five'):
        require(prior_pair is not None, 'PAIR_FREEZE_REQUIRED_FIRST')
        validate_prior(prior_pair, pack, 'pair')
    if mode == 'five':
        require(prior_four is not None, 'FOUR_FREEZE_REQUIRED_FIRST')
        validate_prior(prior_four, pack, 'four')
    prep = check_prep(pack)
    prefix, labels, _, _, _ = MODES[mode]
    original_digests = prep['reviewer_private_csv_sha256']
    frozen = []
    scores = 0
    cases_with_any_flags = 0
    digests = []
    for i, candidate in enumerate(completed, 1):
        candidate = candidate.expanduser()
        valid_private(candidate, 'COMPLETED_REVIEW')
        candidate = candidate.resolve()
        blank = pack / 'reviewers' / f'R55_GOLD5_{prefix}_V2_Reviewer_{i:02d}_PRIVATE.csv'
        valid_private(blank, 'PRISTINE_CSV')
        require(candidate != blank.resolve(), 'COMPLETED_POINTS_TO_PRISTINE')
        blank_b = blank.read_bytes()
        require(sha(blank_b) == original_digests.get(blank.name), 'PRISTINE_CSV_SHA_MISMATCH')
        data = candidate.read_bytes()
        require(sha(data) != sha(blank_b), 'REVIEWER_CSV_UNCHANGED')
        n, v = check_scored_file(blank_b, data, mode)
        scores += n
        cases_with_any_flags += v
        frozen.append((i, data))
        digests.append(sha(data))
    require(len(set(digests)) == 3, 'DUPLICATE_COMPLETED_REVIEW_FILES')
    expected_score_cells = 20 * 3 * len(labels) * len(DIMS)
    require(scores == expected_score_cells, 'RATING_COUNT_MISMATCH')
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    for index, data in frozen:
        name = f'R55_GOLD5_{prefix}_V2_Reviewer_{index:02d}_FROZEN_PRIVATE.csv'
        dest = output / name
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        require(sha(dest.read_bytes()) == sha(data), 'FREEZE_COPY_HASH_MISMATCH')
        dest.chmod(0o400)
    report = {
        'schema': 'storyforge-r55-gold5-v2-round-freeze-count-only-v1',
        'status': f'R55_GOLD5_V2_{prefix}_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50',
        'round': mode,
        'development_only': True,
        'case_count': 20,
        'reviewer_count': 3,
        'ratings_verified': scores,
        'expected_rating_cells': expected_score_cells,
        'reviewer_case_flag_presence_count': cases_with_any_flags,
        'source_prep_receipt_sha256': sha((pack / 'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json').read_bytes()),
        'reviewer_scored_sha256': {f'Reviewer_{i:02d}':h for i,h in enumerate(digests,1)},
        'gold_is_reference': True,
        'r50_accessed': False,
        'unblinding_performed': False,
        'gpu_job': False,
        'model_promotion': False,
    }
    fd = os.open(output / 'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    return report


def validate_prior(prior_path: Path, pack: Path, expected_round: str) -> None:
    prior_path = prior_path.expanduser().resolve()
    valid_private(prior_path, 'PRIOR_FREEZE')
    try:
        data = json.loads(prior_path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise Hold('BAD_PRIOR_FREEZE') from exc
    prefix = MODES[expected_round][0]
    require(data.get('schema') == 'storyforge-r55-gold5-v2-round-freeze-count-only-v1'
            and data.get('status') == f'R55_GOLD5_V2_{prefix}_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50'
            and data.get('round') == expected_round
            and data.get('unblinding_performed') is False
            and data.get('r50_accessed') is False
            and data.get('source_prep_receipt_sha256') == sha((pack / 'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json').read_bytes()),
            'WRONG_PRIOR_FREEZE_RECEIPT')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pack', type=Path, required=True)
    ap.add_argument('--round', choices=MODES, required=True)
    ap.add_argument('--completed', nargs=3, type=Path, required=True,
                    metavar=('REVIEWER01_CSV','REVIEWER02_CSV','REVIEWER03_CSV'))
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--prior-pair-freeze', type=Path)
    ap.add_argument('--prior-four-freeze', type=Path)
    args = ap.parse_args()
    try:
        result = freeze_round(args.pack, args.round, tuple(args.completed), args.output_dir,
                              args.prior_pair_freeze, args.prior_four_freeze)
        print(result['status'])
        print('R55_GOLD5_V2_FREEZE_SAFE_RECEIPT=' + str(args.output_dir / 'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'))
    except (Hold, ValueError, TypeError, OSError, KeyError, AssertionError) as exc:
        reason = str(exc) if isinstance(exc, Hold) else type(exc).__name__
        print('R55_GOLD5_V2_FREEZE_HOLD__'+reason, file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

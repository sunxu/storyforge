#!/usr/bin/env python3
"""R58 G1: Owner-local R04(150) minus accepted Gold108 source UUID check.

Only reads immutable Git blobs and Owner PRIVATE DEV20 case-level metadata.
The narrative-bearing pinned JSONL rows are NEVER JSON-decoded: project only
one structural metadata.story_id token from each byte line, and compare the
source lines byte-for-byte. No R50, remote HF, network, GPU, or admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from check_legacy_dev20_uuid import OWNER_POLICY, private_json, verified_darwin_root_alias

SCHEMA = 'r58_round1_g1_r04_non_gold_uuid_safe_v1'
R04_BLOB = 'b580038f6fef2ffb41831b8f5451ddcac5d610c2'
R04_SHA256 = '8fbd2581b6823882d27e7839238335319202b1d9a726fc25d9aa74fedf5487f1'
GOLD108_BLOB = 'eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90'
GOLD108_SHA256 = '27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308'
UUID = re.compile(r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$', re.IGNORECASE)
WORLD_FIELDS = (
    re.compile(rb'"story_id"\s*:\s*"([0-9a-fA-F-]{36})"'),
    re.compile(rb'"source_story_id"\s*:\s*"([0-9a-fA-F-]{36})"'),
)
META = re.compile(rb'"metadata"\s*:\s*\{')

class Hold(Exception):
    pass


def frozen_blob(repo: Path, sha: str, limit: int) -> bytes:
    if re.fullmatch(r'[a-f0-9]{40}', sha) is None:
        raise Hold('Git object identity invalid')
    try:
        p = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', sha],
                           capture_output=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Hold('pinned Git blob inaccessible')
    if p.returncode or not 0 < len(p.stdout) <= limit:
        raise Hold('pinned Git blob missing or oversized')
    return p.stdout


def structural_world_rows(blob: bytes, digest: str, expected: int,
                          expected_worlds: int) -> tuple[set[str], set[bytes]]:
    if hashlib.sha256(blob).hexdigest() != digest:
        raise Hold('immutable source SHA256 mismatch')
    lines = blob.splitlines()
    if (len(lines) != expected or any(not x for x in lines)
        or len(set(lines)) != expected):
        raise Hold('frozen source row count, blank or duplicate')
    worlds = set()
    for raw in lines:
        # R04's historical curation schema may use metadata.source_story_id
        # whereas later compiled splits use metadata.story_id. Require exactly
        # one unambiguous UUID token; do not JSON-decode narrative fields.
        tokens = [uid for pattern in WORLD_FIELDS for uid in pattern.findall(raw)]
        if len(tokens) != 1 or len(META.findall(raw)) != 1:
            raise Hold('world metadata token ambiguous')
        uid = tokens[0].decode('ascii').lower()
        if UUID.fullmatch(uid) is None:
            raise Hold('world metadata UUID invalid')
        worlds.add(uid)
    if len(worlds) != expected_worlds:
        raise Hold('expected frozen distinct-world count drift')
    return worlds, set(lines)



def source_shape_diagnostic(blob: bytes, digest: str, expected: int,
                            expected_worlds: int) -> dict:
    """Aggregate-only source troubleshooting; never print a UID or row."""
    lines = blob.splitlines()
    counts = {'sha256_pin_verified': hashlib.sha256(blob).hexdigest() == digest,
              'expected_row_count_verified': len(lines) == expected,
              'unique_raw_rows_verified': len(set(lines)) == len(lines),
              'metadata_token_one_rows': 0,
              'story_id_only_rows': 0,
              'source_story_id_only_rows': 0,
              'both_world_fields_rows': 0,
              'no_world_field_rows': 0,
              'valid_single_uuid_rows': 0,
              'distinct_worlds_expected_verified': False}
    worlds = set()
    if not counts['sha256_pin_verified']:
        return counts
    for raw in lines:
        counts['metadata_token_one_rows'] += (len(META.findall(raw)) == 1)
        a, b = (x.findall(raw) for x in WORLD_FIELDS)
        if a and not b:
            counts['story_id_only_rows'] += 1
        elif b and not a:
            counts['source_story_id_only_rows'] += 1
        elif a or b:
            counts['both_world_fields_rows'] += 1
        else:
            counts['no_world_field_rows'] += 1
        if len(a) + len(b) == 1:
            try:
                uid = (a or b)[0].decode('ascii').lower()
            except UnicodeError:
                continue
            if UUID.fullmatch(uid):
                counts['valid_single_uuid_rows'] += 1
                worlds.add(uid)
    if (counts['expected_row_count_verified'] and
        counts['valid_single_uuid_rows'] == len(lines)):
        counts['distinct_worlds_expected_verified'] = len(worlds) == expected_worlds
    return counts


def r04_non_gold_worlds(r04_blob: bytes, gold_blob: bytes,
                        r04_digest: str = R04_SHA256,
                        gold_digest: str = GOLD108_SHA256) -> set[str]:
    r04_worlds, r04_lines = structural_world_rows(r04_blob, r04_digest, 150, 10)
    gold_worlds, gold_lines = structural_world_rows(gold_blob, gold_digest, 108, 8)
    if not gold_lines.issubset(r04_lines) or not gold_worlds.issubset(r04_worlds):
        raise Hold('Gold108 is not an exact source subset of frozen R04')
    diff = r04_worlds - gold_worlds
    if len(diff) != 2:
        raise Hold('non-Gold R04 source scope is not exactly two worlds')
    return diff


def frozen_five_from_dev20(ledger: dict) -> list[dict]:
    if (not isinstance(ledger, dict)
        or ledger.get('schema') != 'r58_round1_g1_legacy_dev20_uuid_private_v1'
        or ledger.get('owner_uuid_world_policy') != OWNER_POLICY
        or ledger.get('expansion_allowed') is not False
        or not isinstance(ledger.get('entries'), list)
        or len(ledger['entries']) != 5):
        raise Hold('prior DEV20 PRIVATE ledger schema mismatch')
    seen = set(); result=[]; exposed=0
    for row in ledger['entries']:
        if not isinstance(row, dict):
            raise Hold('bad prior ledger record')
        uid = row.get('story_id_PRIVATE')
        if not isinstance(uid, str) or UUID.fullmatch(uid) is None or uid.lower() in seen:
            raise Hold('prior ledger invalid or duplicate story UUID')
        seen.add(uid.lower())
        flags = ('historical_sft_uuid_exposed', 'r50_protected_uuid_match',
                 'r57_gold195_source_uuid_match', 'legacy_dev20_uuid_match')
        if any(type(row.get(k)) is not bool for k in flags):
            raise Hold('prior ledger exposure flags invalid')
        sft = row['historical_sft_uuid_exposed']
        exposed += int(sft)
        if not sft and any(row[k] for k in flags[1:]):
            raise Hold('prior 1+4 survivors violated a protected UUID gate')
        if row.get('train_admitted') is not False or row.get('expansion_allowed') is not False:
            raise Hold('prior ledger falsely admitted or expanded a case')
        result.append({'story_id_PRIVATE':uid.lower(), 'historical_sft_uuid_exposed':sft})
    if exposed != 1:
        raise Hold('expected exactly one earlier SFT-excluded world')
    return result


def evaluate(rows: list[dict], other_worlds: set[str]) -> tuple[dict, list[dict]]:
    if len(rows) != 5 or len(other_worlds) != 2 or any(UUID.fullmatch(x) is None for x in other_worlds):
        raise Hold('cohort or non-Gold world scope invalid')
    hits = 0; private_rows=[]
    for row in rows:
        uid = row['story_id_PRIVATE'].lower()
        excluded = row['historical_sft_uuid_exposed']
        collision = uid in other_worlds
        if not excluded:
            hits += int(collision)
        private_rows.append({
            'story_id_PRIVATE': uid,
            'historical_sft_uuid_exposed': excluded,
            'r04_non_gold_source_uuid_match': collision,
            'status': ('EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE' if excluded else
                       'HOLD_R04_NON_GOLD_SOURCE_UUID_OVERLAP' if collision else
                       'HOLD_OTHER_PROTECTED_AND_REMOTE_RUN_COMPLETENESS'),
            'train_admitted': False, 'expansion_allowed': False,
        })
    safe = {
        'schema': SCHEMA,
        'status': 'R58_G1_R04_NON_GOLD_SOURCE_UUID_CHECK_DONE__OTHER_AND_REMOTE_HOLD',
        'fixed_stories': 5,
        'prior_sft_exposed_excluded': 1,
        'r04_frozen_curated_rows': 150,
        'gold108_frozen_accepted_rows': 108,
        'r04_source_world_uuids': 10,
        'gold108_source_world_uuids': 8,
        'r04_non_gold_source_world_uuids': 2,
        'r04_minus_gold108_exact_row_subset_verified': True,
        'r04_and_gold108_frozen_sha256_verified': True,
        'r04_non_gold_exact_uuid_matches_among_remaining_four': hits,
        'remaining_without_known_sft_r50_gold_dev20_and_r04_non_gold_uuid_match': 4-hits,
        'r56_non_gold_r04_metadata_scope_checked': True,
        'r56_rank_07_11_to_uuid_provenance_replayed': False,
        'other_protected_uuids_covered': False,
        'all_actual_sft_runs_and_input_sources_proven_complete': False,
        'source_registry_complete': False,
        'r50_protected_test_content_accessed': False,
        'original_story_archives_read': False,
        'narrative_json_decoded_or_exported': False,
        'g1_clearance': 'HOLD',
        'train_admitted': 0, 'validation_admitted': 0, 'teacher_admitted': 0,
        'expansion_allowed': False,
    }
    return safe, private_rows


def write_private(path: Path, data: list[dict]) -> None:
    parent = path.parent
    if path.exists() or path.is_symlink():
        raise Hold('PRIVATE ledger already exists')
    if parent.is_symlink() or not parent.is_dir() or parent.stat().st_mode & 0o077:
        raise Hold('PRIVATE destination not mode 0700')
    for p in list(parent.parents)[:-1] + [parent]:
        if p.is_symlink() and not verified_darwin_root_alias(p):
            raise Hold('unsafe PRIVATE destination symlink ancestor')
    payload = {'schema':'r58_round1_g1_r04_non_gold_uuid_private_v1',
               'owner_uuid_world_policy':OWNER_POLICY,
               'entries':data, 'expansion_allowed':False,
               'train_admitted':0,'validation_admitted':0,'teacher_admitted':0}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write('\n')
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(repo: Path, dev_holds: Path, private_output: Path|None) -> dict:
    rows = frozen_five_from_dev20(private_json(dev_holds))
    r04 = frozen_blob(repo, R04_BLOB, 2_000_000)
    gold = frozen_blob(repo, GOLD108_BLOB, 2_000_000)
    non_gold = r04_non_gold_worlds(r04, gold)
    safe, private = evaluate(rows, non_gold)
    if private_output is not None:
        write_private(private_output, private)
        safe['private_case_hold_ledger_written'] = True
    return safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=Path, required=True)
    p.add_argument('--private-dev20-holds', type=Path,
                   help='Required for normal check; forbidden with --diagnose-only')
    p.add_argument('--private-output', type=Path)
    p.add_argument('--diagnose-only', action='store_true',
                   help='Only emit aggregate source-shape flags; no private inputs/outputs')
    args = p.parse_args()
    try:
        if args.diagnose_only:
            if args.private_dev20_holds is not None or args.private_output is not None:
                raise Hold('diagnose-only forbids PRIVATE input/output paths')
            r04 = frozen_blob(args.repo_root, R04_BLOB, 2_000_000)
            gold = frozen_blob(args.repo_root, GOLD108_BLOB, 2_000_000)
            result = {
                'schema': 'r58_g1_r04_source_shape_diagnostic_safe_v1',
                'status': 'SOURCE_SHAPE_DIAGNOSTIC_ONLY__G1_HOLD',
                'r04': source_shape_diagnostic(r04, R04_SHA256, 150, 10),
                'gold108': source_shape_diagnostic(gold, GOLD108_SHA256, 108, 8),
                'story_uuids_or_content_exported': False,
                'private_ledgers_accessed': False,
                'g1_clearance': 'HOLD', 'train_admitted': 0,
                'validation_admitted': 0, 'teacher_admitted': 0,
                'expansion_allowed': False,
            }
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        if args.private_dev20_holds is None or args.private_output is None:
            raise Hold('missing private input/output for normal check')
        safe = run(args.repo_root, args.private_dev20_holds, args.private_output)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (Hold, OSError, KeyError, TypeError, ValueError):
        print('R58_G1_R04_NON_GOLD: HOLD (frozen source or private metadata unavailable)', file=sys.stderr)
        return 42

if __name__ == '__main__':
    raise SystemExit(main())

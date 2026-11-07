"""R60: bounded, read-only Supabase extraction using Canonical Reviewer A V3.

Only Gold192 story UUIDs and target turn numbers from the private review packets
are queried. This is source evidence, NOT Quality-v1 admission or SFT training.
Requires `pip install 'psycopg[binary]'` and STORYFORGE_SUPABASE_DSN locally.
No private text, identifiers, database errors or credentials are printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .r60_gold192_canonical_a_v3 import (
        A_SHA,
        B_COUNTS,
        B_SCHEMA,
        B_SHA,
        EX_SHA,
        PACKETS_SHA,
        validate_reviewer_a_v3,
    )
except ImportError:
    from r60_gold192_canonical_a_v3 import (
        A_SHA,
        B_COUNTS,
        B_SCHEMA,
        B_SHA,
        EX_SHA,
        PACKETS_SHA,
        validate_reviewer_a_v3,
    )

HEX = re.compile(r'^[a-f0-9]{64}$')


def hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_text(value: str) -> str:
    return hash_bytes(value.encode('utf-8'))


def read_private(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('INPUT_MISSING_OR_LINK')
    info = path.stat()
    parent = path.parent
    if (stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or parent.is_symlink() or not parent.is_dir()
            or stat.S_IMODE(parent.stat().st_mode) != 0o700):
        raise ValueError('INPUT_PERMISSION_OR_LINK_COUNT_INVALID')
    return path.read_bytes()


def read_json(path: Path, expected: str | None = None):
    raw = read_private(path)
    if expected is not None and hash_bytes(raw) != expected:
        raise ValueError('INPUT_SHA_MISMATCH')
    return json.loads(raw)


def read_jsonl(path: Path, expected: str | None = None):
    raw = read_private(path)
    if expected is not None and hash_bytes(raw) != expected:
        raise ValueError('INPUT_SHA_MISMATCH')
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def index_packets(packets: list[dict]) -> dict[str, dict]:
    if len(packets) != 13:
        raise ValueError('PACKET_STORY_COUNT')
    indexed = {}
    for packet in packets:
        story = packet['story_uuid']
        if not isinstance(story, str) or not story:
            raise ValueError('STORY_ID_MISSING')
        for case in packet['cases']:
            cid, target = case['case_id'], case['target_sha256']
            match = re.search(r't(\d+)$', cid)
            if (cid in indexed or not match or not HEX.fullmatch(target)
                    or sha_text(case['target_assistant_text']) != target):
                raise ValueError('FROZEN_TARGET_IDENTITY_INVALID')
            indexed[cid] = {'case_id': cid, 'target_sha256': target,
                            'story_id': story, 'turn_index': int(match.group(1))}
    if len(indexed) != 192 or len({x['target_sha256'] for x in indexed.values()}) != 192:
        raise ValueError('PACKET_192_UNIQUE_INVALID')
    return indexed


def select_candidates(a: dict, b: dict, exclusions: list[dict], packets: dict) -> list[dict]:
    """Select only explicit case-scored A V3 PASS + B PASS, minus frozen exclusions.

    Aggregate-complement PASS_ONLY rows are intentionally not eligible because
    they carry no case-level score or strict A/B comparison decision.
    """
    a_idx = validate_reviewer_a_v3(a)
    if not isinstance(b, dict):
        raise TypeError('REVIEW_STRUCTURE_INVALID')
    bb = b.get('cases')
    if (b.get('schema') != B_SCHEMA or b.get('counts') != B_COUNTS
            or not isinstance(bb, list) or len(bb) != 192 or len(exclusions) != 11):
        raise ValueError('REVIEW_COUNT_INVALID')

    b_idx = {}
    for row in bb:
        target = row.get('target_sha256')
        if (not isinstance(target, str) or not HEX.fullmatch(target)
                or target in b_idx or row.get('decision') not in {'PASS', 'HOLD', 'REJECT'}):
            raise ValueError('REVIEWER_B_IDENTITY_INVALID')
        b_idx[target] = row

    if dict(Counter(row['decision'] for row in bb)) != B_COUNTS:
        raise ValueError('REVIEWER_B_DECISION_COUNTS_INVALID')
    target_ids = {x['target_sha256'] for x in packets.values()}
    if len(target_ids) != 192 or set(a_idx) != target_ids or set(b_idx) != target_ids:
        raise ValueError('REVIEW_IDENTITY_INVALID')
    for case in packets.values():
        if a_idx[case['target_sha256']].get('case_id') != case['case_id']:
            raise ValueError('REVIEW_CASE_ID_MISMATCH')

    excluded = set()
    for row in exclusions:
        target = row.get('target_sha256')
        if (not isinstance(target, str) or not HEX.fullmatch(target)
                or target in excluded
                or row.get('exclusion_reason') != 'EXCLUDED_FROM_TRAINING_DISAGREEMENT'):
            raise ValueError('EXCLUSION_IDENTITY_INVALID')
        excluded.add(target)
    if len(excluded) != 11 or not excluded <= target_ids:
        raise ValueError('REVIEW_IDENTITY_INVALID')

    selected = []
    for case in packets.values():
        target = case['target_sha256']
        a_row, b_row = a_idx[target], b_idx[target]
        if (
            target not in excluded
            and a_row.get('evidence_granularity') == 'CASE_LEVEL_SCORED_REVIEW'
            and a_row.get('decision_for_strict_ab_decision_comparison') == 'PASS_ONLY'
            and b_row.get('decision') == 'PASS'
        ):
            selected.append(case)
    if not selected:
        raise ValueError('NO_EXPLICIT_CASE_LEVEL_AB_PASS_CANDIDATES')
    return sorted(selected, key=lambda x: (x['story_id'], x['turn_index'], x['case_id']))


def choose_pilot(selected: list[dict], n: int) -> list[dict]:
    if n <= 0 or n >= len(selected):
        return selected
    by_story = defaultdict(list)
    for x in selected:
        by_story[x['story_id']].append(x)
    groups = [sorted(v, key=lambda x: x['turn_index']) for _, v in sorted(by_story.items())]
    # Round-robin first case per story before taking second cases. This avoids
    # letting lexicographically early stories consume a small pilot.
    candidates = [group[0] for group in groups]
    candidates.extend(group[-1] for group in groups if len(group) > 1)
    candidates.extend(
        case for group in groups for case in group[1:-1]
    )
    seen = set()
    unique = []
    for x in candidates + selected:
        if x['case_id'] not in seen:
            seen.add(x['case_id'])
            unique.append(x)
    return unique[:n]


def status_category(value) -> str:
    if value == 'completed':
        return 'completed'
    if value is None:
        return 'null_or_missing'
    if isinstance(value, str):
        return 'other_string'
    return 'other_type'


def decide_matches(case: dict, matches: list[dict]) -> tuple[str, dict | None]:
    exact = [x for x in matches if sha_text(x['content']) == case['target_sha256']]
    if not exact:
        return ('SOURCE_FOUND_BUT_CONTENT_CHANGED' if matches else 'SOURCE_NOT_FOUND'), None
    # Exact text is not sufficient: a target row must also be completed.
    # If duplicate exact rows disagree on status, fail closed rather than
    # choosing one based on session lineage alone.
    if any(x.get('status') != 'completed' for x in exact):
        return 'TARGET_STATUS_NOT_COMPLETED', None
    if len(exact) == 1:
        return 'EXACT_MATCH', exact[0]
    roots = [x for x in exact if x['parent_session_id'] is None]
    if len(roots) == 1:
        return 'EXACT_MATCH', roots[0]
    return 'IDENTITY_AMBIGUOUS', None


def atomic_private_write(path: Path, payload: bytes):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return hash_bytes(payload)


def jsonl_bytes(rows):
    return ''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for x in rows).encode('utf-8')


def execute(db, selected: list[dict], packet_index: dict, max_history: int):
    # Only (story, turn) pairs from Gold192, never a full-database scan.
    grouped = defaultdict(set)
    for case in packet_index.values():
        grouped[case['story_id']].add(case['turn_index'])
    found = defaultdict(list)
    from psycopg.rows import dict_row
    with db.cursor(row_factory=dict_row) as cur:
        for story_id, turns in sorted(grouped.items()):
            cur.execute("""
                SELECT m.id::text AS message_id, m.story_id::text AS story_id,
                       m.session_id::text AS session_id, m.turn_index, m.content,
                       m.status, s.parent_session_id::text AS parent_session_id
                FROM public.v2_chat_messages m
                JOIN public.story_v2_sessions s
                  ON s.story_id = m.story_id AND s.session_id = m.session_id
                WHERE m.story_id = %s AND m.turn_index = ANY(%s)
                  AND m.role = 'assistant'
            """, (story_id, sorted(turns)))
            for row in cur.fetchall():
                found[(story_id, row['turn_index'])].append(row)
        stories = {}
        for story_id in sorted(grouped):
            cur.execute("""
                SELECT id::text AS story_id, v2_data, updated_at
                FROM public.user_stories WHERE id = %s
            """, (story_id,))
            row = cur.fetchone()
            if row is None or not isinstance(row['v2_data'], dict):
                raise ValueError('STORY_DRAFT_MISSING')
            stories[story_id] = row
        locators, contexts = [], []
        selected_ids = {x['case_id'] for x in selected}
        exact_target_status_counts = Counter()
        for case in sorted(packet_index.values(), key=lambda x: x['case_id']):
            variants = found[(case['story_id'], case['turn_index'])]
            exact_variants = [
                x for x in variants
                if sha_text(x['content']) == case['target_sha256']
            ]
            for variant in exact_variants:
                exact_target_status_counts[status_category(variant.get('status'))] += 1
            status, canonical = decide_matches(case, variants)
            locators.append({**case, 'source_status': status,
                             'matched_message_count': len(exact_variants),
                             'exact_target_status_categories': sorted({
                                 status_category(x.get('status')) for x in exact_variants
                             }),
                             'message_id': canonical['message_id'] if canonical else None,
                             'session_id': canonical['session_id'] if canonical else None})
            if case['case_id'] not in selected_ids or canonical is None:
                continue
            cur.execute("""
                SELECT id::text AS message_id, turn_index, role, content, status
                FROM public.v2_chat_messages
                WHERE story_id = %s AND session_id = %s AND turn_index < %s
                  AND role IN ('user','assistant')
                ORDER BY turn_index, created_at, id
            """, (case['story_id'], canonical['session_id'], case['turn_index']))
            history = cur.fetchall()
            if not history or len(history) > max_history or history[-1]['role'] != 'user':
                # Never silently truncate a candidate's history.
                continue
            contexts.append({**case, 'session_id': canonical['session_id'],
                             'message_id': canonical['message_id'],
                             'target_assistant_text': canonical['content'],
                             'history': history,
                             'story_draft_sha256': sha_text(json.dumps(
                                 stories[case['story_id']]['v2_data'], ensure_ascii=False,
                                 sort_keys=True, separators=(',', ':'))),
                             'story_draft_source': 'CURRENT_V2_DATA_NOT_HISTORICAL',
                             'session_summary_used': False,
                             'training_admitted': False})
    drafts = [{'story_id': sid, 'v2_data': row['v2_data'],
               'updated_at': str(row['updated_at']),
               'source_label': 'CURRENT_V2_DATA_NOT_HISTORICAL'}
              for sid, row in sorted(stories.items())]
    return locators, contexts, drafts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reviewer-a', type=Path, required=True)
    p.add_argument('--reviewer-b', type=Path, required=True)
    p.add_argument('--exclusions', type=Path, required=True)
    p.add_argument('--source-packets', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--pilot', type=int, default=7, help='0 = all explicitly scored A/B PASS candidates')
    p.add_argument('--max-history', type=int, default=20000)
    p.add_argument('--dsn-env', default='STORYFORGE_SUPABASE_DSN')
    p.add_argument('--identity-only', action='store_true',
                   help='Validate canonical A V3 identities and 11 exclusions without connecting to Supabase')
    args = p.parse_args()
    try:
        if not (0 <= args.pilot <= 192 and args.max_history >= 12):
            raise ValueError('PARAMETERS_INVALID')
        packets = read_jsonl(args.source_packets, PACKETS_SHA)
        packet_index = index_packets(packets)
        selected = select_candidates(read_json(args.reviewer_a, A_SHA),
                                     read_json(args.reviewer_b, B_SHA),
                                     read_jsonl(args.exclusions, EX_SHA), packet_index)
        priority = choose_pilot(selected, args.pilot)
        if args.identity_only:
            print(json.dumps({
                'schema': 'r60_gold192_supabase_extract_v3_safe_v1',
                'status': 'GOLD192_REVIEW_IDENTITY_PASS__NO_DB_ACCESS',
                'gold192': len(packet_index),
                'excluded_disagreements': 11, 'priority_candidates': len(selected),
                'candidate_policy': 'EXPLICIT_CASE_LEVEL_SCORED_A_V3_PASS_AND_B_PASS_MINUS_11_EXCLUSIONS',
                'aggregate_complement_passes_eligible': False,
                'pilot_requested': len(priority), 'quality_v1_admitted': 0,
                'gpu_started': False, 'database_modified': False, 'private_values_emitted': False,
            }, sort_keys=True))
            return 0
        dsn = os.environ.get(args.dsn_env)
        if not dsn:
            raise ValueError('DB_CONNECTION_MISSING')
        import psycopg
        with psycopg.connect(dsn, autocommit=False, connect_timeout=15) as db:
            db.execute('SET TRANSACTION READ ONLY')
            db.execute("SET LOCAL statement_timeout = '90000ms'")
            db.execute("SET LOCAL lock_timeout = '1000ms'")
            locators, contexts, drafts = execute(db, priority, packet_index, args.max_history)
            db.rollback()
        root = args.output_dir
        if root.exists() or root.is_symlink():
            raise ValueError('OUTPUT_EXISTS')
        if (not root.parent.is_dir() or root.parent.is_symlink()
                or stat.S_IMODE(root.parent.stat().st_mode) != 0o700):
            raise ValueError('OUTPUT_PARENT_PERMISSIONS')
        root.mkdir(mode=0o700, parents=False)
        if stat.S_IMODE(root.stat().st_mode) != 0o700:
            raise ValueError('OUTPUT_PERMISSIONS')
        written = {}
        for name, rows in (
            ('R60_SOURCE_LOCATORS_192.jsonl', locators),
            ('R60_SOURCE_CONTEXT_PRIVATE.jsonl', contexts),
            ('R60_STORY_DRAFTS_PRIVATE.jsonl', drafts),
        ):
            written[name] = {
                'records': len(rows),
                'sha256': atomic_private_write(root / name, jsonl_bytes(rows)),
            }
        counts = Counter(x['source_status'] for x in locators)
        safe = {
            'schema': 'r60_gold192_supabase_extract_v3_safe_v1',
            'status': 'SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED',
            'gold192': len(packet_index), 'excluded_disagreements': 11,
            'reviewer_a_b_explicit_case_level_pass_priority': len(selected),
            'candidate_policy': 'EXPLICIT_CASE_LEVEL_SCORED_A_V3_PASS_AND_B_PASS_MINUS_11_EXCLUSIONS',
            'aggregate_complement_passes_eligible': False,
            'context_requested': len(priority), 'context_exported': len(contexts),
            'source_match_counts': dict(sorted(counts.items())),
            'exact_target_message_status_category_counts': dict(
                sorted(exact_target_status_counts.items())
            ),
            'story_count': len(drafts), 'artifacts': written,
            'system_prompt_reconstructed': False,
            'current_story_snapshot_is_historical': False,
            'historical_exposure_fully_checked': False,
            'quality_v1_admitted': 0, 'training_authorized': False,
            'gpu_started': False, 'r50_accessed': False, 'database_modified': False,
            'private_values_emitted': False,
        }
        atomic_private_write(root / 'R60_SOURCE_SAFE.json',
                             (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2)
                              + '\n').encode())
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - emit only a non-sensitive reason code
        reason = (str(exc) if isinstance(exc, ValueError)
                  and re.fullmatch(r'[A-Z0-9_]+', str(exc))
                  else type(exc).__name__)
        print(json.dumps({
            'schema': 'r60_gold192_supabase_extract_v3_safe_v1',
            'status': 'SOURCE_EXTRACT_FAILED__HOLD',
            'reason_code': reason,
            'quality_v1_admitted': 0, 'gpu_started': False, 'database_modified': False,
            'private_values_emitted': False,
        }, sort_keys=True))
        return 42


if __name__ == '__main__':
    raise SystemExit(main())

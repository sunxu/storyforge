"""R59: bounded, read-only Supabase extraction for frozen Gold192.

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

A_SHA = '641b71e10a14318b57e69cb0239172f7016fe5b9d2149923f876308f5e6fe1e4'
B_SHA = 'bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8'
EX_SHA = '9ca99432e08b680cb67b5a1f89d172a337cb91c9bd02af70b68356938c6c04ed'
HEX = re.compile(r'^[a-f0-9]{64}$')


def hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_text(value: str) -> str:
    return hash_bytes(value.encode('utf-8'))


def read_json(path: Path, expected: str | None = None):
    if not path.is_file() or path.is_symlink():
        raise ValueError('INPUT_MISSING_OR_LINK')
    raw = path.read_bytes()
    if expected is not None and hash_bytes(raw) != expected:
        raise ValueError('INPUT_SHA_MISMATCH')
    return json.loads(raw)


def read_jsonl(path: Path, expected: str | None = None):
    if not path.is_file() or path.is_symlink():
        raise ValueError('INPUT_MISSING_OR_LINK')
    raw = path.read_bytes()
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
    aa = a['records']
    bb = b['cases']
    if len(aa) != 192 or len(bb) != 192 or len(exclusions) != 11:
        raise ValueError('REVIEW_COUNT_INVALID')
    a_idx = {x['target_sha256']: x for x in aa}
    b_idx = {x['target_sha256']: x for x in bb}
    target_ids = {x['target_sha256'] for x in packets.values()}
    excluded = {x['target_sha256'] for x in exclusions}
    if (len(a_idx) != 192 or len(b_idx) != 192 or len(excluded) != 11
            or set(a_idx) != target_ids or set(b_idx) != target_ids
            or not excluded <= target_ids
            or any(x.get('exclusion_reason') != 'EXCLUDED_FROM_TRAINING_DISAGREEMENT'
                   for x in exclusions)):
        raise ValueError('REVIEW_IDENTITY_INVALID')
    for case in packets.values():
        a_case = a_idx[case['target_sha256']]
        if a_case['case_id'] != case['case_id']:
            raise ValueError('REVIEW_CASE_ID_MISMATCH')
    selected = [case for case in packets.values()
                if (case['target_sha256'] not in excluded
                    and a_idx[case['target_sha256']]['decision_for_strict_ab_pairing'] == 'PASS_ONLY'
                    and b_idx[case['target_sha256']]['decision'] == 'PASS')]
    if len(selected) != 72:
        raise ValueError('BOTH_PASS_72_NOT_VERIFIED')
    return sorted(selected, key=lambda x: (x['story_id'], x['turn_index'], x['case_id']))


def choose_pilot(selected: list[dict], n: int) -> list[dict]:
    if n <= 0 or n >= len(selected):
        return selected
    by_story = defaultdict(list)
    for x in selected:
        by_story[x['story_id']].append(x)
    groups = [sorted(v, key=lambda x: x['turn_index']) for _, v in sorted(by_story.items())]
    candidates = []
    for group in groups:
        candidates.extend((group[0], group[-1]))
    seen = set()
    unique = []
    for x in candidates + selected:
        if x['case_id'] not in seen:
            seen.add(x['case_id'])
            unique.append(x)
    return unique[:n]


def decide_matches(case: dict, matches: list[dict]) -> tuple[str, dict | None]:
    exact = [x for x in matches if sha_text(x['content']) == case['target_sha256']]
    if not exact:
        return ('SOURCE_FOUND_BUT_CONTENT_CHANGED' if matches else 'SOURCE_NOT_FOUND'), None
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
        for case in sorted(packet_index.values(), key=lambda x: x['case_id']):
            variants = found[(case['story_id'], case['turn_index'])]
            status, canonical = decide_matches(case, variants)
            locators.append({**case, 'source_status': status,
                             'matched_message_count': sum(
                                 sha_text(x['content']) == case['target_sha256']
                                 for x in variants),
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
    p.add_argument('--pilot', type=int, default=7, help='0 = all 72 priority candidates')
    p.add_argument('--max-history', type=int, default=20000)
    p.add_argument('--dsn-env', default='STORYFORGE_SUPABASE_DSN')
    p.add_argument('--identity-only', action='store_true',
                   help='Validate 192/72/11 without connecting to Supabase')
    args = p.parse_args()
    try:
        if not (0 <= args.pilot <= 72 and args.max_history >= 12):
            raise ValueError('PARAMETERS_INVALID')
        packets = read_jsonl(args.source_packets)
        packet_index = index_packets(packets)
        selected = select_candidates(read_json(args.reviewer_a, A_SHA),
                                     read_json(args.reviewer_b, B_SHA),
                                     read_jsonl(args.exclusions, EX_SHA), packet_index)
        priority = choose_pilot(selected, args.pilot)
        if args.identity_only:
            print(json.dumps({
                'schema': 'r59_gold192_supabase_extract_safe_v1',
                'status': 'GOLD192_REVIEW_IDENTITY_PASS__NO_DB_ACCESS',
                'gold192': len(packet_index),
                'excluded_disagreements': 11, 'priority_candidates': len(selected),
                'pilot_requested': len(priority), 'quality_v1_admitted': 0,
                'gpu_started': False, 'private_values_emitted': False,
            }, sort_keys=True))
            return 0
        dsn = os.environ.get(args.dsn_env)
        if not dsn:
            raise ValueError('DB_CONNECTION_MISSING')
        import psycopg
        with psycopg.connect(dsn, autocommit=False, connect_timeout=15) as db:
            db.execute('SET TRANSACTION READ ONLY')
            locators, contexts, drafts = execute(db, priority, packet_index, args.max_history)
            db.rollback()
        root = args.output_dir
        if root.exists() or root.is_symlink():
            raise ValueError('OUTPUT_EXISTS')
        root.mkdir(mode=0o700, parents=False)
        if stat.S_IMODE(root.stat().st_mode) != 0o700:
            raise ValueError('OUTPUT_PERMISSIONS')
        written = {}
        for name, rows in (
            ('R59_SOURCE_LOCATORS_192.jsonl', locators),
            ('R59_SOURCE_CONTEXT_PRIVATE.jsonl', contexts),
            ('R59_STORY_DRAFTS_PRIVATE.jsonl', drafts),
        ):
            written[name] = {
                'records': len(rows),
                'sha256': atomic_private_write(root / name, jsonl_bytes(rows)),
            }
        counts = Counter(x['source_status'] for x in locators)
        safe = {
            'schema': 'r59_gold192_supabase_extract_safe_v1',
            'status': 'SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED',
            'gold192': len(packet_index), 'excluded_disagreements': 11,
            'reviewer_a_b_pass_priority': len(selected),
            'context_requested': len(priority), 'context_exported': len(contexts),
            'source_match_counts': dict(sorted(counts.items())),
            'story_count': len(drafts), 'artifacts': written,
            'system_prompt_reconstructed': False,
            'current_story_snapshot_is_historical': False,
            'historical_exposure_fully_checked': False,
            'quality_v1_admitted': 0, 'training_authorized': False,
            'gpu_started': False, 'r50_accessed': False,
            'private_values_emitted': False,
        }
        atomic_private_write(root / 'R59_SOURCE_SAFE.json',
                             (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2)
                              + '\n').encode())
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - avoid leaking private database exception details
        print(json.dumps({
            'schema': 'r59_gold192_supabase_extract_safe_v1',
            'status': 'SOURCE_EXTRACT_FAILED__HOLD',
            'quality_v1_admitted': 0, 'gpu_started': False,
            'private_values_emitted': False,
        }, sort_keys=True))
        return 42


if __name__ == '__main__':
    raise SystemExit(main())

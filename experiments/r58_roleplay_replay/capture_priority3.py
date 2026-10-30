#!/usr/bin/env python3
"""R58 PRIVATE ONLY: capture three SQL JSONL records from stdin, no network/DB/model calls."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

SCHEMA = 'storyforge-r58-priority3-private-quarantine-v1'
EXPECTED_ROUTES = {'AUTHOR', 'CURRENT_PUBLIC', 'OLD_PUBLIC'}
EXPECTED_STATUS = 'NOT_ADMITTED_NOT_BYTE_EXACT__REPLAY_PENDING'
MAX_INPUT_BYTES = 50 * 1024 * 1024


class Hold(Exception):
    pass


def canonical(o: object) -> bytes:
    # Stable Python JSON fingerprint; not exact provider-request source bytes.
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_present(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def read_time(value: object, desc: str) -> datetime:
    if not is_present(value):
        raise Hold('missing ' + desc + ' timestamp')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError('timezone missing')
        return result
    except ValueError as exc:
        raise Hold('invalid ' + desc + ' timestamp') from exc


def safe_existing_parent(parent: Path) -> None:
    if not parent.is_absolute() or str(parent) in ('/', '/workspace', '/tmp'):
        raise Hold('output parent must be a dedicated absolute private directory')
    for part in (parent, *parent.parents):
        if part.is_symlink():
            raise Hold('symlinked path component forbidden')
    if not parent.is_dir():
        raise Hold('output parent does not exist')
    mode = stat.S_IMODE(parent.stat().st_mode)
    if mode & 0o077:
        raise Hold('output parent must be inaccessible to group/others (mode 0700)')


def validate_one(row: object) -> tuple[str, str]:
    if not isinstance(row, dict) or row.get('schema') != SCHEMA:
        raise Hold('invalid private source record schema')
    if row.get('status') != EXPECTED_STATUS or row.get('deployed_source_commit_verified') is not False:
        raise Hold('record must remain unadmitted and historical deployed SHA unverified')
    case = row.get('case')
    story = row.get('historical_approved_story')
    checkpoint = row.get('prior_checkpoint')
    history = row.get('history24')
    target = row.get('target')
    structural = row.get('structural_checks')
    if not all(isinstance(x, dict) for x in (case, story, checkpoint, target, structural)):
        raise Hold('missing structured source evidence')
    cohort = case.get('cohort')
    if cohort not in EXPECTED_ROUTES:
        raise Hold('unknown source route')
    if not all(is_present(case.get(k)) for k in
               ('story_id', 'session_id', 'target_message_id', 'target_created_at')):
        raise Hold('missing physical source id or timestamp')
    if not isinstance(case.get('turn_index'), int) or case['turn_index'] < 2:
        raise Hold('invalid target turn')
    target_time = read_time(case['target_created_at'], 'target')
    if not is_present(story.get('submission_id')) or not isinstance(story.get('v2_data'), dict):
        raise Hold('missing approved historical source card')
    if not isinstance(story.get('content_revision'), int):
        raise Hold('missing approved revision')
    if read_time(story.get('approval_at'), 'approval') >= target_time:
        raise Hold('approved story card must predate target')
    if not is_present(checkpoint.get('id')) or not isinstance(checkpoint.get('snapshot'), dict):
        raise Hold('missing historical checkpoint snapshot')
    if read_time(checkpoint.get('created_at'), 'checkpoint') >= target_time:
        raise Hold('checkpoint must predate target')
    if not isinstance(checkpoint.get('turn_index'), int) or checkpoint['turn_index'] * 2 >= case['turn_index']:
        raise Hold('checkpoint is not before the target physical turn')
    if not isinstance(history, list) or len(history) != 24:
        raise Hold('must have exactly 24 prior history rows')
    if (structural.get('prior_24_total') != 24 or structural.get('prior_24_completed') != 24
            or structural.get('post_target_ledger_events') != 0):
        raise Hold('prior history structural guard failed')
    seen = set()
    previous = -1
    for msg in history:
        if not isinstance(msg, dict) or not is_present(msg.get('id')) or msg['id'] in seen:
            raise Hold('invalid or duplicate message in prior history')
        seen.add(msg['id'])
        if msg.get('status') != 'completed' or msg.get('role') not in ('user', 'assistant'):
            raise Hold('prior history must have completed user/assistant rows only')
        if (not isinstance(msg.get('turn_index'), int) or msg['turn_index'] <= previous
                or msg['turn_index'] >= case['turn_index']):
            raise Hold('prior history turns must be strictly increasing before target')
        previous = msg['turn_index']
        if not isinstance(msg.get('content'), str):
            raise Hold('missing history source content')
        if read_time(msg.get('created_at'), 'history') > target_time:
            raise Hold('history message created after target')
    if not is_present(target.get('content')):
        raise Hold('target must contain non-empty text')
    return cohort, case['story_id']


def write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def capture(source: bytes, parent: Path, name: str) -> dict:
    safe_existing_parent(parent)
    if not is_present(name) or not all(c.isascii() and (c.isalnum() or c in '_-') for c in name):
        raise Hold('invalid snapshot directory name')
    final = parent / name
    if final.exists() or final.is_symlink():
        raise Hold('refuse overwrite or reuse existing snapshot')
    if len(source) > MAX_INPUT_BYTES:
        raise Hold('source exceeds size limit')
    try:
        lines = [x for x in source.splitlines() if x.strip()]
        if len(lines) != 3:
            raise Hold('expected exactly 3 private source JSONL records')
        objs = [json.loads(line.decode('utf-8')) for line in lines]
        routes_stories = [validate_one(row) for row in objs]
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Hold('invalid source JSONL or data encoding') from exc
    if {route for route, _ in routes_stories} != EXPECTED_ROUTES:
        raise Hold('missing or duplicate source route')
    if len({story for _, story in routes_stories}) != 3:
        raise Hold('same physical story ID in multiple source routes')
    if len({row['case']['target_message_id'] for row in objs}) != 3:
        raise Hold('duplicate target message ID')
    manifest = {
        'schema': 'storyforge-r58-priority3-private-capture-manifest-v1',
        'stage': 'PRIVATE_SOURCE_CAPTURE_ONLY__NOT_TRAIN_ADMITTED',
        'raw_jsonl_sha256': sha256(source),
        'raw_jsonl_size_bytes': len(source),
        'source_count': 3,
        'runtime_byte_exact_pass': 0,
        'cases': [
            {
                'cohort': row['case']['cohort'],
                'story_id': row['case']['story_id'],
                'message_id': row['case']['target_message_id'],
                'approved_submission_id': row['historical_approved_story']['submission_id'],
                'source_card_json_sha256': sha256(canonical(row['historical_approved_story']['v2_data'])),
                'checkpoint_json_sha256': sha256(canonical(row['prior_checkpoint']['snapshot'])),
                'history24_json_sha256': sha256(canonical(row['history24'])),
                'target_text_utf8_sha256': sha256(row['target']['content'].encode('utf-8')),
            }
            for row in objs
        ],
        'canonicalization': 'private-capture-python-json-canonical-v1 (not HTTP/provider bytes)',
    }
    os.mkdir(final, 0o700)
    try:
        # Keep incomplete directory after an interrupted write; refuse future reuse.
        write_exclusive(final / 'source.private.jsonl', source)
        write_exclusive(final / 'manifest.private.json', canonical(manifest) + b'\n')
        write_exclusive(final / 'CAPTURE_COMPLETE', b'SOURCE_CAPTURE_ONLY_NOT_TRAIN_ADMITTED\n')
    except BaseException:
        raise
    return {'status': 'PRIVATE_CAPTURE_COMPLETE_NOT_TRAIN_ADMITTED',
            'records': 3, 'runtime_byte_exact_pass': 0}


def main() -> int:
    p = argparse.ArgumentParser(description='Capture 3 PRIVATE R58 JSONL records, without logging content.')
    p.add_argument('--private-parent', required=True, help='pre-existing mode-0700 POSIX private directory')
    p.add_argument('--name', required=True, help='new immutable subdirectory name')
    args = p.parse_args()
    try:
        source = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        print(json.dumps(capture(source, Path(args.private_parent), args.name), sort_keys=True))
        return 0
    except Hold as exc:
        print('HOLD: ' + str(exc), file=sys.stderr)
        return 42


if __name__ == '__main__':
    raise SystemExit(main())

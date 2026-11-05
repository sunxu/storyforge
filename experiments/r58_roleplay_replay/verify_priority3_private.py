#!/usr/bin/env python3
"""R58 PRIVATE: verify sealed source capture without printing private IDs, text, or hashes.

No network, no database, no modification to captured files. The result is source
provenance integrity only; it is NOT historical provider-request parity or SFT admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from capture_priority3 import (
    EXPECTED_ROUTES, MAX_INPUT_BYTES, Hold, canonical, safe_existing_parent,
    sha256, validate_one,
)

MANIFEST_SCHEMA = 'storyforge-r58-priority3-private-capture-manifest-v1'
EXPECTED_MARKER = b'SOURCE_CAPTURE_ONLY_NOT_TRAIN_ADMITTED\n'
EXPECTED_STAGE = 'PRIVATE_SOURCE_CAPTURE_ONLY__NOT_TRAIN_ADMITTED'
EXPECTED_CANON = 'private-capture-python-json-canonical-v1 (not HTTP/provider bytes)'
FINGERPRINT_FIELDS = (
    'source_card_json_sha256', 'checkpoint_json_sha256',
    'history24_json_sha256', 'target_text_utf8_sha256',
)


def read_private_file(path: Path, limit: int) -> bytes:
    # Ensure no symlinks, hardlinks, device files or group-readable files.
    meta = path.lstat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
        raise Hold('private capture member must be one regular non-hardlinked file')
    if stat.S_IMODE(meta.st_mode) != 0o600:
        raise Hold('private capture member requires mode 0600')
    if meta.st_size > limit:
        raise Hold('private capture member exceeds size limit')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as f:
        return f.read(limit + 1)


def verify(folder: Path) -> dict:
    safe_existing_parent(folder)
    if stat.S_IMODE(folder.stat().st_mode) != 0o700:
        raise Hold('private capture directory requires mode 0700')
    if not folder.parent.is_dir():
        raise Hold('private capture parent missing')
    safe_existing_parent(folder.parent)

    marker = read_private_file(folder / 'CAPTURE_COMPLETE', 128)
    if marker != EXPECTED_MARKER:
        raise Hold('capture completion marker invalid')
    raw = read_private_file(folder / 'source.private.jsonl', MAX_INPUT_BYTES)
    manifest_data = read_private_file(folder / 'manifest.private.json', 1048576)
    try:
        manifest = json.loads(manifest_data)
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Hold('private source or manifest JSON invalid') from exc
    if not isinstance(manifest, dict) or manifest.get('schema') != MANIFEST_SCHEMA:
        raise Hold('private manifest schema invalid')
    if manifest.get('stage') != EXPECTED_STAGE or manifest.get('runtime_byte_exact_pass') != 0:
        raise Hold('private manifest admission stage invalid')
    if manifest.get('canonicalization') != EXPECTED_CANON:
        raise Hold('private fingerprint canonicalization invalid')
    if (manifest.get('raw_jsonl_size_bytes') != len(raw)
            or manifest.get('raw_jsonl_sha256') != sha256(raw)):
        raise Hold('private source file checksum mismatch')
    if len(rows) != 3 or manifest.get('source_count') != 3:
        raise Hold('private capture must contain exactly three cases')
    records = manifest.get('cases')
    if not isinstance(records, list) or len(records) != 3:
        raise Hold('private case manifest incomplete')

    actual_routes = []
    story_ids = set()
    message_ids = set()
    checked = 0
    for row, saved in zip(rows, records):
        route, story_id = validate_one(row)
        actual_routes.append(route)
        if not isinstance(saved, dict):
            raise Hold('private per-case manifest record invalid')
        if (saved.get('cohort') != route
                or saved.get('story_id') != story_id
                or saved.get('message_id') != row['case']['target_message_id']
                or saved.get('approved_submission_id')
                    != row['historical_approved_story']['submission_id']):
            raise Hold('private provenance identifier mismatch')
        story_ids.add(story_id)
        message_ids.add(row['case']['target_message_id'])
        values = (
            canonical(row['historical_approved_story']['v2_data']),
            canonical(row['prior_checkpoint']['snapshot']),
            canonical(row['history24']),
            row['target']['content'].encode('utf-8'),
        )
        for key, value in zip(FINGERPRINT_FIELDS, values):
            if saved.get(key) != sha256(value):
                raise Hold('private per-case source fingerprint mismatch')
            checked += 1

    if (set(actual_routes) != EXPECTED_ROUTES or len(story_ids) != 3
            or len(message_ids) != 3):
        raise Hold('private source route or uniqueness mismatch')
    return {
        'status': 'R58_OWNER_LOCAL_PRIVATE_CAPTURE_RECHECK_PASS',
        'records': 3,
        'case_fingerprints_verified': checked,
        'private_source_file_sha256': 'PASS',
        'private_file_permissions': 'PASS',
        'training_admission': 'HOLD',
        'runtime_request_byte_exact': 'HOLD',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify R58 private capture; no secret output.')
    parser.add_argument('--private-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.private_dir), sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError) as exc:
        # Do not print exception strings from OS/JSON: they can contain secret paths or values.
        print('R58_LOCAL_CAPTURE_RECHECK: HOLD (integrity, permission, or file error)',
              file=sys.stderr)
        return 42


if __name__ == '__main__':
    raise SystemExit(main())

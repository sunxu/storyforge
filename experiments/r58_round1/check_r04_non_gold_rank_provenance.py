#!/usr/bin/env python3
"""R58 G1: immutable R04/Gold108 non-Gold worlds -> historical rank07/11 provenance.

Owner-Mac, CPU-only, read-only. Reads three Git-resident metadata/snapshot
blobs plus immutable source manifest. Snapshot narrative bytes are never
JSON-decoded, printed or exported. No R50, private candidate ledgers,
original raw story archives, or remote HF data. G1 remains HOLD.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

from check_r04_non_gold_uuid import (
    GOLD108_BLOB,
    GOLD108_SHA256,
    Hold,
    R04_BLOB,
    R04_SHA256,
    UUID,
    frozen_blob,
    r04_non_gold_worlds,
    structural_world_rows,
)

INVENTORY_BLOB = '1b28b2fa935d6cac5464e62d3eaebb8aed5758b6'
MANIFEST_BLOB = 'd83e609c0b529ad8892200a86a05dbd779e9e9c2'
EXPECTED_BUNDLE_SHA256 = 'b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb'
REQUIRED_INVENTORY_COLUMNS = {
    'story_number', 'story_id', 'raw_archive_sha256',
    'source_json_equals_jsonl', 'messages_total',
}
SHA256 = re.compile(r'[a-f0-9]{64}\Z')

def parse_rank_inventory(blob: bytes) -> tuple[dict[int, str], dict[int, str]]:
    """Project rank, UUID, archive digest only; never include private identifiers in SAFE JSON."""
    if not 0 < len(blob) <= 20_000:
        raise Hold('source inventory blob size invalid')
    try:
        text = blob.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text, newline=''))
        if reader.fieldnames is None or not REQUIRED_INVENTORY_COLUMNS <= set(reader.fieldnames):
            raise Hold('missing source inventory columns')
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise Hold('duplicate source inventory columns')
        rows = list(reader)
    except (UnicodeError, csv.Error):
        raise Hold('source inventory parse invalid')
    if len(rows) != 10 or any(not isinstance(x, dict) or None in x for x in rows):
        raise Hold('source inventory ten-row schema mismatch')
    rank_uuid: dict[int, str] = {}
    rank_archives: dict[int, str] = {}
    for row in rows:
        rank = row.get('story_number', '')
        if not isinstance(rank, str) or not re.fullmatch(r'(?:[6-9]|1[0-5])', rank):
            raise Hold('source inventory out-of-scope story rank')
        number = int(rank)
        uid = row.get('story_id')
        archive = row.get('raw_archive_sha256')
        if (number in rank_uuid or not isinstance(uid, str) or UUID.fullmatch(uid) is None
            or not isinstance(archive, str) or SHA256.fullmatch(archive) is None):
            raise Hold('source inventory duplicate or malformed UUID/archive digest')
        if row.get('source_json_equals_jsonl') not in ('True', 'true', 'TRUE', '1'):
            # The original source inventory is expected to certify JSON and JSONL equivalence.
            raise Hold('source story JSON/JSONL equivalence not established')
        if not isinstance(row.get('messages_total'), str) or not row['messages_total'].isdigit() or int(row['messages_total']) <= 0:
            raise Hold('source message counts invalid')
        rank_uuid[number] = uid.lower()
        rank_archives[number] = archive
    if set(rank_uuid) != set(range(6, 16)) or len(set(rank_uuid.values())) != 10:
        raise Hold('source inventory rank/UUID completeness failure')
    return rank_uuid, rank_archives


def verify_nested_source_manifest(blob: bytes, ranks: dict[int, str]) -> None:
    """Bind all ten historical rank/UUID rows to archived raw ZIP SHA256s."""
    if not 0 < len(blob) <= 25_000:
        raise Hold('source manifest size invalid')
    try:
        obj = json.loads(blob)
    except (UnicodeError, ValueError):
        raise Hold('source manifest malformed')
    if (not isinstance(obj, dict)
        or obj.get('schema') != 'storyforge.v0.2.06-15.github-evidence-index.v1'
        or obj.get('bundle_sha256') != EXPECTED_BUNDLE_SHA256
        or obj.get('raw_story_zip_count') != 10
        or not isinstance(obj.get('nested_source_sha256'), list)
        or len(obj['nested_source_sha256']) != 10):
        raise Hold('source archive manifest frozen identity mismatch')
    seen = set()
    for row in obj['nested_source_sha256']:
        if not isinstance(row, dict):
            raise Hold('non-object historical archive record')
        rank, sha = row.get('story_number'), row.get('raw_zip_sha256')
        if (type(rank) is not int or rank not in ranks or rank in seen
            or not isinstance(sha, str) or SHA256.fullmatch(sha) is None
            or ranks[rank] != sha):
            raise Hold('rank-specific raw ZIP SHA256 linkage mismatch')
        seen.add(rank)
    if seen != set(range(6, 16)):
        raise Hold('source raw ZIP rank manifest incomplete')


def reconcile(r04: bytes, gold: bytes, inventory: bytes, manifest: bytes,
              r04_digest: str = R04_SHA256, gold_digest: str = GOLD108_SHA256,
              verify_metadata_git_pins: bool = True) -> dict:
    if verify_metadata_git_pins:
        def git_object_sha1(raw: bytes) -> str:
            return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        if (git_object_sha1(inventory) != INVENTORY_BLOB
            or git_object_sha1(manifest) != MANIFEST_BLOB):
            raise Hold('immutable inventory or source manifest Git blob mismatch')
    ranks, raw_archives = parse_rank_inventory(inventory)
    verify_nested_source_manifest(manifest, raw_archives)
    r04_worlds, _ = structural_world_rows(r04, r04_digest, 150, 10)
    gold_worlds, _ = structural_world_rows(gold, gold_digest, 108, 8)
    non_gold = r04_non_gold_worlds(r04, gold, r04_digest, gold_digest)
    if r04_worlds != set(ranks.values()):
        raise Hold('ten-world R04 snapshot universe != original rank inventory')
    expected_non_gold = {ranks[7], ranks[11]}
    if non_gold != expected_non_gold:
        raise Hold('non-Gold R04 worlds are not exactly rank07 and rank11')
    if gold_worlds != set(ranks.values()) - expected_non_gold:
        raise Hold('Gold108 world composition does not match historical rank inventory')
    return {
        'schema': 'r58_round1_g1_r04_non_gold_rank0711_provenance_safe_v1',
        'status': 'R58_G1_R04_NON_GOLD_RANK07_11_PROVENANCE_VERIFIED__OTHER_REMOTE_HOLD',
        'historical_rank_inventory_source_worlds': 10,
        'historical_rank_inventory_06_through_15_complete': True,
        'rank_inventory_and_source_manifest_blob_pins_verified': verify_metadata_git_pins,
        'original_raw_archive_sha256_links_verified': 10,
        'r04_frozen_curated_rows': 150,
        'gold108_frozen_accepted_rows': 108,
        'r04_minus_gold108_world_count': 2,
        'r04_minus_gold108_is_exactly_ranks_07_and_11': True,
        'rank_07_and_11_story_uuid_mapping_proven_by_frozen_inventory': True,
        'r56_known_rank_07_11_source_scope_covered': True,
        'other_protected_uuids_covered': False,
        'remote_trainer_primary_inputs_verified': False,
        'all_actual_sft_runs_and_input_sources_proven_complete': False,
        'source_registry_complete': False,
        'private_ledgers_accessed': False,
        'r50_protected_content_accessed': False,
        'original_raw_story_archives_accessed': False,
        'source_narratives_json_decoded_or_exported': False,
        'story_uuids_exported': False,
        'g1_clearance': 'HOLD',
        'train_admitted': 0, 'validation_admitted': 0, 'teacher_admitted': 0,
        'expansion_allowed': False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        r04 = frozen_blob(args.repo_root, R04_BLOB, 2_000_000)
        gold = frozen_blob(args.repo_root, GOLD108_BLOB, 2_000_000)
        inventory = frozen_blob(args.repo_root, INVENTORY_BLOB, 20_000)
        manifest = frozen_blob(args.repo_root, MANIFEST_BLOB, 25_000)
        result = reconcile(r04, gold, inventory, manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (Hold, ValueError, OSError, TypeError, KeyError):
        # Never print exception details: errors may contain private source info.
        print('R58_G1_R04_RANK_PROVENANCE: HOLD (frozen source or rank linkage mismatch)', file=sys.stderr)
        return 42


if __name__ == '__main__':
    raise SystemExit(main())

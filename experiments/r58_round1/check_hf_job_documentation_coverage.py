#!/usr/bin/env python3
"""R58 G1: HF Jobs versus frozen Git documentation ID coverage (SAFE, read-only).

The query only uses JobInfo.id and JobInfo.status.stage. Git read is limited to
tracked documentation blobs at HEAD. Document mentions are NOT evidence of
actual training behavior or complete provenance. No secret/command/log access,
no source story reads, and no changes to any private ledger.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

from check_hf_training_job_inventory import (
    JOB_ID, KNOWN_SFT_JOBS, Hold, stage_only,
)

DOC_PATHS = ('docs/evidence', 'docs/handoffs', 'docs/HF_RUN_REGISTRY.md')
DOC_SUFFIXES = ('.md', '.json')
JOB_IN_DOC = re.compile(rb'(?<![0-9a-fA-F])[0-9a-fA-F]{24}(?![0-9a-fA-F])')
GIT_SHA = re.compile(r'^[0-9a-f]{40}$')
MAX_DOCS = 800
MAX_DOC_BYTES = 400_000
MAX_JOBS = 100_000
SCHEMA = 'r58_round1_g1_hf_job_documentation_coverage_safe_v1'


def checked_tree_entries(raw: bytes) -> list[tuple[str, str]]:
    if not raw:
        raise Hold('no frozen documentation at HEAD')
    found: list[tuple[str, str]] = []
    seen = set()
    for part in raw.split(b'\0'):
        if not part:
            continue
        try:
            meta, pathb = part.split(b'\t', 1)
            mode, typ, sha = meta.decode('ascii').split(' ')
            path = pathb.decode('utf-8')
        except (ValueError, UnicodeError):
            raise Hold('malformed Git tree entry')
        if not (path == 'docs/HF_RUN_REGISTRY.md' or
                path.startswith('docs/evidence/') or
                path.startswith('docs/handoffs/')):
            raise Hold('unexpected tree path')
        # These directories also include tracked SAFE .sql queries. They are
        # intentionally outside the approved evidence-document scope.
        if not path.endswith(DOC_SUFFIXES):
            continue
        if mode != '100644' or typ != 'blob' or not GIT_SHA.fullmatch(sha):
            raise Hold('unsupported documentation Git object')
        if path in seen or '..' in Path(path).parts:
            raise Hold('documentation tree duplicate/path mismatch')
        seen.add(path)
        found.append((path, sha))
        if len(found) > MAX_DOCS:
            raise Hold('too many documents')
    if not found or 'docs/HF_RUN_REGISTRY.md' not in seen:
        raise Hold('required registry is absent')
    return found


def git_cmd(repo: Path, command: list[str], limit: int) -> bytes:
    try:
        p = subprocess.run(['git', '-C', str(repo), *command],
                           capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Hold('Git documentation unavailable')
    if p.returncode or len(p.stdout) > limit:
        raise Hold('Git documentation read or bound failed')
    return p.stdout


def frozen_job_mentions(repo: Path) -> tuple[set[str], int]:
    tree = git_cmd(repo, ['ls-tree', '-r', '-z', 'HEAD', '--', *DOC_PATHS],
                   MAX_DOCS * 160)
    entries = checked_tree_entries(tree)
    mentions = set()
    for _path, sha in entries:
        # The blob SHA is read from the frozen Git tree. Avoid local worktree
        # modifications, untracked private files, symlinks and LFS downloads.
        size_raw = git_cmd(repo, ['cat-file', '-s', sha], 20)
        try:
            size = int(size_raw.strip())
        except ValueError:
            raise Hold('invalid Git blob byte count')
        if not 0 <= size <= MAX_DOC_BYTES:
            raise Hold('oversized documentation blob')
        blob = git_cmd(repo, ['cat-file', 'blob', sha], MAX_DOC_BYTES)
        if len(blob) != size or b'\0' in blob:
            raise Hold('documentation blob changed/invalid')
        mentions.update(x.decode('ascii').lower() for x in JOB_IN_DOC.findall(blob))
    return mentions, len(entries)


def classify(jobs, documented: set[str], namespace: str, docs_read: int) -> dict:
    if not isinstance(documented, set) or not all(isinstance(x, str) and
        JOB_ID.fullmatch(x) for x in documented):
        raise Hold('malformed documented Job IDs')
    if not isinstance(docs_read, int) or docs_read <= 0:
        raise Hold('frozen documentation scan not completed')
    stages = Counter(); known = set(); found = set()
    documented_other = Counter(); not_documented_other = Counter()
    known_set = set(KNOWN_SFT_JOBS.values())
    for job in jobs:
        ident = getattr(job, 'id', None)
        if not isinstance(ident, str) or not JOB_ID.fullmatch(ident) or ident in found:
            raise Hold('invalid or repeated Job ID')
        if len(found) >= MAX_JOBS:
            raise Hold('Jobs listing exceeds bounded scan')
        stage = stage_only(job)
        found.add(ident); stages[stage] += 1
        if ident in known_set:
            known.add(ident)
        elif ident in documented:
            documented_other[stage] += 1
        else:
            not_documented_other[stage] += 1
    summarize_from_facts(found, known, namespace)
    other_n = len(found)-len(known)
    mentioned = sum(documented_other.values())
    nonmentioned = sum(not_documented_other.values())
    if mentioned+nonmentioned != other_n or sum(stages.values()) != len(found):
        raise Hold('partition accounting failed')
    return {
        'schema': SCHEMA,
        'status': 'R58_G1_HF_JOB_GIT_DOCUMENT_COVERAGE_SCANNED__CLASSIFICATION_AND_PRIMARY_INPUT_HOLD',
        'queried_namespace':namespace,
        'hf_jobs_returned':len(found),
        'known_parameter_update_job_ids_found':len(known),
        'known_parameter_update_job_ids_missing':len(known_set)-len(known),
        'other_job_ids_unclassified':other_n,
        'other_job_ids_mentioned_in_frozen_safe_docs':mentioned,
        'other_job_ids_not_mentioned_in_frozen_safe_docs':nonmentioned,
        'other_documented_job_status_counts':dict(sorted(documented_other.items())),
        'other_undocumented_job_status_counts':dict(sorted(not_documented_other.items())),
        'frozen_git_docs_scanned': docs_read,
        'frozen_git_docs_query_complete': True,
        'document_mention_proves_non_training': False,
        'undocumented_job_proves_training': False,
        'all_job_roles_proven': False,
        'all_historical_jobs_including_deleted_other_namespaces_proven_complete':False,
        'remote_trainer_primary_input_bytes_verified':False,
        'all_actual_sft_runs_and_input_sources_proven_complete':False,
        'other_protected_uuids_covered':False,
        'source_registry_complete':False,
        'job_commands_arguments_environment_or_secrets_from_hf_accessed':False,
        'r50_protected_test_content_accessed':False,
        'story_uuids_or_private_sources_exported':False,
        'g1_clearance':'HOLD',
        'train_admitted':0,'validation_admitted':0,'teacher_admitted':0,
        'expansion_allowed':False,
    }


def summarize_from_facts(found: set[str], known: set[str], namespace: str) -> bool:
    # Share the existing namespace validation and immutable five-known-Job mapping.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', namespace):
        raise Hold('invalid HF namespace')
    if len(set(KNOWN_SFT_JOBS.values())) != 5 or not known.issubset(found):
        raise Hold('known Job reference inconsistency')
    return True


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,required=True)
    ap.add_argument('--namespace',default='adradar')
    a=ap.parse_args(argv)
    try:
        documented, n = frozen_job_mentions(a.repo_root)
        from huggingface_hub import HfApi
        output = classify(HfApi().list_jobs(namespace=a.namespace), documented,
                          a.namespace, n)
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception:
        print('R58_G1_HF_DOC_COVERAGE: HOLD (frozen Git docs or read-only Jobs unavailable)', file=sys.stderr)
        return 42

if __name__=='__main__':
    raise SystemExit(main())

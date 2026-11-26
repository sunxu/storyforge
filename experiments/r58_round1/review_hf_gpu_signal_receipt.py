#!/usr/bin/env python3
"""R58 G1: offline cross-check of sealed GPU signal and 60-job metadata ledgers.

NO network/HF calls, NO reading remote logs, NO training artifacts or narratives.
Reads only previous Owner PRIVATE JSON metadata receipts; never exports job IDs.
Emits SAFE aggregates and optionally a fresh O_EXCL 0600 priority-1 record.
Always HOLD. Any ambiguous ledger or unexpected counts fail closed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path

from probe_hf_gpu_job_logs import OUTPUT_SCHEMA, authorized_private_path, read_input

SAFE_SCHEMA = 'r58_round1_g1_gpu_signal_priority_crosscheck_safe_v1'
PRIVATE_SCHEMA = 'r58_round1_g1_gpu_signal_priority_case_private_v1'
ID = re.compile(r'^[0-9a-f]{24}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
ALLOWED_SIGNALS = {
    'OPTIMIZER_STEP_LITERAL', 'TRAINER_FINAL_METRIC_PAIR',
    'TRAINING_LOSS_GRAD_TELEMETRY', 'GLOBAL_STEP_TRAIN_TEXT',
}
STAGES = {'COMPLETED', 'ERROR', 'CANCELED'}
ALLOWED_STATES = {
    'POTENTIAL_OPTIMIZER_LOG_INDICATOR',
    'NO_INDICATOR_OBSERVED__NOT_EXCLUDED',
}
MAX_BYTES = 120_000

class Hold(Exception):
    pass


def read_gpu_receipt(path: Path, source: dict, expected_sha: str) -> tuple[dict, dict]:
    authorized_private_path(path, input_mode=True)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as f:
        st = os.fstat(f.fileno())
        if (not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077
                or not 0 < st.st_size <= MAX_BYTES):
            raise Hold('unsafe GPU receipt metadata permissions or size')
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise Hold('GPU receipt too large')
    try:
        receipt = json.loads(raw)
    except (ValueError, UnicodeError):
        raise Hold('invalid GPU receipt JSON')
    if (not isinstance(receipt, dict) or receipt.get('schema') != OUTPUT_SCHEMA
            or receipt.get('status') != 'GPU_LOG_SIGNAL_REVIEW_ONLY__ALL_PENDING'
            or receipt.get('namespace') != 'adradar'
            or receipt.get('input_private_ledger_sha256_PRIVATE') != expected_sha
            or receipt.get('g1_clearance') != 'HOLD'
            or receipt.get('expansion_allowed') is not False):
        raise Hold('GPU receipt source/guard mismatch')
    rows = receipt.get('entries')
    if not isinstance(rows, list) or len(rows) != 18:
        raise Hold('GPU receipt wrong row count')
    gpu = {x['hf_job_id_PRIVATE']: x['stage'] for x in source['gpu']}
    if len(gpu) != 18:
        raise Hold('source GPU count wrong')
    seen = set(); status = Counter(); by_stage = Counter(); positives = []
    for row in rows:
        if not isinstance(row, dict):
            raise Hold('invalid GPU row')
        jid = row.get('hf_job_id_PRIVATE')
        if (not isinstance(jid, str) or not ID.fullmatch(jid)
                or jid not in gpu or jid in seen or row.get('stage') != gpu[jid]):
            raise Hold('GPU receipt row missing, duplicate, or source stage drift')
        seen.add(jid)
        stage = row['stage']; state = row.get('scan_state')
        if stage not in STAGES or state not in ALLOWED_STATES:
            raise Hold('unexpected stage or scan state')
        cls = row.get('indicator_classes')
        if (not isinstance(cls, list) or len(cls) != len(set(cls))
                or any(x not in ALLOWED_SIGNALS for x in cls)
                or (state == 'POTENTIAL_OPTIMIZER_LOG_INDICATOR') != bool(cls)):
            raise Hold('signal state / classes inconsistent')
        if (row.get('parameter_update_proven') is not False
                or row.get('confirmed_no_parameter_update') is not False
                or row.get('primary_input_bytes_verified') is not False):
            raise Hold('unexpected claimed approval')
        digest = row.get('log_sha256_PRIVATE')
        if not isinstance(digest, str) or SHA.fullmatch(digest) is None:
            raise Hold('log SHA256 absent or malformed')
        if (type(row.get('log_bytes_scanned')) is not int or row['log_bytes_scanned'] < 0
                or type(row.get('lines_scanned')) is not int or row['lines_scanned'] < 0):
            raise Hold('invalid log aggregate')
        status[state] += 1
        by_stage[(state, stage)] += 1
        if state == 'POTENTIAL_OPTIMIZER_LOG_INDICATOR':
            positives.append(row)
    if (seen != set(gpu) or len(positives) != 1
            or status['NO_INDICATOR_OBSERVED__NOT_EXCLUDED'] != 17):
        raise Hold('frozen 1+17 scan cohort mismatch')
    pos = positives[0]
    safe = {
        'schema': SAFE_SCHEMA,
        'status': 'R58_G1_GPU_SIGNAL_ONE_CASE_PRIORITIZED__TRAINING_AND_SOURCE_HOLD',
        'prior_unknown_gpu_jobs': 18,
        'prior_unknown_cpu_jobs': 42,
        'potential_indicator_jobs': 1,
        'no_indicator_jobs_not_excluded': 17,
        'priority_job_stage': pos['stage'],
        'priority_job_indicator_classes': sorted(pos['indicator_classes']),
        'gpu_signal_ledger_crosslinked_to_unknown_ledger': True,
        'gpu_receipt_job_ids_and_stages_match_frozen_unknown_ledger': True,
        'existing_gpu_log_sha256_present': True,
        'historical_job_logs_read_this_step': False,
        'hf_api_called_this_step': False,
        'raw_logs_or_job_ids_exported': False,
        'parameter_updates_proven_by_log_signal': False,
        'no_indicator_is_nontraining_proof': False,
        'remote_trainer_primary_input_bytes_verified': False,
        'all_actual_sft_runs_and_input_sources_proven_complete': False,
        'other_protected_worlds_covered': False,
        'source_registry_complete': False,
        'r50_protected_content_accessed_this_step': False,
        'g1_clearance': 'HOLD',
        'train_admitted': 0, 'validation_admitted': 0, 'teacher_admitted': 0,
        'expansion_allowed': False,
    }
    private = {
        'schema': PRIVATE_SCHEMA,
        'status': 'ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED',
        'namespace': 'adradar',
        'hf_job_id_PRIVATE': pos['hf_job_id_PRIVATE'],
        'stage': pos['stage'],
        'indicator_classes': sorted(pos['indicator_classes']),
        'prior_gpu_log_sha256_PRIVATE': pos['log_sha256_PRIVATE'],
        'update_proof_status': 'PENDING_PRIMARY_RUN_ARTIFACT',
        'training_input_sha256_status': 'NOT_VERIFIED',
        'train_validation_usage_status': 'NOT_VERIFIED',
        'r50_content_accessed_this_step': False,
        'g1_clearance': 'HOLD',
        'expansion_allowed': False,
    }
    return safe, private


def write_private(path: Path, data: dict):
    authorized_private_path(path, input_mode=False)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write('\n')
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-unknown-ledger', type=Path, required=True)
    parser.add_argument('--private-gpu-signal-ledger', type=Path, required=True)
    parser.add_argument('--private-priority-output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        paths = (args.private_unknown_ledger, args.private_gpu_signal_ledger, args.private_priority_output)
        if len(set(paths)) != 3:
            raise Hold('overlapping input/output paths forbidden')
        authorized_private_path(args.private_priority_output, input_mode=False)
        source, digest = read_input(args.private_unknown_ledger)
        safe, priority = read_gpu_receipt(args.private_gpu_signal_ledger, source, digest)
        write_private(args.private_priority_output, priority)
        safe['private_single_case_priority_ledger_written'] = True
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception:
        print('R58_G1_GPU_SIGNAL_PRIORITY: HOLD (private receipt missing, inconsistent or destination unsafe)', file=sys.stderr)
        return 42


if __name__ == '__main__':
    raise SystemExit(main())

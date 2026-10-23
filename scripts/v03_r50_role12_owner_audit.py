#!/usr/bin/env python3
"""StoryForge R50: role-order/12 trailing-User audit of frozen private input and pinned HF report.

Owner Mac: stdlib only, no network, no transformers, no model execution.
Public, reviewed input builder reference: audit/r49-r50-source-intake-20261015
scripts/v03_r50_cpu_tokenizer_preflight_46.py (Git blob c546194bd02608e921d9c673fa3e549c022468ae).

Do not print IDs, story text, messages, per-case digests or token counts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

RUN_KEY = 'r50-cpu46-20261022T164410Z-305591'
JOB_ID = '6ada3f1d925af0e27d4f569f'
CASES_SHA = '109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2'
SYSTEM_SHA = '5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83'
REPORT_SHA = '56aeac340ac1c0be1d0000314bcbdc72abd2f59582d643eee9e50698529f748e'
INTAKE_SHA = '9b922c53cdafab11bd523e9c70f71a66a45d631da2b033487f2320b4150fe781'
REV = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
BUILDER_BLOB_SHA = 'c546194bd02608e921d9c673fa3e549c022468ae'
TOKENIZER_JSON_SHA = '0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'
TOKENIZER_CONFIG_SHA = 'b11349aafa7cdc6a320767cf7ceb29ed82f7eda5d65e8e0819e76f0ce947bf27'
CHAT_TEMPLATE_SHA = 'c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041'
EXPECTED_COUNT = 46
EXPECTED_HISTORIES = 364
EXPECTED_TRAILING_USER = 12
MAX_CONTEXT = 16384
RESERVED = 1536
REPORT_SCHEMA = 'storyforge-r50-cpu-real-tokenizer-preflight-v1'

class GateError(Exception):
    pass

def demand(value: bool, code: str) -> None:
    if not value:
        raise GateError(code)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_bytes(path: Path) -> bytes:
    demand(path.is_file() and not path.is_symlink(), 'INPUT_MISSING_OR_SYMLINK')
    return path.read_bytes()

def read_json(path: Path) -> tuple[bytes, object]:
    raw = read_bytes(path)
    try:
        return raw, json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise GateError('INPUT_INVALID_JSON') from None

def build_messages(case: dict, system: str) -> list[dict]:
    """Independently replay exact Option A builder, without tokenization.

    Source identical in structure to the protected original preflight.
    Do not import arbitrary private script or evaluate dynamic expressions.
    """
    demand(isinstance(case, dict), 'BAD_CASE_OBJECT')
    for k in ('history', 'world_card', 'long_term_rules', 'user_input', 'case_id'):
        demand(k in case, 'CASE_REQUIRED_FIELD_MISSING')
    history = case['history']
    demand(isinstance(history, list) and len(history) > 0, 'INVALID_HISTORY_COLLECTION')
    demand(all(isinstance(m, dict) and m.get('role') in ('user', 'assistant')
               and type(m.get('content')) is str for m in history), 'INVALID_HISTORY_ROLES')
    demand(type(case['world_card']) is str and isinstance(case['long_term_rules'], list)
           and all(type(v) is str for v in case['long_term_rules']), 'INVALID_WORLD_RULES')
    demand(type(case['user_input']) is str and type(case['case_id']) is str and case['case_id'],
           'INVALID_CASE_ID_OR_USER_INPUT')
    composed = (system + '\n\n[STORY_WORLD_CARD]\n' + case['world_card'] + '\n[/STORY_WORLD_CARD]'
                + '\n\n[STORY_LONG_TERM_RULES]\n' + '\n'.join(case['long_term_rules'])
                + '\n[/STORY_LONG_TERM_RULES]')
    return ([{'role': 'system', 'content': composed}]
            + [{'role': m['role'], 'content': m['content']} for m in history]
            + [{'role': 'user', 'content': case['user_input']}])

def in_git(path: Path) -> bool:
    return any((d / '.git').exists() for d in (path.parent, *path.parents))

def audit(candidates: Path, system_file: Path, private_report: Path,
          owner_intake: Path, *, pins: dict | None = None) -> dict:
    pins = pins or {
        'cases': CASES_SHA, 'system': SYSTEM_SHA, 'report': REPORT_SHA,
        'intake': INTAKE_SHA,
    }
    cases_raw = read_bytes(candidates)
    sys_raw = read_bytes(system_file)
    rep_raw, report = read_json(private_report)
    intake_raw, intake = read_json(owner_intake)
    for name, raw in (('cases', cases_raw), ('system', sys_raw),
                      ('report', rep_raw), ('intake', intake_raw)):
        demand(sha(raw) == pins[name], 'FROZEN_' + name.upper() + '_SHA_MISMATCH')
    try:
        system = sys_raw.decode('utf-8')
        cases = [json.loads(line) for line in cases_raw.decode('utf-8').splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise GateError('FROZEN_CANDIDATES_NOT_JSONL') from None
    demand(system.strip() != '', 'SYSTEM_EMPTY')
    demand(len(cases) == EXPECTED_COUNT, 'INCORRECT_CASE_COUNT')
    ids = [c.get('case_id') for c in cases if isinstance(c, dict)]
    demand(len(ids) == EXPECTED_COUNT and all(type(x) is str and x for x in ids),
           'DUPLICATE_OR_INVALID_CASE_IDS')
    demand(len(set(ids)) == EXPECTED_COUNT, 'DUPLICATE_OR_INVALID_CASE_IDS')

    demand(isinstance(intake, dict) and
           intake.get('schema') == 'storyforge-r50-hf-cpu46-local-intake-v2'
           and intake.get('status') == 'R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL'
           and intake.get('job_id_reported') == JOB_ID and intake.get('run_key') == RUN_KEY,
           'OWNER_INTAKE_IDENTITY_MISMATCH')
    demand(intake.get('remote_private_report_sha256') == pins['report']
           and intake.get('source_count') == EXPECTED_COUNT
           and intake.get('original_script_exit_0_and_json_generated') is True
           and intake.get('official_heldout_admitted') == 0
           and intake.get('final_seal') is False,
           'OWNER_INTAKE_STATUS_MISMATCH')

    demand(isinstance(report, dict) and report.get('schema') == REPORT_SCHEMA,
           'PRIVATE_REPORT_SCHEMA_HOLD')
    demand(report.get('status') == 'PREFLIGHT_ONLY_NO_FINAL_SEAL'
           and report.get('pinned_model_revision') == REV
           and report.get('candidate_original_sha256') == pins['cases']
           and report.get('system_sha256') == pins['system']
           and report.get('thinking_mode') == 'disabled'
           and report.get('max_context') == MAX_CONTEXT
           and report.get('reserved_output_tokens') == RESERVED
           and report.get('no_model_generation') is True
           and report.get('no_gpu') is True and report.get('no_final_heldout_seal') is True,
           'PRIVATE_REPORT_FROZEN_CONTRACT_MISMATCH')
    demand(report.get('strategy') == 'PRESERVE_CONSECUTIVE_USER_AND_INJECT_WORLD_RULES_TO_SHARED_SYSTEM__DRAFT_ONLY',
           'PRIVATE_REPORT_STRATEGY_MISMATCH')
    token_file_hashes = report.get('tokenizer_file_sha256')
    demand(isinstance(token_file_hashes, dict)
           and token_file_hashes.get('tokenizer.json') == TOKENIZER_JSON_SHA
           and token_file_hashes.get('tokenizer_config.json') == TOKENIZER_CONFIG_SHA
           and report.get('chat_template_sha256') == CHAT_TEMPLATE_SHA,
           'QWEN_FROZEN_TOKENIZER_OR_TEMPLATE_HASH_DRIFT')
    rows = report.get('cases')
    demand(type(rows) is list and len(rows) == EXPECTED_COUNT
           and report.get('case_count') == EXPECTED_COUNT
           and report.get('overflow_count') == 0, 'PRIVATE_REPORT_ROW_COUNT_MISMATCH')
    by_id = {}
    for row in rows:
        demand(isinstance(row, dict) and type(row.get('case_id')) is str
               and row.get('case_id') not in by_id, 'REPORT_DUPLICATE_OR_INVALID_ID')
        by_id[row['case_id']] = row
    demand(set(by_id) == set(ids), 'REPORT_CASE_SET_DIFFERS_FROM_FROZEN_SOURCE')

    historical = 0
    trailing = 0
    encoded_trailing = 0
    within_budget = 0
    builder_preserved = 0
    for case in cases:
        messages = build_messages(case, system)
        history = case['history']
        row = by_id[case['case_id']]
        historical += len(history)
        is_trailing = history[-1]['role'] == 'user'
        trailing += int(is_trailing)
        # Nothing may collapse two adjacent User roles or change content/order.
        original_history = [{'role': m['role'], 'content': m['content']} for m in history]
        demand(len(messages) == len(history) + 2
               and messages[0]['role'] == 'system'
               and messages[1:-1] == original_history
               and messages[-1] == {'role': 'user', 'content': case['user_input']}
               and (messages[-2]['role'] == 'user') == is_trailing,
               'DRAFT_BUILDER_CHANGED_HISTORY_ROLE_ORDER')
        builder_preserved += 1
        demand(type(row.get('history_count')) is int and row['history_count'] == len(history),
               'TOKEN_REPORT_HISTORY_COUNT_DIFFERS')
        demand(type(row.get('consecutive_user')) is bool and row['consecutive_user'] == is_trailing,
               'TOKEN_REPORT_CONSECUTIVE_USER_DIFFERS')
        n = row.get('input_tokens')
        demand(type(n) is int and n > 0
               and type(row.get('input_plus_output_budget')) is int
               and row['input_plus_output_budget'] == n + RESERVED,
               'TOKEN_REPORT_INPUT_LENGTH_INVALID')
        demand(type(row.get('within_budget')) is bool
               and row['within_budget'] == (n + RESERVED <= MAX_CONTEXT),
               'TOKEN_REPORT_BUDGET_FLAG_INVALID')
        demand(type(row.get('input_id_sha256')) is str
               and re.fullmatch('[0-9a-f]{64}', row['input_id_sha256']) is not None,
               'TOKEN_REPORT_ENCODING_PROOF_MISSING')
        if is_trailing:
            encoded_trailing += 1
        within_budget += int(row['within_budget'])
    demand(historical == EXPECTED_HISTORIES, 'FROZEN_HISTORY_TOTAL_DIFFERS')
    demand(trailing == EXPECTED_TRAILING_USER, 'FROZEN_TRAILING_USER_TOTAL_DIFFERS')
    demand(encoded_trailing == EXPECTED_TRAILING_USER, 'TRAILING_USER_ENCODING_INCOMPLETE')
    demand(within_budget == EXPECTED_COUNT, 'DRAFT_TOKEN_BUDGET_OVERFLOW')
    return {
        'schema': 'storyforge-r50-role12-private-owner-count-only-v1',
        'status': 'R50_ROLE12_SOURCE_TO_DRAFT_TEMPLATE_AND_TOKEN_REPORT_STRUCTURE_PASS__NOT_SEMANTIC_APPROVAL',
        'job_id': JOB_ID,
        'run_key': RUN_KEY,
        'source_sha256': pins['cases'],
        'system_sha256': pins['system'],
        'remote_private_report_sha256': pins['report'],
        'owner_intake_sha256': pins['intake'],
        'source_builder_git_blob_sha1': BUILDER_BLOB_SHA,
        'chat_template_sha256': CHAT_TEMPLATE_SHA,
        'tokenizer_json_sha256': TOKENIZER_JSON_SHA,
        'tokenizer_config_sha256': TOKENIZER_CONFIG_SHA,
        'frozen_candidate_count': EXPECTED_COUNT,
        'historical_message_count': historical,
        'history_roles_and_order_preserved_count': builder_preserved,
        'trailing_user_history_count': trailing,
        'trailing_user_consecutive_user_appended_count': trailing,
        'trailing_user_real_tokenizer_encoded_count': encoded_trailing,
        'within_draft_budget_count': within_budget,
        'draft_context_tokens': MAX_CONTEXT,
        'draft_reserved_output_tokens': RESERVED,
        'model_inference_executed': False,
        'paid_cpu_job_launched_by_this_audit': False,
        'no_raw_text_or_case_ids_in_receipt': True,
        'actual_four_arm_runtime_role_parity_verified': False,
        'trailing_user_interpretation_policy_approved': False,
        'r45_r50_world_semantic_isolation': 'HOLD',
        'official_heldout_admitted': 0,
        'final_seal': False,
    }

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ('candidates', 'system-file', 'private-report', 'owner-intake', 'output'):
        ap.add_argument('--'+k, required=True, type=Path)
    args = ap.parse_args()
    os.umask(0o077)
    try:
        output = args.output.expanduser().absolute()
        demand(not output.exists() and not output.is_symlink(), 'REFUSE_OUTPUT_OVERWRITE')
        demand(not in_git(output), 'REFUSE_PRIVATE_OUTPUT_INSIDE_GIT')
        result = audit(args.candidates, args.system_file, args.private_report, args.owner_intake)
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write('\n')
        print('R50_ROLE12_OWNER_DRAFT_STRUCTURE_AND_ENCODING_COUNTS_PASS__NO_HF_JOB')
        print('R50_ROLE12_RUNTIME_SEMANTICS_AND_WORLD_ISOLATION=HOLD')
        print('R50_ROLE12_SAFE_RESULT_WRITTEN')
        return 0
    except (OSError, GateError) as err:
        print('R50_ROLE12_AUDIT_HOLD__' + (str(err) if isinstance(err, GateError) else type(err).__name__),file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())

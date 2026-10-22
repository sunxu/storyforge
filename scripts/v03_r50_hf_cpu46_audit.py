#!/usr/bin/env python3
"""StoryForge R50 protected CPU tokenizer draft job, standard-library gate.

Stage, preflight, run and verify. Never prints private candidate text or case IDs.
HF worker may use transformers; Mac imports only Python standard library.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REV = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
MODEL = "Qwen/Qwen3.8-27B"
CASE_SHA = "109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2"
SYSTEM_SHA = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
RUN_RE = re.compile(r"r50-cpu46-\d{8}T\d{6}Z-\d{6}\Z")
FILES = (
    "code/v03_r50_hf_cpu46_audit.py",
    "code/v03_r50_hf_cpu46_worker.sh",
    "private/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl",
    "private/R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt",
    "private/R50_CPU_TOKENIZER_PREFLIGHT_46.py",
)
CASES = FILES[2]
SYSTEM = FILES[3]
ORIGINAL_PREFLIGHT = FILES[4]
REPORT = "R50_46_CPU_TOKENIZER_DRAFT_PRIVATE.json"
RECEIPT = "R50_CPU46_COUNT_ONLY_RECEIPT.json"
PRIVATE_LOG = "R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt"
LOCAL_ACCEPT = "R50_CPU46_OWNER_INTAKE_COUNT_ONLY.json"
STATUS = "R50_HF_CPU46_TOKENIZER_SCRIPT_COMPLETED__DRAFT_NOT_ADMITTED"

class GateError(ValueError):
    pass


def demand(cond: bool, code: str):
    if not cond:
        raise GateError(code)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verified_regular(path: Path):
    demand(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_INPUT")
    demand(path.stat().st_size > 0, "EMPTY_INPUT")


def write_new_json(path: Path, data: dict):
    demand(not path.exists() and not path.is_symlink(), "REFUSE_OVERWRITE")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as w:
        json.dump(data, w, indent=2, ensure_ascii=False, sort_keys=True)
        w.write('\n')


def pin_sources(root: Path):
    for name in FILES:
        verified_regular(root / name)
    demand(sha(root / CASES) == CASE_SHA, "R50_PRESEAL_INPUT_HASH_MISMATCH")
    demand(sha(root / SYSTEM) == SYSTEM_SHA, "R45_SYSTEM_DRAFT_HASH_MISMATCH")
    count = 0
    with (root / CASES).open('r', encoding='utf-8') as f:
        for line in f:
            demand(bool(line.strip()), "EMPTY_JSONL_LINE")
            demand(isinstance(json.loads(line), dict), "BAD_CASE_JSONL_OBJECT")
            count += 1
    demand(count == 46, "EXPECTED_46_PRESEAL_CASES")
    return count


def manifest(root: Path) -> str:
    return ''.join(f"{sha(root / name)}  {name}\n" for name in FILES)


def check_stage(root: Path):
    pin_sources(root)
    mf = root / 'SHA256SUMS.txt'
    verified_regular(mf)
    demand(mf.read_text(encoding='utf-8') == manifest(root), "BUNDLE_SHA256_MANIFEST_MISMATCH")
    discovered = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    demand(discovered == set(FILES) | {"SHA256SUMS.txt"}, "UNEXPECTED_STAGE_CONTENTS")
    return True


def stage(args):
    srcs = [Path(p).resolve(strict=True) for p in (args.candidates, args.system_file, args.preflight, args.audit_source, args.worker_source)]
    for p in srcs:
        verified_regular(p)
    demand(sha(srcs[0]) == CASE_SHA, "R50_PRESEAL_INPUT_HASH_MISMATCH")
    demand(sha(srcs[1]) == SYSTEM_SHA, "R45_SYSTEM_DRAFT_HASH_MISMATCH")
    root = Path(args.stage).expanduser()
    demand(not root.exists(), "STAGE_DIR_ALREADY_EXISTS")
    # No partial reuse: either fresh local stage or error.
    os.mkdir(root, 0o700)
    (root / 'code').mkdir(mode=0o700)
    (root / 'private').mkdir(mode=0o700)
    target = [root / CASES, root / SYSTEM, root / ORIGINAL_PREFLIGHT,
              root / FILES[0], root / FILES[1]]
    for a, b in zip(srcs, target):
        with a.open('rb') as r:
            fd = os.open(b, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as w:
                for c in iter(lambda: r.read(1024*1024), b''):
                    w.write(c)
    pin_sources(root)
    mf = root / 'SHA256SUMS.txt'
    fd = os.open(mf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(manifest(root))
    check_stage(root)
    print('R50_CPU46_STAGE_LOCAL_SHA256_PASS__NO_JOB')


def cpu_run(args):
    root = Path(args.stage)
    check_stage(root)
    demand(RUN_RE.fullmatch(args.run_key) is not None, "INVALID_RUN_KEY")
    demand(os.environ.get('CUDA_VISIBLE_DEVICES') == '', "GPU_DISABLED_ENV_REQUIRED")
    result = Path(args.output_dir)
    demand(not result.exists(), "RESULT_DIR_ALREADY_EXISTS")
    result.mkdir(parents=True, mode=0o700)

    import transformers  # Only used INSIDE remote HF CPU Job.
    from huggingface_hub import snapshot_download
    demand(transformers.__version__ == '5.16.1', "WRONG_TRANSFORMERS_VERSION")
    # Limit downloads to tokenizer metadata; never request model weights.
    tok_dir = snapshot_download(repo_id=MODEL, revision=REV,
        allow_patterns=['tokenizer.json','tokenizer_config.json','special_tokens_map.json',
                        'added_tokens.json','*.jinja','vocab.json','merges.txt','tokenizer.model'],
        local_dir='/tmp/storyforge-r50-qwen-tokenizer')
    snapshot = Path(tok_dir)
    verified_regular(snapshot / 'tokenizer.json')
    verified_regular(snapshot / 'tokenizer_config.json')
    tok_hashes = {p.name: sha(p) for p in sorted(snapshot.iterdir()) if p.is_file() and not p.name.startswith('.')}
    demand('tokenizer.json' in tok_hashes, "TOKENIZER_NOT_DOWNLOADED")

    out_report = result / REPORT
    cmd = [sys.executable, '-I', str((root / ORIGINAL_PREFLIGHT).resolve()),
           '--candidates', str(root / CASES), '--system-file', str(root / SYSTEM),
           '--tokenizer-snapshot', str(snapshot), '--thinking', 'disabled',
           '--max-context', '16384', '--reserved-output-tokens', '1536',
           '--output', str(out_report)]
    # Capture all potentially private stderr/stdout. Never print script output in HF Job logs.
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=2400, check=False)
    log = result / PRIVATE_LOG
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write('Original private preflight exit code: ' + str(run.returncode) + '\n')
        f.write('STDOUT_PRIVATE\n' + run.stdout[-50000:] + '\nSTDERR_PRIVATE\n' + run.stderr[-50000:] + '\n')
    demand(run.returncode == 0, "SOURCE_PREFLIGHT_RETURNED_ERROR")
    verified_regular(out_report)
    with out_report.open('r', encoding='utf-8') as f:
        report = json.load(f)
    demand(isinstance(report, dict), "TOKEN_REPORT_NOT_OBJECT")
    # Exit zero + a parseable report are not independent proof of 46 valid tokenizations.
    check_stage(root)  # Inputs and runnable code must remain unchanged.
    receipt = {
      'schema': 'storyforge-r50-hf-cpu46-draft-tokenizer-receipt-v2',
      'status': STATUS,
      'run_key': args.run_key,
      'job_id': os.environ.get('JOB_ID', ''),
      'tokenizer_model': MODEL, 'tokenizer_revision': REV,
      'transformers_version': transformers.__version__,
      'tokenizer_files_sha256': tok_hashes,
      'preseal_candidate_count': 46,
      'candidate_sha256': CASE_SHA, 'system_draft_sha256': SYSTEM_SHA,
      'original_preflight_script_sha256': sha(root / ORIGINAL_PREFLIGHT),
      'stage_manifest_sha256': sha(root / 'SHA256SUMS.txt'),
      'private_token_report_sha256': sha(out_report),
      'private_token_report_bytes': out_report.stat().st_size,
      'private_script_output_sha256': sha(log),
      'thinking': 'disabled', 'max_context_draft': 16384, 'reserved_output_draft': 1536,
      'report_json_parseable': True,
      'full_46_token_length_and_role_checks_independently_verified': False,
      'official_heldout_admitted': 0, 'final_seal': False,
      'gpu_used': False, 'model_inference_run': False, 'training_run': False,
      'semantic_world_isolation': 'HOLD',
    }
    write_new_json(result / RECEIPT, receipt)
    print(STATUS)
    print('R50_CPU46_COUNT_ONLY_RECEIPT_WRITTEN__NO_FINAL_SEAL')


def verify(args):
    root = Path(args.stage)
    check_stage(root)
    rfile = Path(args.receipt)
    report = Path(args.report)
    private_log = Path(args.private_log)
    for x in (rfile, report, private_log):
        verified_regular(x)
    receipt = json.loads(rfile.read_text(encoding='utf-8'))
    demand(receipt['schema'] == 'storyforge-r50-hf-cpu46-draft-tokenizer-receipt-v2', 'BAD_SCHEMA')
    demand(receipt['status'] == STATUS, 'UNEXPECTED_JOB_STATUS')
    demand(receipt['run_key'] == args.run_key and bool(RUN_RE.fullmatch(args.run_key)), 'BAD_RUN_KEY')
    demand(receipt['preseal_candidate_count'] == 46, 'INCORRECT_CASE_COUNT')
    demand(receipt['candidate_sha256'] == CASE_SHA and receipt['system_draft_sha256'] == SYSTEM_SHA, 'WRONG_INPUT_SHA')
    demand(receipt['original_preflight_script_sha256'] == sha(root / ORIGINAL_PREFLIGHT), 'WRONG_PREFLIGHT_SHA')
    demand(receipt['stage_manifest_sha256'] == sha(root / 'SHA256SUMS.txt'), 'WRONG_MANIFEST_SHA')
    demand(receipt['private_token_report_sha256'] == sha(report), 'WRONG_REPORT_SHA')
    demand(receipt['private_token_report_bytes'] == report.stat().st_size, 'WRONG_REPORT_SIZE')
    demand(receipt['private_script_output_sha256'] == sha(private_log), 'WRONG_JOB_LOG_SHA')
    demand(receipt['transformers_version'] == '5.16.1' and receipt['tokenizer_revision'] == REV, 'WRONG_RUNTIME')
    demand(receipt['tokenizer_model'] == MODEL and receipt['report_json_parseable'] is True, 'WRONG_TOKENIZER')
    demand(receipt['thinking'] == 'disabled' and receipt['max_context_draft'] == 16384 and receipt['reserved_output_draft'] == 1536, 'WRONG_DRAFT_PARAMETERS')
    demand(receipt['official_heldout_admitted'] == 0 and receipt['final_seal'] is False, 'FALSE_ADMISSION')
    demand(receipt['gpu_used'] is False and receipt['model_inference_run'] is False and receipt['training_run'] is False, 'FORBIDDEN_EXECUTION')
    demand(receipt['semantic_world_isolation'] == 'HOLD', 'FALSE_SEMANTIC_CLEARANCE')
    demand(receipt['full_46_token_length_and_role_checks_independently_verified'] is False, 'FALSE_INDEPENDENT_CHECK_CLAIM')
    demand(isinstance(receipt['tokenizer_files_sha256'], dict) and 'tokenizer.json' in receipt['tokenizer_files_sha256'], 'TOKENIZER_PINS_ABSENT')
    demand(isinstance(json.loads(report.read_text(encoding='utf-8')), dict), 'BROKEN_PRIVATE_REPORT')
    result = {
      'schema':'storyforge-r50-hf-cpu46-local-intake-v2',
      'status':'R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL',
      'run_key': args.run_key, 'job_id_reported': receipt.get('job_id',''),
      'source_count': 46, 'tokenizer_revision': REV, 'runtime_version': 'transformers==5.16.1',
      'stage_manifest_sha256': sha(root / 'SHA256SUMS.txt'),
      'remote_receipt_sha256': sha(rfile), 'remote_private_report_sha256': sha(report),
      'remote_private_log_sha256': sha(private_log),
      'original_script_exit_0_and_json_generated': True,
      'token_length_and_double_user_semantics_require_further_report_analysis': True,
      'semantic_world_isolation': 'HOLD', 'official_heldout_admitted': 0, 'final_seal': False,
      'paid_gpu_run': False, 'model_inference_run': False, 'training_run': False,
    }
    write_new_json(Path(args.output), result)
    print(result['status'])


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd',required=True)
    ps=sub.add_parser('stage')
    for flag in ('candidates','system-file','preflight','audit-source','worker-source','stage'):
        ps.add_argument('--'+flag, required=True)
    ps.set_defaults(fn=stage)
    pc=sub.add_parser('check-stage'); pc.add_argument('--stage',required=True);pc.set_defaults(fn=lambda a: (check_stage(Path(a.stage)),print('R50_CPU46_LOCAL_STAGE_SHA256_PASS')))
    pr=sub.add_parser('run'); pr.add_argument('--stage',required=True); pr.add_argument('--run-key',required=True);pr.add_argument('--output-dir',required=True);pr.set_defaults(fn=cpu_run)
    pv=sub.add_parser('verify')
    for flag in ('stage','receipt','report','private-log','run-key','output'):
        pv.add_argument('--'+flag,required=True)
    pv.set_defaults(fn=verify)
    args=p.parse_args()
    try:
        args.fn(args)
    except Exception as exc:
        # Deliberately no exception message: it may include private paths or text.
        print('R50_CPU46_HOLD__'+(str(exc) if isinstance(exc,GateError) else type(exc).__name__),file=sys.stderr)
        raise SystemExit(2)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""R58 G1: Owner-local, read-only, bounded historical GPU Job log signal scan.

Explicitly reads original existing Job logs via HfApi.fetch_job_logs.
Does NOT inspect Job commands, arguments, labels, env, secrets, or volumes.
Does NOT create jobs or fetch story/checkpoint datasets. Streams the text
in memory without printing or saving lines. Only positive *indicators*;
absence is NOT evidence of nontraining. Never clears G1.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

INPUT_SCHEMA = 'r58_round1_g1_hf_job_exposure_triage_private_v1'
OUTPUT_SCHEMA = 'r58_round1_g1_gpu_log_signal_private_v1'
SAFE_SCHEMA = 'r58_round1_g1_gpu_log_signal_safe_v1'
UUID24 = re.compile(r'^[0-9a-f]{24}$')
ALLOWED_STAGES = {'COMPLETED', 'ERROR', 'CANCELED'}
EXPECTED_STAGE = {'COMPLETED': 7, 'ERROR': 9, 'CANCELED': 2}
MAX_PRIVATE_BYTES = 120_000
MAX_LOG_BYTES = 8_000_000
MAX_LOG_LINES = 200_000
ROOT_NAME = '.storyforge-r58-private'

class Hold(Exception):
    pass


def authorized_private_path(path: Path, *, input_mode: bool):
    home = Path.home()
    allowed = home / ROOT_NAME
    if (not path.is_absolute() or not path.is_relative_to(allowed)
        or path == allowed or path == home):
        raise Hold('path outside frozen private root')
    parent = path.parent
    if not parent.is_dir():
        raise Hold('private parent not directory')
    for ancestor in (parent, *parent.parents):
        if ancestor == home:
            break
        if ancestor.is_symlink():
            raise Hold('private ancestor symlink forbidden')
    if parent.stat().st_mode & 0o077:
        raise Hold('private parent permissions unsafe')
    if input_mode:
        if path.is_symlink():
            raise Hold('input symlink forbidden')
    elif path.exists() or path.is_symlink():
        raise Hold('private destination exists')


def read_input(path: Path) -> tuple[dict, str]:
    authorized_private_path(path, input_mode=True)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or not (0 < st.st_size <= MAX_PRIVATE_BYTES):
            raise Hold('private input permission/size mismatch')
        raw = f.read(MAX_PRIVATE_BYTES + 1)
    if not raw or len(raw) > MAX_PRIVATE_BYTES:
        raise Hold('private ledger oversized')
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeError):
        raise Hold('invalid private ledger')
    if not isinstance(obj, dict) or obj.get('schema') != INPUT_SCHEMA:
        raise Hold('unexpected private ledger schema')
    if obj.get('namespace') != 'adradar' or obj.get('g1_clearance') != 'HOLD' or obj.get('expansion_allowed') is not False:
        raise Hold('private ledger wrong namespace or gate')
    rows = obj.get('entries')
    if not isinstance(rows, list) or len(rows) != 60:
        raise Hold('expected frozen 60 unknown jobs')
    seen = set(); gpu=[]; stage_count=Counter(); cpu=0
    required = {'hf_job_id_PRIVATE','stage','hardware_class','historical_parameter_update_classification','primary_train_input_provenance'}
    for item in rows:
        if not isinstance(item,dict) or set(item) != required:
            raise Hold('unknown ledger row schema changed')
        jid = item['hf_job_id_PRIVATE']
        if not isinstance(jid,str) or not UUID24.fullmatch(jid) or jid in seen:
            raise Hold('duplicate/malformed private job')
        seen.add(jid)
        if item['historical_parameter_update_classification'] != 'PENDING_SOURCE_REVIEW' or item['primary_train_input_provenance'] != 'NOT_VERIFIED':
            raise Hold('unknown job already classified')
        if item['hardware_class'] == 'GPU':
            if item['stage'] not in ALLOWED_STAGES:
                raise Hold('unexpected GPU stage')
            gpu.append({'hf_job_id_PRIVATE':jid, 'stage':item['stage']})
            stage_count[item['stage']] += 1
        elif item['hardware_class'] == 'CPU':
            cpu += 1
        else:
            raise Hold('new hardware class cannot be assumed non-GPU')
    if len(gpu) != 18 or cpu != 42 or dict(stage_count) != EXPECTED_STAGE:
        raise Hold('frozen GPU/CPU cohort changed')
    return {'gpu': sorted(gpu,key=lambda x:x['hf_job_id_PRIVATE']), 'namespace':'adradar'}, hashlib.sha256(raw).hexdigest()


def scan_logs(lines) -> dict:
    digest=hashlib.sha256(); total=0; nlines=0; signs=set()
    # Deliberately detect only indicative telemetry; none is a proof of training.
    # Never return/store an excerpt or any matched text.
    for line in lines:
        if not isinstance(line, str):
            raise Hold('unexpected remote log line type')
        try:
            data=line.encode('utf-8')
        except UnicodeError:
            raise Hold('invalid remote log Unicode')
        total += len(data); nlines += 1
        if total > MAX_LOG_BYTES or nlines > MAX_LOG_LINES:
            return {'scan_state':'BOUNDED_LIMIT_PENDING', 'log_sha256_PRIVATE':None,
                    'log_bytes_scanned':min(total,MAX_LOG_BYTES), 'lines_scanned':min(nlines,MAX_LOG_LINES),
                    'indicator_classes':[]}
        digest.update(data)
        low=line.lower()
        if re.search(r'(?<![a-z])optimizer\.step\s*\(',low):
            signs.add('OPTIMIZER_STEP_LITERAL')
        if re.search(r'[\"\']?train_loss[\"\']?\s*[:=]',low) and ('train_runtime' in low or 'global_step' in low):
            signs.add('TRAINER_FINAL_METRIC_PAIR')
        if 'grad_norm' in low and 'learning_rate' in low and re.search(r'[\"\']?loss[\"\']?\s*:',low):
            signs.add('TRAINING_LOSS_GRAD_TELEMETRY')
        if re.search(r'global_step\s*[=:]\s*[1-9][0-9]*',low) and ('train' in low or 'optimizer' in low):
            signs.add('GLOBAL_STEP_TRAIN_TEXT')
    return {'scan_state':('POTENTIAL_OPTIMIZER_LOG_INDICATOR' if signs
                          else 'NO_INDICATOR_OBSERVED__NOT_EXCLUDED'),
            'log_sha256_PRIVATE':digest.hexdigest(), 'log_bytes_scanned':total,
            'lines_scanned':nlines, 'indicator_classes':sorted(signs)}


def examine(api, ledger:dict, ledger_sha:str) -> tuple[dict,dict]:
    results=[]
    for row in ledger['gpu']:
        try:
            # Read-only non-following API. The generator may fail mid-stream.
            source=api.fetch_job_logs(job_id=row['hf_job_id_PRIVATE'],
                                      namespace=ledger['namespace'],follow=False)
            result=scan_logs(source)
        except Exception:
            # No raw exception, URL, secret, Job ID or log contents to stdout.
            result={'scan_state':'LOG_UNAVAILABLE_PENDING','log_sha256_PRIVATE':None,
                    'log_bytes_scanned':0,'lines_scanned':0,'indicator_classes':[]}
        results.append({'hf_job_id_PRIVATE':row['hf_job_id_PRIVATE'],
                        'stage':row['stage'],**result,
                        'parameter_update_proven':False,
                        'confirmed_no_parameter_update':False,
                        'primary_input_bytes_verified':False})
    states=Counter(x['scan_state'] for x in results)
    safe={
        'schema':SAFE_SCHEMA,
        'status':'R58_G1_GPU_JOB_LOG_SIGNAL_SCAN_DONE__NO_TRAINING_EXCLUSION_OR_COMPLETENESS',
        'namespace':'adradar',
        'input_unclassified_job_count':60,
        'input_unknown_gpu_jobs':18,
        'gpu_logs_requested':len(results),
        'gpu_log_scan_state_counts':dict(sorted(states.items())),
        'cpu_jobs_still_unclassified':42,
        'gpu_jobs_cleared_as_non_training':0,
        'gpu_jobs_with_parameter_updates_independently_proven':0,
        'optimizer_signal_is_not_update_proof':True,
        'absence_of_signal_is_not_nontraining_proof':True,
        'provider_logs_complete_and_retained_verified':False,
        'all_actual_sft_runs_and_input_sources_proven_complete':False,
        'remote_training_primary_input_bytes_verified':False,
        'other_protected_worlds_covered':False,
        'source_registry_complete':False,
        'logs_read_on_owner_mac':True,
        'raw_logs_commands_arguments_environment_or_secrets_exported':False,
        'private_job_ids_exported':False,
        'r50_protected_content_absence_from_historical_logs_verified':False,
        'new_job_started':False,
        'g1_clearance':'HOLD',
        'train_admitted':0, 'validation_admitted':0, 'teacher_admitted':0,
        'expansion_allowed':False,
    }
    private={'schema':OUTPUT_SCHEMA,'status':'GPU_LOG_SIGNAL_REVIEW_ONLY__ALL_PENDING',
             'namespace':'adradar','input_private_ledger_sha256_PRIVATE':ledger_sha,
             'entries':results,'g1_clearance':'HOLD','expansion_allowed':False}
    return safe,private


def write_private(path: Path, private: dict) -> None:
    authorized_private_path(path,input_mode=False)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:
            json.dump(private,out,sort_keys=True,indent=2,ensure_ascii=False)
            out.write('\n')
    except BaseException:
        # Prevent misleading incomplete receipts. Never overwrite another file.
        path.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--namespace',default='adradar')
    p.add_argument('--allow-private-historical-job-logs', action='store_true',
                   help='Explicit Owner opt-in: remote logs may contain sensitive/R50 material; read locally without exporting lines')
    p.add_argument('--private-unknown-ledger',type=Path,required=True)
    p.add_argument('--private-output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if (not args.allow_private_historical_job_logs or args.namespace!='adradar'
            or args.private_output == args.private_unknown_ledger):
            raise Hold('scope mismatch')
        # Check destination BEFORE remote reading; never clobber prior evidence.
        authorized_private_path(args.private_output,input_mode=False)
        ledger,digest=read_input(args.private_unknown_ledger)
        from huggingface_hub import HfApi
        safe,private=examine(HfApi(),ledger,digest)
        write_private(args.private_output,private)
        safe['private_gpu_log_signal_ledger_written']=True
        print(json.dumps(safe,sort_keys=True,indent=2,ensure_ascii=False))
        return 0
    except Exception:
        print('R58_G1_GPU_LOG_SCAN: HOLD (missing private source, remote logs, or unsafe destination)',file=sys.stderr)
        return 42

if __name__=='__main__':
    raise SystemExit(main())

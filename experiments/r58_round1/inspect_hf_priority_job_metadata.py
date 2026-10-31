#!/usr/bin/env python3
"""R58 G1: single canceled GPU priority Job read-only HF metadata audit.

Default mode reads only Job id, status.stage, started_at, finished_at, flavor;
with explicit additional opt-in, locally inspects command/arguments for broad
training intent. Never reads environment/secrets/logs/labels, never prints or
persists command/arguments or raw Job ID. Never infers update or G1 clearance.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

from probe_hf_gpu_job_logs import authorized_private_path
from review_hf_gpu_signal_receipt import PRIVATE_SCHEMA as PRIORITY_SCHEMA
from triage_hf_job_exposure import GPU_FLAVORS

PRIVATE_SCHEMA = 'r58_round1_g1_hf_priority_job_metadata_private_v1'
SAFE_SCHEMA = 'r58_round1_g1_hf_priority_job_metadata_safe_v1'
ID = re.compile(r'^[a-f0-9]{24}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
MAX_INPUT = 12000
MAX_CMD_BYTES = 16000
MARKERS = [
    re.compile(r'(?<![\w])(?:swift\s+sft|swift\s+train|torchrun|accelerate\s+launch)(?![\w])',re.I),
    re.compile(r'(?:^|[\s/])(?:train(?:er)?|finetun(?:e|ing)|sft|gpu_runner|gpu_worker)[\w.-]*\.py(?:\s|$)',re.I),
    re.compile(r'(?:--do_train|--train_type\s+(?:lora|full)|trainer\.train\s*\()',re.I),
]

class Hold(Exception): pass


def read_priority(path: Path) -> dict:
    authorized_private_path(path, input_mode=True)
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or not 0<st.st_size<=MAX_INPUT:
            raise Hold('unsafe input')
        raw=f.read(MAX_INPUT+1)
    if len(raw)>MAX_INPUT:raise Hold('oversized input')
    try: v=json.loads(raw)
    except (UnicodeError,ValueError):raise Hold('invalid input')
    if (not isinstance(v,dict) or v.get('schema')!=PRIORITY_SCHEMA
        or v.get('namespace')!='adradar' or v.get('status')!='ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED'
        or v.get('stage')!='CANCELED' or v.get('indicator_classes')!=['TRAINING_LOSS_GRAD_TELEMETRY']
        or not isinstance(v.get('hf_job_id_PRIVATE'),str) or ID.fullmatch(v['hf_job_id_PRIVATE']) is None
        or not isinstance(v.get('prior_gpu_log_sha256_PRIVATE'),str)
        or SHA.fullmatch(v['prior_gpu_log_sha256_PRIVATE']) is None
        or v.get('update_proof_status')!='PENDING_PRIMARY_RUN_ARTIFACT'
        or v.get('training_input_sha256_status')!='NOT_VERIFIED'
        or v.get('train_validation_usage_status')!='NOT_VERIFIED'
        or v.get('g1_clearance')!='HOLD' or v.get('expansion_allowed') is not False):
        raise Hold('priority source drift')
    return v


def command_intent(job) -> str:
    # Called ONLY after an explicit CLI opt-in. Do not construct repr(job).
    texts=[]
    for name in ('command','arguments'):
        value=getattr(job,name,None)
        if value is None:continue
        if not isinstance(value,list) or len(value)>64 or any(not isinstance(x,str) for x in value):
            return 'UNINSPECTABLE_PENDING'
        texts.extend(value)
    if not texts:return 'COMMAND_UNAVAILABLE_PENDING'
    try: combined=' '.join(texts); size=len(combined.encode('utf-8'))
    except UnicodeError:return 'UNINSPECTABLE_PENDING'
    if size>MAX_CMD_BYTES:return 'BOUNDED_COMMAND_PENDING'
    return ('POTENTIAL_TRAINING_COMMAND_INTENT' if any(p.search(combined) for p in MARKERS)
            else 'NO_TRAINING_COMMAND_MARKER__NOT_EXCLUDED')


def evaluate(job, source:dict, *, allow_command:bool) -> tuple[dict,dict]:
    if getattr(job,'id',None)!=source['hf_job_id_PRIVATE']:
        raise Hold('Job ID differs from pinned private priority')
    status=getattr(job,'status',None)
    stage=getattr(status,'stage',None)
    stage=getattr(stage,'value',stage)
    if stage!='CANCELED':raise Hold('provider status drift')
    started=getattr(job,'started_at',None)
    finished=getattr(job,'finished_at',None)
    # Datetimes from official SDK, but no timestamps or precise duration exported.
    if started is not None and not hasattr(started,'timestamp'):
        raise Hold('malformed start time')
    if finished is not None and not hasattr(finished,'timestamp'):
        raise Hold('malformed finish time')
    if started is not None and finished is not None and finished<started:
        raise Hold('inconsistent timestamps')
    flavor=getattr(job,'flavor',None)
    if flavor not in GPU_FLAVORS:raise Hold('known GPU flavor drift')
    intent=command_intent(job) if allow_command else 'NOT_ACCESSED_NO_OWNER_OPT_IN'
    safe={
        'schema': SAFE_SCHEMA,
        'status':'R58_G1_CANCELED_GPU_PRIORITY_PROVIDER_METADATA_REVIEWED__TRAINING_SOURCE_HOLD',
        'priority_jobs_checked':1,
        'priority_stage_verified':'CANCELED',
        'provider_started_at_present':started is not None,
        'provider_finished_at_present':finished is not None,
        'provider_job_id_matches_private_priority':True,
        'priority_gpu_flavor_verified':True,
        'command_intent_mode_enabled':allow_command,
        'command_intent_class':intent,
        'commands_or_arguments_exported':False,
        'environment_secrets_labels_logs_read':False,
        'hf_job_metadata_read':True,
        'new_job_started':False,
        'parameter_update_proven':False,
        'nontraining_proven':False,
        'remote_training_input_sha256_verified':False,
        'r50_content_accessed':False,
        'provider_job_history_complete':False,
        'source_registry_complete':False,
        'all_actual_sft_runs_and_input_sources_proven_complete':False,
        'g1_clearance':'HOLD','train_admitted':0,'validation_admitted':0,'teacher_admitted':0,
        'expansion_allowed':False,
    }
    private={
        'schema':PRIVATE_SCHEMA,'status':'CANCELED_GPU_PROVIDER_METADATA_ONLY__NO_UPDATE_PROOF',
        'namespace':'adradar','hf_job_id_PRIVATE':source['hf_job_id_PRIVATE'],
        'prior_gpu_log_sha256_PRIVATE':source['prior_gpu_log_sha256_PRIVATE'],
        'provider_started_at_present':started is not None,
        'provider_finished_at_present':finished is not None,
        'command_intent_class':intent,
        'no_optimizer_update_proof':True,
        'primary_inputs_not_verified':True,
        'g1_clearance':'HOLD','expansion_allowed':False,
    }
    return safe,private


def write_private(path:Path, data:dict):
    authorized_private_path(path,input_mode=False)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,sort_keys=True,ensure_ascii=False,indent=2);f.write('\n')
    except BaseException:
        path.unlink(missing_ok=True);raise


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private-priority-ledger',type=Path,required=True)
    p.add_argument('--private-output',type=Path,required=True)
    p.add_argument('--allow-sensitive-command-intent',action='store_true',
                   help='Explicit opt-in to inspect command and argument text locally; never export')
    a=p.parse_args(argv)
    try:
        if a.private_priority_ledger==a.private_output:raise Hold('path collision')
        authorized_private_path(a.private_output,input_mode=False)
        source=read_priority(a.private_priority_ledger)
        from huggingface_hub import HfApi
        job=HfApi().inspect_job(job_id=source['hf_job_id_PRIVATE'],namespace='adradar')
        safe,private=evaluate(job,source,allow_command=a.allow_sensitive_command_intent)
        write_private(a.private_output,private)
        safe['private_metadata_ledger_written']=True
        print(json.dumps(safe,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except Exception:
        print('R58_G1_PRIORITY_GPU_METADATA: HOLD (private or provider metadata invalid/unavailable)',file=sys.stderr)
        return 42

if __name__=='__main__':raise SystemExit(main())

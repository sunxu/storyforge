#!/usr/bin/env python3
"""R50 PRIVATE CPU tokenizer/template preflight (NO GENERATION, NO SEAL).

Requires installed transformers and an ALREADY-LOCAL trusted tokenizer snapshot.
Only accepts the SHA-pinned derived 46-case PRESEAL file; not a final heldout seal.
Never calls Hugging Face, CUDA, GPU, or inference, and does not read source mappings.
The prompt construction here is an UNAPPROVED DRAFT, not R49 registration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

PINNED_REVISION = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
PINNED_CANDIDATE_SHA256 = '109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2'

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def checked_read_jsonl(path: Path) -> list[dict]:
    out = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(out) != 46 or len({c['case_id'] for c in out}) != 46:
        raise ValueError('not 46 unique content-PASS candidate cases')
    return out

def make_messages(case: dict, system_text: str) -> list[dict]:
    # Contract OPTION A: preserve all original historic roles, including
    # consecutive user turns; one frozen System + cards/rules; append new user.
    if any(m['role'] not in ('user', 'assistant') or not isinstance(m['content'],str) for m in case['history']):
        raise ValueError('invalid history roles/content')
    if not isinstance(case['world_card'], str) or not isinstance(case['long_term_rules'], list):
        raise ValueError('invalid case card/rules')
    if any(not isinstance(rule,str) for rule in case['long_term_rules']):
        raise ValueError('invalid rule item')
    if not isinstance(case['user_input'],str):
        raise ValueError('invalid user input')
    card = ('\n\n[STORY_WORLD_CARD]\n' + case['world_card'] + '\n[/STORY_WORLD_CARD]')
    rules = ('\n\n[STORY_LONG_TERM_RULES]\n' + '\n'.join(case['long_term_rules']) + '\n[/STORY_LONG_TERM_RULES]')
    composed = system_text + card + rules
    return [{'role':'system','content':composed}] + [
        {'role':m['role'], 'content':m['content']} for m in case['history']
    ] + [{'role':'user','content':case['user_input']}]

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates',type=Path,required=True,help='private ORIGINAL R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl')
    p.add_argument('--system-file',type=Path,required=True,help='actual preregistered common System UTF-8 file')
    p.add_argument('--tokenizer-snapshot',type=Path,required=True,help='LOCAL snapshot directory under pinned SHA revision')
    p.add_argument('--thinking',choices=('enabled','disabled'),required=True)
    p.add_argument('--max-context',type=int,default=16384,help='DRAFT budget pending approval; NOT automatically an inference limit')
    p.add_argument('--reserved-output-tokens',type=int,default=1536,help='DRAFT; no generation is performed')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if PINNED_REVISION not in a.tokenizer_snapshot.resolve().parts:
        raise ValueError('tokenizer snapshot path must include frozen model revision directory')
    if not a.tokenizer_snapshot.is_dir():raise FileNotFoundError('no local tokenizer snapshot')
    if not a.system_file.is_file():raise FileNotFoundError('no frozen common System file')
    if a.max_context<1 or a.reserved_output_tokens<1 or a.reserved_output_tokens>=a.max_context:
        raise ValueError('invalid context/output budgets')
    # A local snapshot should have the real tokenizer_config and tokenizer file.
    files=('tokenizer.json','tokenizer_config.json','special_tokens_map.json','added_tokens.json')
    receipt={name:sha256((a.tokenizer_snapshot/name).read_bytes()) for name in files if (a.tokenizer_snapshot/name).is_file()}
    if 'tokenizer_config.json' not in receipt or 'tokenizer.json' not in receipt:
        raise ValueError('missing tokenizer.json/tokenizer_config.json; no approximation allowed')
    try:
        from transformers import AutoTokenizer
    except ModuleNotFoundError as exc:
        raise RuntimeError('transformers not installed; use trusted pinned local runtime on CPU') from exc
    tok = AutoTokenizer.from_pretrained(str(a.tokenizer_snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
    if not getattr(tok,'is_fast',False):raise ValueError('actual FAST tokenizer unavailable')
    if not tok.chat_template:raise ValueError('actual tokenizer has no chat template')
    system=a.system_file.read_text(encoding='utf-8')
    if not system.strip():raise ValueError('common System blank')
    if sha256(a.candidates.read_bytes()) != PINNED_CANDIDATE_SHA256:
        raise ValueError('candidate frozen SHA256 mismatch; refuse transformed/edited input')
    if 'enable_thinking' not in str(tok.chat_template):
        raise ValueError('thinking parameter is not explicit in this template; manual pre-registration required')
    cases=checked_read_jsonl(a.candidates)
    rejected={'SFH50-W16-005','SFH50-W18-003','SFH50-W19-003','SFH50-W19-010'}
    if rejected.intersection(x['case_id'] for x in cases):
        raise ValueError('excluded case reappeared in derived file')
    rows=[]
    for case in cases:
        msgs=make_messages(case,system)
        enc=tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=(a.thinking=='enabled'))
        if not isinstance(enc,list) or not all(isinstance(i,int) for i in enc):
            raise TypeError(f"invalid encoded ids for {case['case_id']}")
        n=len(enc)
        b=b''.join(struct.pack('<I',i) for i in enc)
        rows.append({'case_id':case['case_id'],'history_count':len(case['history']),'consecutive_user':bool(case['history'] and case['history'][-1]['role']=='user'),'input_tokens':n,'input_plus_output_budget':n+a.reserved_output_tokens,'within_budget':n+a.reserved_output_tokens<=a.max_context,'input_id_sha256':sha256(b)})
    report={'schema':'storyforge-r50-cpu-real-tokenizer-preflight-v1', 'status':'PREFLIGHT_ONLY_NO_FINAL_SEAL',
       'pinned_model_revision':PINNED_REVISION,'tokenizer_snapshot':str(a.tokenizer_snapshot),
       'tokenizer_file_sha256':receipt,'chat_template_sha256':sha256(str(tok.chat_template).encode('utf-8')),
       'system_sha256':sha256(a.system_file.read_bytes()),'candidate_original_sha256':sha256(a.candidates.read_bytes()),
       'thinking_mode':a.thinking, 'max_context':a.max_context,'reserved_output_tokens':a.reserved_output_tokens,
       'strategy':'PRESERVE_CONSECUTIVE_USER_AND_INJECT_WORLD_RULES_TO_SHARED_SYSTEM__DRAFT_ONLY',
       'case_count':len(rows), 'overflow_count':sum(not r['within_budget'] for r in rows),
       'actual_four_model_inference_input_equality':'NOT_VERIFIED_NO_MODEL_EXECUTED',
       'no_model_generation':True,'no_gpu':True,'no_final_heldout_seal':True,'cases':rows}
    dest=a.output.resolve()
    if any((parent/'.git').exists() for parent in [dest.parent, *dest.parents]):
        raise ValueError('private token reports must not be written inside a Git repository')
    if dest.exists():raise FileExistsError('will not overwrite a previous report')
    dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with dest.open('x',encoding='utf-8') as fh:
        json.dump(report,fh,ensure_ascii=False,indent=2);fh.write('\n')
    print('R50_TOKENIZER_PREFLIGHT__'+('BUDGET_PASS' if report['overflow_count']==0 else 'OVERFLOW_HOLD'))
    print('actual token counts for 46 private cases saved outside repository; no model ran')
    return 0 if report['overflow_count']==0 else 2

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print(f'R50_TOKENIZER_PREFLIGHT_HOLD: {type(e).__name__}: {e}',file=sys.stderr)
        sys.exit(1)

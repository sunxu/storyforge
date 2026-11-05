#!/usr/bin/env python3
"""Execute the OFFICIAL R50 private R45 gate against frozen Git blobs, no GPU/network.

Use a local authorized Git checkout containing both pinned commits.  ZIP input is
read-only; source blobs are extracted to a private temporary directory; nothing is
written to the Git checkout.  Summary never includes story text or source UUIDs.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path

SOURCE_SHA = 'a197923e1e15344e8c98bd96e593e84781b68c83'
AUDIT_SHA = '92828ac0e47c8f7f7307851b8e171f564fd065ed'
ZIP_NAMES = {
    'train': 'R45_TRAIN_FROZEN_CANDIDATE_49_NOT_APPROVED.jsonl',
    'validation': 'R45_VALIDATION_FROZEN_CANDIDATE_15_NOT_APPROVED.jsonl',
}
EXPECTED = {
    'train': ('e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742',49),
    'validation':('5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963',15),
}
ROOT='evaluations/v0.2/source-archives/16-20'
RECEIPT='docs/evidence/V03_R50_SOURCE_16_20_RECEIPT_20261015.json'
HELPERS=('scripts/v03_r50_private_r45_isolation.py', 'scripts/v03_r50_exhaustive_screen.py', 'scripts/v03_r50_text_reuse_screen.py')

def git(repo:Path,*args:str)->bytes:
    cp=subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=False)
    if cp.returncode:
        raise ValueError('required pinned Git object unavailable or invalid')
    return cp.stdout

def git_obj(repo:Path,revision:str,path:str)->bytes:
    if path.startswith('/') or '..' in Path(path).parts:raise ValueError('unsafe Git path')
    return git(repo,'show',f'{revision}:{path}')

def seal_b(blob:bytes)->str:return hashlib.sha256(blob).hexdigest()

def extract_r45(original_zip:Path,temp:Path)->dict:
    counts={}
    with zipfile.ZipFile(original_zip) as z:
        for key,filename in ZIP_NAMES.items():
            matches=[n for n in z.namelist() if n.rsplit('/',1)[-1]==filename]
            if len(matches)!=1:raise ValueError('frozen R45 original missing or ambiguous')
            blob=z.read(matches[0])
            if seal_b(blob)!=EXPECTED[key][0]:raise ValueError('frozen R45 original SHA256 mismatch')
            if len(blob.splitlines())!=EXPECTED[key][1]:raise ValueError('R45 JSONL count mismatch')
            path=temp / (key+'.jsonl'); path.write_bytes(blob);path.chmod(0o600)
            counts[key]=len(blob.splitlines())
    return counts

def run_gate(repo:Path,r45_zip:Path)->dict:
    if not (repo/'.git').exists():
        # A Git worktree may have a .git file, too.
        if not (repo/'.git').is_file():raise ValueError('requires existing local Git checkout')
    if not r45_zip.is_file():raise ValueError('R45 original ZIP unavailable')
    # Source/audit relationship is part of the frozen trust anchor.
    git(repo,'cat-file','-e',f'{SOURCE_SHA}^{{commit}}')
    git(repo,'cat-file','-e',f'{AUDIT_SHA}^{{commit}}')
    git(repo,'merge-base','--is-ancestor',SOURCE_SHA,AUDIT_SHA)
    receipt=json.loads(git_obj(repo,AUDIT_SHA,RECEIPT))
    if receipt.get('source_commit')!=SOURCE_SHA or len(receipt.get('files',[]))!=35:
        raise ValueError('source manifest mismatch')
    if not all(x['path'].startswith(ROOT+'/') for x in receipt['files']):
        raise ValueError('source manifest outside allowed tree')
    checked=0
    for x in receipt['files']:
        oid=git(repo,'rev-parse',f"{SOURCE_SHA}:{x['path']}").decode().strip()
        size=int(git(repo,'cat-file','-s',oid).strip())
        if oid!=x['git_blob_sha1'] or size!=x['size_bytes']:
            raise ValueError('source blob SHA or byte size differs from frozen receipt')
        checked+=1
    with tempfile.TemporaryDirectory(prefix='r50-gate-', dir=str(repo.parent) if False else None) as td:
        base=Path(td);base.chmod(0o700)
        sandbox=base/'repo';(sandbox/ROOT).mkdir(parents=True)
        originals=base/'original_r45';originals.mkdir(mode=0o700)
        counts=extract_r45(r45_zip,originals)
        # Only two files required by the official private-source gate for each world.
        fetched=0
        for x in receipt['files']:
            p=x['path']
            if p.endswith('/age-review.json') or (p.endswith('.jsonl') and p.rsplit('/',1)[-1]==p.rsplit('/',2)[-2]+'.jsonl'):
                target=sandbox/p
                target.parent.mkdir(parents=True,exist_ok=True)
                blob=git_obj(repo,SOURCE_SHA,p)
                if len(blob)!=x['size_bytes'] or git_blob_sha(blob)!=x['git_blob_sha1']:
                    raise ValueError('extracted source blob differs from pinned Git receipt')
                target.write_bytes(blob);target.chmod(0o600);fetched+=1
        if fetched!=10:raise ValueError('expected 5 source transcripts and 5 age-review files')
        # Load the official, pinned validator and its two helper modules from Git.
        scripts=base/'scripts';scripts.mkdir()
        for src in HELPERS:
            blob=git_obj(repo,AUDIT_SHA,src)
            (scripts/Path(src).name).write_bytes(blob)
        sys.path.insert(0,str(scripts))
        try:
            from v03_r50_private_r45_isolation import verify
            summary=verify(sandbox,originals/'train.jsonl',originals/'validation.jsonl')
        finally: sys.path.pop(0)
    if summary.get('status')!='R45_FROZEN_49_15_EXACT_SCREEN_PASS__SEMANTIC_REVIEW_PENDING':
        raise ValueError('official validator did not declare expected status')
    return {'schema':'r50-frozen-git-private-r45-check-v1',
            'status':'FULL_FROZEN_SOURCE_R45_EXACT_PASS__SEMANTIC_WORLD_ALIAS_HOLD',
            'frozen_source_commit':SOURCE_SHA,'frozen_audit_commit':AUDIT_SHA,
            'verified_manifest_files':checked,'extracted_full_sources':fetched,
            'r45_counts':counts,'official_validator_report':summary,
            'scope_limitations':['semantic aliases/paraphrases not proved','does not authorize final heldout seal'],
            'model_generated':False,'gpu_executed':False,'git_worktree_modified':False}

def git_blob_sha(b:bytes)->str:
    import hashlib
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True,help='private local Git repo with pinned objects')
    parser.add_argument('--r45-original-zip',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='new report file outside any Git checkout')
    a=parser.parse_args()
    try:
        out=a.output.resolve();repo=a.repo.resolve()
        if out==repo or repo in out.parents:raise ValueError('output must be outside Git repo')
        if out.exists():raise FileExistsError('no overwrites allowed')
        result=run_gate(repo,a.r45_original_zip)
        out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
        fd=os.open(out,flags,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
        print(result['status']);return 0
    except Exception as e:
        print('R50_FULL_FROZEN_GATE_HOLD:',type(e).__name__,file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""R18 private HF tokenizer + actual ms-swift no-training audit (fail closed)."""
import argparse, csv, hashlib, io, json, os, sys, traceback, zipfile
import importlib.metadata
from pathlib import Path

REV='1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
SOURCE='ba42ad7568ce0ca3ab8b3d218397006b430affc9f1b2f74b7ea4392e5103eab3'
QUEUE='27d63ccc7652e41403d9cb4add58c0aa7d2925282d4bd8605bff4d7564133ac7'
PREVIEW='21255ffaf3460721bfbd89fb448e4cf5bcf53e98d3eec76585a7817e8bafd210'
def digest(b): return hashlib.sha256(b).hexdigest()
def ids(x):
    if hasattr(x,'detach'):x=x.detach().cpu().tolist()
    elif hasattr(x,'tolist'):x=x.tolist()
    if isinstance(x,list) and len(x)==1 and isinstance(x[0],list):x=x[0]
    if not isinstance(x,list) or not x or any(type(t)!=int for t in x):raise ValueError('no genuine token IDs or labels')
    return x

def frozen(path):
    b=Path(path).read_bytes()
    if digest(b)!=SOURCE:raise ValueError('R17 source ZIP SHA256 mismatch')
    queue=None
    for i in range(18):
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            q=[x for x in z.namelist() if x.endswith('/r15_diagnostic_queue_58.csv')]
            if q:
                if queue is not None or len(q)!=1:raise ValueError('queue ambiguous')
                data=z.read(q[0])
                if digest(data)!=QUEUE:raise ValueError('R15 queue hash mismatch')
                queue=list(csv.DictReader(io.StringIO(data.decode())))
            p=[x for x in z.namelist() if x.endswith('inputs/uniform_prompt_preview_195_NOT_TRAIN.jsonl')]
            if p:
                if queue is None or len(p)!=1:raise ValueError('missing queue or ambiguous preview')
                data=z.read(p[0])
                if digest(data)!=PREVIEW:raise ValueError('R07 preview hash mismatch')
                records=[json.loads(x) for x in data.splitlines() if x.strip()]
                by={r['id']:r for r in records}
                selection=[q for q in queue if q['probe_lane']=='FIRST_OFFLINE_INPUT_VALIDATION']
                if len(records)!=195 or len(by)!=195 or len(queue)!=58 or len(selection)!=40 or len({q['candidate_id'] for q in selection})!=40:
                    raise ValueError('R15/R07 count or duplicate mismatch')
                for q in selection:
                    m=by[q['candidate_id']]['messages']
                    if len(m)<2 or m[-2]['role']!='user' or m[-1]['role']!='assistant' or m[-1].get('loss') is not True or any(x.get('loss') is not False for x in m[:-1] if x['role']=='assistant'):raise ValueError('wrong supervised target')
                    if digest(m[-1]['content'].encode())!=q['target_sha256']:raise ValueError('target tampered')
                return selection,by
            n=[x for x in z.namelist() if x.endswith('.zip') and ('/baseline/' in x or x.endswith('evidence/R07_UniformPrompt_Admission_20261013.zip'))]
            if len(n)!=1:raise ValueError('broken nested archive')
            b=z.read(n[0])
    raise ValueError('missing R07 evidence')

def probe(selection,by,stage,report):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    snapshot=Path(snapshot_download(repo_id='Qwen/Qwen3.8-27B',revision=REV,allow_patterns=['tokenizer*','special_tokens_map.json','added_tokens.json','chat_template*','config.json','generation_config.json','*.tiktoken']))
    if REV not in str(snapshot.resolve()) or not all((snapshot/f).is_file() for f in ['tokenizer.json','tokenizer_config.json']):raise ValueError('pinned tokenizer unavailable')
    report['tokenizer_sha256']={f:digest((snapshot/f).read_bytes()) for f in ['tokenizer.json','tokenizer_config.json']}
    tok=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False,use_fast=True)
    report['chat_template_sha256']=digest(str(tok.chat_template).encode())
    template=None
    if stage=='both':
        from swift import get_processor,get_template
        import hf_label_mask_audit as audit
        os.environ['HF_HUB_OFFLINE']='1'
        template=get_template(get_processor(str(snapshot)),loss_scale='last_round',max_length=16384,add_non_thinking_prefix=False)
        template.set_mode('train')
        if getattr(template.loss_scale,'base_strategy',None)!='last_round':raise ValueError('ms-swift last_round not active')
    for i,q in enumerate(selection,1):
        cid=q['candidate_id']; row=by[cid]
        messages=[{'role':m['role'],'content':m['content']} for m in row['messages']]
        t=ids(tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=False))
        result={'candidate_id':cid,'story_id':q['story_id'],'token_count':len(t),'full_tokens_sha256':digest(json.dumps(t,separators=(',',':')).encode()),'mask':'NOT_TESTED'}
        report['rows'].append(result)
        if len(t)>16384:result['error']='TOKEN_OVERFLOW';continue
        if stage=='token':continue
        try:
            audit.audit_row(template,row,i)  # actual installed ms-swift template and captured loss-scale
            encoded=template.encode(row)
            original_ids=ids(encoded['input_ids']); original_labels=ids(encoded['labels'])
            if len(original_ids)!=len(original_labels) or len(original_ids)>16384:raise ValueError('template length invalid')
            collator=getattr(template,'data_collator',None)
            if not callable(collator):raise ValueError('real data_collator unavailable')
            batch=collator([encoded]); b_ids=ids(batch['input_ids']); b_labels=ids(batch['labels'])
            if (b_ids[:len(original_ids)]!=original_ids or b_labels[:len(original_labels)]!=original_labels or len(b_ids)!=len(b_labels) or any(x!=-100 for x in b_labels[len(original_labels):])):raise ValueError('collator labels differ from actual template')
            if not any(x!=-100 for x in original_labels):raise ValueError('Gold target not supervised')
            result['mask']='ACTUAL_COLLATOR_LABELS_CONSISTENT'
            result['ms_swift_token_count']=len(original_ids)
            result['labels_sha256']=digest(json.dumps(original_labels,separators=(',',':')).encode())
            result['transformers_ms_swift_input_same']=t==original_ids
        except Exception as exc:
            result['mask']='BLOCKED'; result['error']=f'{type(exc).__name__}: {str(exc)[:300]}'
    n=sum(r['token_count']<=16384 and (stage=='token' or r['mask']=='ACTUAL_COLLATOR_LABELS_CONSISTENT') for r in report['rows'])
    report['checked']=len(report['rows']);report['consistent']=n
    report['status']=('TOKENIZER_DIAGNOSTIC_ONLY' if stage=='token' else 'COLLATOR_INTERNAL_CONSISTENCY_ONLY') if n==40 else 'BLOCKED'

def main():
    p=argparse.ArgumentParser();p.add_argument('--r17-zip',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--stage',choices=['token','both'],default='both');a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    result={'status':'BLOCKED','admission':'PENDING_NOT_APPROVED','training_performed':False,'stage':a.stage,'rows':[]}
    result['runtime_versions']={}
    for package in ('ms-swift','transformers','tokenizers','torch','huggingface-hub'):
        try:result['runtime_versions'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:result['runtime_versions'][package]=None
    try:
        selection,by=frozen(a.r17_zip)
        result['r17_sha256']=SOURCE;result['model_revision']=REV
        probe(selection,by,a.stage,result)
    except Exception as exc:
        traceback.print_exc();result['error']=f'{type(exc).__name__}: {exc}'
    (a.output_dir/'r18_actual_no_train_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('R18',result['status'],result.get('consistent',0),'of 40; admission=PENDING_NOT_APPROVED')
    return 0 if result['status']!='BLOCKED' else 2
if __name__=='__main__':sys.exit(main())

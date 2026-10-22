#!/usr/bin/env python3
"""R56 Stage5 offline integrity validator; no AI/GPU, no network, no source changes."""
import argparse,hashlib,json
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()
def sha(txt):
    return hashlib.sha256(txt.encode('utf8')).hexdigest()
def read_lines(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]

def validate(candidates,report,decisions):
    old=set(report['old_curation_R04_target_ids_PRIVATE'])
    if len(old)!=8 or len(candidates)!=18 or len(decisions)!=18:raise ValueError('BAD_COUNT')
    linked={x['target_id_PRIVATE']:x for x in decisions}
    if len(linked)!=18:raise ValueError('DECISION_DUPLICATE')
    seen=set()
    for c in candidates:
        target=c['target_message_id_PRIVATE'];hist=c['frozen_history_PRIVATE'];ix=c['target_original_array_index_PRIVATE']
        if target in seen:raise ValueError('DUPLICATE_TARGET')
        seen.add(target)
        if c['target_sha256_PRIVATE']!=sha(c['target_original_for_CONTENT_REVIEW_ONLY_PRIVATE']):raise ValueError('TARGET_SHA_BAD')
        if c['source_jsonl_sha256_PRIVATE']!=report['world11_raw_sha256_PRIVATE']:raise ValueError('SOURCE_REFERENCE_BAD')
        if not 5<=len(hist)<=12 or hist[-1]['role']!='user':raise ValueError('HISTORY_BAD')
        if [m['source_index'] for m in hist]!=list(range(ix-len(hist),ix)):raise ValueError('HISTORY_INDEX_BAD')
        if target in old or any(m['message_id'] in old for m in hist):raise ValueError('EXPOSED_OLD_TARGET')
        d=linked.get(target)
        if not d:raise ValueError('MISSING_REVIEW')
        checksum=d.pop('decision_payload_sha256_PRIVATE',None)
        actual=digest(d)
        d['decision_payload_sha256_PRIVATE']=checksum
        if actual!=checksum:raise ValueError('REVIEW_TAMPERED')
        if d['target_sha256_PRIVATE']!=c['target_sha256_PRIVATE'] or d['original_history_sha256_REFERENCE_PRIVATE']!=c['frozen_history_sha256_PRIVATE']:raise ValueError('EVIDENCE_REFERENCE_MISMATCH')
        if d['normalized_visible_history_sha256_PRIVATE']!=digest(hist):raise ValueError('VISIBLE_HISTORY_SHA_BAD')
        if d['formal_heldout_admission']!='HOLD_NOT_ADMITTED' or d['training_authorized'] or d['gpu_job_authorized']:raise ValueError('FORMAL_ADMISSION_FORBIDDEN')
        if d['content_triage'] not in ('SCREEN_OUT_FOR_CURRENT_R56_EVAL','HOLD_DETAILED_CONTENT_REVIEW'):raise ValueError('INVALID_TRIAGE')
        if d['source_11_raw_content_replay']!='NOT_DONE_IN_THIS_RUNTIME':raise ValueError('FAKE_SOURCE_REPLAY')
    if sum(x['content_triage']=='SCREEN_OUT_FOR_CURRENT_R56_EVAL' for x in decisions)!=9:raise ValueError('SCREEN_OUT_COUNT')
    return {'status':'STAGE5_18_DECISIONS_INTEGRITY_PASS__ZERO_FORMAL_ADMISSION','cases':18,'screen_out':9,'hold':9,'full_original11_replayed':False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--prospects',required=True)
    a.add_argument('--world-report',required=True)
    a.add_argument('--decisions',required=True)
    z=a.parse_args()
    print(json.dumps(validate(read_lines(z.prospects),json.loads(Path(z.world_report).read_text()),read_lines(z.decisions)),ensure_ascii=False))
if __name__=='__main__':main()

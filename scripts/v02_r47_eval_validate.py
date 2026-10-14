#!/usr/bin/env python3
"""R47 legacy-test three-arm validator and private blind package generator."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,secrets
from pathlib import Path

ARMS=("base","v01","v02")
DIMENSIONS=("剧情连续性","角色一致性","指令遵循","文学表现力","互动推进","玩家自主权")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def read(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]
def prompt_hash(msg):
    return hashlib.sha256(json.dumps({"messages":msg},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def validate_prompts(prompts,manifest):
    rows=read(prompts); meta=json.loads(Path(manifest).read_text(encoding="utf-8"))
    entries=meta.get("samples",[])
    if meta.get("schema")!="storyforge-blind-v1" or meta.get("count")!=20 or len(rows)!=20 or len(entries)!=20:
        raise ValueError("requires exactly 20 frozen v0.1 prompts")
    seen=set()
    for i,(row,e) in enumerate(zip(rows,entries,strict=True)):
        msg=row.get("messages")
        if not isinstance(msg,list) or len(msg)<2 or msg[0].get("role")!="system" or msg[-1].get("role")!="user":
            raise ValueError(f"bad prompt roles {i}")
        if any(not isinstance(m,dict) or m.get("role") not in ("system","developer","user","assistant")
               or not isinstance(m.get("content"),str) or not m["content"].strip()
               or "loss" in m for m in msg):
            raise ValueError(f"loss or invalid message in prompt {i}")
        h=prompt_hash(msg); sid=e.get("sample_id")
        if h!=e.get("prompt_sha256") or e.get("source_line")!=i+1 or not isinstance(sid,str) or sid!=f"eval-{i:03d}-{h[:12]}":
            raise ValueError(f"frozen prompt SHA/ID mismatch {i}")
        if sid in seen:raise ValueError("duplicated prompt")
        seen.add(sid)
    return rows,entries
def validate_responses(path,prompts):
    """Check exact input role/content despite ms-swift output-only metadata.

    ms-swift may attach 'loss': null to each input message and append a
    generated Assistant to the returned messages. Those are output formatting,
    not source-input modifications. Never accept a changed prompt or missing
    original prompt history.
    """
    rows=read(path)
    if len(rows)!=len(prompts):
        raise ValueError(f"{path}: expected {len(prompts)} outputs, got {len(rows)}")
    answer=[]
    for i,(row,p) in enumerate(zip(rows,prompts,strict=True)):
        orig=p["messages"]
        observed=row.get("messages")
        if not isinstance(observed,list):
            raise ValueError(f"{path}: missing messages for alignment at {i}")
        if len(observed) not in (len(orig),len(orig)+1):
            raise ValueError(f"{path}: unexpected message count at {i}: {len(observed)}")
        for j,expected in enumerate(orig):
            msg=observed[j]
            if (not isinstance(msg,dict) or msg.get("role")!=expected["role"]
                    or msg.get("content")!=expected["content"]):
                raise ValueError(f"{path}: prompt role/content mismatch at {i}:{j}")
            # Only null/false extra loss metadata is tolerated; loss=true
            # would indicate an invalid supervision field in inference output.
            if "loss" in msg and msg["loss"] not in (None,False):
                raise ValueError(f"{path}: unexpected supervised prompt at {i}:{j}")
        response=row.get("response")
        if not isinstance(response,str) or not response.strip():
            raise ValueError(f"{path}: missing/nontext model response at {i}")
        if len(observed)==len(orig)+1:
            last=observed[-1]
            if (not isinstance(last,dict) or last.get("role")!="assistant"
                    or last.get("content")!=response):
                raise ValueError(f"{path}: appended Assistant differs from response at {i}")
        answer.append(response)
    return answer
def write_blind(prompts,manifest,results,out):
    if set(results)!=set(ARMS):raise ValueError("three arms required")
    data,meta=validate_prompts(prompts,manifest)
    responses={arm:validate_responses(path,data) for arm,path in results.items()}
    out=Path(out)
    if out.exists() and any(out.iterdir()):raise FileExistsError("will not replace review package")
    review=out/"blind-review"; private=out/"private"
    review.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    hdr=["样本编号","故事背景与系统规则","历史对话","当前用户输入","回复A","回复B","回复C",
         "整体最佳(A/B/C/TIE)","评分理由与逐字证据","严重问题与对应回复","玩家自主权严重侵犯(A/B/C/无)"]
    hdr += [f"{dim}·{letter}" for dim in DIMENSIONS for letter in "ABC"]
    rows=[]; blinded=[];keys=[]
    for i,(p,e) in enumerate(zip(data,meta,strict=True)):
        order=list(ARMS);secrets.SystemRandom().shuffle(order)
        mapping=dict(zip("ABC",order,strict=True))
        keys.append({"sample_id":e["sample_id"],"mapping":mapping})
        a={letter:responses[arm][i] for letter,arm in mapping.items()}
        blinded.append({"sample_id":e["sample_id"],"prompt_sha256":e["prompt_sha256"],
                        "response_a":a["A"],"response_b":a["B"],"response_c":a["C"]})
        m=p["messages"]
        bg="\n\n".join(f"【{x['role']}】\n{x['content']}" for x in m if x["role"] in ("system","developer"))
        hist="\n\n".join(f"【{x['role']}】\n{x['content']}" for x in m[:-1] if x["role"] not in ("system","developer"))
        rows.append({"样本编号":e["sample_id"],"故事背景与系统规则":bg,"历史对话":hist,
                     "当前用户输入":m[-1]["content"],"回复A":a["A"],"回复B":a["B"],"回复C":a["C"]})
    blind=review/"R47_BLIND_THREE_WAY_20.jsonl"
    with blind.open("x",encoding="utf-8") as f:
        for row in blinded:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    for i in (1,2,3):
        with (review/f"R47_Reviewer_{i:02d}.csv").open("x",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=hdr);w.writeheader();w.writerows(rows)
    key=private/"R47_PRIVATE_ANSWER_KEY.json"
    with key.open("x",encoding="utf-8") as f:
        json.dump({"mode":"RETROSPECTIVE_EXPOSED_V01_TEST","items":keys},f,ensure_ascii=False,indent=2);f.write("\n")
    os.chmod(key,0o600)
    summary={"status":"R47_BLIND_EXPORT_PASS_NOT_FRESH_HELDOUT","samples":20,"responses":60,
             "prompt_sha256":sha(prompts),"manifest_sha256":sha(manifest),
             "blind_sha256":sha(blind),"key_sha256":sha(key),
             "results_sha256":{name:sha(path) for name,path in results.items()},
             "fresh_independent_heldout":False,"model_promotion":False}
    (private/"R47_AUDIT_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    return summary
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--prompts",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--base",type=Path);ap.add_argument("--v01",type=Path);ap.add_argument("--v02",type=Path)
    ap.add_argument("--output-dir",type=Path)
    a=ap.parse_args()
    if a.output_dir:
        if not all((a.base,a.v01,a.v02)):ap.error("need all three result paths")
        print(json.dumps(write_blind(a.prompts,a.manifest,{"base":a.base,"v01":a.v01,"v02":a.v02},a.output_dir),ensure_ascii=False))
    else:
        rows,_=validate_prompts(a.prompts,a.manifest)
        print(f"R47_FROZEN_V01_20_PROMPTS_PASS {len(rows)}; retrospective only")

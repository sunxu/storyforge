#!/usr/bin/env python3
"""R54 V2 exact-byte 31/9 + CPU40 preflight. No GPU, HF, or paid action."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED = {
    "config":"55ac554a4fe4b4974b7f7f664dcf5a9163b5e37219150acc087309282ef4d861",
    "train":"d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7",
    "validation":"b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d",
    "release":"3d8078ee3b4528521b7f67ba1dd7983f0d20bfeb4d7c79e92d9cabe2c6b2e836",
    "cpu_report":"8624c21b6d9fff5e74006bca000c69f0d39870f1fb030c2ff4fb96cc523f1f45",
    "cpu_intake":"b3bff2625c360aad10d985b42884263a26a72e85e7d1ddc7d0df916b6598381e",
    "cpu_log":"7ebe369f83b168d2c3f0830c91cd77370154638d74482fe57cdc93e55d8ca39f",
}
MODEL="Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
COUNTS={"train":31,"validation":9}

def insist(ok,reason):
    if not ok: raise ValueError(reason)

def digest(path):
    insist(path.is_file() and not path.is_symlink(),"missing/symlinked R54 evidence "+path.name)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path): return json.loads(path.read_text(encoding="utf-8"))

def inspect_split(path, count, expected):
    insist(digest(path)==expected,"R54 frozen dataset bytes changed")
    data=path.read_bytes()
    insist(data.endswith(b"\n") and b"\r" not in data,"R54 invalid JSONL endings")
    rows=[json.loads(x) for x in data.splitlines()]
    insist(len(rows)==count,"R54 formal data row count mismatch")
    targets=set()
    for row in rows:
        insist(isinstance(row,dict) and set(row)=={"messages"},"R54 unexpected row schema")
        messages=row["messages"]
        insist(len(messages)>=3 and messages[0]["role"]=="system" and
               messages[-2]["role"]=="user" and messages[-1]["role"]=="assistant",
               "R54 invalid last-round roles")
        for index, m in enumerate(messages):
            insist(m.get("role") in {"system","user","assistant"}
                   and isinstance(m.get("content"),str) and m["content"].strip(),
                   "R54 invalid message content")
            if m["role"]=="assistant":
                insist(m.get("loss") is (index==len(messages)-1),"R54 history supervision leaked")
            else:
                insist("loss" not in m,"R54 user/system loss annotated")
        target=hashlib.sha256(messages[-1]["content"].encode("utf-8")).hexdigest()
        insist(target not in targets,"R54 duplicate target")
        targets.add(target)
    return targets

def check(release, cpu_report, cpu_intake, config):
    insist(digest(config)==EXPECTED["config"],"R54 V2 training config changed")
    rpath=release/"R53_RELEASE_RECEIPT.json"
    insist(digest(rpath)==EXPECTED["release"],"R54 release receipt changed")
    r=read(rpath)
    insist(r["status"]=="DATA_ONLY_RELEASE_APPROVED__GPU_NOT_AUTHORIZED" and
           r["train_rows"]==31 and r["validation_rows"]==9 and
           r["sha256"]=={k:EXPECTED[k] for k in COUNTS} and
           r["gpu_authorized"] is False and r["r50_sealed"] is True and
           r["model_revision"]==MODEL,"R54 release scope invalid")
    insist(digest(cpu_report)==EXPECTED["cpu_report"] and
           digest(cpu_intake)==EXPECTED["cpu_intake"],"R54 CPU40 file hashes changed")
    c=read(cpu_report);i=read(cpu_intake)
    insist(c.get("status")=="R53_HF_CPU40_REAL_TOKENIZER_COLLATOR_MASK_PASS__NO_DATA_ADMISSION"
           and c.get("compiled_input_sha256")=={k:EXPECTED[k] for k in COUNTS}
           and c.get("checked")==COUNTS and
           len(c.get("rows",[]))==40 and
           all(z.get("status")=="REAL_LAST_ASSISTANT_AND_COLLATOR_PASS" for z in c["rows"]),
           "R54 CPU40 runtime check not 40/40")
    insist(i.get("status")=="R53_CPU40_RECEIPT_SOURCE_LOG_CROSSCHECK_PASS__NOT_DATA_RELEASE"
           and i.get("report_sha256")==EXPECTED["cpu_report"]
           and i.get("log_sha256")==EXPECTED["cpu_log"]
           and r.get("runtime_log_sha256")==EXPECTED["cpu_log"],
           "R54 CPU40 owner intake not matched")
    targets={}
    for name,n in COUNTS.items():
        targets[name]=inspect_split(release/(name+".jsonl"),n,EXPECTED[name])
    insist(not (targets["train"] & targets["validation"]),"R54 cross-split target overlap")
    return {"status":"R54_GPU_SCHEDULE_V2_READY__NO_GPU_AUTHORIZATION__NO_REMOTE_ACTION",
            "schema":"storyforge-r54-gpu-preflight-v2",
            "counts":COUNTS,"model_revision":MODEL,
            "training_config":{"config_sha256":EXPECTED["config"],
                               "optimizer_steps_estimate":16,
                               "gradient_accumulation_steps":2,
                               "eval_every_updates":4,
                               "save_every_updates":8},
            "r50_read":False,"gpu_job_submitted":False}

def main():
    ap=argparse.ArgumentParser()
    for name in ("release-dir","cpu-report","cpu-intake","config","out"):
        ap.add_argument("--"+name,type=Path,required=True)
    a=ap.parse_args()
    try:
        r=check(a.release_dir,a.cpu_report,a.cpu_intake,a.config)
        insist(not a.out.exists(),"R54 output receipt overwrite forbidden")
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
        print("R54_GPU_SCHEDULE_V2_PREFLIGHT_PASS__NO_GPU_JOB__NO_R50")
        return 0
    except (ValueError,KeyError,TypeError,OSError) as e:
        print("R54_PREFLIGHT_BLOCKED:",e,file=sys.stderr);return 2

if __name__=="__main__":raise SystemExit(main())

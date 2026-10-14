#!/usr/bin/env python3
"""StoryForge R46: single bounded, explicitly authorized QLoRA experiment."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

from v02_r46_build_dataset import build

ROOT=Path("/workspace")
MODEL="Qwen/Qwen3.8-27B"
REV="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
PERMIT="R46_ONE_EPOCH_49_15_EXPLORE"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p:Path,obj:dict)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n")

def run(cmd:list[str],log:Path)->None:
    with log.open("a") as f:
        f.write("COMMAND: "+" ".join(cmd)+"\n");f.flush()
        print("COMMAND: "+" ".join(cmd),flush=True)
        p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        assert p.stdout is not None
        for line in p.stdout:
            print(line,end="",flush=True);f.write(line);f.flush()
        if p.wait()!=0:raise RuntimeError(f"command failed ({p.returncode}): {cmd[0]}")

def gpu_gate()->dict:
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:
        raise RuntimeError("one CUDA GPU required")
    dev=torch.cuda.get_device_properties(0)
    free,_=torch.cuda.mem_get_info(0)
    if dev.total_memory<75*1024**3 or free<70*1024**3:
        raise RuntimeError("A100 80 GB capacity gate failed")
    return {"name":dev.name,"total_bytes":dev.total_memory,"free_bytes":free}

def config_gate(path:Path)->dict:
    import yaml
    c=yaml.safe_load(path.read_text())
    expected={"model":MODEL,"lora_rank":64,"lora_alpha":128,"lora_dropout":0.05,
              "max_length":16384,"loss_scale":"last_round",
              "quant_method":"bnb","quant_bits":4,"bnb_4bit_compute_dtype":"bfloat16",
              "disable_ignore_empty_think":True,"add_non_thinking_prefix":False,
              "per_device_train_batch_size":1,"per_device_eval_batch_size":1,
              "gradient_accumulation_steps":8,"num_train_epochs":1,"learning_rate":5e-5,
              "eval_strategy":"steps","eval_steps":3,"save_strategy":"steps","save_steps":3}
    for key,value in expected.items():
        if c.get(key)!=value:raise RuntimeError("config mismatch: "+key)
    if "max_steps" in c:raise RuntimeError("max_steps must not override the epoch")
    if any("test" in str(value).lower() for field in ("dataset","val_dataset")
           for value in c.get(field,[])):
        raise RuntimeError("held-out test data forbidden in training")
    return {"sha256":sha(path),"checked_keys":len(expected)}

def compiled_gate(path:Path,count:int)->None:
    rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    if len(rows)!=count:raise RuntimeError("compiled row count mismatch")
    for row in rows:
        msg=row["messages"]
        if not (msg[0]["role"]=="system" and msg[-2]["role"]=="user"
                and msg[-1]["role"]=="assistant"):
            raise RuntimeError("compiled message roles changed")
        if any(x.get("loss") is not False for x in msg[:-1] if x["role"]=="assistant"):
            raise RuntimeError("historical assistant supervision leaked")
        if any(x.get("loss") is True for x in msg[:-1]):
            raise RuntimeError("historical system/user supervision leaked")
        if msg[-1].get("loss") is not True:
            raise RuntimeError("final assistant supervision missing")

def collect_training(output:Path)->dict:
    states=[]
    for p in output.rglob("trainer_state.json"):
        try:
            data=json.loads(p.read_text())
            states.append((int(data.get("global_step",0)),p,data))
        except (ValueError,TypeError):
            continue
    if not states:raise RuntimeError("trainer_state.json absent")
    step,p,data=max(states,key=lambda x:x[0])
    losses=[float(x["loss"]) for x in data.get("log_history",[]) if x.get("loss") is not None]
    vals=[float(x["eval_loss"]) for x in data.get("log_history",[]) if x.get("eval_loss") is not None]
    if not (6<=step<=9 and losses and vals and all(math.isfinite(x) for x in losses+vals)):
        raise RuntimeError(f"optimizer or evaluation incomplete: step {step}")
    adapters=[q.parent for _,q,_ in states
              if (q.parent/"adapter_model.safetensors").is_file()
              and (q.parent/"adapter_config.json").is_file()]
    if not adapters:raise RuntimeError("adapter checkpoint absent")
    adapter=p.parent if p.parent in adapters else adapters[0]
    return {"recorded_global_step":step,"last_train_loss":losses[-1],
            "last_validation_loss":vals[-1],"adapter_path":str(adapter),
            "adapter_sha256":sha(adapter/"adapter_model.safetensors")}

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--stage",type=Path,required=True)
    p.add_argument("--run-key",required=True)
    a=p.parse_args()
    if re.fullmatch(r"r46-[0-9TZ-]+-[0-9]{6}",a.run_key) is None:
        raise SystemExit("R46 invalid run key")
    if (os.environ.get("STORYFORGE_R46_RUN_KEY")!=a.run_key or
        os.environ.get("STORYFORGE_EXPERIMENTAL_GPU_AUTHORIZED")!=PERMIT):
        raise SystemExit("R46 owner scope approval missing")
    stage=a.stage
    out=ROOT/"experiments/v02-r46"/a.run_key
    if out.exists():raise SystemExit("refusing to overwrite an existing GPU run")
    out.mkdir(parents=True)
    log=out/"commands.log"
    report={"status":"FAILED_OR_INCOMPLETE","run_key":a.run_key,
            "formal_data_admission":False,"training_started":False,
            "training_finished":False,"independent_heldout_used":False}
    started=time.monotonic()
    try:
        for item in (stage/"CODE_SHA256SUMS.txt").read_text().splitlines():
            digest,rel=item.split("  ",1)
            if sha(stage/rel)!=digest:raise RuntimeError("stage code SHA mismatch: "+rel)
        raw=ROOT/"preflight/v02-r27/private/r27_private_candidate_117_NOT_APPROVED.jsonl"
        report["input"]=build(raw,stage/"code/manifest.json",out/"source-data")
        cfg=stage/"code/r46_config.yaml"
        report["config"]=config_gate(cfg)
        report["gpu"]=gpu_gate()
        os.environ.update({"HF_HOME":"/workspace/cache/huggingface",
            "PIP_CACHE_DIR":"/workspace/cache/pip","CUDA_VISIBLE_DEVICES":"0",
            "TOKENIZERS_PARALLELISM":"false","PYTHONUNBUFFERED":"1"})
        run([sys.executable,"-m","pip","install","--disable-pip-version-check",
             "ms-swift==4.5.3","transformers==5.16.1",
             "bitsandbytes==0.50.2","qwen-vl-utils==0.0.14",
             "huggingface_hub>=0.35,<3"],log)
        for split,count in (("train",49),("validation",15)):
            source=out/"source-data"/(split+".jsonl")
            target=out/(split+".jsonl")
            run([sys.executable,str(stage/"scripts/prepare_sft.py"),
                 "--source",str(source),"--output",str(target)],log)
            compiled_gate(target,count)
        run([sys.executable,str(stage/"scripts/hf_cpu_preflight.py"),
             "--data",str(out),"--config",str(cfg)],log)
        for split,count in (("train",49),("validation",15)):
            run([sys.executable,str(stage/"scripts/hf_label_mask_audit.py"),
                 "--dataset",str(out/(split+".jsonl")),
                 "--samples",str(count),"--config",str(cfg)],log)
        print("R46_ACTUAL_COMPILED_LABEL_MASK_PASS_64",flush=True)
        report["compiled_sha256"]={k:sha(out/(k+".jsonl")) for k in ("train","validation")}
        from huggingface_hub import snapshot_download
        snap=Path(snapshot_download(repo_id=MODEL,revision=REV))
        if REV not in str(snap.resolve()) or not (snap/"config.json").is_file():
            raise RuntimeError("pinned model revision unavailable")
        report["training_started"]=True
        save(out/"r46_training_report.json",report)
        run(["swift","sft",str(cfg),"--model",str(snap),
             "--dataset",str(out/"train.jsonl"),
             "--val_dataset",str(out/"validation.jsonl"),
             "--output_dir",str(out/"output"),"--save_only_model","false",
             "--loss_scale","last_round","--custom_register_path",
             str(stage/"scripts/hf_smoke_guard.py")],log)
        result=collect_training(out/"output")
        report["training_evidence"]=result
        sys.path.insert(0,str(stage/"scripts"))
        from hf_job_runner import make_inference_input,check_inference_result
        prompt=out/"adapter_reload_input.jsonl"
        response=out/"adapter_reload_response.jsonl"
        make_inference_input(out/"validation.jsonl",prompt)
        run(["swift","infer","--model",str(snap),"--use_hf","true",
             "--adapters",result["adapter_path"],"--val_dataset",str(prompt),
             "--val_dataset_sample","1","--infer_backend","transformers",
             "--torch_dtype","bfloat16","--quant_method","bnb","--quant_bits","4",
             "--bnb_4bit_compute_dtype","bfloat16","--max_new_tokens","128",
             "--result_path",str(response)],log)
        check_inference_result(response)
        report["training_finished"]=True
        report["adapter_reload"]="PASS"
        report["status"]="EXPLORATORY_GPU_SFT_PASS_NOT_PROMOTED"
        (out/"R46_EXPLORATORY_PASS_NO_PROMOTION").write_text("train and adapter reload PASS\n")
        return 0
    except Exception as e:
        report["error"]=f"{type(e).__name__}: {e}"
        traceback.print_exc()
        return 2
    finally:
        report["elapsed_seconds"]=round(time.monotonic()-started,2)
        save(out/"r46_training_report.json",report)
        print("R46_REPORT="+str(out/"r46_training_report.json"),flush=True)
        print("R46_STATUS="+report["status"],flush=True)

if __name__=="__main__":
    raise SystemExit(main())

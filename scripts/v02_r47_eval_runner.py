#!/usr/bin/env python3
"""R47 three-arm retrospective inference; no training or quality promotion."""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path("/workspace")
MODEL="Qwen/Qwen3.8-27B"
REV="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
V01=ROOT/"baseline-runs/baseline/6ac75bafdf2184ac91acb293/output/v0-20261008-090236/checkpoint-9"
V02=ROOT/"experiments/v02-r46/r46-20261014T070529Z-248172/output/v0-20261014-070817/checkpoint-7"
EXPECTED={"v01":"621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478",
          "v02":"bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b"}
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def run(cmd,log):
    with log.open("a",encoding="utf-8") as f:
        f.write("COMMAND: "+" ".join(cmd)+"\n");f.flush()
        print("COMMAND:", " ".join(cmd),flush=True)
        p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        assert p.stdout
        for s in p.stdout:
            print(s,end="",flush=True);f.write(s);f.flush()
        if p.wait():raise RuntimeError(f"command {cmd[0]} failed, status {p.returncode}")
def store(path,value):
    p=path.with_suffix(".tmp")
    p.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    p.replace(path)
def gate_gpu():
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise RuntimeError("single GPU required")
    g=torch.cuda.get_device_properties(0);free,total=torch.cuda.mem_get_info(0)
    if g.total_memory<75*1024**3 or free<65*1024**3:raise RuntimeError("80GB GPU capacity check failed")
    return {"name":g.name,"total_bytes":total,"free_bytes":free}
def infer(prompts,output,snapshot,adapter):
    cmd=["swift","infer","--model",str(snapshot),"--use_hf","true"]
    if adapter:cmd+=["--adapters",str(adapter)]
    cmd+=["--val_dataset",str(prompts),"--infer_backend","transformers",
          "--torch_dtype","bfloat16","--quant_method","bnb","--quant_bits","4",
          "--bnb_4bit_compute_dtype","bfloat16","--max_new_tokens","1536",
          "--seed","42","--data_seed","42","--temperature","0",
          "--val_dataset_shuffle","false","--result_path",str(output)]
    return cmd
def stage_gate(stage):
    for line in (stage/"SHA256SUMS.txt").read_text().splitlines():
        digest,rel=line.split("  ",1)
        if ".." in Path(rel).parts or Path(rel).is_absolute() or sha(stage/rel)!=digest:
            raise RuntimeError("staged file SHA mismatch "+rel)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",type=Path,required=True);p.add_argument("--run-key",required=True)
    a=p.parse_args()
    if not re.fullmatch(r"r47-[0-9TZ-]+-[0-9]{6}",a.run_key):raise SystemExit("bad R47 run key")
    if (os.environ.get("STORYFORGE_R47_RUN_KEY")!=a.run_key or
        os.environ.get("STORYFORGE_R47_EVAL_AUTHORIZED")!="R47_EXPOSED_TEST_20_3_ARM_REVIEW"):
        raise SystemExit("evaluation owner authorization missing")
    out=ROOT/"evaluation-runs/v02-r47"/a.run_key
    if out.exists():raise SystemExit("refusing existing output directory")
    out.mkdir(parents=True)
    report={"status":"BLOCKED","run_key":a.run_key,"scope":"EXPOSED_V01_20_RETROSPECTIVE_ONLY",
            "fresh_heldout":False,"training_performed":False,"promotion_approved":False,
            "completed_arms":[],"generation_complete":False}
    log=out/"execution.log";started=time.monotonic()
    try:
        stage_gate(a.stage)
        sys.path.insert(0,str(a.stage/"code"))
        from v02_r47_eval_validate import validate_prompts,validate_responses,write_blind
        prompts=a.stage/"private/v01_test_prompts.jsonl"
        manifest=a.stage/"private/v01_test_manifest.json"
        data,_=validate_prompts(prompts,manifest)
        report["input"]={"count":len(data),"prompts_sha256":sha(prompts),"manifest_sha256":sha(manifest)}
        report["gpu"]=gate_gpu()
        os.environ.update({"HF_HOME":"/workspace/cache/huggingface","PIP_CACHE_DIR":"/workspace/cache/pip",
                           "CUDA_VISIBLE_DEVICES":"0","TOKENIZERS_PARALLELISM":"false","PYTHONUNBUFFERED":"1"})
        store(out/"R47_PRIVATE_RUN_REPORT.json",report)
        run([sys.executable,"-m","pip","install","--disable-pip-version-check","ms-swift==4.5.3",
             "transformers==5.16.1","bitsandbytes==0.50.2","qwen-vl-utils==0.0.14",
             "huggingface_hub>=0.35,<3"],log)
        for name,path in (("v01",V01),("v02",V02)):
            weight=path/"adapter_model.safetensors"
            if not weight.is_file() or not (path/"adapter_config.json").is_file() or sha(weight)!=EXPECTED[name]:
                raise RuntimeError(name+" checkpoint absent or SHA mismatch")
        report["adapter_weight_sha256"]=EXPECTED
        from huggingface_hub import snapshot_download
        snap=Path(snapshot_download(repo_id=MODEL,revision=REV))
        if REV not in str(snap.resolve()) or not (snap/"config.json").is_file():
            raise RuntimeError("pinned Qwen model unavailable")
        report["model_revision"]=REV
        # R47.1 rescue: re-use the already-paid, completed Base inference.
        # The old run is immutable, its prompt manifest must match this stage,
        # and its 20 outputs must pass strict role/content alignment BEFORE
        # any old Base result can enter the new blind evaluation.
        reuse=os.environ.get("STORYFORGE_R47_REUSE_BASE_RUN_KEY","")
        if reuse and (not re.fullmatch(r"r47-[0-9TZ-]+-[0-9]{6}",reuse) or reuse==a.run_key):
            raise RuntimeError("invalid Base recovery RUN_KEY")
        for arm,adapter in (("base",None),("v01",V01),("v02",V02)):
            target=out/(arm+"-results.jsonl")
            if arm=="base" and reuse:
                previous=ROOT/"evaluation-runs/v02-r47"/reuse
                previous_report=json.loads((previous/"R47_PRIVATE_RUN_REPORT.json").read_text())
                if (previous_report.get("run_key")!=reuse
                        or previous_report.get("status")!="BLOCKED"
                        or previous_report.get("training_performed") is not False
                        or previous_report.get("input",{}).get("prompts_sha256")!=sha(prompts)
                        or previous_report.get("input",{}).get("manifest_sha256")!=sha(manifest)):
                    raise RuntimeError("old Base report identity/input mismatch")
                source=previous/"base-results.jsonl"
                validate_responses(source,data)
                source_digest=sha(source)
                shutil.copyfile(source,target)
                if sha(target)!=source_digest:
                    raise RuntimeError("copied Base result SHA mismatch")
                report["reused_base"]={"run_key":reuse,"sha256":source_digest,
                                       "source":"original failed R47 GPU run, preserved byte-exact"}
                print("R47_REUSED_BASE_20_20_PASS sha256="+source_digest,flush=True)
            else:
                run(infer(prompts,target,snap,adapter),log)
                validate_responses(target,data)
            report["completed_arms"].append(arm)
            report.setdefault("results_sha256",{})[arm]=sha(target)
            store(out/"R47_PRIVATE_RUN_REPORT.json",report)
        paths={arm:out/(arm+"-results.jsonl") for arm in ("base","v01","v02")}
        report["blind_pack"]=write_blind(prompts,manifest,paths,out/"review-package")
        report["generation_complete"]=True
        report["status"]="R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED"
        (out/"R47_EVAL_PASS_NO_PROMOTION").write_text("three arms on exposed old 20 prompts complete\n")
        return 0
    except Exception as exc:
        report["error"]=f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        return 2
    finally:
        report["elapsed_seconds"]=round(time.monotonic()-started,2)
        store(out/"R47_PRIVATE_RUN_REPORT.json",report)
        print("R47_REPORT="+str(out/"R47_PRIVATE_RUN_REPORT.json"),flush=True)
        print("R47_STATUS="+report["status"],flush=True)
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""R54 V2: one explicitly authorized private GPU experiment, never promote."""
from __future__ import annotations
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

ROOT = Path("/workspace")
BUCKET_RUNS = ROOT / "preflight/v03-r54/gpu/runs"
EXPERIMENTS = ROOT / "experiments/v03-r54"
MODEL = "Qwen/Qwen3.8-27B"
REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
EXPECTED = {"train": ("d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7", 31),
            "validation": ("b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d", 9)}
SCOPE = "R54_31_9_V2_16STEP_ONE_EPOCH"

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def save(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)+"\n")

def insist(ok: bool, why: str) -> None:
    if not ok: raise RuntimeError(why)

def run(command: list[str], log: Path) -> None:
    with log.open("a", encoding="utf-8") as file:
        file.write("COMMAND (args may contain PRIVATE paths): "+str(command)+"\n")
        file.flush()
        process=subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout
        for line in process.stdout:
            file.write(line)
            file.flush()
            print(line, end="", flush=True)
        insist(process.wait()==0, f"command failed: {command[0]}")

def gpu_gate() -> dict:
    import torch
    insist(torch.cuda.is_available() and torch.cuda.device_count()==1, "exactly one CUDA GPU required")
    props=torch.cuda.get_device_properties(0)
    free,_=torch.cuda.mem_get_info(0)
    insist(props.total_memory>=75*1024**3 and free>=70*1024**3,
           "A100 80GB size/free memory gate failed")
    return {"name":props.name, "total_bytes":props.total_memory, "free_bytes_at_start":free}

def stage_gate(stage: Path) -> dict:
    # No training before verifying every uploaded byte, including code.
    manifest=stage/"SHA256SUMS.txt"
    insist(manifest.is_file() and not manifest.is_symlink(),"stage sha manifest missing")
    names=set()
    for line in manifest.read_text().splitlines():
        parts=line.split("  ",1)
        insist(len(parts)==2 and re.fullmatch(r"[0-9a-f]{64}",parts[0]),"bad stage sha line")
        name=parts[1]
        insist(re.fullmatch(r"(code|config|private)/(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+",name)
               and name not in names,"unsafe/duplicate relative stage file")
        names.add(name)
        file=stage/name
        insist(file.is_file() and not file.is_symlink() and digest(file)==parts[0],
               "uploaded stage file sha mismatch: "+name)
    required={"config/r54.yaml",
              "private/release/train.jsonl","private/release/validation.jsonl",
              "private/release/R53_RELEASE_RECEIPT.json",
              "private/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json",
              "private/R53_CPU40_OWNER_INTAKE_VERIFIED.json",
              "code/v03_r54_gpu_runner.py","code/v03_r54_gpu_worker.sh",
              "code/v03_r54_gpu_readiness_v2.py","code/v03_r54_last_step_checkpoint_gate.py",
              "code/hf_label_mask_audit.py","code/hf_smoke_guard.py",
              "code/hf_job_runner.py"}
    insist(names==required,"unexpected or missing stage files")
    sys.path.insert(0,str(stage/"code"))
    from v03_r54_gpu_readiness_v2 import check
    preview=check(stage/"private/release",
                  stage/"private/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json",
                  stage/"private/R53_CPU40_OWNER_INTAKE_VERIFIED.json",
                  stage/"config/r54.yaml")
    insist(preview["training_config"]["optimizer_steps_estimate"]==16,
           "R54 V2 16step preview mismatch")
    return {"sha256sum_sha256":digest(manifest),
            "formal_release_receipt_sha256":digest(stage/"private/release/R53_RELEASE_RECEIPT.json"),
            "train_sha256":digest(stage/"private/release/train.jsonl"),
            "validation_sha256":digest(stage/"private/release/validation.jsonl"),
            "config_sha256":digest(stage/"config/r54.yaml")}

def main() -> int:
    key=os.environ.get("STORYFORGE_R54_RUN_KEY","")
    insist(re.fullmatch(r"r54-v2-[0-9]{8}T[0-9]{6}Z-[0-9]{6}",key) is not None,"invalid R54 key")
    insist(os.environ.get("STORYFORGE_R54_PAID_GPU_SCOPE")==SCOPE,
           "R54 owner paid-GPU scope not given in Job")
    stage=BUCKET_RUNS/key
    result=EXPERIMENTS/key
    insist(stage.is_dir() and not stage.is_symlink(),"missing stage")
    insist(not result.exists() and not result.is_symlink(),"GPU result prefix already exists")
    result.mkdir(parents=True, exist_ok=False)
    report={"schema":"storyforge-r54-v2-gpu-one-epoch-v1",
            "status":"FAILED_OR_INCOMPLETE__NO_PROMOTION","run_key":key,
            "model":MODEL,"revision":REVISION,
            "formal_train_rows":31,"formal_validation_rows":9,
            "training_started":False,"training_finished":False,
            "adapter_reload_pass":False,"model_promoted":False,
            "r50_read":False,"gpu_used":False}
    started=time.monotonic()
    log=result/"R54_GPU_RUNTIME_PRIVATE.log"
    try:
        report["stage"]=stage_gate(stage)
        report["gpu"]=gpu_gate()
        report["gpu_used"]=True
        os.environ.update({"HF_HOME":"/workspace/cache/huggingface",
                           "PIP_CACHE_DIR":"/workspace/cache/pip",
                           "CUDA_VISIBLE_DEVICES":"0","TOKENIZERS_PARALLELISM":"false",
                           "PYTHONUNBUFFERED":"1"})
        run([sys.executable,"-m","pip","install","--disable-pip-version-check",
             "ms-swift==4.5.3","transformers==5.16.1","bitsandbytes==0.50.2",
             "qwen-vl-utils==0.0.14","huggingface_hub>=0.35,<3"],log)
        from importlib.metadata import version
        report["dependencies"]={n:version(n) for n in ("ms-swift","transformers","bitsandbytes")}
        for split,(expected,count) in EXPECTED.items():
            p=stage/"private/release"/(split+".jsonl")
            insist(digest(p)==expected and sum(bool(x.strip()) for x in p.read_text().splitlines())==count,
                   "train/validation mutated before GPU")
            run([sys.executable,str(stage/"code/hf_label_mask_audit.py"),
                 "--dataset",str(p),"--samples",str(count),
                 "--config",str(stage/"config/r54.yaml")],log)
        report["actual_ms_swift_full_label_audit"]="PASS_40"
        from huggingface_hub import snapshot_download
        snap=Path(snapshot_download(repo_id=MODEL,revision=REVISION))
        insist(REVISION in str(snap.resolve()) and (snap/"config.json").is_file(),
               "pinned model snapshot missing")
        # Training starts ONLY after all real-input, label, model and GPU checks.
        report["training_started"]=True
        save(result/"R54_GPU_RUN_REPORT_PRIVATE.json",report)
        train=stage/"private/release/train.jsonl"
        val=stage/"private/release/validation.jsonl"
        output=result/"output"
        run(["swift","sft",str(stage/"config/r54.yaml"),
             "--model",str(snap),"--dataset",str(train),"--val_dataset",str(val),
             "--output_dir",str(output),"--save_only_model","false",
             "--loss_scale","last_round","--custom_register_path",
             str(stage/"code/hf_smoke_guard.py")],log)
        report["training_finished"]=True
        sys.path.insert(0,str(stage/"code"))
        from v03_r54_last_step_checkpoint_gate import check as checkpoint_check
        checkpoint=checkpoint_check(output)
        insist(checkpoint["global_step"]==16,"missing terminal optimizer checkpoint")
        report["checkpoint_before_reload"]=checkpoint
        save(result/"R54_GPU_RUN_REPORT_PRIVATE.json",report)
        from hf_job_runner import make_inference_input,check_inference_result
        inference_input=result/"reload_prompt_PRIVATE.jsonl"
        inference_output=result/"reload_response_PRIVATE.jsonl"
        make_inference_input(val,inference_input)
        # No Gold target in the inference prompt.
        run(["swift","infer","--model",str(snap),"--use_hf","true",
             "--adapters",checkpoint["final_checkpoint_path"],
             "--val_dataset",str(inference_input),"--val_dataset_sample","1",
             "--infer_backend","transformers","--torch_dtype","bfloat16",
             "--quant_method","bnb","--quant_bits","4",
             "--bnb_4bit_compute_dtype","bfloat16","--max_new_tokens","128",
             "--result_path",str(inference_output)],log)
        check_inference_result(inference_output)
        reload_record={"status":"R54_ADAPTER_RELOAD_INFERENCE_PASS",
                       "final_global_step":16,"adapter_sha256":checkpoint["final_adapter_sha256"],
                       "model_revision":REVISION,"inference_output_sha256":digest(inference_output),
                       "gold_target_in_inference_prompt":False}
        reload_file=result/"R54_ADAPTER_RELOAD_VERIFIED_PRIVATE.json"
        save(reload_file,reload_record)
        final=checkpoint_check(output,reload_file)
        report["checkpoint_and_reload"]=final
        report["adapter_reload_pass"]=True
        report["status"]="R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED"
        save(result/"R54_GPU_RUN_REPORT_PRIVATE.json",report)
        (result/"R54_GPU_SUCCESS_NOT_PROMOTED").write_text(report["status"]+"\n")
        with log.open("a",encoding="utf-8") as runtime_log:
            runtime_log.write("R54_STATUS="+report["status"]+"\n")
        print("R54_STATUS="+report["status"],flush=True)
        return 0
    except Exception as exc:
        report["error"]=f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        return 2
    finally:
        report["elapsed_seconds"]=round(time.monotonic()-started,2)
        save(result/"R54_GPU_RUN_REPORT_PRIVATE.json",report)
        if log.exists():
            (result/"R54_GPU_RUNTIME_SHA256.txt").write_text(digest(log)+"  R54_GPU_RUNTIME_PRIVATE.log\n")
        print("R54_REPORT="+str(result/"R54_GPU_RUN_REPORT_PRIVATE.json"),flush=True)
        print("R54_STATUS="+report["status"],flush=True)

if __name__=="__main__":
    raise SystemExit(main())

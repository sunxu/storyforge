#!/usr/bin/env python3
"""R54 V2 owner-returned GPU artifact intake (read-only; no training)."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MODEL="Qwen/Qwen3.8-27B"
REVISION="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
TRAIN_SHA="d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7"
VAL_SHA="b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d"
CONFIG_SHA="55ac554a4fe4b4974b7f7f664dcf5a9163b5e37219150acc087309282ef4d861"
RELEASE_SHA="3d8078ee3b4528521b7f67ba1dd7983f0d20bfeb4d7c79e92d9cabe2c6b2e836"
HEX=re.compile(r"[0-9a-f]{64}\Z")
KEY=re.compile(r"r54-v2-[0-9]{8}T[0-9]{6}Z-[0-9]{6}\Z")

def insist(ok,msg):
    if not ok: raise ValueError(msg)

def hashfile(path: Path) -> str:
    insist(path.is_file() and not path.is_symlink(),"missing/symlinked artifact: "+path.name)
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def verify(report_file: Path,log_file: Path,reload_file: Path,release_dir: Path,config: Path) -> dict:
    insist(hashfile(config)==CONFIG_SHA,"R54 config hash drift")
    insist(hashfile(release_dir/"train.jsonl")==TRAIN_SHA
           and hashfile(release_dir/"validation.jsonl")==VAL_SHA
           and hashfile(release_dir/"R53_RELEASE_RECEIPT.json")==RELEASE_SHA,
           "R53 private release bytes drift")
    r=json.loads(report_file.read_bytes())
    reload=json.loads(reload_file.read_bytes())
    insist(r.get("schema")=="storyforge-r54-v2-gpu-one-epoch-v1","unexpected GPU report schema")
    key=r.get("run_key","")
    insist(isinstance(key,str) and KEY.fullmatch(key),"invalid run key")
    insist(r.get("status")=="R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED"
           and r.get("training_started") is True and r.get("training_finished") is True
           and r.get("adapter_reload_pass") is True,"GPU engineering not fully PASS")
    insist(r.get("model")==MODEL and r.get("revision")==REVISION
           and r.get("formal_train_rows")==31 and r.get("formal_validation_rows")==9,
           "GPU model/size mismatch")
    insist(r.get("r50_read") is False and r.get("model_promoted") is False
           and r.get("gpu_used") is True,"R50/model promotion/GPU scope mismatch")
    stage=r.get("stage")
    insist(isinstance(stage,dict) and
           stage.get("config_sha256")==CONFIG_SHA and
           stage.get("train_sha256")==TRAIN_SHA and
           stage.get("validation_sha256")==VAL_SHA and
           stage.get("formal_release_receipt_sha256")==RELEASE_SHA,
           "GPU source provenance mismatch")
    deps=r.get("dependencies",{})
    insist(deps.get("ms-swift")=="4.5.3" and deps.get("transformers")=="5.16.1"
           and deps.get("bitsandbytes")=="0.50.2","GPU dependency mismatch")
    insist(r.get("actual_ms_swift_full_label_audit")=="PASS_40"
           and isinstance(r.get("gpu"),dict),"GPU mask/device check missing")
    checkpoint=r.get("checkpoint_and_reload")
    insist(isinstance(checkpoint,dict)
           and checkpoint.get("status")=="R54_FINAL_STEP_16_CHECKPOINT_AND_RELOAD_EVIDENCE_ACCEPTED__NOT_PROMOTED"
           and checkpoint.get("global_step")==16
           and checkpoint.get("final_checkpoint")=="checkpoint-16"
           and checkpoint.get("intermediate_checkpoint")=="checkpoint-8"
           and all(k in checkpoint.get("eval_steps_verified",[]) for k in (4,8,12)),
           "step-16 final checkpoint proof incomplete")
    adapter_sha=checkpoint.get("final_adapter_sha256","")
    insist(isinstance(adapter_sha,str) and HEX.fullmatch(adapter_sha),"adapter digest missing")
    insist(reload.get("status")=="R54_ADAPTER_RELOAD_INFERENCE_PASS"
           and reload.get("final_global_step")==16 and
           reload.get("model_revision")==REVISION and
           reload.get("adapter_sha256")==adapter_sha and
           checkpoint.get("reload_report_sha256")==hashfile(reload_file),
           "adapter reload evidence inconsistent")
    log=log_file.read_bytes()
    insist(b"R54_STATUS=R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED" in log,
           "authentic GPU console PASS marker missing in supplied log")
    result={"schema":"storyforge-r54-v2-gpu-owner-intake-v1",
            "status":"R54_V2_OWNER_GPU_ENGINEERING_REPORT_LOG_RELOAD_CROSSCHECK_PASS__NOT_PROMOTED",
            "run_key":key,
            "training_report_sha256":hashfile(report_file),
            "runtime_log_sha256":hashfile(log_file),
            "reload_report_sha256":hashfile(reload_file),
            "adapter_sha256_reported_not_independently_downloaded":adapter_sha,
            "global_step":16,"train_rows":31,"validation_rows":9,
            "independent_remote_weight_sha256_verification":False,
            "model_promoted":False,"r50_opened":False,
            "limitations":"Owner-provided run report/log/reload cross-check only; adapter weight bytes not downloaded/rehashed here."}
    return result

def main() -> int:
    ap=argparse.ArgumentParser()
    for name in ("report","runtime-log","reload-report","release-dir","config","out"):
        ap.add_argument("--"+name,type=Path,required=True)
    a=ap.parse_args()
    try:
        result=verify(a.report,a.runtime_log,a.reload_report,a.release_dir,a.config)
        insist(not a.out.exists(),"receipt overwrite forbidden")
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
        print(result["status"])
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("R54_VERIFY_BLOCKED:",str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())

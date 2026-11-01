#!/usr/bin/env python3
"""Local-only prepare/verify of private R58 HF CPU132 inputs. No job submission."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import stat

from gold195_hf_review_cpu_worker import FILES, verify_stage, load_rows, MODEL_REVISION

def prep(repo, source, output):
    repo=repo.resolve()
    if not (source.is_absolute() and source.is_file() and not source.is_symlink()
            and stat.S_IMODE(source.stat().st_mode)==0o600):
        raise ValueError("private input invalid")
    load_rows(source)
    if (not output.is_absolute() or output.exists() or output.is_symlink()
            or repo==output.resolve() or repo in output.resolve().parents
            or stat.S_IMODE(output.parent.stat().st_mode)&0o077):
        raise ValueError("output directory invalid")
    output.mkdir(mode=0o700)
    (output/"code").mkdir(mode=0o700)
    (output/"private").mkdir(mode=0o700)
    origins=(repo/"experiments/r58_quality/gold195_hf_review_cpu_worker.py",
             repo/"experiments/r58_quality/gold195_hf_review_gpu_runner.py", source)
    lines=[]
    for name, origin in zip(FILES, origins):
        raw=origin.read_bytes()
        with (output/name).open("xb") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(raw)
        lines.append(hashlib.sha256(raw).hexdigest()+"  "+name)
    with (output/"SHA256SUMS.txt").open("xb") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(("\n".join(lines)+"\n").encode())
    verify_stage(output)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,required=True)
    p.add_argument("--private-input",type=Path,required=True)
    p.add_argument("--stage-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        prep(a.repo_root,a.private_input,a.stage_dir)
        state="R58_HF_CPU132_STAGE_READY__NOT_UPLOADED"
        code=0
    except Exception:
        state="R58_HF_CPU132_LOCAL_STAGE_INVALID__HOLD"
        code=42
    print(json.dumps({"status":state,"quality_v1_admitted":0,
         "hf_job_started":False,"private_text_emitted":False}))
    return code
if __name__=="__main__":
    raise SystemExit(main())

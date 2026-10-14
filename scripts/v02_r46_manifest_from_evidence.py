#!/usr/bin/env python3
"""Derive R45 IDs using already recorded R43 report and R44/R45 review gates."""
import argparse
import hashlib
import json
from pathlib import Path

ap=argparse.ArgumentParser()
for name in ("r43-report","r44-gate","r45-gate","output"):
    ap.add_argument("--"+name,type=Path,required=True)
a=ap.parse_args()
r43=a.r43_report.read_bytes()
r44=json.loads(a.r44_gate.read_text())
r45=json.loads(a.r45_gate.read_text())
report=json.loads(r43)
if hashlib.sha256(r43).hexdigest()!=r44["r43_remote_full_json_sha256"]:
    raise SystemExit("R43 source report hash mismatch")
if report["status"]!="ACTUAL_COLLATOR_PASS_NO_TRAINING_APPROVAL":
    raise SystemExit("R43 actual collator did not pass")
if (report.get("training_performed"),report.get("gpu_authorized"))!=(False,False):
    raise SystemExit("R43 must be a no-training CPU report")
excluded=set(r45["new_hold_sample_ids"])|{r44["new_hold_id"]}
if len(excluded)!=8:raise SystemExit("expected eight R44/45 exclusion IDs")
partitions={}
all_remote=set()
for split,original,selected in (("train",56,49),("validation",16,15)):
    group=report["datasets"][split]
    if group["count"]!=original or group["passed"]!=original or len(group["rows"])!=original:
        raise SystemExit("R43 count mismatch")
    if any(r["status"]!="PASS" for r in group["rows"]):
        raise SystemExit("R43 failed record")
    ids=[r["sample_id"] for r in group["rows"]]
    if len(set(ids))!=len(ids):raise SystemExit("R43 duplicate IDs")
    all_remote.update(ids)
    partitions[split]=[id for id in ids if id not in excluded]
    if len(partitions[split])!=selected:raise SystemExit("R45 count mismatch")
if not excluded<=all_remote:raise SystemExit("R45 exclusion not found in R43")
if set(partitions["train"])&set(partitions["validation"]):
    raise SystemExit("overlapping IDs")
manifest={
    "schema":"storyforge-v02-r46-git-plain-source-manifest-v1",
    "experiment":"EXPLORATORY_ONLY_NOT_MODEL_PROMOTION",
    "original_r27_sha256":"cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a",
    "train_sha256":r45["train_sha256"],
    "validation_sha256":r45["validation_sha256"],
    "model_revision":"1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
    "train_ids":partitions["train"],
    "validation_ids":partitions["validation"]
}
a.output.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
print("R46_SELECTION_FROM_PRIOR_EVIDENCE_PASS_49_15")

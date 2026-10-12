#!/usr/bin/env python3
"""Verify original byte-exact R01-R04 snapshots and owner-selected double-ACCEPT 108."""
from pathlib import Path
import csv, hashlib, json, sys

ROOT = Path(__file__).resolve().parent
HASHES = {
    "frozen_r01_63.jsonl": "5f95632e4ee2e5703668518e4743f02325befc95f51c06e58e00f9c6cb196f50",
    "frozen_r02_90.jsonl": "fe8b1a921826a35f1d23541af7e53fc0bce87948c3f4c15d26cd73a376589fa7",
    "frozen_r03_120.jsonl": "3b385db306e11493ac1707f5a02ed4f44c9dd1d71dff93b96bf49a96d575b09c",
    "frozen_r04_150.jsonl": "8fbd2581b6823882d27e7839238335319202b1d9a726fc25d9aa74fedf5487f1",
}
def ck(ok, message):
    if not ok: raise AssertionError(message)
def sha(blob): return hashlib.sha256(blob).hexdigest()
def parse(blob):
    ck(blob.endswith(b"\n"), "missing final newline")
    lines=blob.splitlines(keepends=True)
    return [json.loads(line) for line in lines], lines
def main():
    snapshots=[]
    for (name,digest),count in zip(HASHES.items(),[63,90,120,150]):
        blob=(ROOT/"snapshots"/name).read_bytes()
        ck(sha(blob)==digest,"SHA mismatch: "+name)
        rec,lines=parse(blob)
        ck(len(rec)==count and len({x["id"] for x in rec})==count,"candidate count/uniqueness")
        snapshots.append((blob,lines))
    ck(all(b[0].startswith(a[0]) for a,b in zip(snapshots,snapshots[1:])),"non-exact round prefix")
    accepted_dir=ROOT.parents[1]/"gold-quality-108"
    b=(accepted_dir/"gold_quality_accepted_108.jsonl").read_bytes()
    ck(sha(b)=="27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308","108 sha")
    selected,lines=parse(b)
    ck(len(selected)==108 and len({x["id"] for x in selected})==108,"108 count")
    ck(set(lines).issubset(set(snapshots[-1][1])),"selected source content changed")
    with (accepted_dir/"gold_108_index.csv").open(encoding="utf-8",newline="") as f:
        index=list(csv.DictReader(f))
    ck(len(index)==108 and {x["candidate_id"] for x in index}=={x["id"] for x in selected},"index membership")
    for x in index:
        ck(x["reviewer1_decision"]==x["reviewer2_decision"]=="ACCEPT","not double ACCEPT")
        for label in ("reviewer1_scores","reviewer2_scores"):
            vals=list(map(int,x[label].split(",")))
            ck(len(vals)==5 and min(vals)>=4,"score floor")
    ck(all(x["metadata"].get("training_admission")=="PENDING_NOT_APPROVED" and x["metadata"].get("split") is None for x in selected),"training/split gate")
    print(json.dumps({"status":"PASS","rounds":[63,90,120,150],"accepted":108,"not_selected":42,"training":"PENDING_NOT_APPROVED"}))
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("FAIL:",str(exc),file=sys.stderr)
        sys.exit(1)

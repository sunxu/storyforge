#!/usr/bin/env python3
"""Validate three independent reviewer sheets, optionally unblind regression results."""
from __future__ import annotations
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
from v02_r47_eval_validate import DIMENSIONS

ARMS=("base","v01","v02")
def validate(reviews,manifest):
    meta=json.loads(Path(manifest).read_text(encoding="utf-8"))
    if meta.get("count")!=20 or len(meta.get("samples",[]))!=20:raise ValueError("20 expected")
    expected=[x["sample_id"] for x in meta["samples"]]
    if len(reviews)!=3 or len(set(reviews))!=3:raise ValueError("exact three distinct review files")
    sheets=[]
    for path in reviews:
        with Path(path).open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
        if len(rows)!=20 or [x.get("样本编号") for x in rows]!=expected:raise ValueError("missing/duplicate/reordered sample")
        for row in rows:
            if row.get("整体最佳(A/B/C/TIE)") not in ("A","B","C","TIE"):raise ValueError("preference missing")
            if len(row.get("评分理由与逐字证据","").strip())<8:raise ValueError("verbatim scoring rationale missing")
            if row.get("玩家自主权严重侵犯(A/B/C/无)") not in ("A","B","C","无"):raise ValueError("player agency annotation missing")
            if not row.get("严重问题与对应回复","").strip():raise ValueError("explicit severe-issue/无 note missing")
            for dim in DIMENSIONS:
                for letter in "ABC":
                    try:x=int(row.get(f"{dim}·{letter}",""))
                    except (ValueError,TypeError) as exc:raise ValueError("scores must be integer 1-5") from exc
                    if x<1 or x>5:raise ValueError("score outside 1-5")
        sheets.append(rows)
    return sheets
def aggregate(sheets,key):
    info=json.loads(Path(key).read_text(encoding="utf-8"))
    if info.get("mode")!="RETROSPECTIVE_EXPOSED_V01_TEST" or len(info.get("items",[]))!=20:
        raise ValueError("invalid private answer key")
    mapping={x["sample_id"]:x["mapping"] for x in info["items"]}
    ids=[x["样本编号"] for x in sheets[0]]
    if set(ids)!=set(mapping) or len(mapping)!=20:raise ValueError("key IDs differ")
    votes=Counter();majorities=Counter();scores=defaultdict(list);per_sample=[]
    for i,sid in enumerate(ids):
        trans=mapping[sid]
        if set(trans)!={"A","B","C"} or set(trans.values())!=set(ARMS):raise ValueError("invalid random permutation")
        pref=[]
        for sheet in sheets:
            row=sheet[i];letter=row["整体最佳(A/B/C/TIE)"]
            win=trans[letter] if letter!="TIE" else "TIE"
            votes[win]+=1;pref.append(win)
            for dim in DIMENSIONS:
                for l,arm in trans.items():scores[(arm,dim)].append(int(row[f"{dim}·{l}"]))
        tally=Counter(pref)
        majority=next((a for a,c in tally.items() if c>=2),"NO_MAJORITY")
        majorities[majority]+=1
        per_sample.append({"sample_id":sid,"votes":dict(tally),"majority":majority})
    return {"status":"R47_RETROSPECTIVE_REVIEW_ONLY_NOT_PROMOTED",
            "reviewers":3,"cases":20,"votes":dict(votes),"majority_counts":dict(majorities),
            "means":{arm:{d:round(sum(scores[(arm,d)])/len(scores[(arm,d)]),3) for d in DIMENSIONS} for arm in ARMS},
            "per_sample":per_sample,"fresh_heldout":False,"promotion_approved":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--reviews",type=Path,nargs=3,required=True)
    p.add_argument("--key",type=Path);p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.key and not a.output:p.error("--key requires --output")
    sheets=validate(a.reviews,a.manifest)
    if a.key:
        if a.output.exists():raise FileExistsError("no overwriting aggregate")
        result=aggregate(sheets,a.key)
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("R47_RETROSPECTIVE_AGGREGATE_PASS_NOT_MODEL_PROMOTED")
    else:print("R47_THREE_REVIEWERS_20_CASES_COMPLETE_KEY_NOT_READ")
if __name__=="__main__":main()

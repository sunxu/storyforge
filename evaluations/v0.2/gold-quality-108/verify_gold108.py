#!/usr/bin/env python3
"""Read-only checks for StoryForge v0.2 owner-selected 108 records.

Usage: python3 verify_gold108.py [--source path/to/gold_selected.jsonl]
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

EXPECTED_SHA256 = "27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308"
SOURCE_SHA256 = "8fbd2581b6823882d27e7839238335319202b1d9a726fc25d9aa74fedf5487f1"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, help="Optional frozen source 150-row JSONL, unmodified")
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    payload = (root / "gold_quality_accepted_108.jsonl").read_bytes()
    assert sha(payload) == EXPECTED_SHA256, "108-row file SHA256 mismatch"
    rows_raw = payload.splitlines(keepends=True)
    assert len(rows_raw) == 108 and len({json.loads(x)["id"] for x in rows_raw}) == 108
    rows = [json.loads(x) for x in rows_raw]
    with (root / "gold_108_index.csv").open(encoding="utf-8", newline="") as f:
        idx = list(csv.DictReader(f))
    with (root / "other_42_not_selected.csv").open(encoding="utf-8", newline="") as f:
        other = list(csv.DictReader(f))
    assert len(idx) == 108 and len(other) == 42
    assert [x["candidate_id"] for x in idx] == [x["id"] for x in rows]
    assert not ({x["candidate_id"] for x in idx} & {x["candidate_id"] for x in other})
    assert len({x["candidate_id"] for x in other}) == 42
    assert all(x["reviewer1_decision"] == x["reviewer2_decision"] == "ACCEPT" for x in idx)
    assert all(x["owner_selection"] == "NOT_SELECTED_THIS_RELEASE" for x in other)
    for i, item in zip(idx, rows):
        m = item["metadata"]
        assert item["messages"][-1]["role"] == "assistant"
        assert sha(item["messages"][-1]["content"].encode()) == i["target_sha256"]
        assert m.get("training_admission") == "PENDING_NOT_APPROVED"
        assert m.get("split") is None
        for key in ("reviewer1_scores", "reviewer2_scores"):
            vals = [int(z) for z in i[key].split(",")]
            assert len(vals) == 5 and all(4 <= z <= 5 for z in vals)
    if args.source:
        source = args.source.read_bytes()
        assert sha(source) == SOURCE_SHA256, "Frozen 150-row source SHA256 mismatch"
        exact = set(source.splitlines(keepends=True))
        assert len(exact) == 150
        assert all(line in exact for line in rows_raw), "Selected original line mismatch"
    print(json.dumps({"status":"PASS","selected":108,"unselected":42,"training_admission":"PENDING_NOT_APPROVED","source_byte_match":bool(args.source)},ensure_ascii=False))
if __name__ == "__main__":
    main()

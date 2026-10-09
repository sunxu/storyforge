"""Unblind a frozen four-reviewer StoryForge assessment locally.

Requires the private answer key from the SAME 1536-token evaluation Job.
No network access, no training data content in the output.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

DIMS = ("剧情连续性", "角色一致性", "指令遵循", "文学表现力", "互动推进")
ARBITRATION = {"005": "B", "009": "B", "010": "A", "013": "B"}


def load_sheet(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 15:
        raise ValueError(f"{path}: expected 15 rows")
    result = {}
    for row in rows:
        sid = row["样本编号"]
        if sid in result:
            raise ValueError(f"{path}: duplicate ID {sid}")
        if row["整体偏好(A/B/TIE)"].strip().upper() not in {"A", "B", "TIE"}:
            raise ValueError(f"{path}: invalid preference {sid}")
        for dim in DIMS:
            for arm in "AB":
                v = row[f"{dim}·{arm}"].strip()
                if v not in {"1", "2", "3", "4", "5"}:
                    raise ValueError(f"{path}: invalid {dim}·{arm} for {sid}")
        result[sid] = row
    return result


def unblind(paths: list[Path], key_path: Path) -> dict:
    if len(paths) != 4:
        raise ValueError("exactly four original reviews required")
    reviews = [load_sheet(p) for p in paths]
    ids = set(reviews[0])
    for review in reviews[1:]:
        if set(review) != ids:
            raise ValueError("review sample IDs differ")
        for sid in ids:
            for field in ("故事背景与系统规则", "历史对话",
                          "当前用户输入", "回复A", "回复B"):
                if review[sid][field] != reviews[0][sid][field]:
                    raise ValueError(f"context/A-B mismatch for {sid}")
    entries = json.loads(key_path.read_text(encoding="utf-8"))
    mapping = {entry["sample_id"]: entry for entry in entries}
    if len(mapping) != len(entries) or set(mapping) != ids:
        raise ValueError("private answer key does not exactly match reviews")
    dim_sum = {name: {d: 0 for d in DIMS} for name in ("base", "adapter")}
    votes = Counter()
    per_sample = []
    for sid in sorted(ids):
        key = mapping[sid]
        if {key["a"], key["b"]} != {"base", "adapter"}:
            raise ValueError(f"invalid key for {sid}")
        choices = Counter()
        for review in reviews:
            row = review[sid]
            choice = row["整体偏好(A/B/TIE)"].strip().upper()
            votes["tie" if choice == "TIE" else key[choice.lower()]] += 1
            choices[choice] += 1
            for d in DIMS:
                for arm in "ab":
                    dim_sum[key[arm]][d] += int(row[f"{d}·{arm.upper()}"])
        index = sid.split("-")[1]
        if index in ARBITRATION:
            choices[ARBITRATION[index]] += 1
        a_count, b_count = choices["A"], choices["B"]
        choice = "A" if a_count > b_count else "B" if b_count > a_count else "TIE"
        winner = ("tie" if choice == "TIE" else key[choice.lower()])
        per_sample.append({"sample_id": sid, "votes_a": a_count,
                           "votes_b": b_count, "votes_tie": choices["TIE"],
                           "winner": winner,
                           "arbitrated": index in ARBITRATION})
    return {
        "reviewers": 4, "samples": len(ids),
        "raw_votes": dict(votes),
        "sample_majority": dict(Counter(r["winner"] for r in per_sample)),
        "mean_scores": {
            name: {d: round(value / (4 * len(ids)), 4) for d, value in dims.items()}
            for name, dims in dim_sum.items()
        },
        "per_sample": per_sample,
        "caveat": ("Validation only; small correlated sample. Arbitration resolves "
                   "only original 2:2 cases; do not claim statistical significance."),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, action="append", required=True)
    parser.add_argument("--answer-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = unblind(args.review, args.answer_key)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("STORYFORGE_UNBLIND_PASS")
    print(json.dumps({k: result[k] for k in
          ("raw_votes", "sample_majority", "mean_scores")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

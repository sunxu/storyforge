"""Unblind the frozen StoryForge v0.1 held-out Test locally, after four reviews + arbitration.

No network access. Private answer key is read but never copied into the report.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.unblind_review_v01 import DIMS

ARBITRATION = {"001": "B", "002": "B", "012": "A", "018": "B"}
TEST_JOB_ID = "6ac85c22fee2c90070172dad"


def load_review(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 20:
        raise ValueError(f"{path}: expected 20 rows, got {len(rows)}")
    result = {}
    for row in rows:
        sid = row["样本编号"]
        if sid in result or not sid.startswith("eval-"):
            raise ValueError(f"{path}: invalid or duplicate sample ID {sid}")
        if row["整体偏好(A/B/TIE)"].strip().upper() not in {"A", "B", "TIE"}:
            raise ValueError(f"{path}: invalid preference {sid}")
        for dim in DIMS:
            for arm in ("A", "B"):
                if row[f"{dim}·{arm}"].strip() not in {"1", "2", "3", "4", "5"}:
                    raise ValueError(f"{path}: invalid {dim}·{arm} for {sid}")
        result[sid] = row
    return result


def summarize(reviews: list[Path], key_path: Path) -> dict:
    if len(reviews) != 4:
        raise ValueError("exactly four independent reviews required")
    sheets = [load_review(p) for p in reviews]
    ids = set(sheets[0])
    context_fields = ("故事背景与系统规则", "历史对话", "当前用户输入", "回复A", "回复B")
    for sheet in sheets[1:]:
        if set(sheet) != ids:
            raise ValueError("sample IDs differ between reviews")
        for sid in ids:
            if any(sheet[sid][key] != sheets[0][sid][key] for key in context_fields):
                raise ValueError(f"reviewer context or A/B differs: {sid}")
    raw_key = json.loads(key_path.read_text(encoding="utf-8"))
    mapping = {x["sample_id"]: x for x in raw_key}
    if len(mapping) != len(raw_key) or set(mapping) != ids:
        raise ValueError("private key must match exactly the 20 held-out sample IDs")
    raw_votes = Counter({"base": 0, "adapter": 0, "tie": 0})
    dims = {model: Counter() for model in ("base", "adapter")}
    item_results = []
    for sid in sorted(ids):
        model_key = mapping[sid]
        if {model_key.get("a"), model_key.get("b")} != {"base", "adapter"}:
            raise ValueError(f"invalid private mapping for {sid}")
        votes = Counter()
        for sheet in sheets:
            row = sheet[sid]
            preference = row["整体偏好(A/B/TIE)"].strip().upper()
            votes[preference] += 1
            raw_votes["tie" if preference == "TIE" else model_key[preference.lower()]] += 1
            for dim in DIMS:
                for arm in ("A", "B"):
                    dims[model_key[arm.lower()]][dim] += int(row[f"{dim}·{arm}"])
        suffix = sid.split("-")[1]
        if suffix in ARBITRATION:
            if votes["A"] != 2 or votes["B"] != 2:
                raise ValueError(f"expected exactly 2:2 votes before arbitration: {sid}")
            votes[ARBITRATION[suffix]] += 1
        winner_arm = "A" if votes["A"] > votes["B"] else "B" if votes["B"] > votes["A"] else "TIE"
        winner_model = "tie" if winner_arm == "TIE" else model_key[winner_arm.lower()]
        item_results.append({"sample_id": sid, "winner": winner_model,
                             "arbitrated": suffix in ARBITRATION,
                             "votes_a": votes["A"], "votes_b": votes["B"],
                             "votes_tie": votes["TIE"]})
    if sum(x["arbitrated"] for x in item_results) != 4:
        raise ValueError("arbitration did not cover four expected samples")
    return {
        "split": "test", "evaluation_job_id": TEST_JOB_ID,
        "reviewers": 4, "samples": 20, "arbitration_samples": sorted(ARBITRATION),
        "raw_votes": dict(raw_votes),
        "sample_majority": dict(Counter(x["winner"] for x in item_results)),
        "mean_scores": {model: {dim: round(dims[model][dim] / 80, 4) for dim in DIMS}
                        for model in ("base", "adapter")},
        "per_sample": item_results,
        "limitations": ("20 story-isolated held-out samples, low reviewer agreement; "
                        "descriptive only, not definitive statistical evidence."),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, action="append", required=True)
    parser.add_argument("--answer-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.review, args.answer_key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print("STORYFORGE_HELDOUT_UNBLIND_PASS")
    print(json.dumps({k: report[k] for k in ("raw_votes", "sample_majority", "mean_scores")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Reproduce archived v0.1 Validation 1536-token reviewer evidence checks.

Standard-library only. No inference, remote access, identity assumptions or GPU.
Run: python3 evaluations/v0.1/validation-1536/reproduce.py
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLUMNS = ("样本编号", "故事背景与系统规则", "历史对话", "当前用户输入", "回复A", "回复B")
SCORES = ("剧情连续性", "角色一致性", "指令遵循", "文学表现力", "互动推进")
REVIEWERS = ("b", "c", "g", "q")


def check() -> dict:
    manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    reviewers = {}
    for reviewer in REVIEWERS:
        path = ROOT / f"raw/{reviewer}.csv"
        expected = manifest["raw_review_csvs"][f"raw/{reviewer}.csv"]["sha256"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Source file SHA256 mismatch: {reviewer}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 15:
            raise ValueError(f"{reviewer}: expected 15 scorecard rows")
        if len({row["样本编号"] for row in rows}) != 15:
            raise ValueError(f"{reviewer}: duplicate sample IDs")
        for row in rows:
            sid = row["样本编号"]
            if re.fullmatch(r"eval-\d{3}-[0-9a-f]{12}", sid) is None:
                raise ValueError(f"{reviewer}: invalid sample ID {sid}")
            if row["整体偏好(A/B/TIE)"] not in {"A", "B", "TIE"}:
                raise ValueError(f"{reviewer} {sid}: invalid preference")
            if not row["评分理由"].strip():
                raise ValueError(f"{reviewer} {sid}: missing reason")
            for dim in SCORES:
                for side in ("A", "B"):
                    if row[f"{dim}·{side}"].strip() not in {"1", "2", "3", "4", "5"}:
                        raise ValueError(f"{reviewer} {sid}: missing or invalid score")
        reviewers[reviewer] = rows

    canonical = reviewers["b"]
    for reviewer, rows in reviewers.items():
        for i, (row, expected_row) in enumerate(zip(rows, canonical)):
            for name in COLUMNS:
                if row[name] != expected_row[name]:
                    raise ValueError(f"{reviewer} {i}: mismatched {name}")

    derived_path = ROOT / manifest["derived_response_file"]
    derived = [
        json.loads(line)
        for line in derived_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(derived) != 15:
        raise ValueError("derived full-response archive must have 15 rows")
    for row, expected_row in zip(derived, canonical):
        if (row != {
            "sample_id": expected_row["样本编号"],
            "response_a": expected_row["回复A"],
            "response_b": expected_row["回复B"],
            "source": "reconstructed_from_scored_validation_1536_csv_b",
        }):
            raise ValueError(f"derived 1536 response mismatch: {expected_row['样本编号']}")

    votes = collections.Counter(
        row["整体偏好(A/B/TIE)"]
        for rows in reviewers.values()
        for row in rows
    )
    actual_votes = {label: votes[label] for label in ("A", "B", "TIE")}
    if actual_votes != manifest["anonymous_preference_votes"]:
        raise ValueError("anonymous preference summary mismatch")
    return {
        "status": "VALIDATION_1536_REVIEW_ARCHIVE_PASS",
        "reviewer_files": len(REVIEWERS),
        "samples": len(canonical),
        "total_rating_rows": sum(len(rows) for rows in reviewers.values()),
        "anonymous_preference_votes": actual_votes,
        "model_answer_key": "NOT_VERIFIED",
        "raw_inference_jsonl": "NOT_ARCHIVED",
    }


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False, sort_keys=True))

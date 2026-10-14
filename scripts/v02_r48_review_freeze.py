#!/usr/bin/env python3
"""Freeze original R48 four-option reviewer results before any model unblinding.

Performs exact no-key source reconciliation against v0.1 canonical Gold and
the already-frozen R47 A/B/C outputs. Never reads private R48 answer mapping.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from v02_r47_eval_validate import validate_prompts
from v02_r48_four_arm_build import DIMS, SOURCE_COLS, read_gold

REPO_COMMIT = "c4688f709352642cedec4e273c6c4be75279e786"
FROZEN_BLOBS = (
    "d5e4c259ea0a69904c7dbfe21abac67e4e935514",
    "deecd293903ca89ba406addc9a4cbf9956fae8b0",
    "0185b3cf041f861384cf3cb0bbafb773ed896e87",
)
EXPECTED_TEST_SHA = "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"
LETTERS = "ABCD"
SCORE_FIELDS = tuple(f"{d}·{letter}" for d in DIMS for letter in LETTERS)
REVIEW_FIELDS = (
    "整体最佳(A/B/C/D/TIE)",
    "评分理由与逐字证据",
    "严重问题与对应回复",
    "玩家自主权严重侵犯(A/B/C/D/无)",
)
EXPECTED_COLUMNS = tuple(SOURCE_COLS) + REVIEW_FIELDS + SCORE_FIELDS


def hash256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def parse_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rdr = csv.DictReader(stream)
        header = tuple(rdr.fieldnames or ())
        rows = list(rdr)
    if header != EXPECTED_COLUMNS or len(rows) != 20:
        raise ValueError(f"{path}: invalid header or sample count")
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"{path}: malformed CSV")
    return rows


def quoted_evidence(reason: str, row: dict) -> bool:
    evidence = [
        next((q for q in match if q), "")
        for match in re.findall(
            r"“([^”]{2,90})”|「([^」]{2,90})」|‘([^’]{2,90})’|\"([^\"]{2,90})\"",
            reason,
        )
    ]
    return any(
        quote in row[col]
        for quote in evidence
        for col in SOURCE_COLS
        if col != "样本编号"
    )


def source_multiset(values: list[str]) -> Counter[str]:
    return Counter(values)


def freeze(root: Path, test: Path, prompts_path: Path, manifest_path: Path,
           r47_review_path: Path) -> dict:
    if hash256(test.read_bytes()) != EXPECTED_TEST_SHA:
        raise ValueError("canonical v0.1 Test source bytes are not frozen")
    prompts, entries = validate_prompts(prompts_path, manifest_path)
    gold = read_gold(test, prompts)
    with r47_review_path.open(encoding="utf-8-sig", newline="") as stream:
        reference = list(csv.DictReader(stream))
    if len(reference) != 20:
        raise ValueError("frozen R47 three-arm source must have 20 rows")
    original_headers = (
        "样本编号", "故事背景与系统规则",
        "历史对话", "当前用户输入",
    )
    frozen = []
    hashes = []
    for reviewer in range(1, 4):
        path = root / f"R48_Reviewer_{reviewer:02d}_completed.csv"
        raw = path.read_bytes()
        if git_blob_sha1(raw) != FROZEN_BLOBS[reviewer - 1]:
            raise ValueError(f"reviewer {reviewer}: changed since committed SHA")
        rows = parse_csv(path)
        for i, (row, src) in enumerate(zip(rows, reference, strict=True)):
            if row["样本编号"] != entries[i]["sample_id"]:
                raise ValueError(f"reviewer {reviewer} item {i}: id/order mismatch")
            for column in original_headers:
                if row[column] != src[column]:
                    raise ValueError(f"reviewer {reviewer} item {i}: source {column} altered")
            observed = [row["回复" + letter] for letter in LETTERS]
            originals = [src["回复" + letter] for letter in "ABC"] + [gold[i]]
            if source_multiset(observed) != source_multiset(originals):
                raise ValueError(f"reviewer {reviewer} item {i}: not R47 + canonical Gold")
            if frozen:
                for column in (*original_headers, *(f"回复{x}" for x in LETTERS)):
                    if row[column] != frozen[0][i][column]:
                        raise ValueError(f"reviewer {reviewer} item {i}: 4-way texts differ")
            pref = row[REVIEW_FIELDS[0]]
            if pref not in (*LETTERS, "TIE"):
                raise ValueError(f"reviewer {reviewer} item {i}: bad preference")
            if len(row[REVIEW_FIELDS[1]].strip()) < 8:
                raise ValueError(f"reviewer {reviewer} item {i}: missing written reasoning")
            if not row[REVIEW_FIELDS[2]].strip():
                raise ValueError(f"reviewer {reviewer} item {i}: missing severe-issue comment")
            severe = row[REVIEW_FIELDS[3]]
            if severe != "无":
                parts = severe.split(",")
                if not parts or len(set(parts)) != len(parts) or any(part not in LETTERS for part in parts):
                    raise ValueError(f"reviewer {reviewer} item {i}: bad agency marker")
            if not quoted_evidence(row[REVIEW_FIELDS[1]], row):
                raise ValueError(f"reviewer {reviewer} item {i}: no locatable quote")
            for field in SCORE_FIELDS:
                if row[field] not in ("1", "2", "3", "4", "5"):
                    raise ValueError(f"reviewer {reviewer} item {i}: invalid score {field}")
        hashes.append(hash256(raw))
        frozen.append(rows)
    anonymous_votes = Counter()
    majority = Counter()
    severity = Counter()
    dimension_totals = {letter: Counter() for letter in LETTERS}
    disagreements = []
    for i, entry in enumerate(entries):
        prefs = [review[i][REVIEW_FIELDS[0]] for review in frozen]
        counts = Counter(prefs)
        anonymous_votes.update(prefs)
        severity.update(review[i][REVIEW_FIELDS[3]] for review in frozen)
        winner = next((p for p, n in counts.items() if n >= 2), "NO_MAJORITY")
        majority[winner] += 1
        if len(counts) > 1:
            disagreements.append({"sample_id": entry["sample_id"],
                                  "anonymous_votes": dict(counts)})
        for review in frozen:
            for letter in LETTERS:
                for dim in DIMS:
                    dimension_totals[letter][dim] += int(review[i][f"{dim}·{letter}"])
    result = {
        "schema": "storyforge-r48-preunblind-source-freeze-v1",
        "status": "R48_THREE_SCORING_FILES_20_80_ORIGINAL_GOLD_SOURCE_FROZEN_PRE_UNBLIND",
        "score_commit": REPO_COMMIT,
        "gold_canonical_test_sha256": EXPECTED_TEST_SHA,
        "input_cases": 20,
        "responses_per_case": 4,
        "reviewers": 3,
        "integer_score_cells": 1440,
        "cross_reviewer_original_source_consistency": True,
        "canonical_gold_plus_frozen_r47_three_responses_each": True,
        "gold_assumed_correct": False,
        "score_csv_git_sha1": list(FROZEN_BLOBS),
        "score_csv_sha256": hashes,
        "anonymous_vote_totals": dict(anonymous_votes),
        "anonymous_majority_wins": dict(majority),
        "disagreements": disagreements,
        "anonymous_means_by_dimension": {
            letter: {dim: round(dimension_totals[letter][dim] / 60, 4) for dim in DIMS}
            for letter in LETTERS
        },
        "serious_agency_marker_strings": dict(severity),
        "private_answer_key_read": False,
        "independent_heldout": False,
        "model_promotion": False,
    }
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--review-dir", type=Path,
        default=Path("evaluations/v0.2/r48/reviews/round1"),
    )
    p.add_argument(
        "--compiled-test", type=Path,
        default=Path("data/compiled/v0.3/test.jsonl"),
    )
    p.add_argument(
        "--prompts", type=Path,
        default=Path("evaluations/v0.1/test/prompts.jsonl"),
    )
    p.add_argument(
        "--manifest", type=Path,
        default=Path("evaluations/v0.1/test/manifest.json"),
    )
    p.add_argument(
        "--r47-source", type=Path,
        default=Path("evaluations/v0.2/r47/reviews/round1/R47_Reviewer_01_completed.csv"),
    )
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    results = freeze(a.review_dir, a.compiled_test, a.prompts, a.manifest, a.r47_source)
    if a.output:
        if a.output.exists():
            raise FileExistsError("freeze output already exists")
        a.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(results["status"])
    print("R48_CSV_SHA256=" + ",".join(results["score_csv_sha256"]))
    print("R48_PRIVATE_MODEL_KEY_NOT_READ")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Freeze R47 scored CSVs and audit blinded reviews without reading the key.

The private original review sheets may be supplied for independent verification
that none of the story/system, prior history, player text or A/B/C model replies
was modified by a reviewer. This code never loads an answer-key file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

FROZEN_COMMIT = "04fbf45e73ec824c25d2692c8e6a6ebf4ca14a7d"
GIT_BLOBS = (
    "9f7adee4bb084513dd98a39c5cf91215aa7a32ed",
    "1af161b578966d835a3fede409e2146814252303",
    "6d70353e035f3d335276c1535c8801b848a942c1",
)
REVIEW_PATH = Path("evaluations/v0.2/r47/reviews/round1")
SOURCE_COLS = (
    "样本编号",
    "故事背景与系统规则",
    "历史对话",
    "当前用户输入",
    "回复A",
    "回复B",
    "回复C",
)
DIMENSIONS = (
    "剧情连续性",
    "角色一致性",
    "指令遵循",
    "文学表现力",
    "互动推进",
    "玩家自主权",
)
ANSWER_COLS = (
    "整体最佳(A/B/C/TIE)",
    "评分理由与逐字证据",
    "严重问题与对应回复",
    "玩家自主权严重侵犯(A/B/C/无)",
)
ALPHABET = ("A", "B", "C")


def fail(message: str) -> None:
    raise ValueError("R47_BLIND_FREEZE_REJECTED: " + message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        header = tuple(reader.fieldnames or [])
        rows = list(reader)
    if any(None in row for row in rows):
        fail(str(path) + ": extra cells or malformed CSV")
    return header, rows


def supporting_quote(reason: str, original: dict[str, str]) -> bool:
    # Quoted evidence must actually appear in source history or A/B/C replies.
    quotes = [
        a or b or c or d
        for a, b, c, d in re.findall(
            r"“([^”]{2,80})”|「([^」]{2,80})」|‘([^’]{2,80})’|\"([^\"]{2,80})\"",
            reason,
        )
    ]
    return any(quote in original[col] for quote in quotes for col in SOURCE_COLS)


def review_freeze(root: Path, manifest: Path, pristine: Path | None = None) -> dict:
    canonical = json.loads(manifest.read_text(encoding="utf-8"))
    items = canonical.get("samples") or []
    if canonical.get("schema") != "storyforge-blind-v1" or len(items) != 20:
        fail("original 20-case manifest missing")
    expected_ids = [sample["sample_id"] for sample in items]
    scored = []
    digests = []
    blob_hashes = []
    first = None
    quote_counts = []
    for index, blob in enumerate(GIT_BLOBS, 1):
        path = root / f"R47_Reviewer_{index:02d}_completed.csv"
        content = path.read_bytes()
        actual = git_blob(content)
        if actual != blob:
            fail(f"Reviewer_{index:02d}: bytes differ from Git commit {FROZEN_COMMIT}")
        header, rows = read_csv(path)
        score_cols = tuple(f"{d}·{letter}" for d in DIMENSIONS for letter in ALPHABET)
        expected_header = SOURCE_COLS + ANSWER_COLS + score_cols
        if header != expected_header:
            fail(f"Reviewer_{index:02d}: CSV columns reordered or missing")
        if len(rows) != 20 or [row["样本编号"] for row in rows] != expected_ids:
            fail(f"Reviewer_{index:02d}: row IDs/order changed")
        if pristine is not None:
            original_header, unscored = read_csv(pristine / f"R47_Reviewer_{index:02d}.csv")
            if original_header != header or len(unscored) != 20:
                fail(f"Reviewer_{index:02d}: original blank CSV missing/invalid")
            for row_idx, (row, original) in enumerate(zip(rows, unscored, strict=True)):
                for col in SOURCE_COLS:
                    if row[col] != original[col]:
                        fail(f"Reviewer_{index:02d}:{row_idx} altered original {col}")
                for col in (*ANSWER_COLS, *score_cols):
                    if original[col] != "":
                        fail(f"Reviewer_{index:02d}: original reviewer template not blank")
        if first is not None:
            for i, row in enumerate(rows):
                for col in SOURCE_COLS:
                    if row[col] != first[i][col]:
                        fail(f"Reviewer_{index:02d}:{i} mismatches other reviewer {col}")
        valid_quotes = 0
        for i, row in enumerate(rows):
            if any(not row[col] for col in SOURCE_COLS if col != "历史对话"):
                fail(f"Reviewer_{index:02d}:{i} missing source content")
            if row[ANSWER_COLS[0]] not in (*ALPHABET, "TIE"):
                fail(f"Reviewer_{index:02d}:{i} missing/invalid preference")
            if len(row[ANSWER_COLS[1]].strip()) < 8 or not row[ANSWER_COLS[2]].strip():
                fail(f"Reviewer_{index:02d}:{i} missing review evidence")
            if row[ANSWER_COLS[3]] not in (*ALPHABET, "无"):
                fail(f"Reviewer_{index:02d}:{i} invalid player-agency marker")
            if not supporting_quote(row[ANSWER_COLS[1]], row):
                fail(f"Reviewer_{index:02d}:{i} has no locatable original quotation")
            valid_quotes += 1
            for col in score_cols:
                if row[col] not in ("1", "2", "3", "4", "5"):
                    fail(f"Reviewer_{index:02d}:{i} incomplete/out-of-range {col}")
        quote_counts.append(valid_quotes)
        scored.append(rows)
        digests.append(sha256(content))
        blob_hashes.append(actual)
        if first is None:
            first = rows
    # Neither the old v0.1 evaluation nor any model-to-letter key is read.
    anonymous_votes = Counter()
    unanimous = 0
    two_agree = 0
    split_all = 0
    dim_sum = {letter: Counter() for letter in ALPHABET}
    severe = Counter()
    prefer_and_severe = []
    disagreements = []
    for i, entry in enumerate(items):
        prefs = [r[i][ANSWER_COLS[0]] for r in scored]
        choices = Counter(prefs)
        anonymous_votes.update(prefs)
        severe.update(row[i][ANSWER_COLS[3]] for row in scored)
        if max(choices.values()) == 3:
            unanimous += 1
        elif max(choices.values()) == 2:
            two_agree += 1
            disagreements.append(entry["sample_id"])
        else:
            split_all += 1
            disagreements.append(entry["sample_id"])
        for index, review in enumerate(scored, 1):
            row = review[i]
            if row[ANSWER_COLS[0]] == row[ANSWER_COLS[3]]:
                prefer_and_severe.append({"sample_id": entry["sample_id"], "reviewer": index})
            for letter in ALPHABET:
                for dimension in DIMENSIONS:
                    dim_sum[letter][dimension] += int(row[f"{dimension}·{letter}"])
    means = {
        letter: {
            dimension: round(dim_sum[letter][dimension] / 60, 4)
            for dimension in DIMENSIONS
        }
        for letter in ALPHABET
    }
    result = {
        "schema": "storyforge-r47-preunblind-freeze-v1",
        "status": (
            "R47_THREE_INDEPENDENT_SCORING_FILES_FROZEN_PRE_UNBLIND"
            if pristine is not None
            else "R47_THREE_SCORING_FILES_GIT_FROZEN_PRISTINE_SOURCE_PENDING"
        ),
        "git_commit": FROZEN_COMMIT,
        "source_file_paths": [
            str(root / f"R47_Reviewer_{i:02d}_completed.csv") for i in (1, 2, 3)
        ],
        "git_blob_sha1": blob_hashes,
        "exact_csv_sha256": digests,
        "independent_original_template_check": pristine is not None,
        "full_reviewers": 3,
        "samples_each": 20,
        "ratings_total": 1080,
        "locatable_quote_rows_each": quote_counts,
        "model_key_opened": False,
        "anonymous_preferences": dict(anonymous_votes),
        "unanimous_samples": unanimous,
        "two_to_one_samples": two_agree,
        "split_three_ways": split_all,
        "disagreement_samples": disagreements,
        "anonymous_dimension_means": means,
        "player_agency_severe_markers": dict(severe),
        "prefer_and_agency_severe_examples": prefer_and_severe,
        "fresh_heldout": False,
        "quality_promotion": False,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews-dir", type=Path, default=REVIEW_PATH)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("evaluations/v0.1/test/manifest.json"),
    )
    parser.add_argument("--pristine-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = review_freeze(args.reviews_dir, args.manifest, args.pristine_dir)
    if args.output:
        if args.output.exists():
            raise FileExistsError("refusing overwrite of audit report")
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(result["status"])
    print("R47_REVIEWERS=3 CASES_EACH=20 RATINGS=1080")
    print("R47_REVIEW_SHA256=" + ",".join(result["exact_csv_sha256"]))
    print("R47_PRIVATE_MODEL_KEY_NOT_READ")


if __name__ == "__main__":
    main()

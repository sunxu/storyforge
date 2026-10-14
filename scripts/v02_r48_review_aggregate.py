"""R48 offline four-arm review validation and private unblinding.

The model key is NEVER read unless all three filled reviewer sheets pass
completeness and original-source integrity checks first.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from v02_r48_four_arm_build import ARMS, COLUMNS, DIMS, EVAL_COLS, SCORE_COLS, SOURCE_COLS


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = tuple(reader.fieldnames or ())
        data = list(reader)
    if headers != COLUMNS or any(None in row for row in data):
        raise ValueError(f"R48 CSV format modified: {path}")
    return headers, data


def completed_reviews(reviews: list[Path], pristine: Path, manifest: Path) -> tuple[list[list[dict]], dict]:
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    expected = [item["sample_id"] for item in meta["samples"]]
    if meta.get("schema") != "storyforge-blind-v1" or len(expected) != 20:
        raise ValueError("expected the frozen original v0.1 20-case manifest")
    if len(reviews) != 3 or len(set(reviews)) != 3:
        raise ValueError("three distinct completed reviews required")
    checked = []
    hashes = []
    for index, path in enumerate(reviews, 1):
        _, rows = read_csv(path)
        _, blank = read_csv(pristine / f"R48_Reviewer_{index:02d}.csv")
        if len(rows) != len(blank) or len(rows) != 20:
            raise ValueError(f"reviewer {index}: missing cases")
        if [row["样本编号"] for row in rows] != expected:
            raise ValueError(f"reviewer {index}: reordered samples")
        for row_idx, (scored, original) in enumerate(zip(rows, blank, strict=True)):
            for col in SOURCE_COLS:
                if scored[col] != original[col]:
                    raise ValueError(f"reviewer {index}:{row_idx}: source {col} edited")
            for col in (*EVAL_COLS, *SCORE_COLS):
                if original[col] != "":
                    raise ValueError("original R48 reviewer template already contains scores")
            pref = scored[EVAL_COLS[0]]
            if pref not in ("A", "B", "C", "D", "TIE"):
                raise ValueError(f"reviewer {index}:{row_idx}: preference incomplete")
            if len(scored[EVAL_COLS[1]].strip()) < 8:
                raise ValueError(f"reviewer {index}:{row_idx}: explanation missing")
            if not scored[EVAL_COLS[2]].strip():
                raise ValueError(f"reviewer {index}:{row_idx}: serious error note missing")
            flags = scored[EVAL_COLS[3]]
            if flags != "无":
                items = flags.split(",")
                if not items or len(items) != len(set(items)) or any(x not in "ABCD" or len(x) != 1 for x in items):
                    raise ValueError(f"reviewer {index}:{row_idx}: invalid severe marker")
            for col in SCORE_COLS:
                if scored[col] not in ("1", "2", "3", "4", "5"):
                    raise ValueError(f"reviewer {index}:{row_idx}: score {col} invalid")
        checked.append(rows)
        hashes.append(sha(path))
    return checked, {
        "completed_reviewer_sha256": hashes,
        "reviewers": 3,
        "cases_per_reviewer": 20,
        "rating_cells": 1440,
        "pristine_csvs_verified": True,
        "original_key_opened": False,
    }


def combine(sheets: list[list[dict]], key: Path) -> dict:
    mapping = json.loads(key.read_text(encoding="utf-8"))
    if mapping.get("schema") != "storyforge-r48-gold-four-arm-v1":
        raise ValueError("R48 private key schema mismatch")
    items = mapping.get("items", [])
    if len(items) != 20 or [x["sample_id"] for x in items] != [
        row["样本编号"] for row in sheets[0]
    ]:
        raise ValueError("R48 private key sample identities mismatch")
    vote_count = Counter()
    majority_count = Counter()
    scores = defaultdict(list)
    severe = Counter()
    per_sample = []
    for index, key_entry in enumerate(items):
        perm = key_entry.get("mapping")
        if not isinstance(perm, dict) or set(perm) != set("ABCD") or set(perm.values()) != set(ARMS):
            raise ValueError(f"R48 sample {index} is not a four-model permutation")
        tally = Counter()
        detail = []
        for reviewer_num, sheet in enumerate(sheets, 1):
            row = sheet[index]
            choice = row[EVAL_COLS[0]]
            arm = perm[choice] if choice != "TIE" else "TIE"
            vote_count[arm] += 1
            tally[arm] += 1
            severe_labels = row[EVAL_COLS[3]]
            for letter in ([] if severe_labels == "无" else severe_labels.split(",")):
                severe[perm[letter]] += 1
            for letter, model in perm.items():
                for dim in DIMS:
                    scores[(model, dim)].append(int(row[f"{dim}·{letter}"]))
            detail.append({"reviewer": reviewer_num, "winner": arm,
                           "severe_models": [] if severe_labels == "无"
                           else [perm[s] for s in severe_labels.split(",")]})
        win = next((model for model, count in tally.items() if count >= 2), "NO_MAJORITY")
        majority_count[win] += 1
        per_sample.append({
            "sample_id": key_entry["sample_id"],
            "votes": dict(tally),
            "majority": win,
            "reviews": detail,
        })
    dim_means = {
        model: {dimension: round(sum(scores[(model, dimension)]) /
                                 len(scores[(model, dimension)]), 4)
                for dimension in DIMS}
        for model in ARMS
    }
    combined_means = {
        model: round(sum(sum(scores[(model, dim)]) for dim in DIMS) / 360, 4)
        for model in ARMS
    }
    return {
        "status": "R48_GOLD_FOUR_ARM_RETROSPECTIVE_UNBLIND_NOT_PROMOTED",
        "model_votes": dict(vote_count),
        "majority_wins": dict(majority_count),
        "overall_means": combined_means,
        "dimension_means": dim_means,
        "severe_player_agency_model_markers": dict(severe),
        "per_sample": per_sample,
        "fresh_heldout": False,
        "quality_promotion": False,
        "gold_not_absolute_truth": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pristine-dir", type=Path, required=True)
    p.add_argument("--reviews", type=Path, nargs=3, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--key", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if bool(a.key) != bool(a.output):
        p.error("--key and --output must be provided together")
    sheets, evidence = completed_reviews(a.reviews, a.pristine_dir, a.manifest)
    if not a.key:
        print("R48_THREE_REVIEWERS_20_CASES_1440_RATINGS_COMPLETE_KEY_NOT_READ")
        print("R48_REVIEWER_SHA256=" + ",".join(evidence["completed_reviewer_sha256"]))
        return
    if a.output.exists():
        raise FileExistsError("refusing to overwrite R48 aggregate")
    output = combine(sheets, a.key)
    output["reviewer_evidence"] = evidence
    output["reviewer_evidence"]["original_key_opened"] = True
    output["private_key_sha256"] = sha(a.key)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output["status"])
    print("R48_PRIVATE_AGGREGATE=" + str(a.output))


if __name__ == "__main__":
    main()

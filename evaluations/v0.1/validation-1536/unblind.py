"""Recompute v0.1 Validation 1536 Gold-free Base/Adapter quality from original key.

This verifies the archived authentic HF Job answer key + prompt manifest and the
four byte-preserved scored CSVs. Original large inference JSONLs remain in HF
Bucket, and were separately checked against these scorer texts on 2026-10-10.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIMS = ("剧情连续性", "角色一致性", "指令遵循", "文学表现力", "互动推进")


def run() -> dict:
    source = ROOT / "hf-source"
    record = json.loads((source / "source_verification.json").read_text(encoding="utf-8"))
    digest_lines = (source / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    checksums = {}
    for line in digest_lines:
        digest, filename = line.split("  ", 1)
        if len(digest) != 64 or filename in checksums:
            raise ValueError("invalid original HF checksum record")
        checksums[filename] = digest
    for filename in ("PRIVATE-answer-key.json", "validation-manifest.json", "summary.md"):
        actual = hashlib.sha256((source / filename).read_bytes()).hexdigest()
        if actual != checksums[filename]:
            raise ValueError(f"original HF file has changed: {filename}")

    keys = json.loads((source / "PRIVATE-answer-key.json").read_text(encoding="utf-8"))
    manifest = json.loads((source / "validation-manifest.json").read_text(encoding="utf-8"))
    if manifest["schema"] != "storyforge-blind-v1" or len(keys) != 15:
        raise ValueError("invalid official validation manifest/key")
    if manifest["count"] != 15 or len(manifest["samples"]) != 15:
        raise ValueError("invalid validation prompt count")
    for i, (entry, key) in enumerate(zip(manifest["samples"], keys)):
        if entry["source_line"] != i + 1 or key["sample_id"] != entry["sample_id"]:
            raise ValueError(f"identity/order mismatch in original HF manifest row {i}")
        if entry["sample_id"] != f"eval-{i:03d}-{entry['prompt_sha256'][:12]}":
            raise ValueError(f"prompt digest/sample ID mismatch at row {i}")
        if {key["a"], key["b"]} != {"base", "adapter"}:
            raise ValueError(f"invalid model identity at row {i}")

    results = {}
    source_manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    for reviewer in "bcgq":
        path = ROOT / "raw" / f"{reviewer}.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source_manifest["raw_review_csvs"][f"raw/{reviewer}.csv"]["sha256"]:
            raise ValueError(f"reviewer original CSV SHA256 mismatch: {reviewer}")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 15:
            raise ValueError(f"{reviewer}: wrong row count")
        results[reviewer] = rows

    base_rows = results["b"]
    scores = {model: {dim: [] for dim in DIMS} for model in ("base", "adapter")}
    votes = collections.Counter()
    per_sample = []
    for i, key in enumerate(keys):
        cast = collections.Counter()
        for reviewer, rows in results.items():
            row = rows[i]
            if row["样本编号"] != key["sample_id"]:
                raise ValueError(f"{reviewer}: wrong sample ID at {i}")
            if any(row[c] != base_rows[i][c] for c in
                   ("故事背景与系统规则", "历史对话", "当前用户输入", "回复A", "回复B")):
                raise ValueError(f"{reviewer}: response/context misalignment at {i}")
            choice = row["整体偏好(A/B/TIE)"]
            if choice not in ("A", "B", "TIE") or not row["评分理由"].strip():
                raise ValueError(f"{reviewer}: missing preference or rationale at {i}")
            winner = "tie" if choice == "TIE" else key[choice.lower()]
            votes[winner] += 1
            cast[winner] += 1
            for model in ("base", "adapter"):
                side = "A" if key["a"] == model else "B"
                for dim in DIMS:
                    val = row[f"{dim}·{side}"]
                    if val not in ("1", "2", "3", "4", "5"):
                        raise ValueError(f"{reviewer}: invalid score at {i}")
                    scores[model][dim].append(int(val))
        per_sample.append({
            "sample_id": key["sample_id"],
            "base": cast["base"], "adapter": cast["adapter"], "tie": cast["tie"],
        })

    strict = collections.Counter()
    plurality = collections.Counter()
    for case in per_sample:
        b, a = case["base"], case["adapter"]
        strict["base" if b >= 3 else "adapter" if a >= 3 else "no_majority"] += 1
        plurality["base" if b > a else "adapter" if a > b else "equal_top"] += 1
    out_means = {}
    for model in ("base", "adapter"):
        dims = {d: round(statistics.mean(scores[model][d]), 6) for d in DIMS}
        dims["overall"] = round(statistics.mean(
            v for d in DIMS for v in scores[model][d]
        ), 6)
        out_means[model] = dims
        expected = record["five_dimension_means"][model]
        if any(abs(dims[d] - expected[d]) > 0.00001 for d in dims):
            raise ValueError(f"archived model means changed: {model}")
    raw_votes = {"base": votes["base"], "adapter": votes["adapter"], "tie": votes["tie"]}
    if raw_votes != record["model_votes"]:
        raise ValueError("original mapped votes have changed")
    if dict(strict) != record["strict_sample_majority"]:
        raise ValueError("strict sample majority differs")
    if dict(plurality) != record["sample_plurality"]:
        raise ValueError("sample plurality differs")
    return {
        "status": "VALIDATION_1536_ORIGINAL_KEY_AND_SCORER_REPRO_PASS",
        "job_id": record["source_job_id"],
        "reviewers": 4, "samples": 15, "rated_rows": 60,
        "votes": raw_votes, "strict_majority": dict(strict),
        "plurality": dict(plurality), "means": out_means,
        "raw_hf_inference_bytes_in_git": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))

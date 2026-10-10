"""Verify archived StoryForge v0.1 six-reviewer Gold-reference scores.

Run: python3 evaluations/v0.1/gold-reference/2026-10-10/reproduce.py
Uses only the Python standard library, without GPU, API access or network.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATEGORIES = ("剧情连续性", "角色一致性", "指令遵循", "文学表现力", "互动推进")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check() -> dict:
    source = load_json(ROOT / "source_manifest.json")
    mapping_doc = load_json(ROOT / "organizer/identity_map.json")
    expected = load_json(ROOT / "results/quality_summary.json")
    mapping = {}
    for row in mapping_doc["items"]:
        key = (row["reviewer_id"], row["anonymous_case_id"])
        if key in mapping:
            raise ValueError(f"duplicate organizer map key: {key}")
        mapping[key] = row
    if len(mapping) != 120:
        raise ValueError("organizer map does not cover 120 comparisons")

    decoded = []
    for number in range(1, 7):
        rid = f"R{number:02d}"
        relpath = f"raw/StoryForge_{rid}.csv"
        path = ROOT / relpath
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source["archive_original_sha256"][relpath]:
            raise ValueError(f"original raw reviewer CSV SHA256 mismatch: {rid}")
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 20:
            raise ValueError(f"{rid}: expected exactly 20 rows")
        seen = set()
        seen_sources = set()
        for row in rows:
            cid = row["匿名题号"]
            if cid in seen:
                raise ValueError(f"duplicate case ID {cid}")
            seen.add(cid)
            key = (rid, cid)
            if key not in mapping:
                raise ValueError(f"unknown case ID {cid}")
            case = mapping[key]
            if case["source_index"] in seen_sources:
                raise ValueError(f"{rid}: one source prompt appears twice")
            seen_sources.add(case["source_index"])
            pref = row["整体偏好(A/B/TIE)"].strip().upper()
            if pref not in ("A", "B", "TIE"):
                raise ValueError(f"invalid preference {cid}")
            if len(row["评分理由（引用具体文本）"].strip()) < 12:
                raise ValueError(f"reason missing/too short for {cid}")
            if row["信心(高/中/低)"].strip() not in ("高", "中", "低"):
                raise ValueError(f"invalid confidence {cid}")
            scores = {}
            for dim in CATEGORIES:
                for side in ("A", "B"):
                    value = row[f"{dim}·{side}"].strip()
                    if value not in ("1", "2", "3", "4", "5"):
                        raise ValueError(f"invalid {dim} score in {cid}")
                    role = case[f"response_{side.lower()}_role"]
                    scores[(dim, role)] = int(value)
            winner = ("tie" if pref == "TIE"
                      else case[f"response_{pref.lower()}_role"])
            decoded.append({
                "source": case["source_sample_id"],
                "comparison": case["comparison"],
                "winner": winner,
                "scores": scores,
            })
        if len(seen_sources) != 20:
            raise ValueError(f"{rid}: missing source prompt")

    observed = {}
    for comp in ("GOLD_BASE", "GOLD_ADAPTER"):
        rows = [r for r in decoded if r["comparison"] == comp]
        if len(rows) != 60:
            raise ValueError(f"{comp}: expected exactly 60 ratings")
        per_source = collections.defaultdict(list)
        for row in rows:
            per_source[row["source"]].append(row)
        if len(per_source) != 20 or any(len(v) != 3 for v in per_source.values()):
            raise ValueError(f"{comp}: need exactly 3 scores per each of 20 prompts")
        raw = collections.Counter(r["winner"] for r in rows)
        majority = collections.Counter()
        for items in per_source.values():
            votes = collections.Counter(r["winner"] for r in items)
            winner, count = votes.most_common(1)[0]
            majority[winner if count >= 2 else "no_majority"] += 1
        gold_scores = [r["scores"][(d, "gold")] for r in rows for d in CATEGORIES]
        model_scores = [r["scores"][(d, "model")] for r in rows for d in CATEGORIES]
        observed[comp] = {
            "votes": {k: raw[k] for k in ("gold", "model", "tie")},
            "majority": {k: majority[k] for k in ("gold", "model")},
            "gold_mean": round(statistics.mean(gold_scores), 4),
            "model_mean": round(statistics.mean(model_scores), 4),
        }
        saved = expected["comparisons"][comp]
        if observed[comp]["votes"] != saved["votes"]:
            raise ValueError(f"{comp}: preferences disagree with recorded report")
        if observed[comp]["majority"] != saved["majority"]:
            raise ValueError(f"{comp}: per-source majorities disagree")
        if abs(observed[comp]["gold_mean"] - saved["overall"]["gold"]) > 0.00011:
            raise ValueError(f"{comp}: Gold means disagree")
        if abs(observed[comp]["model_mean"] - saved["overall"]["model"]) > 0.00011:
            raise ValueError(f"{comp}: model means disagree")
    if len(decoded) != 120:
        raise ValueError("unexpected aggregate record count")
    return observed


if __name__ == "__main__":
    print(json.dumps({"status": "SIX_REVIEW_REPRO_PASS", "results": check()}, ensure_ascii=False))

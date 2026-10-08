"""CPU-only analysis of existing blind evaluation generations; no model calls."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = ("narrative_continuity", "character_consistency",
          "instruction_adherence", "writing_quality", "interactive_progression")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def inspect_pairs(path: Path) -> dict:
    rows = read_jsonl(path)
    if not rows:
        raise ValueError("empty blind evaluation")
    ids = [row["sample_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate sample_id")
    arm_stats = {}
    for arm in ("a", "b"):
        responses = [row[f"response_{arm}"] for row in rows]
        if any(not isinstance(x, str) or not x.strip() for x in responses):
            raise ValueError(f"empty response in arm {arm}")
        lengths = [len(x) for x in responses]
        arm_stats[arm] = {
            "min_chars": min(lengths), "max_chars": max(lengths),
            "mean_chars": round(sum(lengths) / len(lengths), 1),
            "short_under_100_chars": sum(x < 100 for x in lengths),
            "possible_truncation": sum(
                not x.rstrip().endswith((".", "!", "?", "。", "！", "？", "”", "’", "」", "』"))
                for x in responses),
        }
    return {"pairs": len(rows), "arms": arm_stats,
            "note": "possible_truncation is a heuristic, not proof of token-limit truncation"}


CHINESE_SCORE_FIELDS = {
    "narrative_continuity": "剧情连续性",
    "character_consistency": "角色一致性",
    "instruction_adherence": "指令遵循",
    "writing_quality": "文学表现力",
    "interactive_progression": "互动推进",
}


def export_scorecard(source: Path, output: Path) -> int:
    """Export a blind, reviewer-friendly UTF-8 BOM CSV with both actual replies."""
    if output.exists():
        raise FileExistsError(f"will not overwrite {output}")
    rows = read_jsonl(source)
    if not rows:
        raise ValueError("empty blind evaluation")
    columns = ["样本编号", "回复A", "回复B", "整体偏好(A/B/TIE)", "评分理由", "严重问题"]
    columns += [f"{label}·{arm}" for label in CHINESE_SCORE_FIELDS.values()
                for arm in ("A", "B")]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "样本编号": row["sample_id"],
                "回复A": row["response_a"],
                "回复B": row["response_b"],
            })
    return len(rows)


def summarize_scores(scorecard: Path, private_key: Path) -> dict:
    with scorecard.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    mapping = json.loads(private_key.read_text(encoding="utf-8"))
    lookup = {entry["sample_id"]: entry for entry in mapping}
    if len(lookup) != len(mapping) or len(rows) != len(mapping):
        raise ValueError("scorecard and mapping mismatch")
    preferences = {"base": 0, "adapter": 0, "tie": 0}
    score_sums = {"base": 0, "adapter": 0}
    seen = set()
    for row in rows:
        sid = row.get("样本编号", row.get("sample_id"))
        if sid in seen or sid not in lookup:
            raise ValueError("duplicate or unknown sample_id")
        seen.add(sid)
        order = lookup[sid]
        if {order["a"], order["b"]} != {"base", "adapter"}:
            raise ValueError("invalid answer key")
        pref = row.get("整体偏好(A/B/TIE)", row.get("preference", "")).strip().upper()
        if pref not in {"A", "B", "TIE"}:
            raise ValueError(f"invalid or missing preference for {sid}")
        preferences["tie" if pref == "TIE" else order[pref.lower()]] += 1
        for field in FIELDS:
            for arm in ("a", "b"):
                chinese_key = f"{CHINESE_SCORE_FIELDS[field]}·{arm.upper()}"
                raw = row.get(chinese_key, row.get(f"{field}_{arm}", "")).strip()
                if not raw.isdecimal() or int(raw) not in range(1, 6):
                    raise ValueError(f"invalid {field}_{arm} for {sid}")
                score_sums[order[arm]] += int(raw)
    n = len(rows)
    return {"samples": n, "preferences": preferences,
            "mean_rubric_score": {name: round(value / (n * len(FIELDS)), 3)
                                  for name, value in score_sums.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--scorecard", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--private-key", type=Path)
    args = parser.parse_args()
    report = inspect_pairs(args.pairs)
    if args.scorecard and not args.private_key:
        report["scorecard_rows"] = export_scorecard(args.pairs, args.scorecard)
    elif args.scorecard and args.private_key:
        report["scoring"] = summarize_scores(args.scorecard, args.private_key)
    elif args.private_key:
        parser.error("--private-key requires --scorecard")
    if args.results:
        if args.results.exists():
            raise FileExistsError(args.results)
        args.results.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

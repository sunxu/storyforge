import csv
import json

import pytest

from scripts.analyze_blind_eval import export_scorecard, inspect_pairs, summarize_scores


def test_inspect_and_score_without_revealing_mapping(tmp_path):
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(json.dumps({
        "sample_id": str(i), "response_a": "An ending.", "response_b": "Another ending."
    }) + chr(10) for i in range(2)))
    report = inspect_pairs(pairs)
    assert report["pairs"] == 2
    sheet = tmp_path / "sheet.csv"
    assert export_scorecard(pairs, sheet) == 2
    with sheet.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row.update({"preference": "A", **{
            f"{field}_{arm}": "4" for field in (
                "narrative_continuity", "character_consistency", "instruction_adherence",
                "writing_quality", "interactive_progression") for arm in ("a", "b")
        }})
    with sheet.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    key = tmp_path / "key.json"
    key.write_text(json.dumps([
        {"sample_id": "0", "a": "base", "b": "adapter"},
        {"sample_id": "1", "a": "adapter", "b": "base"},
    ]))
    outcome = summarize_scores(sheet, key)
    assert outcome["preferences"] == {"base": 1, "adapter": 1, "tie": 0}
    assert outcome["mean_rubric_score"] == {"base": 4.0, "adapter": 4.0}
    with pytest.raises(FileExistsError):
        export_scorecard(pairs, sheet)


def test_missing_scores_rejected(tmp_path):
    key = tmp_path / "key.json"
    key.write_text(json.dumps([{"sample_id": "x", "a": "base", "b": "adapter"}]))
    sheet = tmp_path / "sheet.csv"
    sheet.write_text("sample_id,preference\nx,A\n")
    with pytest.raises(KeyError):
        summarize_scores(sheet, key)

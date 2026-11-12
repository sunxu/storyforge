"""Synthetic story-disjoint, quota and fail-closed calibration sampling tests."""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "experiments/r58_quality"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location(
    "r60_real1000_calibration_sample_cpu",
    SRC / "r60_real1000_calibration_sample_cpu.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_cases():
    result = []
    for index in range(1000):
        length = 350 if index < 545 else 750 if index < 925 else 1150
        result.append({
            "case_key": f"case-{index}",
            "source": {
                "story_id": f"story-{index // 4}",
                "assistant_message_id": f"target-{index}",
            },
            "history_messages": [
                {"role": "user", "content": "前文"},
                {"role": "assistant", "content": "人物说话"},
                {"role": "user", "content": "继续"},
            ],
            "target_text": "中" * length,
            "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
            "train_admitted": False,
        })
    return result


def test_100_distinct_stories_and_quotas():
    cases = make_cases()
    result = module.select(cases, "a" * 64)
    positions = [item["position"] for item in result["cases"]]
    assert len(positions) == len(set(positions)) == 100
    assert len({cases[pos - 1]["source"]["story_id"] for pos in positions}) == 100
    assert Counter(x["target_char_bin"] for x in result["cases"]) == module.QUOTAS
    assert result["quality_review_performed"] is False
    assert result["train_admitted"] == 0
    assert module.safe(result)["quality_pass"] == 0


def test_reproducible_without_private_body():
    cases = make_cases()
    a = module.select(cases, "a" * 64)
    b = module.select(cases, "a" * 64)
    assert a == b
    assert all(set(item) == {"position", "target_char_bin"} for item in a["cases"])


def test_change_pool_fingerprint_changes_selection():
    cases = make_cases()
    a = module.select(cases, "a" * 64)
    b = module.select(cases, "b" * 64)
    assert a["cases"] != b["cases"]


def test_insufficient_distinct_long_stories_holds():
    cases = make_cases()
    for index in range(925, 1000):
        cases[index]["source"]["story_id"] = "long-one-story"
    # The frozen pool verifier caps each story at four candidates.
    try:
        module.select(cases, "a" * 64)
    except (module.SampleHold, module.technical.Hold):
        return
    raise AssertionError("expected HOLD")

"""No-model synthetic tests for Owner-private pilot20 packet builder."""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "experiments/r58_quality"
sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location(
    "r60_real1000_pilot20_packets_cpu",
    SRC / "r60_real1000_pilot20_packets_cpu.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def cases():
    output = []
    for idx in range(1000):
        length = 350 if idx < 545 else 750 if idx < 925 else 1150
        output.append({
            "case_key": f"case-{idx}",
            "source": {
                "story_id": f"story-{idx // 4}",
                "assistant_message_id": f"assistant-{idx}",
            },
            "history_messages": [
                {"role": "user", "content": "用户甲"},
                {"role": "assistant", "content": "角色乙"},
                {"role": "user", "content": "用户丙"},
            ],
            "target_text": "中" * length,
            "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
            "train_admitted": False,
        })
    return output


def test_private_pilot20_binds_sample100_and_quotas():
    rows = cases()
    manifest = mod.sample.select(rows, "a" * 64)
    result = mod.build(rows, "a" * 64, manifest)
    assert len(result["packets"]) == 20
    assert Counter(x["target_char_bin"] for x in result["packets"]) == mod.SAMPLE_QUOTAS
    story_ids = {
        rows[x["sample100_position"] - 1]["source"]["story_id"]
        for x in result["packets"]
    }
    assert len(story_ids) == 20
    assert result["quality_review_performed"] is False
    assert result["train_admitted"] == 0
    assert mod.safe_report(result)["quality_pass"] == 0
    assert all("source" not in p for p in result["packets"])


def test_reproducible():
    rows = cases()
    m = mod.sample.select(rows, "a" * 64)
    assert mod.build(rows, "a" * 64, m) == mod.build(rows, "a" * 64, m)


def test_tampered_sample_rejected():
    rows = cases()
    manifest = mod.sample.select(rows, "a" * 64)
    manifest["cases"][0]["position"] += 1
    try:
        mod.build(rows, "a" * 64, manifest)
    except mod.Hold:
        return
    raise AssertionError("must reject modified source selection")


def test_wrong_pool_digest_rejected():
    rows = cases()
    manifest = mod.sample.select(rows, "a" * 64)
    try:
        mod.build(rows, "b" * 64, manifest)
    except mod.Hold:
        return
    raise AssertionError("must bind original frozen pool")

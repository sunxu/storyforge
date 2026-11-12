"""Synthetic evidence selection for partial new/old dual-PASS disagreements."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
import r60_real1000_qd20_disagreement_packet_cpu as evidence


def old_row(pos, pass_both=False):
    return {
        "pilot_position": pos,
        "claude_review_kind": "VALID_ADVISORY",
        "claude_decision_raw": "PASS" if pass_both else "HOLD",
        "codex_decision": "PASS" if pass_both else "HOLD",
        "claude_scores": {k: 5 for k in evidence.private.FLOORS},
        "codex_scores": {k: 5 for k in evidence.private.FLOORS},
        "claude_severe_flags": {k: False for k in evidence.private.SEVERE},
        "codex_severe_flags": {k: False for k in evidence.private.SEVERE},
    }


def test_only_three_disagreements_with_complete_pairs():
    old = [old_row(i, i in (1, 2, 3)) for i in range(1, 21)]
    receipts = {}
    for pos in range(1, 15):
        decision = "PASS" if pos in (1, 2, 4, 5) else "HOLD"
        for model in evidence.live.MODELS:
            receipts[(pos, model)] = {
                "result": {"decision": decision,
                           "scores": {k: 5 for k in evidence.private.FLOORS},
                           "severe_flags": {k: False for k in evidence.private.SEVERE},
                           "reason_cn": "用于合成验证"},
            }
    packets = [
        {"pilot_position": p, "history_messages": [
            {"role": "user", "content": "询问"},
            {"role": "assistant", "content": "回答"},
            {"role": "user", "content": "继续"},
        ], "assistant_target": "持续推进", "target_char_bin": "300_499"}
        for p in range(1, 21)
    ]
    safe, manifest = evidence.prepare(old, receipts, packets, "hash")
    assert safe["cases_for_evidence_review"] == 3
    assert safe["new_only_double_pass"] == 2
    assert safe["old_only_double_pass"] == 1
    assert safe["new_review_pairs_complete"] == 14
    assert manifest["train_admitted"] == 0
    assert all(x["owner_evidence_decision"] == "NOT_REVIEWED"
               for x in manifest["cases"])
    assert all(x["train_admitted"] is False for x in manifest["cases"])


def test_invalid_partial_compare_not_silently_used():
    try:
        evidence.prepare([], {}, [], "hash")
    except evidence.compare.Hold as exc:
        assert str(exc) == "OLD_COMPARE_ROWS_HOLD"
    else:
        raise AssertionError("missing baseline must fail closed")

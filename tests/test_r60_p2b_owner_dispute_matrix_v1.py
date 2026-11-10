"""Synthetic checks for private P2-B dispute worksheets (no real stories)."""
from unittest import TestCase

from scripts import r60_p2b_owner_dispute_matrix_v1 as mod


def fixture():
    packets = []
    disagreements = []
    for i in range(30):
        cid = f"synthetic_{i:02d}"
        reviews = {}
        for dim in mod.DIMS:
            diff = ((dim == "hard_rule" and i < 20)
                    or (dim == "player_agency" and i < 3)
                    or (dim == "safety" and i < 6))
            codex = "INSUFFICIENT_CONTEXT" if dim == "hard_rule" and diff else "NOT_SUPPORTED"
            claude = "NOT_SUPPORTED" if dim == "hard_rule" else (
                "SUPPORTED" if diff else "NOT_SUPPORTED"
            )
            c = {"verdict": codex, "evidence": [], "rule_basis": {},
                 "reasoning_summary": "synthetic codex", "missing_context": []}
            l = {"verdict": claude, "evidence": [], "rule_basis": {},
                 "reasoning_summary": "synthetic claude", "missing_context": []}
            reviews[dim] = {"codex": c, "claude": l}
            if diff:
                disagreements.append({
                    "calibration_id": cid, "dimension": dim,
                    "verdict_agreement": False,
                    "codex_verdict": codex, "claude_verdict": claude,
                })
        packets.append({"calibration_id": cid, "dimension_reviews": reviews})
    return disagreements, packets


def test_build_preserves_holds_and_owner_pending():
    disagreements, packets = fixture()
    matrix, checks, safe = mod.build(disagreements, packets)
    assert len(matrix) == 29
    assert len(checks) == 90
    assert [x["dimension"] for x in matrix[:20]] == ["hard_rule"] * 20
    assert all(x["owner_decision"] is None for x in matrix)
    assert all(x["owner_final_verdict"] is None for x in checks)
    assert all(x["owner_semantic_entailment_checked"] is None for x in checks)
    assert safe["hard_rule_disagreements"] == 20
    assert safe["other_disagreements"] == 9
    assert safe["owner_confirmations_completed"] == 0


def test_build_rejects_mismatched_frozen_counts():
    diffs, packets = fixture()
    with TestCase().assertRaisesRegex(mod.Hold, "EXPECTED_CASE_OR_DISAGREEMENT_COUNT_HOLD"):
        mod.build(diffs[:-1], packets)


def test_build_rejects_duplicate_disagreement():
    diffs, packets = fixture()
    diffs[-1] = diffs[0].copy()
    with TestCase().assertRaisesRegex(mod.Hold, "DISAGREEMENT_BINDING_HOLD"):
        mod.build(diffs, packets)


def test_build_rejects_hard_rule_flip():
    diffs, packets = fixture()
    hard = next(x for x in diffs if x["dimension"] == "hard_rule")
    hard["codex_verdict"] = "SUPPORTED"
    with TestCase().assertRaisesRegex(mod.Hold, "DISAGREEMENT_VERDICT_BINDING_HOLD"):
        mod.build(diffs, packets)


def test_build_rejects_inconsistent_review_context():
    diffs, packets = fixture()
    packets[0]["dimension_reviews"].pop("safety")
    with TestCase().assertRaisesRegex(mod.Hold, "OWNER_PACKET_DIMENSIONS_HOLD"):
        mod.build(diffs, packets)


def test_build_ignores_same_verdict_owner_attention_rows_for_disagreement_count():
    diffs, packets = fixture()
    diffs.append({
        "calibration_id": "synthetic_29",
        "dimension": "hard_rule",
        "verdict_agreement": True,
    })
    matrix, checks, safe = mod.build(diffs, packets)
    assert len(matrix) == 29
    assert len(checks) == 90
    assert safe["hard_rule_disagreements"] == 20

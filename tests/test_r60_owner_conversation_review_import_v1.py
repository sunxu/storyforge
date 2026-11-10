from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from scripts import r60_owner_conversation_review_import_v1 as MODULE


def _handoff() -> dict:
    dimensions = ("player_agency", "hard_rule", "safety")
    items = []
    for item in range(1, 61):
        case_number = ((item - 1) // 3) + 1
        dimension = dimensions[(item - 1) % 3]
        decision = "C" if item == 5 else "B" if item == 10 else "A"
        items.append({
            "item": item,
            "case_number": case_number,
            "blind_id": f"blind-case-{case_number:02d}",
            "dimension": dimension,
            "original_owner_verdict": "NOT_SUPPORTED",
            "owner_conversation_decision": decision,
            "owner_decision_interpretation": "Conversation confirmation only; not formal semantic review.",
            "owner_note": "Preserve the evidence concern." if item in (5, 10, 34, 58) else None,
            "claude_conclusion": "SUPPORTS_VERDICT",
            "claude_reasoning_summary": "Claude advisory reviewed the evidence against the source verdict.",
            "claude_unresolved_context": [],
            "formal_owner_receipt": False,
        })
    return {
        "schema": MODULE.SCHEMA,
        "status": "CONVERSATIONAL_OWNER_REVIEW_COMPLETE__FORMAL_RECEIPT_NOT_CREATED",
        "review_scope": {
            "cases": 20,
            "dimensions_per_case": 3,
            "total_items": 60,
            "dimensions": list(dimensions),
        },
        "owner_review": {
            "reviewer_type": "OWNER_EXPLICIT_CONVERSATION_CONFIRMATIONS",
            "formal_owner_identity_attested": False,
            "formal_owner_receipt_created": False,
            "decision_counts": {
                "A_SUPPORT_ORIGINAL": 58,
                "B_DO_NOT_SUPPORT_ORIGINAL": 1,
                "C_CONTEXT_INSUFFICIENT_REVIEW": 1,
            },
        },
        "claude_cross_review": {
            "model": "claude-opus-5-5",
            "reviewer_type": "AI_CROSS_REVIEW_ADVISORY_NOT_OWNER",
            "validated_rows": 60,
        },
        "safety_and_scope": {
            "original_files_modified": False,
            "owner_formal_jsonl_created": False,
            "owner_identity_fabricated": False,
            "gpu_started": False,
            "training_authorized": False,
        },
        "items": items,
    }


def test_validate_handoff_preserves_explicit_a_b_c_decisions():
    rows = MODULE.validate_handoff(_handoff())
    assert len(rows) == 60
    assert [r["owner_conversation_decision"] for r in rows].count("A") == 58
    assert [r["owner_conversation_decision"] for r in rows].count("B") == 1
    assert [r["owner_conversation_decision"] for r in rows].count("C") == 1


def test_build_artifacts_does_not_create_official_reviewer_identity():
    artifacts = MODULE.build_artifacts(_handoff(), "a" * 64)
    ledger = [json.loads(x) for x in artifacts[
        "OWNER_CONVERSATION_REVIEW_LEDGER_PRIVATE.jsonl"
    ].decode().splitlines()]
    assert len(ledger) == 60
    assert all(r["record_type"] == "CONVERSATION_AUDIT_NOT_OFFICIAL_SEMANTIC_CHECK"
               for r in ledger)
    assert all(r["formal_owner_receipt"] is False for r in ledger)
    assert all("reviewer_role" not in r and "reviewer_ref" not in r for r in ledger)
    safe = json.loads(artifacts["OWNER_CONVERSATION_REVIEW_IMPORT_SAFE.json"])
    assert safe["decision_counts"] == {"A": 58, "B": 1, "C": 1}
    assert safe["official_semantic_checks_created"] is False


def test_validate_rejects_decision_count_mismatch():
    data = _handoff()
    data["items"][0]["owner_conversation_decision"] = "B"
    with pytest.raises(MODULE.ImportHold, match="OWNER_DECISION_COUNTS_HOLD"):
        MODULE.validate_handoff(data)


def test_validate_rejects_missing_or_duplicate_dimension_pair():
    data = _handoff()
    data["items"][2]["dimension"] = data["items"][1]["dimension"]
    with pytest.raises(MODULE.ImportHold):
        MODULE.validate_handoff(data)


def test_validate_rejects_fabricated_formal_identity():
    data = _handoff()
    data["owner_review"]["formal_owner_identity_attested"] = True
    with pytest.raises(MODULE.ImportHold, match="FORMAL_IDENTITY_MUST_NOT_BE_ATTESTED"):
        MODULE.validate_handoff(data)


def test_import_is_create_only_and_writes_private_files(tmp_path: Path):
    source = tmp_path / "handoff.json"
    source.write_text(json.dumps(_handoff()), encoding="utf-8")
    source.chmod(0o600)
    private_parent = tmp_path / "private"
    private_parent.mkdir(mode=0o700)
    private_parent.chmod(0o700)
    output = private_parent / "ledger"

    result = MODULE.import_handoff(source, output)
    assert result["status"] == (
        "OWNER_CONVERSATION_LEDGER_CREATED__NOT_FORMAL_OWNER_RECEIPT"
    )
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert len(list(output.iterdir())) == 3
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in output.iterdir())
    with pytest.raises(MODULE.ImportHold, match="OUTPUT_MUST_BE_NEW"):
        MODULE.import_handoff(source, output)


def test_import_rejects_non_private_input_mode(tmp_path: Path):
    source = tmp_path / "handoff.json"
    source.write_text(json.dumps(_handoff()), encoding="utf-8")
    source.chmod(0o644)
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    parent.chmod(0o700)
    with pytest.raises(MODULE.ImportHold, match="INPUT_MODE_MUST_BE_0600"):
        MODULE.import_handoff(source, parent / "ledger")

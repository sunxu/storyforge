"""Synthetic-only Pilot5 evidence tests. Never touch private story data."""
import hashlib
import json

import r60_pilot5_v2_safe_audit as audit


def case(n):
    history = [
        {"role": "user", "content": "sample " + str(n)},
        {"role": "assistant", "content": "example"},
        {"role": "user", "content": "continue"},
    ]
    text = "synthetic output " + str(n)
    return {
        "case_key": "test-" + str(n),
        "history_messages": history,
        "history_messages_sha256": audit.digest(history),
        "target_text": text,
        "assistant_target_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def fixture(tmp_path):
    seed = tmp_path / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
    source = [case(i) for i in range(1, 7)]
    seed.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in source),
        encoding="utf-8",
    )
    quality = tmp_path / "quality"
    quality.mkdir()
    for index in range(1, 6):
        c = source[index - 1]
        receipt = {
            "position": index,
            "case_key": c["case_key"],
            "history_messages_sha256": c["history_messages_sha256"],
            "assistant_target_sha256": c["assistant_target_sha256"],
            "quality_decision": "HOLD",
            "reviews": [{
                "decision": "HOLD",
                "reviewer_key": "ai-model-a",
            }],
            "attempt_holds": ["MODEL_JSON_INVALID"],
        }
        receipt["receipt_sha256"] = audit.digest(receipt)
        (quality / audit.RECEIPT_TEMPLATE.format(index)).write_text(
            json.dumps(receipt), encoding="utf-8"
        )
    return seed, quality


def test_integrity_all_five_pass_without_private_values(tmp_path):
    seed, quality = fixture(tmp_path)
    result = audit.audit(seed, quality)
    assert result["status"] == "PILOT5_V2_EVIDENCE_INTEGRITY_PASS__NO_PROMOTION"
    assert result["cases_checked"] == 5
    assert result["attempt_hold_counts"] == {"MODEL_JSON_INVALID": 5}
    assert result["model_requests"] == 0
    assert result["train_admitted"] == 0
    assert "synthetic output" not in json.dumps(result)


def test_target_text_mutation_fails_closed(tmp_path):
    seed, quality = fixture(tmp_path)
    rows = seed.read_text().splitlines()
    first = json.loads(rows[0])
    first["target_text"] = "tampered"
    rows[0] = json.dumps(first)
    seed.write_text("\n".join(rows) + "\n")
    result = audit.audit(seed, quality)
    assert result["status"] == "PILOT5_V2_EVIDENCE_HOLD"
    assert result["all_source_binding_verified"] is False


def test_receipt_mutation_fails_closed(tmp_path):
    seed, quality = fixture(tmp_path)
    path = quality / audit.RECEIPT_TEMPLATE.format(2)
    row = json.loads(path.read_text())
    row["quality_decision"] = "PASS"
    path.write_text(json.dumps(row))
    result = audit.audit(seed, quality)
    assert result["status"] == "PILOT5_V2_EVIDENCE_HOLD"


def test_missing_receipt_fails_closed(tmp_path):
    seed, quality = fixture(tmp_path)
    (quality / audit.RECEIPT_TEMPLATE.format(4)).unlink()
    result = audit.audit(seed, quality)
    assert result["status"] == "PILOT5_V2_EVIDENCE_HOLD"


def test_unknown_attempt_reason_is_not_echoed(tmp_path):
    seed, quality = fixture(tmp_path)
    path = quality / audit.RECEIPT_TEMPLATE.format(1)
    row = json.loads(path.read_text())
    row["attempt_holds"] = ["PRIVATE_PROVIDER_BODY"]
    row["receipt_sha256"] = audit.digest(
        {k: v for k, v in row.items() if k != "receipt_sha256"}
    )
    path.write_text(json.dumps(row))
    result = audit.audit(seed, quality)
    assert result["status"] == "PILOT5_V2_EVIDENCE_HOLD"
    assert "PRIVATE_PROVIDER_BODY" not in json.dumps(result)

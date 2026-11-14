"""Synthetic-only SAFE receipt verification; no HF remote or model."""
import hashlib
import json

from scripts import r60_base_cpu336_hf_receipt_verify as verifier
from scripts import r60_base_cpu336_hf_worker as worker


def example(key):
    record = worker.base(key)
    record.update(
        status="BASE_CPU336_ACTUAL_COLLATOR_PASS__ALL_HELD",
        stage="AUDIT_COMPLETE", audited_cases=336,
        input_sha_verified=True, tokenizer_verified=True,
        actual_collator_verified=True,
        last_assistant_label_mask_verified=True,
        tokenizer_tokens={"min": 100, "median": 200, "p95": 300, "max": 400},
        collator_tokens={"min": 90, "median": 190, "p95": 290, "max": 390},
        supervised_tokens={"min": 10, "median": 20, "p95": 30, "max": 40},
    )
    return record


def test_verified_receipt_strict_schema(tmp_path):
    key = "r60-base-cpu336-20261115T000000Z-abcdef123456"
    path = tmp_path / worker.RECEIPT
    payload = (json.dumps(example(key), sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    path.chmod(0o600)
    safe = verifier.accept(path, key, hashlib.sha256(payload).hexdigest())
    assert safe["status"] == "BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD"
    assert safe["verified_cases"] == 336
    assert safe["train_admitted"] == 0
    safe = verifier.accept(path, key, "0" * 64)
    assert safe["status"] == "BASE_CPU336_RECEIPT_HOLD"


def test_false_promotion_and_invalid_mask_rejected(tmp_path):
    key = "r60-base-cpu336-20261115T000000Z-abcdef123456"
    path = tmp_path / worker.RECEIPT
    record = example(key)
    record["train_admitted"] = 1
    path.write_text(json.dumps(record))
    assert verifier.accept(path, key)["actual_collator_verified"] is False
    record = example(key)
    record["last_assistant_label_mask_verified"] = False
    path.write_text(json.dumps(record))
    assert verifier.accept(path, key)["actual_collator_verified"] is False


def test_bad_aggregate_or_wrong_key_rejected(tmp_path):
    key = "r60-base-cpu336-20261115T000000Z-abcdef123456"
    path = tmp_path / worker.RECEIPT
    record = example(key)
    record["collator_tokens"]["median"] = 500
    path.write_text(json.dumps(record))
    assert verifier.accept(path, key)["actual_collator_verified"] is False
    assert verifier.accept(path, "wrong")["actual_collator_verified"] is False

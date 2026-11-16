"""Synthetic-only transfer tests: no HF, GPU, private originals or network."""
import hashlib
import json

import pytest
import r60_base336_exploratory_collator_transfer as target


def setup(monkeypatch, tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(target.private, "BASE", root)
    source = root / "source"
    dest = root / "release"
    for path in (source, dest):
        path.mkdir(mode=0o700)
    rows = [
        (json.dumps({"messages": [{"role": "user", "content": f"synthetic-{i}"}]},
                    separators=(",", ":")) + "\n").encode()
        for i in range(336)
    ]
    original = b"".join(rows)
    manifest = {
        "schema": target.packet.SCHEMA,
        "status": "TECHNICAL_INPUT_ONLY__ALL_HELD",
        "examples": 336,
        "training_dataset_created": False,
        "train_admitted": 0,
        "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
        "data_sha256": hashlib.sha256(original).hexdigest(),
    }
    target.private.write_new(source / target.packet.DATA, original)
    target.private.write_new(
        source / target.packet.MANIFEST, (json.dumps(manifest) + "\n").encode())
    target.private.write_new(dest / "train.jsonl", b"".join(rows[:293]))
    target.private.write_new(dest / "validation.jsonl", b"".join(rows[293:]))
    receipt = tmp_path / "safe-receipt.json"
    receipt.write_text("{}")
    monkeypatch.setattr(target.release, "verify", lambda _: {
        "train_rows": 293, "validation_rows": 43,
    })
    monkeypatch.setattr(target.receipt_verifier, "accept", lambda *a: {
        "status": "BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD",
        "actual_collator_verified": True,
        "verified_cases": 336,
    })
    return source, dest, receipt, rows


def test_all_rows_exact_transfer_pass(monkeypatch, tmp_path):
    source, dest, receipt, _ = setup(monkeypatch, tmp_path)
    out = target.verify(dest, source, receipt)
    assert out["actual_final_collator_verified"] is True
    assert out["collator_executed_in_this_run"] is False
    assert out["train_admitted"] == 0


def test_even_one_changed_row_rejected(monkeypatch, tmp_path):
    source, dest, receipt, rows = setup(monkeypatch, tmp_path)
    edited = list(rows[:293])
    edited[0] = edited[0].replace(b"synthetic-0", b"synthetic-new")
    (dest / "train.jsonl").write_bytes(b"".join(edited))
    with pytest.raises(target.Hold, match="FINAL_ROWS_NOT_IDENTICAL"):
        target.verify(dest, source, receipt)


def test_missing_source_row_rejected(monkeypatch, tmp_path):
    source, dest, receipt, rows = setup(monkeypatch, tmp_path)
    (dest / "validation.jsonl").write_bytes(b"".join(rows[293:-1]))
    with pytest.raises(target.Hold, match="TECHNICAL_ROW_COUNT_HOLD"):
        target.verify(dest, source, receipt)


def test_original_receipt_failure_rejected(monkeypatch, tmp_path):
    source, dest, receipt, _ = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(target.receipt_verifier, "accept",
                        lambda *a: {"actual_collator_verified": False})
    with pytest.raises(target.Hold, match="ORIGINAL_CPU_RECEIPT_HOLD"):
        target.verify(dest, source, receipt)


def test_original_packet_mutated_rejected(monkeypatch, tmp_path):
    source, dest, receipt, _ = setup(monkeypatch, tmp_path)
    with (source / target.packet.DATA).open("ab") as stream:
        stream.write(b"x")
    with pytest.raises(target.Hold, match="TECHNICAL_PACKET_DIGEST_HOLD"):
        target.verify(dest, source, receipt)

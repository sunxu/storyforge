"""S0 SAFE audit synthetic regression: no network, no DB, no GPU."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
import r60_real1000_pilot20_local_review as review
import r60_real1000_s0_audit_cpu as s0


def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(s0.private, "private_dir",
                        lambda path, create: path.mkdir() if create else None)
    monkeypatch.setattr(s0.private, "read_private",
                        lambda path, limit: path.read_bytes())
    monkeypatch.setattr(s0.private, "write_new",
                        lambda path, value: path.write_bytes(value))
    sample_dir = tmp_path / "sample"
    packets_dir = tmp_path / "packets"
    output_dir = tmp_path / "review"
    sample_dir.mkdir()
    packets_dir.mkdir()
    pool_sha = "a" * 64
    categories = (["300_499"] * 55 + ["500_999"] * 38
                  + ["1000_1500"] * 7)
    entries = [{"position": i, "target_char_bin": cat}
               for i, cat in enumerate(categories, 1)]
    manifest = {
        "schema": s0.sample.SCHEMA,
        "status": "CALIBRATION_SAMPLE100_PRIVATE__NOT_REVIEWED",
        "pool_sha256": pool_sha,
        "method": "stable_sha256_rank_unique_story_per_bin_v1",
        "cases": entries, "quality_review_performed": False,
        "train_admitted": 0,
    }
    (sample_dir / s0.sample.FILENAME).write_bytes(review.canonical(manifest))
    chosen = []
    for entry in entries:
        i = entry["position"]
        rank = hashlib.sha256(b"r60-pilot20-v1\x00" + pool_sha.encode()
                              + b"\x00" + str(i).encode()).hexdigest()
        chosen.append((rank, i, entry["target_char_bin"]))
    selected = []
    for cat, count in s0.pilot.SAMPLE_QUOTAS.items():
        selected.extend(sorted(r for r in chosen if r[2] == cat)[:count])
    selected.sort(key=lambda r: r[1])
    lengths = {"300_499": 350, "500_999": 750, "1000_1500": 1100}
    packets = []
    for i, (_, source, category) in enumerate(selected, 1):
        packets.append({
            "pilot_position": i, "sample100_position": source,
            "target_char_bin": category,
            "history_messages": [
                {"role": "user", "content": "开门。"},
                {"role": "assistant", "content": "门已打开。"},
                {"role": "user", "content": "继续。"},
            ],
            "assistant_target": "文" * lengths[category],
            "human_reference_status": "NOT_ADJUDICATED",
            "model_quality_status": "NOT_REVIEWED",
        })
    packet_doc = {
        "schema": s0.pilot.SCHEMA,
        "status": "PILOT20_PACKETS_PRIVATE__NOT_REVIEWED",
        "sample100_binding": "RECOMPUTED_EXACT",
        "packets": packets,
        "quality_review_performed": False, "train_admitted": 0,
    }
    (packets_dir / s0.pilot.FILENAME).write_bytes(review.canonical(packet_doc))
    review.initialize(packets_dir, output_dir, "https://4router.ai/v1/chat/completions",
                      "claude-opus-5-5", 300)
    config = review.validate_config(output_dir)
    for i in range(1, 21):
        row = {
            "schema": review.SCHEMA, "position": i,
            "packets_sha256": config["packets_sha256"], "model_id": config["model_id"],
            "decision": "HOLD",
            "scores": {name: 3 for name in s0.private.FLOORS},
            "severe_flags": {name: False for name in s0.private.SEVERE},
            "reason_cn": "仅用于合成测试。",
        }
        row["receipt_sha256"] = review.sha(review.canonical(row))
        (output_dir / review.receipt_name(i)).write_bytes(review.canonical(row))
    return sample_dir, packets_dir, output_dir


def test_complete_s0_safe_aggregate(monkeypatch, tmp_path):
    sample_dir, _, out = setup(monkeypatch, tmp_path)
    safe, ledger = s0.audit(sample_dir, out)
    assert safe["status"] == "S0_PILOT20_SAMPLE100_AUDIT_PASS__ADJUDICATION_PENDING"
    assert safe["pilot20_receipts_valid"] == 20
    assert safe["sample100_pilot20_exact_binding"] is True
    assert len(ledger["rows"]) == 20
    assert all("reason_cn" not in row and "assistant_target" not in row
               for row in ledger["rows"])
    assert safe["train_admitted"] == 0


def test_sample100_tamper_detected(monkeypatch, tmp_path):
    sample_dir, _, out = setup(monkeypatch, tmp_path)
    path = sample_dir / s0.sample.FILENAME
    value = json.loads(path.read_bytes())
    value["cases"][0]["position"] = 999
    path.write_bytes(review.canonical(value))
    try:
        s0.audit(sample_dir, out)
    except s0.Hold as exc:
        assert str(exc) in ("SAMPLE100_ENTRY_HOLD", "PILOT20_SAMPLE100_BINDING_HOLD")
    else:
        raise AssertionError("must reject changed sample positions")


def test_receipt_tamper_detected(monkeypatch, tmp_path):
    sample_dir, _, out = setup(monkeypatch, tmp_path)
    path = out / review.receipt_name(2)
    value = json.loads(path.read_bytes())
    value["scores"]["chinese_prose"] = 4
    path.write_bytes(review.canonical(value))
    try:
        s0.audit(sample_dir, out)
    except (s0.Hold, review.Hold):
        return
    raise AssertionError("must reject modified receipt without valid checksum")


def test_incomplete_pilot_must_hold(monkeypatch, tmp_path):
    sample_dir, _, out = setup(monkeypatch, tmp_path)
    (out / review.receipt_name(20)).unlink()
    try:
        s0.audit(sample_dir, out)
    except s0.Hold as exc:
        assert str(exc) == "PILOT20_NOT_COMPLETE_HOLD"
    else:
        raise AssertionError("partial pilot cannot pass S0")

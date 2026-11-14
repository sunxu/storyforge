"""Synthetic-only regression for Base CPU336 packet, stage and HF worker."""
import hashlib
import json
from pathlib import Path

import pytest
import r60_base_cpu336_hf_packet as packet
from test_r60_base_start_cpu336_template_audit import sample

from scripts import r60_base_cpu336_hf_stage as stage
from scripts import r60_base_cpu336_hf_worker as worker


def test_packet_no_training_and_336_rows():
    cases, quarantine = sample()
    data, raw_manifest = packet.packet(cases, {
        **quarantine, "source_crosswalk_sha256": "source-hash",
    })
    rows = [json.loads(line) for line in data.splitlines()]
    assert len(rows) == 336
    assert all(len(row["messages"]) == 4 for row in rows)
    assert all(message["role"] != "system" for row in rows
               for message in row["messages"])
    manifest = json.loads(raw_manifest)
    assert manifest["data_sha256"] == hashlib.sha256(data).hexdigest()
    assert manifest["train_admitted"] == 0
    assert manifest["training_dataset_created"] is False


def test_stage_create_verify_immutable_and_worker_input(tmp_path):
    cases, quarantine = sample()
    data, raw_manifest = packet.packet(cases, {
        **quarantine, "source_crosswalk_sha256": "source-hash",
    })
    folder = tmp_path / "private"
    folder.mkdir(mode=0o700)
    for name, blob in ((packet.DATA, data), (packet.MANIFEST, raw_manifest)):
        file = folder / name
        file.write_bytes(blob)
        file.chmod(0o600)
    key = "r60-base-cpu336-20261115T000000Z-abcdef123456"
    dest = tmp_path / key
    result = stage.prepare(folder, dest, key)
    assert result["status"] == "BASE_CPU336_STAGE_VERIFIED__NO_JOB"
    assert stage.verify(dest, key)["cases"] == 336
    assert len(worker.inspect_technical_rows(data)) == 336
    with pytest.raises(ValueError, match="STAGE_PATH_HOLD"):
        stage.prepare(folder, dest, key)
    # Hash mismatch must never silently overwrite original technical packet.
    (dest / "private" / packet.DATA).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        stage.verify(dest, key)


def test_stage_dependency_closure_reuses_existing_auditor():
    paths = stage.dependencies()
    assert len(paths) == len(set(paths))
    assert "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py" in paths
    assert "scripts/r60_common2_wrapped_hf_stage.py" in paths
    assert "scripts/r60_base_cpu336_hf_worker.sh" in paths


def test_worker_counts_fail_closed_and_private_held():
    assert worker.summary([100] * 336)["max"] == 100
    with pytest.raises(ValueError, match="COUNTS_HOLD"):
        worker.summary([5])
    assert worker.base("synthetic")["train_admitted"] == 0
    assert worker.base("synthetic")["r50_complete_exclusion_verified"] is False
    with pytest.raises(ValueError, match="DATA_COUNT_HOLD"):
        worker.inspect_technical_rows(b'{"messages": []}\n')


def test_worker_rejects_malformed_roles():
    cases, quarantine = sample()
    data, _ = packet.packet(cases, {
        **quarantine, "source_crosswalk_sha256": "source-hash",
    })
    lines = data.splitlines()
    record = json.loads(lines[0])
    record["messages"][0]["role"] = "system"
    lines[0] = json.dumps(record).encode()
    with pytest.raises(ValueError, match="MESSAGES_HOLD"):
        worker.inspect_technical_rows(b"\n".join(lines))


def test_stage_sanitized_input_contract(tmp_path):
    file = tmp_path / "a"
    assert isinstance(file, Path)
    assert stage.RUN_RE.fullmatch("r60-base-cpu336-20261115T000000Z-abcdef123456")
    assert not stage.RUN_RE.fullmatch("r60-base-cpu336-invalid")

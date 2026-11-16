"""Final 293/43 HF CPU path synthetic-only regression, no remote calls."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import r60_base336_final_cpu_stage as stage
import r60_base336_final_cpu_worker as worker


def test_fixed_final_counts_and_pins():
    assert worker._summary([4] * 293, 293) == {
        "min": 4, "median": 4, "p95": 4, "max": 4,
    }
    assert stage.RUN_RE.fullmatch(
        "r60-base336-finalcpu-20261116T030000Z-012345abcdef"
    )
    assert not stage.RUN_RE.fullmatch(
        "r60-base-cpu336-20261114T165256Z-9e35795990aa"
    )
    assert worker.common.PIN == (
        "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
    )


def test_reject_bad_token_count():
    with pytest.raises(ValueError, match="TOKEN_COUNTS_HOLD"):
        worker._summary([4] * 292, 293)
    with pytest.raises(ValueError, match="TOKEN_COUNTS_HOLD"):
        worker._summary([-1] * 293, 293)


def test_stage_entry_has_worker_shell_and_source():
    assert "scripts/r60_base336_final_cpu_worker.sh" in stage.ENTRY
    assert "scripts/r60_base336_final_cpu_worker.py" in stage.ENTRY
    assert "scripts/r60_base336_final_cpu_stage.py" in stage.ENTRY
    assert stage.FILES == (
        "train.jsonl", "validation.jsonl",
        "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json",
    )


def test_manifest_load_293_43_synthetic(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    all_files = {}
    for part, count in (("train", 293), ("validation", 43)):
        row = {"messages": [
            {"role": "user", "content": "fiction"},
            {"role": "assistant", "content": "history"},
            {"role": "user", "content": "continue"},
            {"role": "assistant", "content": "target"},
        ]}
        raw = (json.dumps(row) + "\n").encode() * count
        path = root / f"{part}.jsonl"
        path.write_bytes(raw)
        path.chmod(0o600)
        all_files[part] = raw
    import hashlib
    doc = {
        "status": "EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED",
        "case_pool": 336, "train_admitted": 0,
        "statistics": {"rows": {"train": 293, "validation": 43}},
        "data_sha256": {k: hashlib.sha256(v).hexdigest()
                        for k, v in all_files.items()},
    }
    f = root / "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json"
    f.write_text(json.dumps(doc))
    f.chmod(0o600)
    rows, loaded = worker.load_release(tmp_path)
    assert len(rows["train"]) == 293
    assert len(rows["validation"]) == 43
    assert loaded["case_pool"] == 336


def test_manifest_sha_mismatch_fails(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    manifest = {
        "status": "EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED",
        "case_pool": 336, "train_admitted": 0,
        "statistics": {"rows": {"train": 293, "validation": 43}},
        "data_sha256": {"train": "0" * 64, "validation": "0" * 64},
    }
    f = root / "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json"
    f.write_text(json.dumps(manifest))
    f.chmod(0o600)
    data = root / "train.jsonl"
    data.write_text("{}\n")
    data.chmod(0o600)
    with pytest.raises(Exception):
        worker.load_release(tmp_path)

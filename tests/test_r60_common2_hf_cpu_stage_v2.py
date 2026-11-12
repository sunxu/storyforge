"""CPU2 v2 stage tests, synthetic private records only; no network."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import r60_common2_hf_cpu_stage as staging
from scripts import r60_common2_hf_cpu_stage_v2 as v2
from scripts import r60_common2_hf_cpu_image_retry as retry
from scripts import r60_common2_hf_cpu_image_probe as probe
from tests.test_r60_common2_hf_cpu_stage import fixture


NEW_KEY = "r60-common2-cpu2-20261112T090000Z-bbbbbbbbbbbb"


def prepare(tmp_path):
    inp = fixture(tmp_path)
    old = tmp_path / retry.RUN_KEY
    staging.stage(inp, old, retry.RUN_KEY)
    return old


def test_create_only_reuses_source_and_preserves_frozen(tmp_path):
    old = prepare(tmp_path)
    old_manifest = (old / "SHA256SUMS.txt").read_bytes()
    old_data = (old / "private_stage" / staging.DATA).read_bytes()
    new = tmp_path / NEW_KEY
    result = v2.build(old, new, NEW_KEY)
    assert result["status"] == "CPU2_V2_NEW_STAGE_READY__NO_SYNC_NO_JOB"
    assert result["hf_jobs_submitted"] == 0
    assert result["train_admitted"] == 0
    assert result["original_stage_untouched"] is True
    assert not (new / v2.OLD_WORKER).exists()
    assert (new / v2.NEW_WORKER).is_file()
    assert (old / "SHA256SUMS.txt").read_bytes() == old_manifest
    assert (old / "private_stage" / staging.DATA).read_bytes() == old_data
    assert (new / "private_stage" / staging.DATA).read_bytes() == old_data
    probe.check_local(new, NEW_KEY)
    with pytest.raises(ValueError, match="CREATE_ONLY_DESTINATION_HOLD"):
        v2.build(old, new, NEW_KEY)


def test_source_tampering_holds_without_creating_destination(tmp_path):
    old = prepare(tmp_path)
    target = old / "private_stage" / staging.DATA
    target.write_bytes(b"tampered")
    new = tmp_path / NEW_KEY
    with pytest.raises(ValueError, match="LOCAL_HASH_HOLD"):
        v2.build(old, new, NEW_KEY)
    assert not new.exists()


def test_no_reuse_of_original_key_or_symlink(tmp_path):
    old = prepare(tmp_path)
    with pytest.raises(ValueError, match="NEW_RUN_KEY_HOLD"):
        v2.build(old, tmp_path / "new", retry.RUN_KEY)
    alias = tmp_path / "alias"
    alias.symlink_to(old, target_is_directory=True)
    with pytest.raises(ValueError, match="FROZEN_STAGE_BINDING_HOLD"):
        v2.build(alias, tmp_path / NEW_KEY, NEW_KEY)


def test_v2_worker_is_cpu_only_ro_rw_create_only_and_no_training():
    source = v2.WORKER.read_text()
    assert 'ROOT="/input/common2"' in source
    assert 'OUT="/output"' in source
    assert 'sha256sum --check --status SHA256SUMS.txt' in source
    assert 'os.O_EXCL' in source
    assert 'export CUDA_VISIBLE_DEVICES=""' in source
    assert '--stage both' in source
    assert 'swift sft ' not in source
    assert 'HF_HUB_OFFLINE=1' in source
    assert 'PRIVATE_PARENT="$HOME/.local/share/storyforge/r60/private"' in source
    assert 'PRIVATE_INPUT="$PRIVATE_PARENT/$KEY"' in source
    assert '--input-dir "$PRIVATE_INPUT"' in source
    assert 'mkdir -m 700 "$PRIVATE_INPUT"' in source
    assert 'chmod 600 "$PRIVATE_INPUT/"*' in source
    assert 'SCRATCH/private' not in source
    assert "/workspace" not in source

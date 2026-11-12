"""Offline stdlib-only HF CPU handoff tests; no Hub, Swift, models, R50."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts import r60_common2_hf_cpu_stage as stage
from scripts import r60_common2_hf_cpu_bucket_guard as guard


def fixture(tmp_path: Path):
    inp = tmp_path / "input"
    inp.mkdir(mode=0o700)
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"synthetic-{i}"}
        for i in range(11)
    ] + [{"role": "assistant", "content": "synthetic-target"}]
    rows = [{
        "schema": "storyforge_r60_source_bound_experimental_sft_v1",
        "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
        "supervision_scope": "FINAL_ASSISTANT_ONLY",
        "system_prompt": None, "world_card": None,
        "train_admitted": False, "messages": messages,
    } for _ in range(2)]
    payload = b"".join((json.dumps(r, ensure_ascii=False) + "\n").encode() for r in rows)
    manifest = {
        "schema": "storyforge_r60_common2_sft_experimental_manifest_private_v1",
        "status": "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED",
        "window": 11, "examples": 2, "train_admitted": 0,
        "r50_complete_exclusion_verified": False,
        "data_sha256": hashlib.sha256(payload).hexdigest(),
    }
    for name, data in [(stage.DATA, payload),
                       (stage.MANIFEST, json.dumps(manifest).encode())]:
        p = inp / name
        p.write_bytes(data)
        os.chmod(p, 0o600)
    return inp


def test_stage_reuses_unchanged_real_source_code(tmp_path):
    inp = fixture(tmp_path)
    run_key = "r60-common2-cpu2-20261112T030000Z-012345abcdef"
    out = tmp_path / run_key
    receipt = stage.stage(inp, out, run_key)
    assert receipt["hf_jobs_submitted"] == 0
    assert receipt["private_values_emitted"] is False
    assert len((out / "SHA256SUMS.txt").read_text().splitlines()) > 3
    assert (out / "code/scripts/hf_label_mask_audit.py").is_file()
    assert (out / "code/experiments/r58_quality/r60_common2_sft_cpu_template_audit.py").is_file()
    assert (out / "private_stage" / stage.DATA).read_bytes() == (inp / stage.DATA).read_bytes()
    assert guard.expected(out)
    with pytest.raises(ValueError, match="OUTPUT_EXISTS_HOLD"):
        stage.stage(inp, out, run_key)


def test_modified_manifest_is_rejected(tmp_path):
    inp = fixture(tmp_path)
    p = inp / stage.MANIFEST
    manifest = json.loads(p.read_text())
    manifest["data_sha256"] = "0" * 64
    p.write_text(json.dumps(manifest))
    os.chmod(p, 0o600)
    with pytest.raises(ValueError, match="EXPERIMENT_BINDING_HOLD"):
        stage.validate_inputs(inp)


def test_unsafe_permissions_and_run_key_hold(tmp_path):
    inp = fixture(tmp_path)
    os.chmod(inp / stage.DATA, 0o644)
    with pytest.raises(ValueError, match="PRIVATE_FILES_PERMISSIONS_HOLD"):
        stage.validate_inputs(inp)
    os.chmod(inp / stage.DATA, 0o600)
    with pytest.raises(ValueError, match="RUN_KEY_HOLD"):
        stage.stage(inp, tmp_path / "output", "r60-bad")


class FakeApi:
    def __init__(self, objects):
        self.objects = objects

    def list_bucket_tree(self, bucket, prefix, recursive):
        assert bucket == guard.BUCKET and recursive
        return [type("Entry", (), {"path": prefix + name, "type": "file"})()
                for name in self.objects]


def test_bucket_guard_fails_closed_on_missing_file(tmp_path):
    inp = fixture(tmp_path)
    key = "r60-common2-cpu2-20261112T030000Z-012345abcdef"
    out = tmp_path / key
    stage.stage(inp, out, key)
    names = guard.expected(out)
    guard.check("empty", key, out, FakeApi([]))
    guard.check("ready", key, out, FakeApi(sorted(names)))
    with pytest.raises(ValueError, match="REMOTE_RUN_FILESET_HOLD"):
        guard.check("ready", key, out, FakeApi(["SHA256SUMS.txt"]))
    with pytest.raises(ValueError, match="REMOTE_RUN_ALREADY_EXISTS"):
        guard.check("empty", key, out, FakeApi(sorted(names)))

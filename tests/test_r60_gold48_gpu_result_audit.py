"""Gold48 independent Owner download audit: synthetic bytes, fake HF only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import r60_gold48_gpu_result_audit as audit
from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    MODEL,
    REVISION,
)

RUN = "gold48-owner-synthetic-20261121"


def _payload():
    outputs = []
    for i in range(48):
        outputs.append({
            "sample_id": f"G48-C{i + 1:02d}",
            "effective_seed": 42 + i,
            "text": "synthetic text",
            "input_tokens": 10,
            "output_tokens": 3,
            "finish_reason": "eos",
        })
    return {
        "schema": "storyforge_r60_generation_outputs_private_v1",
        "model_role": "base",
        "model": MODEL,
        "revision": REVISION,
        "seed": 42,
        "record_count": 48,
        "outputs": outputs,
    }


def _files(input_sha):
    obj = _payload()
    raw_output = (json.dumps(obj, sort_keys=True) + "\n").encode()
    sha = hashlib.sha256(raw_output).hexdigest()
    provider_sha = "a" * 64
    receipt_sha = "b" * 64
    launch = {
        "schema": "storyforge_r60_gold48_generation_launch_private_v1",
        "run_id": RUN, "model_role": "base",
        "input_sha256": input_sha,
        "runtime_image_measured": True,
        "provider_image_attestation_sha256": provider_sha,
        "owner_authorization_receipt_sha256": receipt_sha,
    }
    identity = {
        "schema": "storyforge_r60_gold48_generation_identity_private_v1",
        "run_id": RUN, "selected_model_role": "base",
        "output_sha256": sha, "input_sha256": input_sha,
        "record_count": 48, "runtime_image_measured": True,
        "provider_image_attestation_sha256": provider_sha,
        "owner_authorization_receipt_sha256": receipt_sha,
    }
    name = "base.private.json"
    files = {
        name: raw_output,
        name + ".launch.private.json": (json.dumps(launch) + "\n").encode(),
        name + ".identity.private.json": (json.dumps(identity) + "\n").encode(),
    }
    rows = [
        {"name": key, "size_bytes": len(value),
         "sha256": hashlib.sha256(value).hexdigest()}
        for key, value in files.items()
    ]
    manifest = {
        "schema": audit.MANIFEST_SCHEMA, "run_id": RUN,
        "model_role": "base", "record_count": 48,
        "files": rows,
        "owner_mac_independent_download_and_sha_audit_required": True,
    }
    files[name + ".result-sha256-manifest.private.json"] = (
        json.dumps(manifest) + "\n"
    ).encode()
    return files


def _setup(tmp_path, monkeypatch, corrupt=None, missing=False):
    root = tmp_path / "owner-downloads"
    root.mkdir(mode=0o700)
    input_manifest = tmp_path / "input-manifest.json"
    input_sha = "c" * 64
    input_manifest.write_text(json.dumps({
        "schema": "synthetic-input", "record_count": 48,
        "sha256": input_sha,
    }))
    input_manifest.chmod(0o600)
    remote = _files(input_sha)
    if corrupt is not None:
        remote[corrupt] = b"tampered"
    fileset = set(remote)
    if missing:
        fileset.remove("base.private.json.identity.private.json")
    monkeypatch.setattr(audit.shared, "remote_set", lambda _api, _prefix: fileset)

    def copy_anon(argv, **_kwargs):
        assert argv[:3] == ["hf", "buckets", "cp"]
        name = argv[3].rsplit("/", 1)[-1]
        Path(argv[4]).write_bytes(remote[name])
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(audit.subprocess, "run", copy_anon)
    return root, input_manifest


def test_owner_mac_downloads_and_verifies_48_outputs(tmp_path, monkeypatch):
    root, manifest = _setup(tmp_path, monkeypatch)
    result = audit.audit(RUN, "base", root, manifest, api=object())
    assert result["status"] == "OWNER_GOLD48_RESULT_BYTES_AUDITED__SIGNATURE_REVIEW_PENDING"
    assert result["record_count"] == 48 and result["file_count"] == 4
    assert result["quality_v1_admitted"] == 0
    assert result["owner_signature_independently_reverified"] is False
    assert (root / RUN / "base.private.json").is_file()
    assert all(
        (p.stat().st_mode & 0o777) == 0o600
        for p in (root / RUN).iterdir()
    )
    with pytest.raises(audit.AuditHold, match="OWNER_RESULT_ALREADY_DOWNLOADED_HOLD"):
        audit.audit(RUN, "base", root, manifest, api=object())


def test_owner_mac_bad_remote_sha_never_claims_pass(tmp_path, monkeypatch):
    root, manifest = _setup(
        tmp_path, monkeypatch, corrupt="base.private.json"
    )
    with pytest.raises(ValueError):
        audit.audit(RUN, "base", root, manifest, api=object())


def test_owner_mac_incomplete_remote_set_creates_no_output(tmp_path, monkeypatch):
    root, manifest = _setup(tmp_path, monkeypatch, missing=True)
    with pytest.raises(audit.AuditHold, match="OWNER_REMOTE_RESULT_FILESET_HOLD"):
        audit.audit(RUN, "base", root, manifest, api=object())
    assert list(root.iterdir()) == []


def test_owner_mac_entrypoint_fails_closed_and_safe(tmp_path, capsys):
    rc = audit.main([
        "--run-id", "../escape", "--model-role", "base",
        "--owner-download-root", str(tmp_path),
        "--frozen-input-manifest", str(tmp_path / "absent"),
    ])
    assert rc == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "HOLD"
    assert report["gpu_started"] is False
    assert report["private_values_emitted"] is False

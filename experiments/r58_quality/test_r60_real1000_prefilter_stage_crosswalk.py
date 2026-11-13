"""Synthetic tests for prefilter and pre-existing HF stage identity gate."""
from __future__ import annotations

import json

import r60_real1000_offline_prefilter as prefilter
import r60_real1000_prefilter_stage_crosswalk as gate
import r60_real_private_batch as private
from test_r60_real1000_offline_prefilter import candidates


def stage_verified(_stage, pool_hash, cases):
    assert pool_hash == "synthetic-pool"
    assert len(cases) == 1000
    return {"count": 1000}, {"bindings": {"A": [], "B": []}}


def test_verified_existing_stage_for_all_1000(tmp_path, monkeypatch):
    cases = candidates()
    monkeypatch.setattr(gate.quality, "frozen_pool",
                        lambda _d: (cases, "synthetic-pool"))
    monkeypatch.setattr(gate.hf_blind_stage, "verified_stage", stage_verified)
    monkeypatch.setattr(gate.private, "BASE", tmp_path)
    directory = tmp_path / "r60-real1000-prefilter-synthetic"
    result = prefilter.run(tmp_path, directory)
    assert result["structure_pass"] == 1000
    safe = gate.audit(tmp_path, directory, tmp_path / "old-stage")
    assert safe["status"] == (
        "PREFILTER_STAGE_ALL_ELIGIBLE__CONTENT_REVIEW_PENDING"
    )
    assert safe["stage_identity_verified"] == 1000
    assert safe["model_requests"] == safe["train_admitted"] == 0


def test_modification_of_page_fail_closed(tmp_path, monkeypatch):
    cases = candidates()
    monkeypatch.setattr(gate.quality, "frozen_pool",
                        lambda _d: (cases, "synthetic-pool"))
    monkeypatch.setattr(gate.hf_blind_stage, "verified_stage", stage_verified)
    monkeypatch.setattr(gate.private, "BASE", tmp_path)
    directory = tmp_path / "r60-real1000-prefilter-synthetic"
    prefilter.run(tmp_path, directory)
    page = directory / "R60_REAL1000_PREFILTER_PAGE_0001_PRIVATE.json"
    obj = json.loads(page.read_text())
    obj["rows"][0]["state"] = "EXCLUDE"
    page.write_text(json.dumps(obj))
    page.chmod(0o600)
    assert gate.audit(tmp_path, directory, tmp_path)["status"] == (
        "PREFILTER_STAGE_CROSSWALK_HOLD"
    )


def test_subset_requires_new_stage_not_implicit_filter(tmp_path, monkeypatch):
    cases = candidates()
    cases[3]["target_text"] = cases[2]["target_text"]
    cases[3]["assistant_target_sha256"] = private.digest(
        cases[3]["target_text"]
    )
    monkeypatch.setattr(gate.quality, "frozen_pool",
                        lambda _d: (cases, "synthetic-pool"))
    monkeypatch.setattr(gate.hf_blind_stage, "verified_stage", stage_verified)
    monkeypatch.setattr(gate.private, "BASE", tmp_path)
    directory = tmp_path / "r60-real1000-prefilter-synthetic"
    prefilter.run(tmp_path, directory)
    result = gate.audit(tmp_path, directory, tmp_path)
    assert result["status"] == (
        "PREFILTER_STAGE_SUBSET_REQUIRED__NO_MODEL_REQUEST"
    )
    assert result["prefilter_excluded"] == 1

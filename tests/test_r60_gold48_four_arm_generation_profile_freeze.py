"""Gold48 Owner-approved frozen four-arm profile: byte-bound and inference HOLD."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "experiments/r60_quality"
CAND = DIR / "gold48_four_arm_generation_profile_candidate_v1.json"
FROZEN = DIR / "gold48_four_arm_generation_profile_frozen_v1.json"
SHA = "394013dc182fa095040808e02c4ea2e393636d30"


def test_exact_candidate_blob_and_narrow_owner_profile_freeze_delta():
    candidate_raw = CAND.read_bytes()
    actual_blob = hashlib.sha1(
        b"blob " + str(len(candidate_raw)).encode() + b"\\0" + candidate_raw
    ).hexdigest()
    assert actual_blob == SHA
    original = json.loads(candidate_raw)
    frozen = json.loads(FROZEN.read_bytes())

    approval = frozen.pop("owner_generation_profile_approval")
    assert approval["status"] == "OWNER_APPROVED"
    assert approval["scope"] == "GENERATION_PROFILE_FREEZE_ONLY"
    assert approval["candidate_git_blob_sha"] == actual_blob
    assert approval["candidate_source_commit"] == (
        "4fd87b2574f80e6d376b82dd66c605e4c01e8186"
    )
    assert approval["inference_authorized"] is False
    assert approval["gpu_authorized"] is False
    assert approval["training_authorized"] is False

    assert frozen.pop("schema") == (
        "storyforge_r60_gold48_four_arm_generation_profile_frozen_v1"
    )
    assert frozen.pop("status") == (
        "GOLD48_FOUR_ARM_PROFILE_FROZEN__RUNTIME_VALIDATION_PENDING"
    )
    assert frozen.pop("owner_generation_profile_freeze") is True
    assert original.pop("schema") == (
        "storyforge_r60_gold48_four_arm_generation_profile_candidate_v1"
    )
    assert original.pop("status") == (
        "OWNER_REVIEW_PENDING__MODEL_RUNTIME_COMPATIBILITY_HOLD"
    )
    assert original.pop("owner_generation_profile_freeze") is False
    old = original["pre_generation_blockers"]
    new = frozen["pre_generation_blockers"]
    assert new == [v for v in old if v != "OWNER_GENERATION_PROFILE_FREEZE_PENDING"]
    assert len(old) == len(new) + 1
    del original["pre_generation_blockers"]
    del frozen["pre_generation_blockers"]
    assert original == frozen


def test_frozen_gold48_cannot_authorize_model_or_training():
    profile = json.loads(FROZEN.read_bytes())
    assert profile["owner_generation_profile_freeze"] is True
    assert profile["inference_authorized"] is False
    assert profile["gpu_authorized_by_this_document"] is False
    assert profile["training_authorized"] is False
    assert profile["model_generation_started"] is False
    assert profile["model_promoted"] is False
    assert profile["dataset"]["historical_actual_sent_verified"] is False
    assert profile["dataset"]["full_protected_universe_independence_verified"] is False
    assert profile["base_model"]["generation_model_architecture_runtime_verified"] is False
    assert profile["generation"]["prefill_and_decode_runtime_parity_verified"] is False
    assert "FOUR_ARM_BACKEND_THIN_ADAPTER_AND_NO_TRUNCATION_INFERENCE_SMOKE_PENDING" in (
        profile["pre_generation_blockers"]
    )

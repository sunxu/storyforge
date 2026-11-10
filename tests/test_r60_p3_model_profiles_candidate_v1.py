"""P3 pinned profile contract tests: synthetic/static, no model download."""
import json
import re
from pathlib import Path

from storyforge_gold_quality import hf_severity_evidence_v2 as severity

PROFILES = Path(__file__).resolve().parents[1] / (
    "experiments/r60_quality/p3_model_profiles_candidate_v1.json"
)

EXPECTED_MODELS = {
    "A": (
        "Qwen/Qwen3-32B",
        "9216db5781bf21249d130ec9da846c4624c16137",
    ),
    "B": (
        "zai-org/GLM-4-32B-0414",
        "8dea913c41b543527c2860fb6f3c15c202f24aeb",
    ),
    "challenger": (
        "zai-org/GLM-Z1-32B-0414",
        "8eb2858992c1f749e2a6d4075455decc2484722d",
    ),
}


def test_three_p3_models_are_exactly_revision_pinned():
    obj = json.loads(PROFILES.read_text(encoding="utf-8"))
    assert obj["schema"] == "storyforge_r60_p3_model_profiles_v1"
    assert obj["rubric_version"] == severity.RUBRIC_VERSION
    profiles = obj["model_profiles"]
    assert set(profiles) == set(EXPECTED_MODELS)
    for role, (model, revision) in EXPECTED_MODELS.items():
        assert profiles[role]["model"] == model
        assert profiles[role]["revision"] == revision
        assert re.fullmatch("[a-f0-9]{40}", profiles[role]["revision"])

    assert profiles["A"]["enable_thinking"] is True
    assert profiles["A"]["sampling"] == {
        "do_sample": True, "temperature": 0.6,
        "top_p": 0.95, "top_k": 20, "min_p": 0,
    }
    assert profiles["B"]["sampling"] is None
    assert profiles["challenger"]["sampling"] is None
    assert obj["input_budget_tokens"] is None
    assert obj["generation_budget_tokens"] is None
    assert obj["profile_freeze_authorized"] is False
    assert obj["gpu_authorized"] is False
    assert obj["inference_authorized"] is False
    assert obj["training_authorized"] is False

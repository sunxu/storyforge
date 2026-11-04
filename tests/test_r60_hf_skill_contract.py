"""Static contract tests for the reusable HF Jobs Skill; no network or private data."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/storyforge-hf-jobs"


def test_skill_documents_cover_runtime_and_safety_contract() -> None:
    required = [
        SKILL / "SKILL.md",
        SKILL / "README.md",
        SKILL / "references/RUNTIME.md",
        SKILL / "references/CPU_SMOKE.md",
        SKILL / "references/DIAGNOSTICS.md",
        SKILL / "references/SECURITY.md",
        SKILL / "references/TROUBLESHOOTING.md",
    ]
    assert all(path.is_file() for path in required)
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "doctor --profile cpu --json",
        "token_preflight.py",
        "不自动重试",
        "GPU",
        "SAFE",
        "Worktree",
    ):
        assert phrase in body


def test_skill_examples_call_public_runtime_without_model_or_hf_api() -> None:
    examples = list((SKILL / "examples").glob("*.py"))
    assert {path.name for path in examples} == {
        "cpu_job.py", "safe_receipt.py", "local_test.py"
    }
    forbidden = (
        "import torch", "from torch", "import transformers",
        "from transformers", "import huggingface_hub", "from huggingface_hub",
        "hf jobs run", "swift sft",
    )
    for path in examples:
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source
    assert "storyforge_dataset.hf_runtime" in (SKILL / "examples/cpu_job.py").read_text()
    assert "OutputManager.write_safe" in (SKILL / "examples/safe_receipt.py").read_text()

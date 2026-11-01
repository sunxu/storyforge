"""Synthetic-only guard for the reusable HF Token skill contract.

No HF, GPU, tokenizer, production database or private data access.
"""
from pathlib import Path
import hashlib
import json
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]


class ReuseContractTests(unittest.TestCase):
    def test_v011_skill_points_to_single_real_core(self):
        source = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("version: 0.1.3", source)
        self.assertIn("## HF Token 预检复用", source)
        self.assertIn("src/storyforge_dataset/token_preflight.py", source)
        self.assertIn("docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md", source)
        self.assertIn("固定 SAFE 阶段码", source)
        self.assertIn("工具变更执行顺序", source)
        self.assertIn("只允许一次受控纠错", source)
        self.assertTrue((REPO_ROOT / "docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md").is_file())
        self.assertIn("无需逐 Job 费用授权", source)
        self.assertTrue((REPO_ROOT / "src/storyforge_dataset/token_preflight.py").is_file())
        self.assertTrue((REPO_ROOT / "docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md").is_file())
        self.assertTrue((REPO_ROOT / "experiments/r58_quality/r58_hf_cpu_literary_token_preflight.py").is_file())

    def test_cost_privacy_and_legacy_gates_remain_explicit(self):
        source = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "Owner crosswalk", "HF CPU", "last_round",
            "Quality-v1", "G2", "--verify-cache-only",
            "--refresh-code", "len(BatchEncoding)", "不得",
        ):
            self.assertIn(phrase, source)
        self.assertIn("不是当前 Quality-v1 高质量 LoRA 的必需条件", source)

    def test_readme_and_changelog_document_reuse(self):
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Skill v0.1.3", readme)
        self.assertIn("HF_TOKEN_PREFLIGHT_REUSE_CN.md", readme)
        self.assertIn("无需逐 Job 费用授权", readme)
        self.assertTrue(changelog.startswith("# 0.1.3"))
        self.assertIn("不发起 Job", changelog)

    def test_manifest_v011_file_hashes_match(self):
        manifest = json.loads((SKILL_ROOT / "MANIFEST_SAFE.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.1.3")
        declared = {x["path"]: x for x in manifest["files"]}
        # v02/ is a separate, unreleased preview; it is intentionally outside
        # the frozen v0.1.2 package and must never enter this manifest.
        self.assertFalse(any(name.startswith("v02/") for name in declared))
        expected = {
            str(path.relative_to(SKILL_ROOT))
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and path.name != "MANIFEST_SAFE.json"
            and "__pycache__" not in path.parts
            and path.relative_to(SKILL_ROOT).parts[0] != "v02"
        }
        self.assertEqual(set(declared), expected)
        for name, record in declared.items():
            payload = (SKILL_ROOT / name).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"], name)
            self.assertEqual(len(payload), record["bytes"], name)

    def test_no_duplicate_core_in_skill(self):
        self.assertFalse((SKILL_ROOT / "scripts/token_preflight.py").exists())
        self.assertFalse((SKILL_ROOT / "token_preflight.py").exists())


if __name__ == "__main__":
    unittest.main()

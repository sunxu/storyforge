"""Synthetic-only contract tests for the StoryForge Skill boundaries.

No HF, GPU, tokenizer, production database or private data access.
"""
import hashlib
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]


class ReuseContractTests(unittest.TestCase):
    def test_skill_owns_execution_order_and_links_authoritative_specs(self):
        source = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("version: 0.1.9", source)
        for phrase in (
            "查找已有工具和证据",
            "优先复用",
            "必要时扩展共享核心",
            "添加回归测试",
            "更新 Skill 和文档",
            "docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md",
            "docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md",
            "docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md",
            "experiments/r58_quality/private_review_evidence_reuse.py",
            "src/storyforge_dataset/token_preflight.py",
            "R50",
            "Quality-v1",
            "last_round",
            "training_authorized=false",
        ):
            self.assertIn(phrase, source)
        self.assertTrue(
            (REPO_ROOT / "docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md").is_file()
        )
        self.assertTrue(
            (REPO_ROOT / "docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md").is_file()
        )
        self.assertTrue(
            (REPO_ROOT / "src/storyforge_dataset/token_preflight.py").is_file()
        )
        self.assertTrue(
            (REPO_ROOT / "docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md").is_file()
        )
        self.assertTrue(
            (REPO_ROOT / "experiments/r58_quality/private_review_evidence_reuse.py").is_file()
        )

    def test_skill_does_not_duplicate_technical_implementations(self):
        source = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for implementation_detail in (
            "candidate_index",
            "quote_index",
            "review_policy_version",
            "prompt_sha256",
            "len(BatchEncoding)",
            "--verify-cache-only",
            "--refresh-code",
            "token_core.py",
            "object_pairs_hook",
            "O_NOFOLLOW",
        ):
            self.assertNotIn(implementation_detail, source)

    def test_agents_keeps_general_policy_and_points_to_the_standard(self):
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("HF CPU", agents)
        self.assertIn("docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md", agents)
        self.assertIn("src/storyforge_dataset/token_preflight.py", agents)
        self.assertIn("GPU inference or training", agents)
        self.assertNotIn("len(BatchEncoding)", agents)
        self.assertNotIn("candidate_index", agents)
        self.assertNotIn("private_review_evidence_reuse.py", agents)

    def test_technical_standards_own_algorithm_details(self):
        token_spec = (REPO_ROOT / "docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md").read_text(
            encoding="utf-8"
        )
        quote_spec = (
            REPO_ROOT / "docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md"
        ).read_text(encoding="utf-8")
        reuse_spec = (
            REPO_ROOT / "docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("extract_input_ids", token_spec)
        self.assertIn("BatchEncoding", token_spec)
        self.assertIn("SAFE 诊断码", token_spec)
        self.assertIn("candidate_index", quote_spec)
        self.assertIn("Checkpoint v3", quote_spec)
        self.assertIn("QUOTE_REPAIR_SELECTION_INVALID", quote_spec)
        self.assertIn("case_id + input_messages_sha256 + target_sha256", reuse_spec)
        self.assertIn("不得写死批次大小", reuse_spec)
        self.assertIn("EXACT_REUSE_MATCH__NO_QUALITY_ADMISSION", reuse_spec)

    def test_readme_and_changelog_document_the_new_responsibilities(self):
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("v0.1.9", readme)
        self.assertIn("固定执行顺序", readme)
        self.assertIn("HF_TOKEN_PREFLIGHT_REUSE_CN.md", readme)
        self.assertIn("R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md", readme)
        self.assertIn("R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md", readme)
        self.assertTrue(changelog.startswith("# 0.1.9"))
        self.assertIn("AGENTS.md 只保留仓库通用规则", changelog)

    def test_manifest_hashes_and_file_inventory_match(self):
        manifest = json.loads(
            (SKILL_ROOT / "MANIFEST_SAFE.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "0.1.9")
        declared = {item["path"]: item for item in manifest["files"]}
        self.assertFalse(any(name.startswith("v02/") for name in declared))
        expected = {
            str(path.relative_to(SKILL_ROOT))
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and path.name != "MANIFEST_SAFE.json"
            and "__pycache__" not in path.parts
            and path.relative_to(SKILL_ROOT).parts[0] != "v02"
        }
        self.assertEqual(set(declared), expected)
        for name, record in declared.items():
            payload = (SKILL_ROOT / name).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"], name)
            self.assertEqual(len(payload), record["bytes"], name)

    def test_no_duplicate_shared_token_core(self):
        self.assertFalse((SKILL_ROOT / "scripts/token_preflight.py").exists())
        self.assertFalse((SKILL_ROOT / "token_preflight.py").exists())


if __name__ == "__main__":
    unittest.main()

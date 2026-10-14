"""CPU-only contract tests for R47 final blind review collection."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v02_r47_collect_validate import ADAPTERS, OLD_BASE_SHA, OLD_KEY, RUN_KEY, STATUS, sha, verify
from v02_r47_eval_validate import write_blind


class R47CollectorTests(unittest.TestCase):
    def fixture(self, root):
        original = []
        samples = []
        for i in range(20):
            msgs = [{"role": "system", "content": f"world {i//10}"},
                    {"role": "user", "content": f"player input {i}"}]
            digest = hashlib.sha256(json.dumps(
                {"messages": msgs}, sort_keys=True, ensure_ascii=False
            ).encode()).hexdigest()
            original.append({"messages": msgs})
            samples.append({"sample_id": f"eval-{i:03d}-{digest[:12]}",
                            "prompt_sha256": digest, "source_line": i+1})
        prompts = root / "prompts.jsonl"
        prompts.write_text("".join(json.dumps(item)+"\n" for item in original))
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"schema": "storyforge-blind-v1",
                                        "count": 20, "samples": samples}))
        dest = root / "dest"
        coordinator = dest / "coordinator"
        coordinator.mkdir(parents=True)
        response_paths = {}
        for arm in ("base", "v01", "v02"):
            path = coordinator / f"{arm}-results.jsonl"
            path.write_text("".join(json.dumps({
                "messages": source["messages"], "response": f"{arm} reply {i}",
            })+"\n" for i, source in enumerate(original)))
            response_paths[arm] = path
        package = root / "source-package"
        blind_summary = write_blind(prompts, manifest, response_paths, package)
        shutil.copytree(package / "blind-review", dest / "reviewers")
        shutil.copytree(package / "private", coordinator / "private")
        # The ordinary test fixture's Base is not the production Base.
        # Override the run's source hash by mocking the constant in test.
        report = {
            "status": STATUS, "run_key": RUN_KEY, "generation_complete": True,
            "scope": "EXPOSED_V01_20_RETROSPECTIVE_ONLY",
            "completed_arms": ["base", "v01", "v02"],
            "training_performed": False, "fresh_heldout": False,
            "promotion_approved": False,
            "model_revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
            "adapter_weight_sha256": ADAPTERS,
            "reused_base": {"run_key": OLD_KEY, "sha256": sha(response_paths["base"])},
            "input": {"count": 20, "prompts_sha256": sha(prompts),
                      "manifest_sha256": sha(manifest)},
            "results_sha256": {key: sha(path) for key, path in response_paths.items()},
            "blind_pack": blind_summary,
        }
        report_path = coordinator / "R47_PRIVATE_RUN_REPORT.json"
        report_path.write_text(json.dumps(report))
        return dest, prompts, manifest, report_path

    def test_complete_package_integrity(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            d, p, m, report = self.fixture(Path(t))
            base_sha = json.loads(report.read_text())["results_sha256"]["base"]
            with patch("v02_r47_collect_validate.OLD_BASE_SHA", base_sha):
                result = verify(d, p, m)
            self.assertEqual(result["responses"], 60)
            self.assertFalse(result["model_promotion"])

    def test_tampered_blind_reply_refused(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            d, p, m, report = self.fixture(Path(t))
            base_sha = json.loads(report.read_text())["results_sha256"]["base"]
            file = d / "reviewers" / "R47_BLIND_THREE_WAY_20.jsonl"
            text = file.read_text()
            file.write_text(text.replace("reply 0", "wrong answer", 1))
            with patch("v02_r47_collect_validate.OLD_BASE_SHA", base_sha):
                with self.assertRaises(ValueError):
                    verify(d, p, m)

    def test_missing_arm_refused(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            d, p, m, report = self.fixture(Path(t))
            base_sha = json.loads(report.read_text())["results_sha256"]["base"]
            info = json.loads(report.read_text())
            info["completed_arms"] = ["base", "v02"]
            report.write_text(json.dumps(info))
            with patch("v02_r47_collect_validate.OLD_BASE_SHA", base_sha):
                with self.assertRaises(ValueError):
                    verify(d, p, m)


if __name__ == "__main__":
    unittest.main()

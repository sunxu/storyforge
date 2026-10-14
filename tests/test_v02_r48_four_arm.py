"""CPU-only four-arm original Gold alignment and reviewer independence tests."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v02_r47_eval_validate import validate_prompts
from v02_r48_four_arm_build import build, read_gold, sha
from v02_r48_review_aggregate import combine, completed_reviews


class R48Test(unittest.TestCase):
    def test_actual_canonical_gold_20_matches_v01_prompts(self):
        test = ROOT / "data/compiled/v0.3/test.jsonl"
        prompts_file = ROOT / "evaluations/v0.1/test/prompts.jsonl"
        manifest = ROOT / "evaluations/v0.1/test/manifest.json"
        prompts, _ = validate_prompts(prompts_file, manifest)
        self.assertEqual(len(read_gold(test, prompts)), 20)

    def fixture(self, root: Path):
        prompts = []
        entries = []
        compiled = []
        for i in range(20):
            msg = [
                {"role": "system", "content": f"the setting of world {i//10}"},
                {"role": "user", "content": f"player message {i}"},
            ]
            payload = json.dumps({"messages": msg}, sort_keys=True, ensure_ascii=False)
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            prompts.append({"messages": msg})
            entries.append({
                "sample_id": f"eval-{i:03d}-{digest[:12]}",
                "prompt_sha256": digest, "source_line": i + 1,
            })
            compiled.append({
                "messages": msg + [{"role": "assistant", "content": f"human Gold {i}"}],
            })
        def dump(path, values):
            path.write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in values))
        p = root / "prompts.jsonl"
        m = root / "manifest.json"
        t = root / "test.jsonl"
        dump(p, prompts)
        dump(t, compiled)
        m.write_text(json.dumps({
            "schema": "storyforge-blind-v1", "count": 20, "samples": entries,
        }))
        coord = root / "coordinator"
        coord.mkdir()
        model_files = {}
        for arm in ("base", "v01", "v02"):
            f = coord / f"{arm}-results.jsonl"
            dump(f, [
                {"messages": prompts[i]["messages"], "response": f"{arm} reply {i}"}
                for i in range(20)
            ])
            model_files[arm] = f
        r = coord / "R47_PRIVATE_RUN_REPORT.json"
        r.write_text(json.dumps({
            "status": "R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED",
            "run_key": "r47-20261014T091647Z-637890",
            "generation_complete": True,
            "completed_arms": ["base", "v01", "v02"],
            "training_performed": False,
            "fresh_heldout": False,
            "promotion_approved": False,
            "reused_base": {
                "run_key": "r47-20261014T082109Z-820409",
                "sha256": sha(model_files["base"]),
            },
            "input": {"count": 20, "prompts_sha256": sha(p), "manifest_sha256": sha(m)},
            "results_sha256": {arm: sha(f) for arm, f in model_files.items()},
        }))
        return t, p, m, r, model_files

    def test_build_four_arm_and_blind_key_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            t, p, m, r, mf = self.fixture(root)
            out = root / "r48"
            with patch("v02_r48_four_arm_build.BASE_SHA256", sha(mf["base"])), \
                 patch("v02_r48_four_arm_build.CANONICAL_TEST_SHA256", sha(t)):
                report = build(compiled_test=t, prompts_file=p, manifest_file=m,
                               report_file=r, model_files=mf, output=out)
            self.assertEqual(report["reply_count"], 80)
            self.assertEqual(report["sample_count"], 20)
            self.assertTrue((out / "coordinator/private/R48_PRIVATE_ANSWER_KEY.json").is_file())
            blind = [
                json.loads(x) for x in
                (out / "reviewers/R48_BLIND_FOUR_WAY_20.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(blind), 20)
            self.assertEqual(set(blind[0]) - {"sample_id", "prompt_sha256"},
                             {"response_a", "response_b", "response_c", "response_d"})
            self.assertFalse(any("gold" in str(path.name).lower() for path in
                                 (out / "reviewers").glob("R48_Reviewer_*.csv")))
            with self.assertRaises(FileExistsError):
                with patch("v02_r48_four_arm_build.BASE_SHA256", sha(mf["base"])), \
                     patch("v02_r48_four_arm_build.CANONICAL_TEST_SHA256", sha(t)):
                    build(compiled_test=t, prompts_file=p, manifest_file=m,
                          report_file=r, model_files=mf, output=out)

            submitted = []
            for i in (1, 2, 3):
                original = out / f"reviewers/R48_Reviewer_{i:02d}.csv"
                target = root / f"completed_{i}.csv"
                with original.open(encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    fields = list(reader.fieldnames)
                for row in rows:
                    row["整体最佳(A/B/C/D/TIE)"] = "A"
                    row["评分理由与逐字证据"] = "A: 角色语言自然且保留了玩家选择权；对比其他回复更完整。"
                    row["严重问题与对应回复"] = "无"
                    row["玩家自主权严重侵犯(A/B/C/D/无)"] = "无"
                    for col in fields:
                        if "·" in col:
                            row[col] = "4"
                with target.open("w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                submitted.append(target)
            sheets, record = completed_reviews(submitted, out / "reviewers", m)
            self.assertEqual(record["rating_cells"], 1440)
            key = out / "coordinator/private/R48_PRIVATE_ANSWER_KEY.json"
            summary = combine(sheets, key)
            self.assertEqual(sum(summary["model_votes"].values()), 60)
            self.assertEqual(sum(summary["majority_wins"].values()), 20)
            self.assertFalse(summary["quality_promotion"])
            # Guard the unscored original, not just the 3 matching modified sheets.
            with submitted[0].open(encoding="utf-8-sig", newline="") as f:
                rd = csv.DictReader(f)
                data = list(rd)
                hdr = list(rd.fieldnames)
            data[0]["回复D"] = "changed response"
            with submitted[0].open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=hdr)
                w.writeheader()
                w.writerows(data)
            with self.assertRaises(ValueError):
                completed_reviews(submitted, out / "reviewers", m)

    def test_source_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            t, p, m, r, mf = self.fixture(Path(tmp))
            data = json.loads(t.read_text().splitlines()[0])
            data["messages"][-2]["content"] += " changed"
            rows = [json.loads(line) for line in t.read_text().splitlines()]
            rows[0] = data
            t.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
            prompts, _ = validate_prompts(p, m)
            with self.assertRaises(ValueError):
                read_gold(t, prompts)


if __name__ == "__main__":
    unittest.main()

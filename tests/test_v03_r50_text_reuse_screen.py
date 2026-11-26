"""Synthetic R50 exact/long-fragment overlap tests (never use actual story text)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_text_reuse_screen import HIST, SOURCE, scan


def make(repo: Path, *, shared: bool = False, old: bool = False) -> None:
    shared_string = "一段用来核对长文本重合的虚构消息甲乙丙丁。" * 15
    different = ["甲" * 160, "乙" * 160, "丙" * 160, "丁" * 160, "戊" * 160]
    for rank in range(16, 21):
        folder = repo / SOURCE / f"{rank}-sample"
        folder.mkdir(parents=True)
        text = shared_string if shared and rank in (16, 17) else different[rank - 16]
        if old and rank == 16:
            text = shared_string
        (folder / f"{folder.name}.jsonl").write_text(
            json.dumps({"rank": rank, "messages": [
                {"role": "user", "content": text},
                {"role": "assistant", "content": ""},
            ]}, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    for path, n in HIST:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as f:
            for idx in range(n):
                text = shared_string if old and idx == 0 else "己" * 160
                f.write(json.dumps({"messages": [
                    {"role": "user", "content": text}
                ]}, ensure_ascii=False) + "\n")


class LongTextReuseTests(unittest.TestCase):
    def test_no_overlap_does_not_grant_admission(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make(root)
            r = scan(root)
            self.assertEqual(r["historic_records"], 215)
            self.assertEqual(len(r["worlds"]), 5)
            self.assertEqual(r["cross_world_exact_message_pairs"], [])
            self.assertEqual(r["fresh_heldout_cases"], 0)

    def test_exact_cross_world_source_match(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make(root, shared=True)
            r = scan(root)
            self.assertIn([16, 17], r["cross_world_exact_message_pairs"])
            self.assertIn([16, 17], r["cross_world_shared_long_fragment_pairs"])

    def test_old_history_overlap_detected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make(root, old=True)
            r = scan(root)
            w16 = next(w for w in r["worlds"] if w["rank"] == 16)
            self.assertGreater(w16["historic_exact_message_hit_count"], 0)
            self.assertGreater(w16["historic_120char_block_hit_count"], 0)

    def test_late_excerpt_overlap_not_identical_message(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make(root, shared=True)
            p = root / SOURCE / "17-sample" / "17-sample.jsonl"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["messages"][0]["content"] = "额外前言" + obj["messages"][0]["content"] + "末尾变化"
            p.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")
            r = scan(root)
            self.assertNotIn([16, 17], r["cross_world_exact_message_pairs"])
            self.assertIn([16, 17], r["cross_world_shared_long_fragment_pairs"])

    def test_missing_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make(root)
            (root / HIST[0][0]).unlink()
            with self.assertRaises(FileNotFoundError):
                scan(root)


if __name__ == "__main__":
    unittest.main()

"""Synthetic offset-shift tests for full-window R50 overlap detection."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_exhaustive_screen import all_windows, scan
from v03_r50_text_reuse_screen import BLOCK, HIST, SOURCE


def fixture(repo: Path, *, share_shifted: bool = False):
    seed = "".join(chr(0x4e00 + (i % 1500)) for i in range(250))
    for rank in range(16, 21):
        folder = repo / SOURCE / f"{rank}-sample"
        folder.mkdir(parents=True)
        if rank == 16:
            value = "!" * 7 + seed + "!" * 7
        elif rank == 17 and share_shifted:
            value = "#" * 11 + seed + "#" * 7
        else:
            value = chr(0x5f00 + rank) * 130
        (folder / f"{folder.name}.jsonl").write_text(
            json.dumps({"rank": rank, "messages": [{"role": "user", "content": value}]},
                       ensure_ascii=False) + "\n", encoding="utf-8"
        )
    for path, count in HIST:
        p = repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as w:
            for idx in range(count):
                text = ("@" * 3 + seed + "@" * 6) if share_shifted and idx == 0 else "其他" * 80
                w.write(json.dumps({"messages": [{"role": "assistant", "content": text}]},
                                   ensure_ascii=False) + "\n")


class ExhaustiveTests(unittest.TestCase):
    def test_exact_all_offset_count(self):
        s = "x" * (BLOCK + 9)
        self.assertEqual(len(list(all_windows(s))), 10)
        self.assertEqual(len(list(all_windows("a" * (BLOCK - 1)))), 0)

    def test_shifted_overlap_detected(self):
        with tempfile.TemporaryDirectory() as t:
            fixture(Path(t), share_shifted=True)
            r = scan(Path(t))
            self.assertIn([16, 17], r["new_world_shared_120_codepoint_window_pairs"])
            a = {w["rank"]: w for w in r["worlds"]}
            self.assertGreater(a[16]["historic_all_offset_120_codepoint_fingerprints"], 0)
            self.assertGreater(a[17]["historic_all_offset_120_codepoint_fingerprints"], 0)
            self.assertEqual(r["heldout_test_cases"], 0)
            self.assertEqual(r["window_step"], 1)

    def test_baseline_keeps_manual_gate(self):
        with tempfile.TemporaryDirectory() as t:
            fixture(Path(t))
            r = scan(Path(t))
            self.assertEqual(r["new_world_shared_120_codepoint_window_pairs"], [])
            self.assertEqual(r["status"], "ALL_OFFSET_120_CODEPOINT_SCREEN_DONE__SEMANTIC_REVIEW_PENDING")

    def test_missing_historic_file_fails(self):
        with tempfile.TemporaryDirectory() as t:
            fixture(Path(t))
            (Path(t) / HIST[0][0]).unlink()
            with self.assertRaises(FileNotFoundError):
                scan(Path(t))


if __name__ == "__main__":
    unittest.main()

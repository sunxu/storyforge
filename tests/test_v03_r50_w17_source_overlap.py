"""Pure synthetic regressions for R50 W17 source overlap triage."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "v03_r50_w17_source_overlap.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("w17_source", SCRIPT)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def example(i, common=None):
    messages = [{"role": "user", "content": "unique synthetic " + str(i)}]
    if common:
        messages.append({"role": "assistant", "content": common})
    return {"story": {"id": f"synthetic-{i}"}, "messages": messages}


class R50W17OverlapTests(unittest.TestCase):
    def setUp(self):
        self.message = "SYNTHETIC LONG SHARED TEXT " * 25
        self.old = {i: example(i, self.message) for i in (2, 4, 10)}
        self.old[7] = example(7)
        self.new = {17: example(17, self.message), 16: example(16)}

    def test_one_literal_three_pairs(self):
        result, exact, spans = m.diagnose(self.old, self.new)
        self.assertEqual(len(result["flagged_pairs"]), 3)
        self.assertEqual(len(exact), 1)
        self.assertGreater(len(spans), 0)
        self.assertTrue(result["one_literal_shared_by_old_02_04_10"])
        self.assertTrue(all(r["all_sampled_chunks_from_full_exact_message"]
                            for r in result["flagged_pairs"]))

    def test_distinct_strings_not_mislabeled_one_template(self):
        self.old[10] = example(10, "DIFFERENT SYNTHETIC TEXT " * 15)
        result, _, _ = m.diagnose(self.old, self.new)
        self.assertFalse(result["one_literal_shared_by_old_02_04_10"])

    def test_no_story_text_in_report(self):
        result, _, _ = m.diagnose(self.old, self.new)
        self.assertNotIn(self.message, str(result))
        self.assertNotIn("synthetic-17", str(result))

    def test_r50_history_matching(self):
        cases = []
        for world, n in ((16, 9), (17, 10), (18, 9), (19, 8), (20, 10)):
            for i in range(1, n + 1):
                hist = [{"role": "user", "content": "other"}]
                if world == 17 and i == 1:
                    hist.append({"role": "assistant", "content": self.message})
                cases.append({
                    "case_id": f"SFH50-W{world}-{i:03d}", "history": hist,
                    "world_card": "other", "long_term_rules": ["other"],
                    "user_input": "other",
                })
        report = m.check_46_cases(cases, {m.normalize(self.message)},
                                  m.chunks(m.normalize(self.message)), "other")
        self.assertEqual(report["w17_cases_containing_shared_long_literal"]["history"], 1)
        self.assertEqual(report["w17_cases_containing_shared_120_window"]["history"], 1)


if __name__ == "__main__":
    unittest.main()

import copy
import json
from pathlib import Path
import tempfile
import unittest

from gold195_case02_final_disposition import make_template, validate_decision, private_write
from gold195_grok_web_export import export
from gold195_grok_web_followup import make_packets, write_packets
from test_gold195_grok_web_pilot import review, task


class FinalDispositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.private = root / "private"
        self.private.mkdir(mode=0o700)
        self.pilot = self.private / "pilot"
        export(self.repo, self.pilot, [task(1), task(2), task(3)])

        def store(case, who, obj):
            file = self.pilot / ("case%02d-reviewer-%s.json" % (case, who))
            file.write_text(json.dumps(obj))
            file.chmod(0o600)

        for who in "AB":
            store(1, who, review(task(1)["target_text"]))
        severe = review(task(2)["target_text"])
        severe["severe_flags"]["hard_fact_or_ban"] = True
        store(2, "A", severe)
        store(2, "B", review(task(2)["target_text"]))
        store(3, "A", {"invalid": True})
        misquote = review(task(3)["target_text"])
        misquote["evidence_quotes"] = ["FAKE"]
        store(3, "B", misquote)
        self.follow = self.private / "follow"
        write_packets(make_packets(self.pilot), self.follow, self.repo)
        for who in "AB":
            file = self.follow / ("case03-reviewer-%s-retry.json" % who)
            file.write_text(json.dumps(review(task(3)["target_text"])))
            file.chmod(0o600)
        arbiter = {
            "arbiter_verdict": "NOT_SUPPORTED",
            "severe_flag_names": ["hard_fact_or_ban"],
            "gold_exact_quotes": [task(2)["target_text"][:10]],
            "rule_or_card_evidence": ["未发现明确禁令"],
            "analysis": "原材料无法证明严重问题",
            "remaining_uncertainty": "",
        }
        arbiter_path = self.follow / "case02-independent-severe-arbitration.json"
        arbiter_path.write_text(json.dumps(arbiter, ensure_ascii=False))
        arbiter_path.chmod(0o600)

    def tearDown(self):
        self.temp.cleanup()

    def test_template_is_hold_and_source_immutable(self):
        before = {p.name: p.read_bytes() for p in self.pilot.iterdir()}
        obj = make_template(self.pilot, self.follow)
        self.assertEqual(obj["decision"], "UNRESOLVED")
        self.assertEqual(validate_decision(obj, self.pilot, self.follow),
                         "CASE02_UNRESOLVED__HOLD")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.pilot.iterdir()})
        path = self.private / "case02.json"
        private_write(path, self.repo, obj)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            private_write(path, self.repo, obj)

    def test_evidence_based_finalization_remains_no_train(self):
        obj = make_template(self.pilot, self.follow)
        obj.update({
            "decision": "NOT_SUPPORTED_WITH_EVIDENCE",
            "decision_maker": "independent human",
            "independent_reasoning": "可见原文与故事卡的禁令并不对应，不应仅凭普通 NPC 行动认定严重侵犯。",
            "actual_source_evidence": ["来源故事规则中不存在被推断的禁令"],
            "gold_exact_quotes": [task(2)["target_text"][:10]],
            "uncertainty": "",
            "decision_completed": True,
        })
        self.assertEqual(
            validate_decision(obj, self.pilot, self.follow),
            "CASE02_SEVERE_NOT_SUPPORTED__OTHER_QUALITY_GATES_HOLD")
        obj["gold_exact_quotes"] = ["unavailable exact text"]
        with self.assertRaises(ValueError):
            validate_decision(obj, self.pilot, self.follow)

    def test_severe_remains_excluded(self):
        obj = make_template(self.pilot, self.follow)
        obj.update({
            "decision": "CONFIRMED_SEVERE",
            "decision_maker": "independent human",
            "independent_reasoning": "这段回复的行为与明确禁止的角色决策规则相抵触，需要排除。",
            "actual_source_evidence": ["明确规则冲突举证"],
            "gold_exact_quotes": [task(2)["target_text"][:10]],
            "decision_completed": True,
        })
        self.assertEqual(validate_decision(obj, self.pilot, self.follow),
                         "CASE02_SEVERE_CONFIRMED__EXCLUDE_FROM_TRAINING")
        tampered = copy.deepcopy(obj)
        tampered["original_A"]["severe_flags"]["hard_fact_or_ban"] = False
        with self.assertRaises(ValueError):
            validate_decision(tampered, self.pilot, self.follow)


if __name__ == "__main__":
    unittest.main()

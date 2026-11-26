import json
from pathlib import Path
import tempfile
import unittest

from gold195_grok_web_export import export
from gold195_grok_web_followup import make_packets, write_packets
from test_gold195_grok_web_pilot import task, review


class TargetedFollowupTests(unittest.TestCase):
    def test_followup_only_case02_case03_and_originals_intact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            pilot = private / "pilot"
            export(repo, pilot, [task(1), task(2), task(3)])

            def store(i, reviewer, value):
                path = pilot / ("case%02d-reviewer-%s.json" % (i, reviewer))
                path.write_text(json.dumps(value, ensure_ascii=False))
                path.chmod(0o600)
            for who in "AB":
                store(1, who, review(task(1)["target_text"]))
            severe = review(task(2)["target_text"])
            severe["severe_flags"]["hard_fact_or_ban"] = True
            store(2, "A", severe)
            store(2, "B", review(task(2)["target_text"]))
            store(3, "A", {"not_a_review": True})
            invalid = review(task(3)["target_text"])
            invalid["evidence_quotes"] = ["FAKE_QUOTE_NOT_IN_GOLD"]
            store(3, "B", invalid)

            before = {f.name: f.read_bytes() for f in pilot.iterdir()}
            packets = make_packets(pilot)
            self.assertEqual(set(packets), {
                "case02-independent-severe-arbitration.md",
                "case03-reviewer-A-retry.md",
                "case03-reviewer-B-retry.md",
            })
            self.assertNotIn(b"PRIVATE_GOLD_TARGET_01", b"".join(packets.values()))
            self.assertNotIn(b"PRIVATE_GOLD_TARGET_03",
                             packets["case02-independent-severe-arbitration.md"])
            self.assertNotIn(b"FAKE_QUOTE_NOT_IN_GOLD",
                             packets["case03-reviewer-B-retry.md"])
            self.assertIn(b"PRIVATE_GOLD_TARGET_02",
                          packets["case02-independent-severe-arbitration.md"])
            dest = private / "targeted"
            write_packets(packets, dest, repo)
            self.assertEqual(len(list(dest.iterdir())), 3)
            self.assertTrue(all((x.stat().st_mode & 0o777) == 0o600
                                for x in dest.iterdir()))
            self.assertEqual(before, {f.name: f.read_bytes() for f in pilot.iterdir()})
            with self.assertRaises(ValueError):
                write_packets(packets, dest, repo)

    def test_mismatched_triage_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            pilot = private / "pilot"
            export(repo, pilot, [task(1), task(2), task(3)])
            with self.assertRaises(ValueError):
                make_packets(pilot)


if __name__ == "__main__":
    unittest.main()

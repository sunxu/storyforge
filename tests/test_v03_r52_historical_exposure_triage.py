"""R52 historical exposure screen synthetic checks only, no real stories."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_historical_exposure_triage as triage


def fake_world(rank):
    content = "Some invented scene content, no private source is present. " * 5
    return {
        "source_story_id": f"synthetic-source-{rank}",
        "original_root_messages": [{
            "original_source_array_index": 0,
            "source_body_sha256": triage.sha_bytes(content.encode("utf8")),
            "content": content,
        }],
    }


class TestR52HistoricalExposure(unittest.TestCase):
    def worlds(self):
        return {x: fake_world(x) for x in (6, 9, 10, 12, 13, 14, 15)}

    def test_exact_same_message_is_flagged_not_approved(self):
        worlds = self.worlds()
        source = worlds[6]["original_root_messages"][0]["content"]
        cohorts = {"gold87": [{
            "metadata": {"story_id": "other-synthetic-source"},
            "messages": [{"role": "assistant", "content": source}],
        }]}
        witnesses, counts, collisions = triage.triage(worlds, cohorts)
        self.assertGreater(len(witnesses), 0)
        self.assertGreater(counts["EXACT_LONG_MESSAGE"], 0)
        self.assertTrue(all(x["training_admission"] == "PENDING_NOT_APPROVED"
                            for x in witnesses))
        self.assertEqual(collisions, {})
        self.assertTrue(all("source_body_sha256" in x for x in witnesses))

    def test_same_uuid_not_hidden_by_lack_of_text_match(self):
        worlds = self.worlds()
        cohorts = {"v01_train": [{
            "metadata": {"story_id": worlds[9]["source_story_id"]},
            "messages": [{"role": "user", "content": "Different text"}],
        }]}
        witnesses, counts, collisions = triage.triage(worlds, cohorts)
        self.assertEqual(len(witnesses), 0)
        self.assertEqual(collisions["v01_train"], 1)

    def test_few_evidence_capacity_fails_closed(self):
        worlds = self.worlds()
        content = worlds[6]["original_root_messages"][0]["content"]
        cohorts = {"gold87": [{
            "metadata": {"story_id": "other"},
            "messages": [{"content": content}],
        }]}
        with self.assertRaisesRegex(
            triage.exact.GateHold, "TOO_MANY_HISTORIC_CANDIDATES"):
            triage.triage(worlds, cohorts, max_evidence=1)

    def test_exact_and_fragment_semantics_are_limited(self):
        text = "A" * 200
        self.assertEqual(len(set(triage.probes(text))), 1)
        self.assertEqual(list(triage.probes("short")), [])
        self.assertEqual(triage.STRIDE, 40)
        self.assertEqual(triage.FRAGMENT, 120)


if __name__ == "__main__":
    unittest.main()

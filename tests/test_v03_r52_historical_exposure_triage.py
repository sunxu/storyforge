"""R52 historical exposure screen synthetic checks only, no real stories."""
from __future__ import annotations
import sys
import tempfile
import zipfile
import stat
from unittest.mock import patch
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

    def test_r45_zip_ephemeral_verified_and_private(self):
        with tempfile.TemporaryDirectory() as location:
            parent = Path(location)
            safe = parent / "verified"
            safe.mkdir(mode=0o700)
            contents = {
                split: (('{"metadata":{"source_story_id":"fake"},'
                         '"messages":[{"content":"no private content"}]}'
                         '\n') * count).encode()
                for split, count in triage.R45_REQUIRED.items()
            }
            want = {
                k: {"count": triage.R45_REQUIRED[k],
                    "sha256": triage.sha_bytes(v)}
                for k, v in contents.items()
            }
            archive = parent / "r45_frozen.zip"
            with zipfile.ZipFile(archive, "w") as z:
                for split, filename in triage.R45_ARCHIVE_NAMES.items():
                    z.writestr("nested/" + filename, contents[split])
            with patch.object(triage.r45, "FROZEN", want):
                a, b = triage.extract_verified_r45_archive(archive, safe)
                self.assertEqual(a.read_bytes(), contents["train"])
                self.assertEqual(b.read_bytes(), contents["validation"])
                self.assertEqual(stat.S_IMODE(a.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(b.stat().st_mode), 0o600)

    def test_r45_zip_tampered_or_ambiguous_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as location:
            home = Path(location)
            safe = home / "priv"
            safe.mkdir(mode=0o700)
            archive = home / "bad_r45.zip"
            with zipfile.ZipFile(archive, "w") as z:
                for filename in triage.R45_ARCHIVE_NAMES.values():
                    z.writestr(filename, b"WRONG_DATA")
            with self.assertRaisesRegex(
                triage.exact.GateHold, "R45_FROZEN_SOURCE_BYTES_OR_ROWS_CHANGED"):
                triage.extract_verified_r45_archive(archive, safe)
            with zipfile.ZipFile(archive, "w") as z:
                for filename in triage.R45_ARCHIVE_NAMES.values():
                    z.writestr("a/" + filename, b"same")
                    z.writestr("b/" + filename, b"same")
            with self.assertRaisesRegex(
                triage.exact.GateHold, "R45_ORIGINAL_FROZEN_MEMBER_AMBIGUOUS"):
                triage.extract_verified_r45_archive(archive, safe)

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

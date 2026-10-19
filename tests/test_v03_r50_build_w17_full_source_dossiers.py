"""All-synthetic provenance tests for complete W17 original-source dossiers."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "dossier", SCRIPTS / "v03_r50_build_w17_full_source_dossiers.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def world(rank):
    return {"messages": [
        {"role": "user", "content": f"Synthetic start world {rank}"},
        {"role": "assistant", "content": f"Full source message world {rank} is unique."},
        {"role": "user", "content": f"World {rank} extended neighbor context"},
        {"role": "assistant", "content": f"World {rank} ending."},
    ]}


def scenario():
    sources = {rank: world(rank) for rank in m.RANKS}
    packets = []
    workpaper = {"gap_reviews": []}
    for gap in range(7):
        refs = []
        cited = []
        for rank in m.RANKS:
            content = sources[rank]["messages"][1]["content"]
            refs.append({
                "source_rank": rank, "source_message_index": 1,
                "full_untruncated_message_reviewed": False,
            })
            cited.append({
                "source_rank": rank, "original_source_message_index": 1,
                "original_source_role": "assistant",
                "original_message_sha256": m.digest(content.encode("utf8")),
                "original_message_codepoints": len(content),
                "focus_start_character": 0,
                "focus_excerpt": content,
            })
        packets.append({
            "gap_index": gap,
            "original_private_missing_evidence_requirement": f"synthetic gap {gap}",
            "private_candidate_contexts": cited,
        })
        workpaper["gap_reviews"].append({
            "gap_index": gap,
            "source_refs": refs,
            "private_reasoning": "synthetic scoped note",
            "remaining_evidence_requirements": ["synthetic missing fact"],
        })
    return packets, workpaper, sources


class FullSourceDossierTests(unittest.TestCase):
    def test_five_cited_complete_messages_with_neighbors_each(self):
        packets, workpaper, sources = scenario()
        result = m.build_dossiers(packets, workpaper, sources)
        self.assertEqual(len(result), 7)
        self.assertEqual(result[0]["prior_workpaper_referenced_source_count"], 5)
        self.assertEqual(result[0]["source_full_message_count"], 20)
        self.assertTrue(all(x["complete_original_message_untruncated"]
                            for x in result[0]["full_original_messages"]))
        self.assertEqual(result[0]["semantic_world_gate"], "HOLD")
        self.assertFalse(result[0]["historical_card_cutoff_verified"])

    def test_cited_message_bytes_original_only(self):
        packets, workpaper, sources = scenario()
        dossier = m.build_dossiers(packets, workpaper, sources)[0]
        rec = next(x for x in dossier["full_original_messages"]
                   if x["source_rank"] == 2 and x["original_source_message_index"] == 1)
        self.assertTrue(rec["cited_in_previous_workpaper"])
        self.assertEqual(rec["full_source_text"], sources[2]["messages"][1]["content"])
        self.assertEqual(m.digest(rec["full_source_text"].encode()),
                         rec["original_message_sha256"])

    def test_tampered_message_is_rejected(self):
        packets, workpaper, sources = scenario()
        sources[2]["messages"][1]["content"] = "Changed without new hash"
        with self.assertRaisesRegex(ValueError,
                                    "FULL_SOURCE_MESSAGE_HASH_OR_LENGTH_MISMATCH"):
            m.build_dossiers(packets, workpaper, sources)

    def test_other_source_rank_rejected(self):
        packets, workpaper, sources = scenario()
        packets[0]["private_candidate_contexts"][0]["source_rank"] = 88
        with self.assertRaisesRegex(ValueError,
                                    "REVIEWED_MESSAGE_NOT_IN_FROZEN_PACKET"):
            m.build_dossiers(packets, workpaper, sources)

    def test_same_rank_duplicate_source_ref_rejected(self):
        packets, workpaper, sources = scenario()
        workpaper["gap_reviews"][0]["source_refs"].append(
            workpaper["gap_reviews"][0]["source_refs"][0].copy()
        )
        with self.assertRaisesRegex(ValueError,
                                    "DUPLICATE_REVIEWED_SOURCE_POINTER"):
            m.build_dossiers(packets, workpaper, sources)

    def test_missing_world_seven_is_error(self):
        packets, workpaper, sources = scenario()
        del sources[7]
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_REVIEW_SCOPE_CHANGED"):
            m.build_dossiers(packets, workpaper, sources)


if __name__ == "__main__":
    unittest.main()

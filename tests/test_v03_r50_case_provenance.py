"""Synthetic proof for R50 source-cutoff provenance; never reads real prompts."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_case_provenance import ROOT, verify_case_sources


def fixture(repo: Path):
    inputs, provenance = [], []
    for rank in range(16, 21):
        folder = repo / ROOT / f"{rank}-example"
        folder.mkdir(parents=True)
        story_id = f"source-story-{rank}"
        session_id = f"session-{rank}"
        card = {
            "rank": rank,
            "story_id": story_id,
            "session_id": session_id,
            "export_time_card": {
                "id": f"card-{rank}",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
            "content_versions": [{
                "id": f"version-{rank}",
                "source_updated_at": "2026-01-01T00:00:00+00:00",
                "archived_at": "2026-01-04T00:00:00+00:00",
            }],
            "moderation_source_snapshots": [],
        }
        messages = [
            {"id": f"message-{rank}-1", "created_at": "2026-01-02T00:00:00+00:00",
             "role": "user", "content": f"玩家在故事{rank}询问现状"},
            {"id": f"message-{rank}-2", "created_at": "2026-01-03T00:00:00+00:00",
             "role": "assistant", "content": f"角色在故事{rank}回应玩家"},
        ]
        raw = {"rank": rank, "story": {"id": story_id},
               "session": {"session_id": session_id}, "messages": messages}
        (folder / "story-cards.json").write_text(json.dumps(card), encoding="utf-8")
        (folder / f"{folder.name}.jsonl").write_text(
            json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
        for number in range(8):
            case_id = f"SFH50-W{rank}-{number+1:03d}"
            inputs.append({
                "case_id": case_id, "world_id": f"w{rank}",
                "world_card": "故事世界的完整背景和人物已知规则，来自历史证据",
                "long_term_rules": ["玩家自主决定自己行动"],
                "history": [{"role": m["role"], "content": m["content"]}
                            for m in messages],
                "user_input": f"这是独立编写的全新测试输入 {rank} / {number+1}，继续该剧情。",
            })
            provenance.append({
                "case_id": case_id, "story_number": rank,
                "source_story_id": story_id, "source_session_id": session_id,
                "cutoff_message_id": f"message-{rank}-2",
                "history_message_ids": [f"message-{rank}-1", f"message-{rank}-2"],
                "card_evidence": {"kind": "export_time_card",
                                  "record_id": f"card-{rank}"},
            })
    return inputs, provenance


class CaseProvenanceTests(unittest.TestCase):
    def test_all_40_source_cutoffs_match_but_not_eligible(self):
        with tempfile.TemporaryDirectory() as temp:
            x, p = fixture(Path(temp))
            result = verify_case_sources(Path(temp), x, p)
            self.assertEqual(result["case_count"], 40)
            self.assertEqual(result["world_count"], 5)
            self.assertEqual(result["source_history_exactly_matched"], 40)
            self.assertFalse(result["independent_authorship_attested"])
            self.assertFalse(result["new_cases_sealed_for_evaluation"])

    def test_history_rewrite_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            x, p = fixture(Path(temp))
            x[0]["history"][0]["content"] = "人为改变历史"
            with self.assertRaisesRegex(ValueError, "changed"):
                verify_case_sources(Path(temp), x, p)

    def test_future_card_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            x, p = fixture(root)
            folder = root / ROOT / "16-example" / "story-cards.json"
            card = json.loads(folder.read_text(encoding="utf-8"))
            card["export_time_card"]["updated_at"] = "2026-01-05T00:00:00+00:00"
            folder.write_text(json.dumps(card), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "postdates"):
                verify_case_sources(root, x, p)

    def test_historical_version_accepted_as_evidence_not_final_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            x, p = fixture(Path(temp))
            for entry in p:
                rank = entry["story_number"]
                entry["card_evidence"] = {"kind": "content_versions",
                                          "record_id": f"version-{rank}"}
            result = verify_case_sources(Path(temp), x, p)
            self.assertEqual(result["card_evidence_type_counts"]["content_versions"], 40)
            self.assertEqual(result["semantic_world_and_card_fact_review"], "PENDING")

    def test_wrong_cutoff_and_duplicate_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            x, p = fixture(Path(temp))
            p[0]["cutoff_message_id"] = "message-16-1"
            with self.assertRaisesRegex(ValueError, "source cutoff"):
                verify_case_sources(Path(temp), x, p)

    def test_copied_player_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            x, p = fixture(root)
            folder = root / ROOT / "16-example" / "16-example.jsonl"
            source = json.loads(folder.read_text(encoding="utf-8"))
            source["messages"].append({
                "id": "message-16-3", "role": "user",
                "content": "这是一段有一定长度并且会被重复的玩家消息内容，必须作为非独立输入排除。",
                "created_at": "2026-01-04T00:00:00+00:00",
            })
            folder.write_text(json.dumps(source, ensure_ascii=False) + "\n", encoding="utf-8")
            x[0]["user_input"] = source["messages"][2]["content"]
            with self.assertRaisesRegex(ValueError, "copied verbatim"):
                verify_case_sources(root, x, p)

    def test_duplicate_case_id_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            x, p = fixture(Path(temp))
            p[1]["case_id"] = p[0]["case_id"]
            with self.assertRaisesRegex(ValueError, "duplicate case_id"):
                verify_case_sources(Path(temp), x, p)

    def test_different_world_mapping_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            x, p = fixture(Path(temp))
            x[8]["world_id"] = x[0]["world_id"]
            with self.assertRaisesRegex(ValueError, "world_id"):
                verify_case_sources(Path(temp), x, p)


if __name__ == "__main__":
    unittest.main()

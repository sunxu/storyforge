"""Synthetic tests for R50 world alias and timeline screen."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_world_alias_screen import GOLD, OLD_TEST, SOURCE, scan


def fixture(root: Path, *, common_name: bool = False, historical_name: bool = False,
            late_card: bool = False) -> None:
    for rank in range(16, 21):
        folder = root / SOURCE / f"{rank}-example"
        folder.mkdir(parents=True)
        name = "同名人物" if common_name and rank in (16, 17) else f"测试角色{rank}"
        card = {
            "rank": rank,
            "story_id": f"world-{rank}",
            "chat_window": {
                "first_message_at": "2026-01-03T00:00:00+00:00",
                "last_message_at": "2026-02-10T00:00:00+00:00",
            },
            "export_time_card": {
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-02-01T00:00:00+00:00"
                if late_card and rank == 16 else "2026-01-02T00:00:00+00:00",
                "v2_data": {"characters": [{"id": f"char-{rank}", "name": name}]},
            },
        }
        (folder / "story-cards.json").write_text(json.dumps(card), encoding="utf-8")
        (folder / "runtime-context.json").write_text(json.dumps({
            "rank": rank, "story_id": f"world-{rank}",
        }), encoding="utf-8")
    for path, n in (*GOLD, OLD_TEST):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as stream:
            for i in range(n):
                content = "测试角色16曾经登场" if historical_name and i == 0 else "老故事中的其他人"
                stream.write(json.dumps({
                    "messages": [{"role": "user", "content": content}]
                }, ensure_ascii=False) + "\n")


class WorldAliasScreenTests(unittest.TestCase):
    def test_baseline_keeps_isolation_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture(Path(tmp))
            result = scan(Path(tmp))
            self.assertEqual(result["historic_rows_scanned"], 215)
            self.assertEqual(result["final_heldout_cases"], 0)
            self.assertEqual(result["status"], "AUTOMATED_CANDIDATE_SCREEN_DONE__MANUAL_WORLD_ISOLATION_PENDING")
            self.assertEqual(result["same_character_id_world_groups"], [])

    def test_duplicate_name_gets_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture(Path(tmp), common_name=True)
            result = scan(Path(tmp))
            self.assertIn([16, 17], result["same_name_world_groups"])

    def test_potential_historical_mention_gets_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture(Path(tmp), historical_name=True)
            result = scan(Path(tmp))
            self.assertEqual(result["historical_rows_with_name_mentions_by_world"]["16"], 3)

    def test_timepoint_card_change_flags_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture(Path(tmp), late_card=True)
            result = scan(Path(tmp))
            self.assertTrue(result["worlds"][0]["export_card_updated_after_first_message"])
            self.assertEqual(result["worlds"][0]["timepoint_card_provenance"], "PER_CASE_REQUIRED")

    def test_missing_historic_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture(Path(tmp))
            (Path(tmp) / GOLD[0][0]).unlink()
            with self.assertRaises(FileNotFoundError):
                scan(Path(tmp))

    def test_duplicate_character_id_flags_cross_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            p = root / SOURCE / "17-example" / "story-cards.json"
            card = json.loads(p.read_text(encoding="utf-8"))
            card["export_time_card"]["v2_data"]["characters"][0]["id"] = "char-16"
            p.write_text(json.dumps(card), encoding="utf-8")
            self.assertIn([16, 17], scan(root)["same_character_id_world_groups"])


if __name__ == "__main__":
    unittest.main()

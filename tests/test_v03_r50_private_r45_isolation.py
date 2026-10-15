"""Private R45 checks use synthetic fixtures only; no frozen original files needed."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_private_r45_isolation import SOURCE, file_hash, verify


def setup(repo: Path, *, id_clash=False, text_clash=False):
    repeated = "".join(chr(0x4E00 + i) for i in range(180))
    for rank in range(16, 21):
        folder = repo / SOURCE / f"{rank}-case"
        folder.mkdir(parents=True)
        (folder / "age-review.json").write_text(
            json.dumps({"rank": rank, "story_id": f"world-{rank}"}), encoding="utf-8")
        text = ("!" * 5 + repeated + "!" * 5) if text_clash and rank == 16 else f"新消息{rank}" * 20
        (folder / (folder.name + ".jsonl")).write_text(
            json.dumps({"rank": rank, "messages": [{"role": "user", "content": text}]},
                       ensure_ascii=False) + "\n", encoding="utf-8"
        )
    paths = {}
    expectations = {}
    for split, count in (("train", 49), ("validation", 15)):
        p = repo / (split + ".jsonl")
        rows = []
        for n in range(count):
            story = "world-16" if id_clash and split == "train" and n == 0 else f"historic-{split}"
            content = ("%" * 9 + repeated + "%" * 6) if text_clash and n == 0 else ("历史无交叉" * 27)
            rows.append({
                "id": f"{split}-{n}",
                "metadata": {"source_story_id": story},
                "messages": [{"role": "user", "content": content}],
            })
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                     encoding="utf-8")
        paths[split] = p
        expectations[split] = {"count": count, "sha256": file_hash(p)}
    return paths, expectations


class PrivateR45Tests(unittest.TestCase):
    def test_good_fixture_produces_only_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files, hashes = setup(root)
            report = verify(root, files["train"], files["validation"], expected=hashes)
            self.assertEqual(report["verified_r45_counts"], {"train": 49, "validation": 15})
            self.assertEqual(report["status"],
                             "R45_FROZEN_49_15_EXACT_SCREEN_PASS__SEMANTIC_REVIEW_PENDING")
            self.assertNotIn("world-16", json.dumps(report))

    def test_hash_guard_prevents_changed_training_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files, hashes = setup(root)
            files["train"].write_text("modified", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                verify(root, files["train"], files["validation"], expected=hashes)

    def test_world_id_overlap_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files, hashes = setup(root, id_clash=True)
            with self.assertRaisesRegex(ValueError, "overlap"):
                verify(root, files["train"], files["validation"], expected=hashes)

    def test_shifted_target_excerpt_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files, hashes = setup(root, text_clash=True)
            with self.assertRaisesRegex(ValueError, "overlap"):
                verify(root, files["train"], files["validation"], expected=hashes)

    def test_missing_metadata_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files, hashes = setup(root)
            p = files["validation"]
            records = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()]
            records[0]["metadata"] = {}
            p.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
            hashes["validation"]["sha256"] = file_hash(p)
            with self.assertRaisesRegex(ValueError, "source_story_id"):
                verify(root, files["train"], files["validation"], expected=hashes)


if __name__ == "__main__":
    unittest.main()

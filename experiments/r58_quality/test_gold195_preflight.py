import json
from pathlib import Path
import tempfile
import unittest

from gold195_preflight import COHORTS, inventory, scan


class Tests(unittest.TestCase):
    def row(self, story, roles=("assistant", "user", "assistant")):
        return {
            "id": "PRIVATE_CANARY_DO_NOT_EMIT",
            "messages": [{"role": role, "content": "PRIVATE_CANARY_DO_NOT_EMIT"} for role in roles],
            "metadata": {"story_id": story, "target_sha256_utf8": "f" * 64, "split": None},
        }

    def test_counts_no_private_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _, relative, count in COHORTS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("".join(json.dumps(self.row("secret-world")) + "\n" for _ in range(count)), encoding="utf-8")
            result = inventory(root)
            self.assertEqual(result["total_records"], 195)
            self.assertEqual(result["cohorts"]["gold87"]["structural_counts"]["needs_system_derivation"], 87)
            self.assertEqual(result["training_admitted"], 0)
            self.assertNotIn("PRIVATE_CANARY", json.dumps(result))
            self.assertNotIn("secret-world", json.dumps(result))

    def test_missing_file_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(inventory(Path(tmp))["status"], "INPUT_MISSING_OR_UNSAFE__HOLD")

    def test_missing_world_id_count_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jsonl"
            row = self.row("private")
            del row["metadata"]["story_id"]
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.assertEqual(scan(path)["structural_counts"]["world_id_missing"], 1)

    def test_role_anomaly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jsonl"
            path.write_text(json.dumps(self.row("private", ("system", "user", "user"))) + "\n", encoding="utf-8")
            self.assertEqual(scan(path)["structural_counts"]["non_alternating_roles"], 1)


if __name__ == "__main__":
    unittest.main()

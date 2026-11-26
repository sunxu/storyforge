import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from gold195_target_source import FROM, INDEX108, audit


class TargetSourceTests(unittest.TestCase):
    def setup_data(self, root, *, break_hash=False, break_role=False):
        idx = root / INDEX108
        idx.parent.mkdir(parents=True, exist_ok=True)
        with idx.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["candidate_id", "target_sha256", "story_id"])
            writer.writeheader()
            for cohort, (relative, n) in FROM.items():
                dest = root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("w", encoding="utf-8") as out:
                    for i in range(n):
                        rid = f"{cohort}-{i}"
                        target = "SYNTHETIC_PRIVATE_CANARY"
                        messages = [
                            {"role":"assistant", "content":"historical"},
                            {"role":"user", "content":"current"},
                            {"role":"assistant", "content":target},
                        ]
                        if break_role and i == 0 and cohort == "gold87":
                            messages[-2]["role"] = "assistant"
                        h = hashlib.sha256(target.encode()).hexdigest()
                        if break_hash and i == 0 and cohort == "gold108":
                            h = "0" * 64
                        meta = {"story_id": "private_uuid", "target_sha256_utf8": h}
                        if cohort == "gold108":
                            writer.writerow({"candidate_id":rid, "target_sha256":h, "story_id":"private_uuid"})
                            meta = {}
                        out.write(json.dumps({"id":rid, "metadata":meta, "messages":messages})+"\n")

    def test_195_matches_no_leak(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.setup_data(root)
            result = audit(root)
            self.assertEqual(result["records_checked"], 195)
            self.assertTrue(result["all_target_hashes_verified"])
            self.assertEqual(result["quality_v1_admitted"], 0)
            encoded = json.dumps(result)
            self.assertNotIn("SYNTHETIC_PRIVATE_CANARY", encoded)
            self.assertNotIn("private_uuid", encoded)

    def test_tampered_hash_holds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.setup_data(root, break_hash=True)
            self.assertEqual(audit(root)["status"], "SOURCE_TARGET_PREFLIGHT_HOLD")

    def test_bad_user_target_holds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.setup_data(root, break_role=True)
            self.assertEqual(audit(root)["status"], "SOURCE_TARGET_PREFLIGHT_HOLD")

    def test_missing_index_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                audit(Path(td))


if __name__ == "__main__":
    unittest.main()

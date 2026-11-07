"""Synthetic-only tests for Gold192 input-evidence seed stage."""
import hashlib
import json
import unittest

from experiments.r58_quality.r60_model_input_evidence_seed import seed


class TestModelInputEvidenceSeed(unittest.TestCase):
    def inputs(self, count=192):
        rows = [{"case_id": f"synthetic-{i}", "source_status": "EXACT_MATCH"}
                for i in range(count)]
        raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
        safe = {
            "schema": "r60_gold192_supabase_extract_v3_safe_v1",
            "status": "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED",
            "gold192": 192,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "private_values_emitted": False,
            "artifacts": {
                "R60_SOURCE_LOCATORS_192.jsonl": {
                    "records": 192,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                },
            },
        }
        return raw, json.dumps(safe).encode()

    def test_starts_all_unknown_and_no_admission(self):
        private, receipt = seed(*self.inputs())
        rows = [json.loads(line) for line in private.splitlines()]
        self.assertEqual(len(rows), 192)
        self.assertEqual(receipt["input_evidence_class_counts"]["UNKNOWN_NOT_REVIEWED"], 192)
        self.assertIsNone(receipt["input_evidence_class_counts"]["A"])
        self.assertFalse(receipt["evidence_review_started"])
        self.assertEqual(receipt["quality_v1_admitted"], 0)
        self.assertEqual(receipt["private_slots_sha256"], hashlib.sha256(private).hexdigest())
        self.assertNotIn("synthetic-0", json.dumps(receipt))

    def test_rejects_source_tampering(self):
        raw, safe = self.inputs()
        with self.assertRaisesRegex(ValueError, "SOURCE_PIN_OR_COUNT_INVALID"):
            seed(raw.replace(b"synthetic-0", b"modified-00"), safe)

    def test_rejects_duplicate_identity(self):
        raw, safe = self.inputs()
        rows = [json.loads(line) for line in raw.splitlines()]
        rows[1]["case_id"] = rows[0]["case_id"]
        altered = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
        receipt = json.loads(safe)
        receipt["artifacts"]["R60_SOURCE_LOCATORS_192.jsonl"]["sha256"] = (
            hashlib.sha256(altered).hexdigest()
        )
        with self.assertRaisesRegex(ValueError, "CASE_IDS_NOT_UNIQUE"):
            seed(altered, json.dumps(receipt).encode())

    def test_rejects_unapproved_safe(self):
        raw, safe = self.inputs()
        receipt = json.loads(safe)
        receipt["training_authorized"] = True
        with self.assertRaisesRegex(ValueError, "SOURCE_PIN_OR_COUNT_INVALID"):
            seed(raw, json.dumps(receipt).encode())


if __name__ == "__main__":
    unittest.main()

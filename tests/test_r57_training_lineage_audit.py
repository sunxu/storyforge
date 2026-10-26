"""Synthetic-only R57 G2 exposure audit tests; contains no private story data."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "r57_training_lineage_audit.py"
spec = importlib.util.spec_from_file_location("r57_training_lineage_audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def digest(tag):
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def row(tag, component="component-test"):
    return {
        "target_sha256": digest("target:" + tag),
        "input_sha256": digest("input:" + tag),
        "history_sha256": digest("history:" + tag),
        "world_component_token": component,
    }


def collection(name, rows):
    return {"id": name, "source_file_sha256": digest("file:" + name), "rows": rows}


def packet(sources=None):
    return {
        "schema": mod.FORMAT,
        "no_protected_evaluation_accessed": True,
        "training_authorized": False,
        "sources": [] if sources is None else sources,
    }


def full_synthetic_index():
    sources = []
    for name, count in mod.EXPECTED.items():
        records = [row(f"{name}:{i}", component=f"component-{name}-{i//10}") for i in range(count)]
        sources.append(collection(name, records))
    by_name = {item["id"]: item for item in sources}
    r46_train = by_name["R46_TRAIN"]["rows"]
    r46_val = by_name["R46_VALIDATION"]["rows"]
    r54 = by_name["R54_TRAIN"]["rows"]
    for i in range(14):
        r54[i]["target_sha256"] = r46_train[i]["target_sha256"]
    for i in range(9):
        r54[i+14]["target_sha256"] = r46_val[i]["target_sha256"]
    return packet(sources)


class TestR57Lineage(unittest.TestCase):
    def hold(self, value, *, full=False):
        with self.assertRaises(mod.AuditHold):
            mod.audit(value, full=full)

    def test_empty_draft_is_not_audit_pass(self):
        result = mod.audit(packet())
        self.assertIn("DRAFT", result["status"])
        self.assertEqual(result["collections_seen"], 0)

    def test_empty_full_is_blocked(self):
        self.hold(packet(), full=True)

    def test_only_whitelisted_source_collections(self):
        x = collection("R50", [row("x")])
        self.hold(packet([x]))

    def test_rejects_claimed_protected_access(self):
        x = packet()
        x["no_protected_evaluation_accessed"] = False
        self.hold(x)

    def test_rejects_training_authorization(self):
        x = packet()
        x["training_authorized"] = True
        self.hold(x)

    def test_rejects_unknown_narrative_fields(self):
        x = row("x")
        x["story_text"] = "fake example"
        self.hold(packet([collection("GOLD87", [x])]))

    def test_rejects_invalid_hash(self):
        x = row("x")
        x["history_sha256"] = "0" * 63
        self.hold(packet([collection("GOLD87", [x])]))

    def test_rejects_duplicate_source_id(self):
        self.hold(packet([collection("GOLD87", []), collection("GOLD87", [])]))

    def test_same_target_overlap_reported_as_count_only(self):
        x = row("same")
        result = mod.audit(packet([
            collection("GOLD87", [x]),
            collection("R46_TRAIN", [copy.deepcopy(x)]),
        ]))
        pair = result["source_pairs"][0]
        self.assertEqual(pair["exact_target_matches"], 1)
        self.assertEqual(pair["exact_input_matches"], 1)
        self.assertEqual(pair["declared_world_component_overlap"], 1)
        output = json.dumps(result)
        self.assertNotIn(x["target_sha256"], output)
        self.assertNotIn("component-test", output)

    def test_within_source_duplicates_are_reported(self):
        x = row("same")
        result = mod.audit(packet([collection("GOLD87", [x, copy.deepcopy(x)])]))
        self.assertEqual(result["duplicate_exact_target_rows_within_source"]["GOLD87"], 1)

    def test_frozen_14_9_8_synthetic_replay(self):
        result = mod.audit(full_synthetic_index(), full=True)
        self.assertEqual(result["distinct_gold_target_hashes_seen"], 195)
        receipt = result["historical_r46_r54_receipt_replay"]
        self.assertEqual(
            [receipt["r54_train_in_r46_train"],
             receipt["r54_train_in_r46_validation"],
             receipt["r54_train_not_in_r46_splits"]],
            [14, 9, 8],
        )
        self.assertTrue(receipt["historical_receipt_14_9_8_agrees"])
        self.assertTrue(result["source_bytes_independently_rehashed"] is False)
        self.assertEqual(result["v04_samples_admitted"], 0)

    def test_full_replay_detects_changed_historical_overlap(self):
        x = full_synthetic_index()
        by_name = {s["id"]: s for s in x["sources"]}
        by_name["R54_TRAIN"]["rows"][0]["target_sha256"] = digest("tampered")
        self.hold(x, full=True)

    def test_full_replay_detects_missing_counts(self):
        x = full_synthetic_index()
        x["sources"][0]["rows"].pop()
        self.hold(x, full=True)

    def test_full_replay_detects_gold_duplicates(self):
        x = full_synthetic_index()
        a = {s["id"]: s for s in x["sources"]}
        a["GOLD108"]["rows"][0]["target_sha256"] = a["GOLD87"]["rows"][0]["target_sha256"]
        self.hold(x, full=True)

    def test_cli_no_overwrite_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original = base / "approved_index.json"
            original.write_text(json.dumps(packet()), encoding="utf-8")
            before = original.read_bytes()
            receipt = base / "receipt.json"
            receipt.write_text("SENTINEL", encoding="utf-8")
            p = subprocess.run([
                sys.executable, str(SCRIPT), "--private-index", str(original),
                "--safe-out", str(receipt),
            ], capture_output=True, text=True, check=False)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "SENTINEL")
            self.assertEqual(original.read_bytes(), before)

    def test_cli_rejects_named_protected_path_without_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "r50_fake.json"
            protected.write_text("SENTINEL NOT JSON", encoding="utf-8")
            p = subprocess.run([
                sys.executable, str(SCRIPT), "--private-index", str(protected),
            ], capture_output=True, text=True, check=False)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("protected data path", p.stderr)
            self.assertNotIn("SENTINEL", p.stderr)


if __name__ == "__main__":
    unittest.main()

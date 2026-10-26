"""CPU synthetic-only checks for metadata-free byte-pinned Trainer exact comparison."""

import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "r57_trainer_exact_replay", ROOT / "scripts" / "r57_trainer_exact_replay.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def row(name, *, source="R46_TRAIN", metadata=True, alternate=False):
    """One fully fictitious two-turn dialogue."""
    md = {}
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    if source == "GOLD87":
        md = {"story_id": "fictional", "target_sha256_utf8": digest}
    elif source == "GOLD108":
        md = ({"source_story_id": "fictional", "target_content_sha256": digest}
              if alternate else {"story_id": "fictional", "target_sha256": digest})
    elif metadata:
        md = {"source_story_id": "fictional"}
    data = {"messages": [
        {"role": "user", "content": "synthetic prompt"},
        {"role": "assistant", "content": name, "loss": True},
    ]}
    if metadata:
        data["metadata"] = md
    return data


def archive(name, labels, *, metadata=True):
    records = []
    for i, label in enumerate(labels):
        item = row(label, source=name, metadata=metadata,
                   alternate=(name == "GOLD108" and i >= 105))
        if name == "GOLD108" and 90 <= i < 105:
            digest = item["metadata"].pop("target_sha256")
            item["metadata"]["target_sha256_utf8"] = digest
        records.append(json.dumps(item) + "\n")
    return "".join(records).encode("utf-8")


def fixture_all():
    source = mod.frozen.SOURCE_PATHS
    data = {}
    for group, (_, _, count) in source.items():
        data[group] = [f"{group}:target-{i}" for i in range(count)]
    for i in range(14):
        data["R54_TRAIN"][i] = data["R46_TRAIN"][i]
    for i in range(9):
        data["R54_TRAIN"][i + 14] = data["R46_VALIDATION"][i]
    return {
        name: archive(name, rows, metadata=name.startswith("GOLD"))
        for name, rows in data.items()
    }


class TestExactReplay(unittest.TestCase):
    def test_partial_four_collections_counts_and_gold_status(self):
        data = fixture_all()
        subset = {k: data[k] for k in mod.GIT_SOURCES}
        out = mod.replay_payloads(subset)
        self.assertEqual(out["gold_distinct_target_count"], 195)
        self.assertEqual(len(out["exact_pairwise"]), 6)
        self.assertEqual([v["rows_without_metadata"] for v in
                          out["source_metadata_coverage"].values()], [0, 0, 65, 15])
        self.assertIn("PARTIAL", out["status"])
        self.assertFalse(out["true_world_component_isolation_verified"])
        self.assertEqual(out["v04_admitted"], 0)

    def test_full_eight_source_replays_14_9_8_without_trainer_metadata(self):
        out = mod.replay_payloads(fixture_all(), require_all=True)
        self.assertEqual(out["historical_r46_r54"], {
            "r54_train_in_r46_train": 14,
            "r54_train_in_r46_validation": 9,
            "r54_train_not_in_r46": 8,
        })
        self.assertEqual(out["source_metadata_coverage"]["R54_TRAIN"]["rows_without_metadata"], 31)
        self.assertIn("WORLD_ALIAS_HOLD", out["status"])
        self.assertEqual(out["gold_exact_target_seen_in_previous_train"], 0)

    def test_no_secret_or_target_hash_in_report(self):
        data = fixture_all()
        out = mod.replay_payloads(data, require_all=True)
        report = json.dumps(out)
        self.assertNotIn("R46_TRAIN:target-0", report)
        self.assertNotIn(hashlib.sha256(b"R46_TRAIN:target-0").hexdigest(), report)
        self.assertNotIn("synthetic prompt", report)

    def test_full_without_eight_sources_denied(self):
        data = fixture_all()
        data.pop("R54_VALIDATION")
        with self.assertRaises(mod.ExactReplayHold):
            mod.replay_payloads(data, require_all=True)

    def test_historical_replay_mismatch_denied(self):
        data = fixture_all()
        originals = [f"new-uncollided:{i}" for i in range(31)]
        data["R54_TRAIN"] = archive("R54_TRAIN", originals, metadata=False)
        with self.assertRaises(mod.ExactReplayHold):
            mod.replay_payloads(data, require_all=True)

    def test_wrong_gold108_digest_denied(self):
        data = fixture_all()
        rows = [json.loads(line) for line in data["GOLD108"].splitlines()]
        rows[-1]["metadata"]["target_content_sha256"] = "0" * 64
        data["GOLD108"] = ("".join(json.dumps(x) + "\n" for x in rows)).encode()
        with self.assertRaises(mod.ExactReplayHold):
            mod.replay_payloads(data)

    def test_missing_or_ambiguous_gold108_schema_denied(self):
        data = fixture_all()
        rows = [json.loads(line) for line in data["GOLD108"].splitlines()]
        rows[-1]["metadata"]["story_id"] = "another-world"
        data["GOLD108"] = ("".join(json.dumps(x) + "\n" for x in rows)).encode()
        with self.assertRaises(mod.ExactReplayHold):
            mod.replay_payloads(data)

    def test_disallow_metadata_only_source_without_messages(self):
        data = fixture_all()
        data["R46_TRAIN"] = (json.dumps({"metadata": {}}) + "\n").encode() * 49
        with self.assertRaises(mod.frozen.ExportHold):
            mod.replay_payloads(data)

    def test_duplicate_exact_target_within_source_denied(self):
        data = fixture_all()
        data["R46_TRAIN"] = archive("R46_TRAIN", ["same"] * 49, metadata=False)
        with self.assertRaises(mod.ExactReplayHold):
            mod.replay_payloads(data)

    def test_frozen_compiled_trainer_pin_rejects_fabricated_bytes(self):
        with self.assertRaises(mod.ExactReplayHold):
            mod.verify_source_pin("R46_TRAIN", b'{"messages": []}\n')

    def test_frozen_git_blob_pin_rejects_fabricated_bytes(self):
        with self.assertRaises(mod.ExactReplayHold):
            mod.verify_source_pin("GOLD108", b'{"messages": []}\n')

    def test_mixed_105_and_3_distribution_frozen(self):
        data = fixture_all()
        original = [json.loads(item) for item in data["GOLD108"].splitlines()]
        original[104]["metadata"] = {
            "source_story_id": "fictional",
            "target_content_sha256": hashlib.sha256(
                original[104]["messages"][-1]["content"].encode()
            ).hexdigest(),
        }
        data["GOLD108"] = ("".join(json.dumps(x) + "\n" for x in original)).encode()
        with self.assertRaises(mod.ExactReplayHold):
            mod.replay_payloads(data)

    def test_v01_missing_metadata_supported_but_not_world_certified(self):
        data = fixture_all()
        partial = {"V01_TRAIN": data["V01_TRAIN"]}
        result = mod.replay_payloads(partial)
        self.assertEqual(result["source_metadata_coverage"]["V01_TRAIN"]["rows_without_metadata"], 65)
        self.assertFalse(result["true_world_component_isolation_verified"])


if __name__ == "__main__":
    unittest.main()

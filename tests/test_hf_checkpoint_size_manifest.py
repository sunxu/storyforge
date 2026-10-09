"""Offline, no-GPU, no-network tests for v0.1 checkpoint size auditing."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hf_checkpoint_size_manifest.py"
spec = importlib.util.spec_from_file_location("hf_checkpoint_size_manifest", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DummyFS:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def ls(self, path, *, detail, refresh):
        self.calls.append((path, detail, refresh))
        return self.data


class TestCheckpointSizeManifest(unittest.TestCase):
    HASHES = {
        "adapter_model.safetensors": "a" * 64,
        "adapter_config.json": "b" * 64,
    }

    def test_parse_archived_hashes(self):
        fence = chr(96) * 3
        source = (
            f"{module.SECTION_HEADING}\n\n{fence}text\n"
            f"{'a' * 64}  ./adapter_model.safetensors\n"
            f"{'b' * 64}  ./adapter_config.json\n{fence}\n"
        )
        self.assertEqual(module.parse_archived_hashes(source), self.HASHES)

    def test_metadata_only_and_file_size(self):
        fs = DummyFS([
            {"name": "buckets/adradar/storyforge-training/checkpoint-9/adapter_model.safetensors", "type": "file", "size": 5600000000},
            {"name": "buckets/adradar/storyforge-training/checkpoint-9/adapter_config.json", "type": "file", "size": 2048},
        ])
        result = module.build_report(fs, self.HASHES, observed_at="2026-10-09T10:00:00+00:00")
        self.assertEqual(result["total_size_bytes"], 5600002048)
        self.assertFalse(result["sha256_recomputed_by_this_script"])
        self.assertEqual(fs.calls, [(module.CHECKPOINT_URI, True, True)])
        self.assertEqual(result["file_count"], 2)

    def test_fail_closed_on_missing_or_unexpected(self):
        items = [{"name": "foo/adapter_config.json", "type": "file", "size": 3}]
        with self.assertRaisesRegex(ValueError, "missing="):
            module.build_report(DummyFS(items), self.HASHES, observed_at="now")
        items.append({"name": "foo/adapter_model.safetensors", "type": "file", "size": 12})
        items.append({"name": "foo/unexpected.txt", "type": "file", "size": 0})
        with self.assertRaisesRegex(ValueError, "unexpected="):
            module.build_report(DummyFS(items), self.HASHES, observed_at="now")

    def test_reject_missing_size_and_duplicate(self):
        invalid = [{"name": "foo/adapter_model.safetensors", "type": "file", "size": None}]
        with self.assertRaisesRegex(ValueError, "byte size"):
            module.build_report(DummyFS(invalid), self.HASHES, observed_at="now")
        duplicate = [{"name": "foo/adapter_model.safetensors", "type": "file", "size": 1}] * 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.build_report(DummyFS(duplicate), self.HASHES, observed_at="now")


if __name__ == "__main__":
    unittest.main()

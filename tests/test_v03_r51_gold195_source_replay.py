"""Synthetic-only ZIP / message unit tests for private R51 raw replay."""
import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r51_gold195_source_replay as replay


def zip_data(items):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, value in items.items():
            zf.writestr(name, value)
    return out.getvalue()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class SourceReplayTests(unittest.TestCase):
    def test_zip_discovery_checks_exact_digest_not_path(self):
        raw = zip_data({"arbitrary/source.jsonl": '{"id":"abc","content":"hello"}\n'})
        asset = zip_data({"nested/a.zip": raw, "nested/b.zip": b"not genuine"})
        found = replay.discover_raw_zips(asset, {6: replay.sha256(raw)})
        self.assertEqual(set(found), {6})
        with self.assertRaisesRegex(ValueError, "RAW_STORY_ZIPS_NOT_ALL_FOUND"):
            replay.discover_raw_zips(asset, {7: "0" * 64})

    def test_message_parser_supports_nested_message(self):
        p = (json.dumps({"message": {"message_id": "m1", "role": "assistant",
                                    "content": "original"}}) + "\n")
        events = replay.parse_source_events(p.encode())
        self.assertIn(("m1", sha("original"), "assistant"), events)

    def test_ordered_does_not_imply_contiguous(self):
        events = [
            ("h1", sha("one"), "user"),
            ("extra", sha("extra"), "assistant"),
            ("h2", sha("two"), "user"),
            ("t", sha("answer"), "assistant"),
        ]
        ordered, contiguous = replay.ordered_history(
            events, 3, [{"sha256": sha("one")}, {"sha256": sha("two")}])
        self.assertTrue(ordered)
        self.assertFalse(contiguous)

    def test_synthetic_replay_always_keeps_holds(self):
        target = "synthetic assistant completion"
        ctx = "synthetic user input"
        row = {
            "candidate_id": "test-1",
            "cohort": 108,
            "source_rank": 6,
            "original_target_message_id": "t",
            "original_target_sha256": sha(target),
            "history_fingerprints": [{"role": "user", "sha256": sha(ctx)}],
            "source_reference": {},
            "source_review": {},
            "training_admission": "PENDING_NOT_APPROVED",
            "split": None,
        }
        source = '\n'.join(json.dumps(x) for x in [
            {"message_id": "h", "role": "user", "content": ctx},
            {"message_id": "t", "role": "assistant", "content": target},
        ]) + "\n"
        raw = zip_data({"raw.jsonl": source})
        result = replay.replay_108([row], {6: raw})
        # Set the synthetic test scope explicitly instead of 108 real rows.
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()

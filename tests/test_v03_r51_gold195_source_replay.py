"""Synthetic-only ZIP / message unit tests for private R51 raw replay."""
import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

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


    def test_safe_schema_probe_never_returns_story_or_message_content(self):
        source = {
            "messages": [
                {"message_id": "highly-sensitive-id",
                 "role": "assistant",
                 "content": {"text": "PRIVATE_SCENE_TEXT"},
                 "secret_field_for_character_name": "PRIVATE_PERSON"}
            ],
            "private_story_name": "PRIVATE_STORY",
        }
        report = replay.safe_shape(source)
        dump = json.dumps(report)
        self.assertIn("messages", dump)
        self.assertIn("message_id", dump)
        self.assertIn("content", dump)
        self.assertNotIn("PRIVATE", dump)
        self.assertNotIn("highly-sensitive-id", dump)
        self.assertNotIn("secret_field_for_character_name", dump)
        self.assertNotIn("private_story_name", dump)


    def test_root_messages_probe_separates_id_and_hash_disagreements(self):
        gold = []
        original_messages = []
        for i in range(108):
            body = f"synthetic-target-{i}"
            gold.append({
                "cohort": 108,
                "source_rank": 6,
                "source_reference": {},
                "original_target_message_id": f"expected-{i}",
                "original_target_sha256": sha(body),
            })
            actual_id = f"expected-{i}" if i < 104 else f"alternate-{i}"
            actual_body = body if i < 100 or i >= 104 else f"edited-{i}"
            original_messages.append({
                "id": actual_id, "content": actual_body,
                "role": "assistant", "turn_index": i,
            })
        payload = (json.dumps({"messages": original_messages}) + "\n").encode()
        with patch.object(replay, "read_private_v2", return_value=gold), \
             patch.object(replay, "choose_source_jsonl", return_value=payload):
            result = replay.probe_original_target_matching(
                Path("."), Path("unused-private-v2"), {6: b"synthetic-source"})
        self.assertEqual(result["summary"]["root_messages_id_hit"], 104)
        self.assertEqual(result["summary"]["root_messages_sha_hit"], 104)
        self.assertEqual(result["summary"]["root_messages_id_and_sha_hit"], 100)
        self.assertEqual(result["summary"]["recursive_parser_id_and_sha_hit"], 100)
        self.assertEqual(result["summary"]["candidates"], 108)
        self.assertEqual(result["training_admitted"], 0)
        public = json.dumps(result)
        self.assertNotIn("synthetic-target", public)
        self.assertNotIn("expected-0", public)


    def test_root_message_replay_ignores_recursive_metadata_wrappers(self):
        events = []
        rows = []
        for i in range(108):
            target = f"synthetic answer {i}"
            user = f"synthetic user {i}"
            events += [
                {"id": f"u-{i}", "role": "user", "content": user,
                 "turn_index": i * 2, "metadata": {"content": "metadata only"}},
                {"id": f"a-{i}", "role": "assistant", "content": target,
                 "turn_index": i * 2 + 1, "metadata": {
                     "content": "nested unrelated text", "id": f"a-{i}"}},
            ]
            rows.append({
                "candidate_id": f"synthetic-{i}",
                "cohort": 108, "source_rank": 6,
                "original_target_message_id": f"a-{i}",
                "original_target_sha256": sha(target),
                "history_fingerprints": [{"role": "user", "sha256": sha(user)}],
                "source_reference": {}, "source_review": {},
                "holds": ["CONTENT_OR_RIGHTS_HOLD",
                          "SOURCE_POINTER_RECONCILIATION_HOLD"],
                "training_admission": "PENDING_NOT_APPROVED", "split": None,
            })
        root = (json.dumps({"messages": events}) + "\n").encode()
        self.assertGreater(len(replay.parse_source_events(root)),
                           len(replay.parse_root_source_events(root)))
        report = replay.replay_108(rows, {6: zip_data({"source.jsonl": root})})
        self.assertEqual(report["gold108_target_unique_id_sha_matches"], 108)
        self.assertEqual(report["gold108_history_immediately_contiguous"], 108)
        self.assertEqual(report["gold108_history_source_turns_consecutive"], 108)
        self.assertEqual(report[
            "previous_22_pointer_gaps_original_indices_recovered"], 108)
        self.assertTrue(all(
            r["source_review"]["source_pointer_verified"] ==
            "ROOT_MESSAGES_INDEX_ID_SHA_ROLE_VERIFIED" for r in rows))
        self.assertTrue(all(
            "SOURCE_POINTER_RECONCILIATION_HOLD" in r["holds"] and
            r["training_admission"] == "PENDING_NOT_APPROVED" and
            r["split"] is None for r in rows))

    def test_original_root_parser_rejects_multiple_snapshots(self):
        source = {"messages": [{"id": "1", "role": "user",
                                "content": "alpha", "turn_index": 0}]}
        raw = (json.dumps(source) + "\n" + json.dumps(source) + "\n").encode()
        with self.assertRaisesRegex(ValueError, "MULTIPLE_ROOT_SOURCE_RECORDS_HOLD"):
            replay.parse_root_source_events(raw)

    def test_ordered_history_must_match_role_and_actual_suffix(self):
        events = [
            ("u", sha("same"), "user", 10),
            ("a", sha("same"), "assistant", 11),
            ("t", sha("answer"), "assistant", 12),
        ]
        ordered, contiguous = replay.ordered_history(
            events, 2, [{"role": "user", "sha256": sha("same")}])
        self.assertTrue(ordered)
        self.assertFalse(contiguous)

    def test_synthetic_replay_always_keeps_holds(self):
        events = []
        rows = []
        for i in range(108):
            target = f"synthetic completion {i}"
            ctx = f"synthetic user input {i}"
            events.extend([
                {"message_id": f"h-{i}", "role": "user", "content": ctx},
                {"message_id": f"t-{i}", "role": "assistant", "content": target},
            ])
            rows.append({
                "candidate_id": f"test-{i}",
                "cohort": 108,
                "source_rank": 6,
                "original_target_message_id": f"t-{i}",
                "original_target_sha256": sha(target),
                "history_fingerprints": [{"role": "user", "sha256": sha(ctx)}],
                "source_reference": {},
                "source_review": {},
                "training_admission": "PENDING_NOT_APPROVED",
                "split": None,
            })
        source = "\n".join(json.dumps(x) for x in events) + "\n"
        raw = zip_data({"raw.jsonl": source})
        result = replay.replay_108(rows, {6: raw})
        self.assertEqual(result["gold108_target_unique_id_sha_matches"], 108)
        self.assertEqual(result["gold108_history_sha_in_original_order"], 108)
        self.assertEqual(result["gold108_history_immediately_contiguous"], 108)
        self.assertTrue(all(r["training_admission"] == "PENDING_NOT_APPROVED"
                            and r["split"] is None for r in rows))
        self.assertTrue(all(r["source_archive_replay"] ==
                            "RAW_TARGET_ID_AND_SHA_PASS" for r in rows))

if __name__ == "__main__":
    unittest.main()

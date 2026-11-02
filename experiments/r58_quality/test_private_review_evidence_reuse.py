import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from private_review_evidence_reuse import (
    DEFAULT_MANIFEST_SCHEMA,
    DEFAULT_TASK_SCHEMA,
    ReuseInputError,
    audit,
    canonical_json,
    compare,
    _strict_json_loads,
)


def make_task(case_id, input_marker="same-input", target="same-target"):
    messages = [{"role": "system", "content": input_marker}]
    return {
        "schema": DEFAULT_TASK_SCHEMA,
        "case_id": case_id,
        "messages": messages,
        "target_text": target,
        "input_messages_sha256": hashlib.sha256(canonical_json(messages)).hexdigest(),
        "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "review_results": [],
        "review_status": "UNREVIEWED",
        "quality_v1_admitted": False,
        "training_authorized": False,
    }


def make_manifest(tasks):
    cases = []
    for index, task in enumerate(tasks, 1):
        cases.append({
            "label": f"review-{index}",
            "case_id": task["case_id"],
            "input_messages_sha256": task["input_messages_sha256"],
            "target_sha256": task["target_sha256"],
            "target_text": task["target_text"],
        })
    return {
        "schema": DEFAULT_MANIFEST_SCHEMA,
        "quality_approved": False,
        "cases": cases,
    }


class PrivateReviewReuseTests(unittest.TestCase):
    def test_variable_case_counts_exact_match(self):
        for count in (1, 2, 3, 17):
            with self.subTest(count=count):
                tasks = [make_task(f"case-{i}", target=f"target-{i}") for i in range(count)]
                result = compare(make_manifest(tasks), tasks)
                self.assertEqual(result["status"], "EXACT_REUSE_MATCH__NO_QUALITY_ADMISSION")
                self.assertEqual(result["historical_cases_checked"], count)
                self.assertEqual(result["exact_matches"], count)
                self.assertEqual(result["quality_v1_admitted"], 0)
                self.assertFalse(result["training_authorized"])

    def test_input_or_target_change_holds_only_affected_case(self):
        original = [make_task("one"), make_task("two", target="target-two")]
        changed = [
            make_task("one", input_marker="changed"),
            make_task("two", target="changed-target"),
        ]
        result = compare(make_manifest(original), changed)
        self.assertEqual(result["status"], "NO_EXACT_REUSE_MATCH__HOLD")
        self.assertEqual(result["case_states"], {
            "INPUT_MESSAGES_HASH_MISMATCH": 1,
            "TARGET_HASH_MISMATCH": 1,
        })

    def test_both_hash_mismatches_are_reported_together(self):
        original = [make_task("one")]
        changed = [make_task("one", input_marker="changed", target="changed")]
        result = compare(make_manifest(original), changed)
        self.assertEqual(result["case_states"], {
            "INPUT_AND_TARGET_HASH_MISMATCH": 1,
        })

    def test_duplicate_json_object_keys_are_rejected(self):
        with self.assertRaisesRegex(ReuseInputError, "JSON_DUPLICATE_KEY"):
            _strict_json_loads('{"case_id":"first","case_id":"second"}')

    def test_partial_match_does_not_discard_exact_case(self):
        original = [make_task("one"), make_task("two")]
        changed = [make_task("one"), make_task("two", target="new")]
        result = compare(make_manifest(original), changed)
        self.assertEqual(result["status"], "PARTIAL_REUSE_MATCH__MISMATCHES_HOLD")
        self.assertEqual(result["exact_matches"], 1)
        self.assertEqual(result["mismatches"], 1)

    def test_case_id_missing_and_extra_current_tasks(self):
        historical = [make_task("old")]
        current = [make_task("new"), make_task("extra")]
        result = compare(make_manifest(historical), current)
        self.assertEqual(result["case_states"], {"CASE_ID_NOT_FOUND": 1})
        self.assertEqual(result["unmatched_current_tasks"], 2)

    def test_duplicate_manifest_case_id_rejected(self):
        task = make_task("dup")
        manifest = make_manifest([task, task])
        with self.assertRaisesRegex(ReuseInputError, "MANIFEST_CASE_ID_DUPLICATE"):
            compare(manifest, [task])

    def test_duplicate_current_case_id_rejected(self):
        task = make_task("dup")
        with self.assertRaisesRegex(ReuseInputError, "TASK_CASE_ID_DUPLICATE"):
            compare(make_manifest([task]), [task, task])

    def test_manifest_target_hash_is_recomputed(self):
        task = make_task("one")
        manifest = make_manifest([task])
        manifest["cases"][0]["target_text"] = "tampered"
        with self.assertRaisesRegex(ReuseInputError, "MANIFEST_TARGET_DIGEST_MISMATCH"):
            compare(manifest, [task])

    def test_current_task_input_and_target_hashes_are_recomputed(self):
        task = make_task("one")
        manifest = make_manifest([task])
        bad_input = dict(task, input_messages_sha256="0" * 64)
        with self.assertRaisesRegex(ReuseInputError, "TASK_INPUT_DIGEST_MISMATCH"):
            compare(manifest, [bad_input])
        bad_target = dict(task, target_sha256="0" * 64)
        with self.assertRaisesRegex(ReuseInputError, "TASK_TARGET_DIGEST_MISMATCH"):
            compare(manifest, [bad_target])

    def test_nonempty_review_or_admission_state_rejected(self):
        task = make_task("one")
        with self.assertRaisesRegex(ReuseInputError, "TASK_ALREADY_HAS_REVIEW_RESULTS"):
            compare(make_manifest([task]), [dict(task, review_results=[{"decision": "PASS"}])])
        with self.assertRaisesRegex(ReuseInputError, "TASK_QUALITY_ADMISSION_STATE_INVALID"):
            compare(make_manifest([task]), [dict(task, quality_v1_admitted=True)])

    def test_manifest_must_not_claim_approved(self):
        task = make_task("one")
        with self.assertRaisesRegex(ReuseInputError, "MANIFEST_APPROVAL_STATE_INVALID"):
            compare(dict(make_manifest([task]), quality_approved=True), [task])

    def test_private_file_permissions_and_repo_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            task = make_task("one")
            manifest_path = private / "manifest.json"
            tasks_path = private / "tasks.jsonl"
            manifest_path.write_text(json.dumps(make_manifest([task])))
            tasks_path.write_text(json.dumps(task) + "\n")
            manifest_path.chmod(0o600)
            tasks_path.chmod(0o600)
            result = audit(manifest_path, tasks_path, repo)
            self.assertEqual(result["exact_matches"], 1)
            with self.assertRaisesRegex(
                ReuseInputError, "PRIVATE_FILE_PERMISSIONS_OR_SIZE_INVALID"
            ):
                manifest_path.chmod(0o644)
                audit(manifest_path, tasks_path, repo)
            manifest_path.chmod(0o600)
            with self.assertRaisesRegex(ReuseInputError, "PRIVATE_FILE_INSIDE_REPOSITORY"):
                in_repo = repo / "manifest.json"
                in_repo.write_text(json.dumps(make_manifest([task])))
                in_repo.chmod(0o600)
                audit(in_repo, tasks_path, repo)

    def test_safe_receipt_contains_no_private_values(self):
        task = make_task("SECRET_CASE_ID", input_marker="SECRET_WORLD", target="SECRET_TARGET")
        result = compare(make_manifest([task]), [task])
        serialized = json.dumps(result)
        private_values = (
            "SECRET_CASE_ID", "SECRET_WORLD", "SECRET_TARGET", task["target_sha256"]
        )
        for private_value in private_values:
            self.assertNotIn(private_value, serialized)
        self.assertFalse(result["private_values_emitted"])
        self.assertFalse(result["files_written"])


if __name__ == "__main__":
    unittest.main()

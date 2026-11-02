import hashlib
import unittest

from experiments.r58_quality.r59_gold192_historical_exposure import (
    classify,
    git_blob,
)


class R59HistoricalExposureTest(unittest.TestCase):
    def test_train_validation_test_flags_are_independent(self):
        target = hashlib.sha256(b"target").hexdigest()
        train = {target}
        validation = {hashlib.sha256(b"other").hexdigest()}
        test = {target}
        result = classify(target, train, validation, test)
        self.assertEqual(result["status"], "EXPOSED")
        self.assertTrue(result["train_exposed"])
        self.assertFalse(result["validation_exposed"])
        self.assertTrue(result["test_exposed"])
        self.assertEqual(result["matched_splits"], ["TRAIN", "TEST"])

    def test_not_found_only_after_all_three_sets_checked(self):
        target = hashlib.sha256(b"target").hexdigest()
        result = classify(target, set(), set(), set())
        self.assertEqual(result["status"], "NOT_FOUND_IN_PINNED_HISTORY")
        self.assertEqual(result["matched_splits"], [])

    def test_duplicate_or_missing_split_is_not_silently_classified(self):
        target = hashlib.sha256(b"target").hexdigest()
        result = classify(target, set(), {target}, set())
        self.assertTrue(result["validation_exposed"])
        self.assertFalse(result["train_exposed"])
        self.assertFalse(result["test_exposed"])


    def test_git_blob_uses_nul_byte_header(self):
        raw = b"gold192-test"
        expected = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        ).hexdigest()
        self.assertEqual(git_blob(raw), expected)
if __name__ == "__main__":
    unittest.main()

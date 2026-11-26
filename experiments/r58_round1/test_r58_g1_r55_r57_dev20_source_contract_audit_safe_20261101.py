#!/usr/bin/env python3
"""In-memory synthetic-only tests; no Git repo, PRIVATE data, HF or files."""
import json
import unittest

from r58_g1_r55_r57_dev20_source_contract_audit_safe_20261101 import (
    Hold,
    TEST_SHA256,
    MANIFEST_BLOB,
    PROMPTS_BLOB,
    PINS,
    r55_contract,
    r57_owner_receipt,
    summarize,
)


def fixtures():
    r48 = f'''
CANONICAL_TEST_SHA256 = "{TEST_SHA256}"
def read_gold(source, prompts): return []
'''.encode()
    r55 = f'''
EXPECTED_PROMPTS_BLOB = "{PROMPTS_BLOB}"
EXPECTED_MANIFEST_BLOB = "{MANIFEST_BLOB}"
def load_exact_sources(a):
    check = sha(a.compiled_test) == CANONICAL_TEST_SHA256
    check = validate_prompts(a.prompts, a.manifest)
    check = read_gold(a.compiled_test, check)
    check = check_r47(check)
    check = EXPECTED_PROMPTS_BLOB == EXPECTED_MANIFEST_BLOB
    return check
'''.encode()
    v2 = b'''
def main():
    return legacy.load_exact_sources(a)
'''
    p = {
        "schema": "storyforge-r55-exposed20-pairwise-dev-preregistration-v1",
        "source": {
            "exposed_unique_cases": 20, "worlds": 2,
            "r47_and_r48_same_20": True,
            "fresh_independent_heldout": False,
            "prompts_git_blob_sha1": PROMPTS_BLOB,
            "manifest_git_blob_sha1": MANIFEST_BLOB,
        },
        "review": {"case_count": 20, "not_independent_test": True},
        "promotion": {"r50_sealed": True, "automatically_permitted": False},
    }
    r57 = {
        "schema": "storyforge-r57-bprompt-safe-archive-v1",
        "suite": "EXPOSED_DEV20_NOT_HELDOUT",
        "outcome": "EXPLORATORY_DEV_ONLY_NO_PROMOTION",
        "config": {
            "stories": 2, "pairs": 20, "responses": 40, "reviewers": 3,
            "model_weights_changed": False,
        },
        "serious_selected_subset": {
            "cases": 10, "verdict_slots": 40,
            "unbiased_full20_rate": False,
        },
        "audit": {"independent_original_key_mapping_verified": False},
    }
    return {
        "R48_VALIDATOR": r48,
        "R55_GOLD5_BUILDER": r55,
        "R55_GOLD5_V2_BUILDER": v2,
        "R55_DEV20_PREREG": json.dumps(p).encode(),
        "R57_BPROMPT_SAFE_RECEIPT": json.dumps(r57).encode(),
    }


class TestScopedDev20SourceContracts(unittest.TestCase):
    def test_expected_five_pinned_sources(self):
        self.assertEqual(set(fixtures()), set(PINS))

    def test_success_never_clears_g1(self):
        r = summarize(fixtures())
        self.assertEqual(r["r55_legacy_dev_cases"], 20)
        self.assertEqual(r["r57_bprompt_serious_subset_of_owner_reported_dev20_cases"], 10)
        self.assertFalse(r["r57_private_per_case_source_mapping_independently_replayed"])
        self.assertFalse(r["all_other_r55_r57_dev_and_arbitration_worlds_exhausted"])
        self.assertEqual(r["g1_clearance"], "HOLD")
        self.assertEqual(r["train_admitted"], 0)

    def test_r55_test_digest_changed_holds(self):
        f = fixtures()
        f["R48_VALIDATOR"] = f["R48_VALIDATOR"].replace(TEST_SHA256.encode(), b"0" * 64)
        with self.assertRaises(Hold):
            summarize(f)

    def test_r55_v2_no_original_loader_holds(self):
        f = fixtures()
        f["R55_GOLD5_V2_BUILDER"] = b"def main(): return 1\n"
        with self.assertRaises(Hold):
            summarize(f)

    def test_r55_unpinned_prompt_holds(self):
        f = fixtures()
        p = json.loads(f["R55_DEV20_PREREG"])
        p["source"]["prompts_git_blob_sha1"] = "0" * 40
        f["R55_DEV20_PREREG"] = json.dumps(p).encode()
        with self.assertRaises(Hold):
            summarize(f)

    def test_r55_new_source_worlds_holds(self):
        f = fixtures()
        p = json.loads(f["R55_DEV20_PREREG"])
        p["source"]["worlds"] = 3
        f["R55_DEV20_PREREG"] = json.dumps(p).encode()
        with self.assertRaises(Hold):
            summarize(f)

    def test_r57_dev10_drift_holds(self):
        f = fixtures()
        p = json.loads(f["R57_BPROMPT_SAFE_RECEIPT"])
        p["serious_selected_subset"]["cases"] = 11
        f["R57_BPROMPT_SAFE_RECEIPT"] = json.dumps(p).encode()
        with self.assertRaises(Hold):
            summarize(f)

    def test_r57_receipt_not_independent_source_attestation(self):
        f = fixtures()
        p = json.loads(f["R57_BPROMPT_SAFE_RECEIPT"])
        p["audit"]["independent_original_key_mapping_verified"] = True
        f["R57_BPROMPT_SAFE_RECEIPT"] = json.dumps(p).encode()
        with self.assertRaises(Hold):
            summarize(f)

    def test_unrecognized_extra_source_holds(self):
        f = fixtures()
        f["UNSCOPED_EXTRA_INPUT"] = b"never"
        with self.assertRaises(Hold):
            summarize(f)


if __name__ == "__main__":
    unittest.main()

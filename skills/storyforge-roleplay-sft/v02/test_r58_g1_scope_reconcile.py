"""Only fabricated UUIDs; no protected/real data or training access."""
import hashlib
import json
import stat
import tempfile
import unittest
from pathlib import Path

import r58_g1_scope_reconcile as m


def uid(n):
    return f"00000000-0000-0000-0000-{n:012x}"


def fixture():
    candidates = [uid(n) for n in range(1, 6)]
    ledger = {
        "schema": m.LEDGER_SCHEMA,
        "owner_world_identity_policy": "OWNER_ATTESTED_ROLEPLAY_UUID_ONE_UUID_ONE_WORLD_V1",
        "status": "G1_FIVE_STORIES_HOLD_ONLY__NOT_ADMITTED",
        "roster_bytes_sha256_PRIVATE": "a" * 64,
        "namespace_equivalence_owner_confirmed": True,
        "cross_uuid_semantic_world_review_required": False,
        "frozen_queue_unmodified": True,
        "expansion_allowed": False,
        "entries": [{
            "story_id_PRIVATE": item,
            "historical_sft_exact_uuid_overlap": i == 0,
            "status": ("EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if i == 0
                       else "HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING"),
            "owner_attested_world_component_UUID": item,
            "owner_attested_distinct_semantic_world": True,
            "historical_sft_exact_uuid_set_nonoverlap": i != 0,
            "r50_protected_clear": False,
            "prior_sft_clear": False,
            "r55_r57_dev_clear": False,
            "other_protected_clear": False,
            "train_admitted": False,
        } for i, item in enumerate(candidates)],
    }
    rosters = {
        "known_historical_sft": [uid(1)] + [uid(i) for i in range(100, 126)],
        "r50_known_protected": [uid(i) for i in range(200, 205)],
        "gold195_source": [uid(i) for i in range(300, 313)],
        "legacy_dev20": [uid(400), uid(401)],
        "r04_non_gold": [uid(402), uid(403)],
        "r55_r57_other_dev": [],
        "other_reserved_heldout": [],
        "other_historical_training": [],
    }
    manifest = {
        "schema": m.SCHEMA,
        "world_identity_policy": m.POLICY,
        "candidate_uuids": candidates,
        "source_scopes": [{
            "scope": scope, "world_uuids": ids,
            "roster_sha256": m.roster_digest(set(ids)),
            "coverage_claim": "OWNER_PARTIAL" if ids else "UNKNOWN",
            "source_revision": "a" * 40 if ids else None,
        } for scope, ids in rosters.items()],
    }
    return manifest, ledger


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.ledger = fixture()

    def test_valid_stays_hold(self):
        result = m.reconcile(self.manifest, self.ledger)
        self.assertEqual((result["frozen_candidates"], result["remaining_candidates_held"]), (5, 4))
        self.assertEqual(result["scopes_checked"], 8)
        self.assertEqual(result["g1_clearance"], "HOLD")
        self.assertFalse(result["all_source_universes_verified"])

    def test_no_fabricated_uuids_in_safe_result(self):
        out = json.dumps(m.reconcile(self.manifest, self.ledger))
        self.assertNotIn(uid(1), out)
        self.assertNotIn(uid(200), out)
        self.assertNotIn("story_id_PRIVATE", out)

    def test_unknown_scope_remains_unverified(self):
        res = m.reconcile(self.manifest, self.ledger)
        self.assertEqual(res["independently_complete_scope_count"], 0)
        self.assertFalse(res["scoped_results"]["other_reserved_heldout"]["independent_universe_completeness_verified"])

    def test_missing_scope_fails(self):
        self.manifest["source_scopes"].pop()
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_unknown_extra_scope_fails(self):
        self.manifest["source_scopes"][0]["scope"] = "r50_raw_text"
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_tampered_roster_digest_fails(self):
        self.manifest["source_scopes"][1]["roster_sha256"] = "a" * 64
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_same_id_duplicate_fails(self):
        self.manifest["candidate_uuids"][-1] = uid(1)
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_candidate_cohort_mismatch_fails(self):
        self.manifest["candidate_uuids"][-1] = uid(30)
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_prior_sft_exclusion_mismatch_fails(self):
        row = self.manifest["source_scopes"][0]
        row["world_uuids"][0] = uid(999)
        row["roster_sha256"] = m.roster_digest(set(row["world_uuids"]))
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_metadata_only_disallows_extra_story_text(self):
        self.manifest["story_text"] = "never ingest narrative body"
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_metadata_only_rejects_nonuuid(self):
        self.manifest["source_scopes"][2]["world_uuids"][0] = "protected text"
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_known_count_missing_fails(self):
        row = self.manifest["source_scopes"][2]
        row["world_uuids"].pop()
        row["roster_sha256"] = m.roster_digest(set(row["world_uuids"]))
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_owner_complete_claim_never_grants_pass(self):
        for scope in self.manifest["source_scopes"]:
            scope["coverage_claim"] = "OWNER_COMPLETE"
            scope["source_revision"] = "a" * 40
        result = m.reconcile(self.manifest, self.ledger)
        self.assertEqual(result["g1_clearance"], "HOLD")
        self.assertEqual(result["independently_complete_scope_count"], 0)

    def test_explicit_but_unproven_claim_not_accepted(self):
        row = self.manifest["source_scopes"][5]
        row["coverage_claim"] = "INDEPENDENT_VERIFIED"
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_known_scope_exact_collision_detected_without_identifier(self):
        row = self.manifest["source_scopes"][5]
        row["world_uuids"] = [uid(3)]
        row["roster_sha256"] = m.roster_digest({uid(3)})
        result = m.reconcile(self.manifest, self.ledger)
        self.assertEqual(result["remaining_four_with_any_scoped_collision"], 1)
        self.assertEqual(result["scoped_results"]["r55_r57_other_dev"]["remaining_four_exact_uuid_matches"], 1)
        self.assertEqual(result["g1_clearance"], "HOLD")

    def test_ledger_duplicate_field_fails(self):
        self.ledger["entries"][0]["unexpected"] = True
        with self.assertRaises(m.Hold):
            m.reconcile(self.manifest, self.ledger)

    def test_json_duplicate_keys_fails(self):
        with self.assertRaises(m.Hold):
            m.decode_json(b'{"schema":1,"schema":2}')

    def test_private_permissions_and_no_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".storyforge-r58-private"
            root.mkdir(mode=0o700)
            item = root / "scope_PRIVATE.json"
            item.write_text(json.dumps(self.manifest), encoding="utf8")
            item.chmod(0o600)
            self.assertEqual(m.read_private(item, root)["schema"], m.SCHEMA)
            item.chmod(0o644)
            with self.assertRaises(m.Hold):
                m.read_private(item, root)
            item.chmod(0o600)
            link = root / "linked_PRIVATE.json"
            link.symlink_to(item)
            with self.assertRaises(m.Hold):
                m.read_private(link, root)

    def test_private_file_outside_root_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "allowed"
            root.mkdir(mode=0o700)
            item = Path(tmp) / "outside.json"
            item.write_text("{}")
            item.chmod(0o600)
            with self.assertRaises(m.Hold):
                m.read_private(item, root)


if __name__ == "__main__":
    unittest.main()

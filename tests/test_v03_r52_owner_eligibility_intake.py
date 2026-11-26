"""Synthetic, no-private-data tests for R52 owner-eligibility intake."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_owner_eligibility_intake as m


def fixtures():
    source, register = [], []
    for i in range(108):
        body = f"synthetic-body-{i}"
        sha = hashlib.sha256(body.encode()).hexdigest()
        cid = f"synthetic-{i:03d}"
        if i < 62:
            a = b = m.CONTEXT
            c, relation = None, m.AGREED
        elif i < 88:
            a = b = m.LONG
            c, relation = None, m.AGREED
        elif i < 94:
            a = b = m.AGENCY
            c, relation = None, m.AGREED
        else:
            a, b = m.CONTEXT, m.LONG
            j = i - 94
            if j < 5:
                c, relation = a, m.CA
            elif j < 10:
                c, relation = b, m.CB
            else:
                c, relation = m.AGENCY, m.NEITHER
        source.append({
            "schema": m.PACKET_SCHEMA, "private_do_not_commit": True,
            "candidate_id": cid, "target_sha256": sha,
            "target_content_for_review_only": body,
            "training_admission": m.HOLD, "split": None,
            "historical_card_version_verified": False,
            "story_rank": i % 8 + 1, "source_story_id": f"synthetic-world-{i % 8}",
            "target_original_array_index": i,
        })
        register.append({
            "schema": m.REG_SCHEMA, "private_do_not_commit": True,
            "candidate_id": cid, "target_sha256": sha,
            "reviewer_A_route": a, "reviewer_B_route": b,
            "reviewer_C_route": c, "post_c_relation": relation,
            "training_admission": m.HOLD, "train_admitted": False,
            "validation_admitted": False,
            "risk_flags_from_reviewer_routes_only": [],
        })
    return register, source


class TestR52OwnerIntake(unittest.TestCase):
    def test_partition_and_hold(self):
        grouped, safe = m.build(*fixtures())
        self.assertEqual({k: len(v) for k, v in grouped.items()}, {
            "context_62": 62, "three_way_04": 4,
            "other_disputes_10": 10, "baseline_holds_32": 32,
        })
        self.assertEqual(safe["train_admitted"], 0)
        self.assertTrue(all(
            r["training_admission"] == m.HOLD and r["world_split"] is None and
            r["historical_card_at_target_time"] == "NOT_VERIFIED"
            for rows in grouped.values() for r in rows
        ))

    def test_damaged_source_or_three_way_misclassification_is_rejected(self):
        register, source = fixtures()
        register[0]["target_sha256"] = "0" * 64
        with self.assertRaisesRegex(m.IntakeHold, "RISK_REGISTER_PROVENANCE_CHANGED"):
            m.build(register, source)
        register, source = fixtures()
        register[-1]["post_c_relation"] = m.AGREED
        with self.assertRaisesRegex(m.IntakeHold, "RISK_AGREEMENT_INCONSISTENT"):
            m.build(register, source)

    def test_owner_switch_private_output_and_no_overwrite(self):
        register, source = fixtures()
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            repo = root / "repo"
            private = root / "private"
            dest = private / "r52"
            for folder in (repo, private, dest):
                folder.mkdir()
                folder.chmod(0o700)
            a = private / "register.jsonl"
            b = private / "packets.jsonl"
            for path, records in ((a, register), (b, source)):
                path.write_text("".join(json.dumps(x) + "\n" for x in records))
                path.chmod(0o600)
            with self.assertRaisesRegex(m.IntakeHold, "EXPLICIT_SWITCH_REQUIRED"):
                m.execute(a, b, dest, attested=False, repo=repo)
            m.execute(a, b, dest, attested=True, repo=repo)
            self.assertEqual(len(list(dest.iterdir())), 6)
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600
                                for p in dest.iterdir()))
            with self.assertRaisesRegex(m.IntakeHold, "OUTPUT_ALREADY_EXISTS"):
                m.execute(a, b, dest, attested=True, repo=repo)


if __name__ == "__main__":
    unittest.main()

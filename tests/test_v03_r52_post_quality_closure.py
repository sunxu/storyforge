"""Synthetic-only tests: R52 frozen 62-case no-card quality closure."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_no_card_quality_reviews as q
import v03_r52_post_quality_closure as closure


def write_private(path, rows):
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    path.chmod(0o600)


def fake_source():
    packets, queue = [], []
    for i in range(108):
        ident = "fake-%03d" % i
        target, user = "target-%03d" % i, "visible-%03d" % i
        p = {
            "schema": q.PACKET_SCHEMA, "private_do_not_commit": True,
            "candidate_id": ident, "target_sha256": q.digest(target),
            "target_content_for_review_only": target,
            "story_rank": i // 18 + 1, "source_story_id": "world-%02d" % (i // 18),
            "target_original_array_index": i * 10 + 2,
            "training_admission": q.HOLD, "split": None,
            "historical_card_version_verified": False,
            "frozen_visible_history": [
                {"role": "user", "content": user,
                 "source_body_sha256": q.digest(user),
                 "original_source_array_index": i * 10 + 1}],
            "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT": [],
        }
        packets.append(p)
        if i < 62:
            queue.append({
                "schema": q.QUEUE_SCHEMA,
                "candidate_id": ident, "private_do_not_commit": True,
                "r52_queue": "context_62",
                "r51_review_relation": "A_B_AGREE__HOLD",
                "reviewer_A_route": q.CONTEXT, "reviewer_B_route": q.CONTEXT,
                "reviewer_C_route": None, "target_sha256": p["target_sha256"],
                "story_rank": p["story_rank"], "source_story_id": p["source_story_id"],
                "target_original_array_index": p["target_original_array_index"],
                "owner_rights_status": "OWNER_ATTESTED_FULL_OWNERSHIP",
                "training_admission": q.HOLD, "world_split": None,
            })
    return queue, packets


def fixture(tmp):
    qdir = tmp / "quality"
    qdir.mkdir(mode=0o700)
    qfile, pfile = tmp / "queue.jsonl", tmp / "packets.jsonl"
    queue, packets = fake_source()
    write_private(qfile, queue)
    write_private(pfile, packets)
    for batch, _, _, routes in closure.EXPECTED:
        tasks, _ = q.make_batch(queue, packets, batch)
        write_private(qdir / f"R52_NO_CARD_BATCH_{batch:02d}_QUALITY_TASKS.jsonl", tasks)
        ordered = []
        for route, count in routes.items():
            ordered.extend([route] * count)
        results = []
        for task, route in zip(tasks, ordered, strict=True):
            msg = task["frozen_visible_history"][0]
            results.append({
                "schema": q.RESULT_SCHEMA,
                "candidate_id": task["candidate_id"],
                "target_sha256": task["target_sha256"],
                "quality_batch_number": batch, "review_route": route,
                "training_admission": q.HOLD,
                "rationale": "Synthetic review rationale is for technical testing only.",
                "source_citations": [
                    {"scope": "FROZEN_VISIBLE",
                     "original_source_array_index": msg["original_source_array_index"],
                     "source_body_sha256": msg["source_body_sha256"]},
                    {"scope": "TARGET",
                     "original_source_array_index": task["target_original_array_index"],
                     "source_body_sha256": task["target_sha256"]},
                ],
            })
        # Synthetic citations must match frozen batch totals; adding distinct
        # valid citations requires more than one visible message in fake fixtures.
        write_private(qdir / f"R52_NO_CARD_BATCH_{batch:02d}_QUALITY_RESULTS.jsonl",
                      results)
    return qfile, pfile, qdir


class QualityClosureTests(unittest.TestCase):
    def test_expected_routes_are_exhaustive(self):
        self.assertEqual(sum(n for _, n, _, _ in closure.EXPECTED), 62)
        self.assertEqual(sum(c for _, _, c, _ in closure.EXPECTED), 205)
        self.assertEqual(sum(x.get(closure.ROUTE_GOOD, 0)
                             for _, _, _, x in closure.EXPECTED), 46)
        self.assertEqual(q.HOLD, "PENDING_NOT_APPROVED")

    def test_does_not_rewrite_training_admission(self):
        self.assertTrue(closure.ROUTE_GOOD.endswith("__HOLD"))
        self.assertFalse(closure.original_history_digest({
            "frozen_visible_history": [{
                "role": "user",
                "original_source_array_index": 1,
                "source_body_sha256": "c" * 64,
            }]
        }) == closure.original_history_digest({"frozen_visible_history": []}))

    def test_fail_closed_if_citation_counts_differ(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            qfile, pfile, qdir = fixture(path)
            with self.assertRaisesRegex(q.Hold, "FROZEN_BATCH_VERIFICATION_MISMATCH"):
                closure.collect(qfile, pfile, qdir)


if __name__ == "__main__":
    unittest.main()

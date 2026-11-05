import io
from collections import Counter, defaultdict
import json
import unittest
import zipfile

from gold195_card_source_coverage import worlds_from_source


class WorldSourceCoverageTests(unittest.TestCase):
    @staticmethod
    def nested_json_zip(items):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for i, x in enumerate(items):
                z.writestr(f"source_{i}.json", json.dumps(x))
        b.seek(0)
        return b

    def test_same_world_versions_dedup_and_conflict(self):
        items = [
            {"story": {"id": "PRIVATE_WORLD", "v2_data": {"scene": "A"}}},
            {"story": {"id": "PRIVATE_WORLD", "v2_data": {"scene": "A"}}},
            {"story": {"id": "PRIVATE_WORLD", "v2_data": {"scene": "B"}}},
        ]
        counts = Counter()
        worlds = defaultdict(set)
        worlds_from_source(self.nested_json_zip(items), counts, worlds)
        self.assertEqual(counts["story_card_object_seen"], 3)
        self.assertEqual(len(worlds), 1)
        self.assertEqual(len(worlds["PRIVATE_WORLD"]), 2)
        self.assertNotIn("PRIVATE_WORLD", str(counts))

    def test_no_identity_is_not_promoted(self):
        counts, worlds = Counter(), defaultdict(set)
        worlds_from_source(self.nested_json_zip(
            [{"story": {"v2_data": {"scene": "secret"}}}]), counts, worlds)
        self.assertEqual(counts["card_missing_story_identity"], 1)
        self.assertEqual(len(worlds), 0)

    def test_empty_card_rejected(self):
        counts, worlds = Counter(), defaultdict(set)
        worlds_from_source(self.nested_json_zip(
            [{"story": {"id": "private", "v2_data": {}}}]), counts, worlds)
        self.assertEqual(len(worlds), 0)


if __name__ == "__main__":
    unittest.main()

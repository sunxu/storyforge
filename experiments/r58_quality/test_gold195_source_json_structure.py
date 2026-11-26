import io
import json
from collections import Counter
import unittest
import zipfile

from gold195_source_json_structure import KEYS, inspect_zip, shape


class SchemaScoutTests(unittest.TestCase):
    def test_values_not_emitted(self):
        counts = Counter()
        shape({"story": {"v2_data": {"characters": [{"name": "PRIVATE_NAME"}]}},
               "messages": [{"content": "PRIVATE_STORY"}],
               "PRIVATE_KEY": "SECRET"}, counts)
        self.assertEqual(counts["key_v2_data"], 1)
        self.assertEqual(counts["type_characters_list"], 1)
        self.assertNotIn("PRIVATE", str(counts))
        self.assertNotIn("SECRET", str(counts))

    def test_zip_with_json_and_jsonl(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("story.json", json.dumps({"story": {"v2_data": {}}}))
            z.writestr("messages.jsonl", json.dumps({"messages": []}) + "\n")
        buf.seek(0)
        counts = Counter()
        inspect_zip(buf, counts)
        self.assertEqual(counts["json_parsed"], 2)
        self.assertEqual(counts["key_story"], 1)
        self.assertEqual(counts["key_messages"], 1)

    def test_output_allowlist_is_fixed(self):
        self.assertNotIn("name", KEYS)
        self.assertNotIn("content", KEYS)


if __name__ == "__main__":
    unittest.main()

"""R58 synthetic-only offline integrity checks for frozen Priority3 source captures."""
from pathlib import Path
import json
import os
import tempfile
import unittest

from capture_priority3 import capture, Hold
from test_capture_priority3 import row, encode
from verify_priority3_private import verify


class TestRecheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parent = Path(self.tmp.name) / 'private'
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [row('AUTHOR', 1), row('CURRENT_PUBLIC', 2), row('OLD_PUBLIC', 3)]
        capture(encode(self.rows), self.parent, 'freeze1')
        self.folder = self.parent / 'freeze1'

    def tearDown(self):
        self.tmp.cleanup()

    def mutate(self, filename, transform):
        path = self.folder / filename
        before = path.read_bytes()
        path.write_bytes(transform(before))
        os.chmod(path, 0o600)

    def test_unchanged_capture(self):
        result = verify(self.folder)
        self.assertEqual(result['records'], 3)
        self.assertEqual(result['case_fingerprints_verified'], 12)
        self.assertEqual(result['training_admission'], 'HOLD')
        self.assertNotIn('story-', json.dumps(result))

    def test_raw_content_changed(self):
        self.mutate('source.private.jsonl', lambda data: data.replace(b'test target', b'fake target', 1))
        with self.assertRaisesRegex(Hold, 'source file checksum'):
            verify(self.folder)

    def test_source_manifest_file_digest_forged_without_case_digest(self):
        path = self.folder / 'source.private.jsonl'
        raw = path.read_bytes().replace(b'test target', b'fake target', 1)
        path.write_bytes(raw)
        self.mutate('manifest.private.json', lambda data:
            self._replace_file_digest(data, raw))
        with self.assertRaisesRegex(Hold, 'per-case source fingerprint'):
            verify(self.folder)

    @staticmethod
    def _replace_file_digest(data, raw):
        import hashlib
        manifest = json.loads(data)
        manifest['raw_jsonl_sha256'] = hashlib.sha256(raw).hexdigest()
        manifest['raw_jsonl_size_bytes'] = len(raw)
        return json.dumps(manifest).encode()

    def test_case_digest_changed(self):
        def edit(data):
            v = json.loads(data)
            v['cases'][1]['history24_json_sha256'] = '0' * 64
            return json.dumps(v).encode()
        self.mutate('manifest.private.json', edit)
        with self.assertRaisesRegex(Hold, 'per-case source fingerprint'):
            verify(self.folder)

    def test_missing_completion_marker(self):
        (self.folder / 'CAPTURE_COMPLETE').unlink()
        with self.assertRaises(OSError):
            verify(self.folder)

    def test_symlinked_source_rejected(self):
        source = self.folder / 'source.private.jsonl'
        moved = self.folder / 'other.private'
        source.rename(moved)
        source.symlink_to(moved)
        with self.assertRaisesRegex(Hold, 'regular non-hardlinked'):
            verify(self.folder)

    def test_readable_permissions_rejected(self):
        os.chmod(self.folder / 'source.private.jsonl', 0o644)
        with self.assertRaisesRegex(Hold, '0600'):
            verify(self.folder)

    def test_private_folder_permissions_rejected(self):
        os.chmod(self.folder, 0o755)
        with self.assertRaisesRegex(Hold, 'inaccessible|0700'):
            verify(self.folder)

    def test_wrong_source_identifier(self):
        def edit(data):
            v = json.loads(data)
            v['cases'][0]['message_id'] = 'incorrect-message-id'
            return json.dumps(v).encode()
        self.mutate('manifest.private.json', edit)
        with self.assertRaisesRegex(Hold, 'provenance identifier'):
            verify(self.folder)


if __name__ == '__main__':
    unittest.main()

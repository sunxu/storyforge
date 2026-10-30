"""Synthetic-only tests. No Supabase, Hugging Face, or narrative text."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

from capture_priority3 import capture, Hold, SCHEMA, EXPECTED_STATUS, _trusted_macos_system_link


def row(route, idx):
    history = [
        {'id': str(idx) + '-' + str(i), 'turn_index': i + 1,
         'role': 'user' if i % 2 == 0 else 'assistant', 'status': 'completed',
         'created_at': '2026-10-01T00:00:00Z', 'content': 'fiction ' + str(i)}
        for i in range(24)
    ]
    return {
        'schema': SCHEMA, 'status': EXPECTED_STATUS,
        'deployed_source_commit_verified': False,
        'case': {
            'cohort': route, 'story_id': 'story-' + str(idx),
            'session_id': 'session-' + str(idx),
            'target_message_id': 'target-' + str(idx),
            'target_created_at': '2026-10-30T00:00:00Z', 'turn_index': 30,
        },
        'historical_approved_story': {
            'submission_id': 'submission-' + str(idx),
            'v2_data': {'world': 'fiction'}, 'content_revision': 2,
            'approval_at': '2026-10-01T00:00:00Z',
        },
        'prior_checkpoint': {
            'id': 'cp-' + str(idx), 'snapshot': {'memory_facts': []},
            'created_at': '2026-10-29T00:00:00Z', 'turn_index': 13,
        },
        'history24': history, 'target': {'content': 'test target'},
        'structural_checks': {
            'prior_24_total': 24, 'prior_24_completed': 24,
            'post_target_ledger_events': 0,
        },
    }


def encode(rows):
    return b''.join(
        json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\n'
        for obj in rows
    )


class TestCapture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parent = Path(self.tmp.name) / 'private'
        self.parent.mkdir(mode=0o700)
        os.chmod(self.parent, 0o700)
        self.rows = [row('AUTHOR', 1), row('CURRENT_PUBLIC', 2), row('OLD_PUBLIC', 3)]

    def tearDown(self):
        self.tmp.cleanup()

    def hold(self, reason=None, raw=None):
        with self.assertRaises(Hold) as raised:
            capture(encode(self.rows) if raw is None else raw, self.parent, 'freeze1')
        if reason:
            self.assertIn(reason, str(raised.exception))
        self.assertFalse((self.parent / 'freeze1').exists())

    def test_success_permissions_and_hashes(self):
        self.assertEqual(capture(encode(self.rows), self.parent, 'freeze1')['records'], 3)
        root = self.parent / 'freeze1'
        self.assertTrue((root / 'CAPTURE_COMPLETE').exists())
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        for file in ('source.private.jsonl', 'manifest.private.json', 'CAPTURE_COMPLETE'):
            self.assertEqual(stat.S_IMODE((root / file).stat().st_mode), 0o600)
        m = json.loads((root / 'manifest.private.json').read_text())
        self.assertEqual(m['runtime_byte_exact_pass'], 0)
        self.assertEqual(len(m['cases']), 3)
        self.assertNotIn('fiction', json.dumps(m))

    def test_no_overwrite(self):
        capture(encode(self.rows), self.parent, 'freeze1')
        with self.assertRaisesRegex(Hold, 'overwrite'):
            capture(encode(self.rows), self.parent, 'freeze1')

    def test_missing_route(self):
        self.rows[2]['case']['cohort'] = 'CURRENT_PUBLIC'
        self.hold('missing or duplicate')

    def test_same_story(self):
        self.rows[2]['case']['story_id'] = self.rows[0]['case']['story_id']
        self.hold('same physical story')

    def test_invalid_history(self):
        self.rows[1]['history24'][3]['status'] = 'failed'
        self.hold('completed')

    def test_later_checkpoint_turn(self):
        self.rows[2]['prior_checkpoint']['turn_index'] = 20
        self.hold('checkpoint')

    def test_missing_card(self):
        self.rows[2]['historical_approved_story']['v2_data'] = None
        self.hold('source card')

    def test_extra_row(self):
        self.rows.append(self.rows[0])
        self.hold('exactly 3')

    def test_invalid_json(self):
        self.hold('invalid source', raw=b'broken\nbroken\nbroken\n')

    def test_bad_parent_permissions(self):
        os.chmod(self.parent, 0o755)
        self.hold('inaccessible')

    def test_parent_symlink(self):
        link = Path(self.tmp.name) / 'link'
        link.symlink_to(self.parent)
        with self.assertRaisesRegex(Hold, 'symlink'):
            capture(encode(self.rows), link, 'freeze1')

    def test_macos_system_temp_alias(self):
        if sys.platform != 'darwin':
            self.skipTest('macOS-specific /var -> /private/var alias')
        var = Path('/var')
        self.assertTrue(var.is_symlink(), 'macOS /var is expected to be a system alias')
        self.assertEqual(var.resolve(strict=True), Path('/private/var').resolve(strict=True))
        self.assertTrue(_trusted_macos_system_link(var))
        self.assertEqual(capture(encode(self.rows), self.parent, 'freeze1')['records'], 3)

    def test_untrusted_ancestor_symlink(self):
        storage = Path(self.tmp.name) / 'storage'
        storage.mkdir(mode=0o700)
        secure = storage / 'secure'
        secure.mkdir(mode=0o700)
        redirect = Path(self.tmp.name) / 'redirect'
        redirect.symlink_to(storage, target_is_directory=True)
        with self.assertRaisesRegex(Hold, 'symlink'):
            capture(encode(self.rows), redirect / 'secure', 'freeze1')

    def test_no_target(self):
        self.rows[0]['target']['content'] = ''
        self.hold('target')

    def test_duplicate_prior_messages(self):
        self.rows[1]['history24'][5]['id'] = self.rows[1]['history24'][4]['id']
        self.hold('duplicate')

    def test_size_limit(self):
        self.hold('size limit', raw=b'a' * (50 * 1024 * 1024 + 1))

    def test_post_target_approval(self):
        self.rows[1]['historical_approved_story']['approval_at'] = '2026-11-01T00:00:00Z'
        self.hold('predate target')

    def test_post_target_history(self):
        self.rows[1]['history24'][0]['created_at'] = '2026-11-01T00:00:00Z'
        self.hold('after target')

    def test_post_target_checkpoint(self):
        self.rows[1]['prior_checkpoint']['created_at'] = '2026-11-01T00:00:00Z'
        self.hold('predate target')


if __name__ == '__main__':
    unittest.main()

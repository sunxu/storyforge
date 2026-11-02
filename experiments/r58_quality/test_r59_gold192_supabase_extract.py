"""R59 bounded Supabase extraction identity and safety tests. No DB/network required."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from experiments.r58_quality import r59_gold192_supabase_extract as m


class R59Gold192ExtractTest(unittest.TestCase):
    def test_pilot_story_diversity(self):
        cases = [
            {'case_id': f's{i}-t{n:05d}', 'story_id': f's{i}', 'turn_index': n}
            for i in range(3) for n in (1, 900)
        ]
        selected = m.choose_pilot(cases, 5)
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({c['case_id'] for c in selected}), 5)
        self.assertEqual(len({c['story_id'] for c in selected}), 3)

    def test_exact_and_root_resolution(self):
        case = {'target_sha256': m.sha_text('目标')}
        self.assertEqual(m.decide_matches(case, [])[0], 'SOURCE_NOT_FOUND')
        self.assertEqual(m.decide_matches(case, [{'content': '改变'}])[0],
                         'SOURCE_FOUND_BUT_CONTENT_CHANGED')
        exact = {'content': '目标', 'parent_session_id': None, 'session_id': 'root'}
        fork = {'content': '目标', 'parent_session_id': 'root', 'session_id': 'fork'}
        self.assertEqual(m.decide_matches(case, [exact, fork]), ('EXACT_MATCH', exact))
        self.assertEqual(m.decide_matches(case, [fork, fork])[0], 'IDENTITY_AMBIGUOUS')
        self.assertEqual(m.decide_matches(case, [exact, exact])[0], 'IDENTITY_AMBIGUOUS')

    def test_exclusive_private_file_write(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'safe.json'
            digest = m.atomic_private_write(p, b'{}\n')
            self.assertEqual(digest, hashlib.sha256(b'{}\n').hexdigest())
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                m.atomic_private_write(p, b'REPLACED')
            self.assertEqual(p.read_bytes(), b'{}\n')

    def test_scope_192_review_a_b_and_exclusion_11(self):
        cases = [
            {'case_id': f's{n//16}-t{n:05d}',
             'target_assistant_text': f'target {n}',
             'target_sha256': m.sha_text(f'target {n}')}
            for n in range(192)
        ]
        packets = [
            {'story_uuid': f'uuid-{i}', 'cases': cases[i*16:(i+1)*16]}
            for i in range(12)
        ] + [{'story_uuid': 'uuid-12', 'cases': []}]
        indexed = m.index_packets(packets)
        a = {'records': [
            {'case_id': x['case_id'], 'target_sha256': x['target_sha256'],
             'decision_for_strict_ab_pairing': 'PASS_ONLY' if i < 79 else None}
            for i, x in enumerate(cases)
        ]}
        b = {'cases': [
            {'target_sha256': x['target_sha256'], 'decision': 'PASS'}
            for x in cases
        ]}
        exclusions = [
            {'target_sha256': x['target_sha256'],
             'exclusion_reason': 'EXCLUDED_FROM_TRAINING_DISAGREEMENT'}
            for x in cases[:7] + cases[100:104]
        ]
        self.assertEqual(len(m.select_candidates(a, b, exclusions, indexed)), 72)
        a['records'][7]['case_id'] = 'other-case'
        with self.assertRaisesRegex(ValueError, 'REVIEW_CASE_ID_MISMATCH'):
            m.select_candidates(a, b, exclusions, indexed)


if __name__ == '__main__':
    unittest.main()

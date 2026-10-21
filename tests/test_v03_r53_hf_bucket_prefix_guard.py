"""Offline regression for empty-prefix detection and paid-job fail-closed guard."""
import importlib.util
import pathlib
from types import SimpleNamespace
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "scripts/v03_r53_hf_bucket_prefix_guard.py"
spec = importlib.util.spec_from_file_location("r53_prefix_guard", MODULE)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
KEY = "r53-cpu40-20261021T190800Z-123456"
PREFIX = f"{g.BASE}/{KEY}/"

class FakeAPI:
    def __init__(self, paths=(), exc=None):
        self.paths = paths
        self.exc = exc
        self.calls = []
    def list_bucket_tree(self, bucket, *, prefix, recursive):
        self.calls.append((bucket, prefix, recursive))
        if self.exc:
            raise self.exc
        for path in self.paths:
            yield SimpleNamespace(path=path, type="file")

class TestPrefixGuard(unittest.TestCase):
    def test_empty_prefix_is_available_even_if_api_call_succeeds(self):
        api = FakeAPI([])
        self.assertEqual(g.check("empty", KEY, api), "R53_REMOTE_RUN_PREFIX_AVAILABLE")
        self.assertEqual(api.calls, [(g.BUCKET, PREFIX, True)])
    def test_collision_rejected(self):
        with self.assertRaisesRegex(ValueError,"ALREADY_EXISTS"):
            g.check("empty", KEY, FakeAPI([PREFIX + "code/foo.py"]))
    def test_partial_upload_rejected(self):
        with self.assertRaisesRegex(ValueError,"NOT_READY"):
            g.check("ready", KEY, FakeAPI([PREFIX+"SHA256SUMS.txt"]))
    def test_complete_ready(self):
        self.assertEqual(g.check("ready", KEY, FakeAPI([PREFIX+n for n in sorted(g.EXPECTED)])),
                         "R53_REMOTE_STAGE_FILES_PRESENT")
    def test_bad_foreign_or_similar_prefix_blocked(self):
        with self.assertRaisesRegex(ValueError,"INVALID_ENTRY"):
            g.check("empty", KEY, FakeAPI([PREFIX[:-1]+"-extra/code/foo.py"]))
    def test_network_error_not_mistaken_for_empty(self):
        with self.assertRaisesRegex(PermissionError,"denied"):
            g.check("empty", KEY, FakeAPI(exc=PermissionError("denied")))
    def test_extra_file_blocked_ready(self):
        with self.assertRaisesRegex(ValueError,"NOT_READY"):
            g.check("ready", KEY, FakeAPI([PREFIX+n for n in g.EXPECTED]+[PREFIX+'other.txt']))
    def test_bad_key_blocked(self):
        with self.assertRaisesRegex(ValueError,"INVALID_RUN_KEY"):
            g.check("empty", "../r53-nope", FakeAPI())
    def test_directory_prefix_blocked(self):
        class FakeDir:
            def list_bucket_tree(self,*a,**k):
                return [SimpleNamespace(path=PREFIX+'code/',type='directory')]
        with self.assertRaisesRegex(ValueError,"ALREADY_EXISTS"):
            g.check("empty", KEY, FakeDir())
    def test_no_submit_without_two_env_flags(self):
        s=(MODULE.parent/'v03_r53_hf_cpu40_submit.sh').read_text()
        self.assertIn('STORYFORGE_ALLOW_PAID_CPU:-', s)
        self.assertIn('STORYFORGE_R53_CPU40_NO_TRAIN_ONLY:-', s)
        self.assertLess(s.index('STORYFORGE_ALLOW_PAID_CPU:-'),s.index('hf jobs run'))
        self.assertIn('v03_r53_hf_bucket_prefix_guard.py empty', s)
        self.assertIn('v03_r53_hf_bucket_prefix_guard.py ready', s)
        self.assertNotIn('if hf buckets ls "$PREFIX/runs/$RUN_KEY"', s)

if __name__=='__main__': unittest.main()

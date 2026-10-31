"""Synthetic-only tests. No HF reads, no real story data."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest import mock

import check_hf_primary_input_bytes as m


def fake_pin(name, data):
    return m.Pin(name, f"hf://synthetic/{name}", data.count(b"\n"), hashlib.sha256(data).hexdigest(), len(data))


def make_pins():
    names = ["R46_TRAIN", "R46_VALIDATION", "R54_TRAIN", "R54_VALIDATION"]
    data = {name: (name.encode() + b"\n") * (i + 1) for i, name in enumerate(names)}
    return tuple(fake_pin(name, data[name]) for name in names), data


class FakeFS:
    def __init__(self, data, bad_uri=None):
        self.data = data
        self.calls = []
        self.bad_uri = bad_uri
    def open(self, uri, mode):
        self.calls.append((uri, mode))
        if uri == self.bad_uri:
            raise OSError("secret=user_token_dont_echo")
        return io.BytesIO(self.data[uri.split("/")[-1]])


class TestPrimaryByteHashes(unittest.TestCase):
    def test_01_exact_four_fake_bytes_pass(self):
        pins, data = make_pins()
        f = FakeFS(data)
        result = m.read_and_verify(f, pins)
        self.assertEqual(result["hf_bucket_objects_read"],4)
        self.assertTrue(result["r46_original_run_compiled_train_validation_bytes_verified"])
        self.assertEqual([mode for _, mode in f.calls], ["rb"]*4)
        self.assertEqual(result["g1_clearance"], "HOLD")
        self.assertFalse(result["source_registry_complete"])
    def test_02_mutated_remote_blob_holds(self):
        pins, data = make_pins()
        data["R54_TRAIN"] += b"bad\n"
        with self.assertRaises(m.Hold):m.read_and_verify(FakeFS(data),pins)
    def test_03_incorrect_expected_row_count_holds(self):
        pins, data=make_pins()
        pin=pins[0]
        p = m.Pin(pin.role,pin.uri,pin.rows+1,pin.digest,pin.expected_bytes)
        with self.assertRaises(m.Hold):m.read_and_verify(FakeFS(data), (p,*pins[1:]))
    def test_04_incorrect_size_holds(self):
        pins,data=make_pins()
        pin=pins[0];p=m.Pin(pin.role,pin.uri,pin.rows,pin.digest,pin.expected_bytes+1)
        with self.assertRaises(m.Hold):m.read_and_verify(FakeFS(data),(p,*pins[1:]))
    def test_05_missing_remote_file_holds(self):
        pins,data=make_pins()
        with self.assertRaises(OSError):m.read_and_verify(FakeFS(data,pins[0].uri),pins)
    def test_06_duplicate_roles_holds(self):
        pins,data=make_pins()
        with self.assertRaises(m.Hold):m.read_and_verify(FakeFS(data),(pins[0],pins[0],*pins[2:]))
    def test_07_empty_file_holds(self):
        with self.assertRaises(m.Hold):m.hash_existing_object(io.BytesIO(b""))
    def test_08_nonbytes_holds(self):
        with self.assertRaises(m.Hold):m.hash_existing_object(io.StringIO("a\n"))
    def test_09_size_cap_holds(self):
        with mock.patch.object(m,"MAX_FILE_BYTES",9):
            with self.assertRaises(m.Hold):m.hash_existing_object(io.BytesIO(b"x"*10))
    def test_10_unterminated_last_line_counted(self):
        digest, n, lines = m.hash_existing_object(io.BytesIO(b"abc\ndef"))
        self.assertEqual(lines,2)
        self.assertEqual(n,7)
    def test_11_no_opt_in_never_imports_hf(self):
        err=io.StringIO()
        with redirect_stderr(err), mock.patch.dict(sys.modules, {"huggingface_hub":None}):
            self.assertEqual(m.main([]),42)
        self.assertIn("opt-in required",err.getvalue())
    def test_12_owner_opt_in_fake_sdk_pass(self):
        pins,data=make_pins()
        fs=FakeFS(data)
        fake=SimpleNamespace(HfFileSystem=lambda:fs)
        out=io.StringIO()
        with mock.patch.object(m,"PINS",pins),mock.patch.dict(sys.modules,{"huggingface_hub":fake}),redirect_stdout(out):
            self.assertEqual(m.main(["--allow-read-only-private-primary-input-bytes"]),0)
        result=json.loads(out.getvalue())
        self.assertFalse(result["historical_bucket_object_immutability_proven"])
        self.assertFalse(result["current_bucket_equality_proves_historical_job_read_these_bytes"])
        self.assertFalse(result["r50_protected_content_absence_proven"])
        self.assertEqual(result["train_admitted"],0)
    def test_13_failure_hides_provider_details(self):
        pins,data=make_pins()
        fake=SimpleNamespace(HfFileSystem=lambda:FakeFS(data,pins[0].uri))
        err=io.StringIO();out=io.StringIO()
        with mock.patch.object(m,"PINS",pins),mock.patch.dict(sys.modules,{"huggingface_hub":fake}),redirect_stderr(err),redirect_stdout(out):
            self.assertEqual(m.main(["--allow-read-only-private-primary-input-bytes"]),42)
        self.assertEqual(out.getvalue(),"")
        self.assertNotIn("user_token_dont_echo",err.getvalue())
    def test_14_no_real_source_in_output(self):
        pins,data=make_pins()
        result=m.read_and_verify(FakeFS(data),pins)
        raw=json.dumps(result)
        for pin in pins:
            self.assertNotIn(pin.uri,raw)
            self.assertNotIn(pin.digest,raw)
    def test_15_fixed_production_pins(self):
        self.assertEqual(len(m.PINS),4)
        self.assertEqual([x.rows for x in m.PINS],[49,15,31,9])
        self.assertEqual([x.role for x in m.PINS],["R46_TRAIN","R46_VALIDATION","R54_TRAIN","R54_VALIDATION"])
        self.assertTrue(all(x.uri.startswith(m.BUCKET) for x in m.PINS))
        self.assertEqual(len({x.uri for x in m.PINS}),4)
        self.assertEqual(len({x.digest for x in m.PINS}),4)

if __name__ == "__main__": unittest.main()

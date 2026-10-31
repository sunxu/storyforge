"""Synthetic and stdlib-only tests. No HF, no real v0.1 stories or R50."""
from __future__ import annotations
from contextlib import redirect_stderr,redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock
import check_v01_hf_primary_inputs as m


def public_fixture(n):
    out=[]
    for i in range(n):
        row={"id":f"sample-{i:06d}","metadata":{"story_id":"00000000-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
             "messages":[{"role":"system","content":"中文"},
                         {"role":"user","content":"问"},
                         {"role":"assistant","content":f"回答{i}"}]}
        out.append(json.dumps(row,ensure_ascii=False)+"\n")
    return "".join(out).encode()

class FakeFS:
    def __init__(self, source, compiled, fail=None):
        self.source=source;self.compiled=compiled;self.calls=[];self.fail=fail
    def open(self,uri,mode):
        self.calls.append((uri,mode))
        if uri==self.fail:raise OSError("SECRET_AUTH_TOKEN_DONT_ECHO")
        split=uri.rsplit("/",1)[1].split(".")[0]
        if "/datasets/v0.3/" in uri:return io.BytesIO(self.source[split])
        return io.BytesIO(self.compiled[split])

def inputs():
    source={"train":public_fixture(3),"validation":public_fixture(2)}
    compiled={k:m.replay_prepare_sft(v,hashlib.sha256(v).hexdigest(),n)
              for k,v,n in (("train",source["train"],3),("validation",source["validation"],2))}
    expected={k:(hashlib.sha256(source[k]).hexdigest(),hashlib.sha256(compiled[k]).hexdigest(),n)
              for k,n in (("train",3),("validation",2))}
    return source,compiled,expected

class TestV01Primary(unittest.TestCase):
    def setUp(self):
        self.source,self.compiled,self.expected=inputs()
        self.p=mock.patch.object(m,"SOURCE_PINS",{key:("abc",value[0],value[2]) for key,value in self.expected.items()})
        self.p.start();self.addCleanup(self.p.stop)
    def test_01_compiler_exact_expected_messages(self):
        val=self.compiled["train"].splitlines()[0]
        row=json.loads(val)
        self.assertEqual(set(row),{"messages"})
        self.assertEqual(row["messages"][-1]["loss"],True)
        self.assertFalse(any("loss" in x for x in row["messages"][:-1]))
    def test_02_compiler_preserves_chinese(self):
        self.assertIn("中文".encode(),self.compiled["train"])
    def test_03_source_digest_mismatch(self):
        with self.assertRaises(m.Hold):m.replay_prepare_sft(self.source["train"],"0"*64,3)
    def test_04_source_count_mismatch(self):
        with self.assertRaises(m.Hold):m.replay_prepare_sft(self.source["train"],self.expected["train"][0],4)
    def test_05_invalid_source_roles_fail(self):
        row=json.loads(self.source["train"].splitlines()[0]);row["messages"][-1]["role"]="user"
        raw=(json.dumps(row).encode()+b"\n")
        with self.assertRaises(m.Hold):m.replay_prepare_sft(raw,hashlib.sha256(raw).hexdigest(),1)
    def test_06_all_eight_current_remote_sources_pass(self):
        fs=FakeFS(self.source,self.compiled)
        r=m.verify_remote(fs,self.expected)
        self.assertEqual(len(fs.calls),8)
        self.assertTrue(all(mode=="rb" for _,mode in fs.calls))
        self.assertEqual(r["v01_known_parameter_update_jobs_with_compiled_inputs_verified"],3)
        self.assertFalse(r["source_registry_complete"])
    def test_07_shared_source_mutation_holds(self):
        src=dict(self.source);src["train"]+=b"corruption"
        with self.assertRaises(m.Hold):m.verify_remote(FakeFS(src,self.compiled),self.expected)
    def test_08_job_compiled_mutation_holds(self):
        c=dict(self.compiled);c["validation"]+=b"corruption"
        with self.assertRaises(m.Hold):m.verify_remote(FakeFS(self.source,c),self.expected)
    def test_09_remote_file_missing_holds(self):
        fs=FakeFS(self.source,self.compiled,fail=f"{m.BUCKET}/datasets/v0.3/train.jsonl")
        with self.assertRaises(OSError):m.verify_remote(fs,self.expected)
    def test_10_bounded_binary_stream(self):
        with mock.patch.object(m,"MAX_REMOTE_BYTES",4):
            with self.assertRaises(m.Hold):m.hash_binary(io.BytesIO(b"abcde"))
    def test_11_reject_text_stream(self):
        with self.assertRaises(m.Hold):m.hash_binary(io.StringIO("hello"))
    def test_12_nonterminated_last_line_count(self):
        self.assertEqual(m.hash_binary(io.BytesIO(b"abc\ndef"))[2],2)
    def test_13_unknown_source_split_holds(self):
        with self.assertRaises(m.Hold):m.verify_remote(FakeFS(self.source,self.compiled),{"train":self.expected["train"]})
    def test_14_bogus_pinned_source_hash_holds(self):
        bad=dict(self.expected);bad["train"]=("0"*64,bad["train"][1],bad["train"][2])
        with self.assertRaises(m.Hold):m.verify_remote(FakeFS(self.source,self.compiled),bad)
    def test_15_no_opt_in_no_hf_import(self):
        err=io.StringIO()
        with mock.patch.dict(sys.modules,{"huggingface_hub":None}),redirect_stderr(err):
            self.assertEqual(m.main(["--repo-root","/tmp"]),42)
        self.assertIn("opt-in",err.getvalue())
    def test_16_secret_in_remote_error_not_printed(self):
        fs=FakeFS(self.source,self.compiled,fail=f"{m.BUCKET}/datasets/v0.3/train.jsonl")
        fake=SimpleNamespace(HfFileSystem=lambda:fs)
        err=io.StringIO();out=io.StringIO()
        with mock.patch.object(m,"git_blob",side_effect=[b"def convert(source: Path, dest: Path)",*self.source.values()]),\
             mock.patch.dict(sys.modules,{"huggingface_hub":fake}),\
             redirect_stderr(err),redirect_stdout(out):
            self.assertEqual(m.main(["--repo-root","/tmp","--allow-read-only-private-v01-input-bytes"]),42)
        self.assertNotIn("SECRET_AUTH_TOKEN_DONT_ECHO",err.getvalue())
        self.assertEqual(out.getvalue(),"")
    def test_17_main_all_sources_with_fake_fs(self):
        fake=SimpleNamespace(HfFileSystem=lambda:FakeFS(self.source,self.compiled))
        err=io.StringIO();out=io.StringIO()
        # Must inject matching SOURCE_PINS Git bytes in deterministic iteration order.
        with mock.patch.object(m,"git_blob",side_effect=[b"def convert(source: Path, dest: Path)",self.source["train"],self.source["validation"]]),\
             mock.patch.dict(sys.modules,{"huggingface_hub":fake}),\
             redirect_stderr(err),redirect_stdout(out):
            self.assertEqual(m.main(["--repo-root","/tmp","--allow-read-only-private-v01-input-bytes"]),0,err.getvalue())
        r=json.loads(out.getvalue())
        self.assertEqual(r["hf_bucket_objects_read"],8)
        self.assertFalse(r["historical_bucket_immutability_proven"])
        self.assertEqual(r["train_admitted"],0)
        for x in m.RUN_DIRS:
            self.assertNotIn(x,out.getvalue())
    def test_18_schema_and_count_unique(self):
        self.assertEqual(len(m.RUN_DIRS),3)
        self.assertEqual(len({x[0] for x in m.RUN_DIRS.values()}),3)
        self.assertEqual(m.SCHEMA,"r58_g1_v01_three_job_primary_input_bytes_safe_v1")
    def test_19_no_secrets_or_source_payload_in_safe(self):
        r=m.verify_remote(FakeFS(self.source,self.compiled),self.expected)
        self.assertNotIn(self.source["train"].decode(),json.dumps(r))
        self.assertNotIn(m.BUCKET,json.dumps(r))
    def test_20_actual_compile_semantics_match_git_script_on_synthetic(self):
        # Actual repo module is present in standard Git checkout. Import it if importable.
        import importlib.util
        src=Path(__file__).resolve().parents[2]/"scripts/prepare_sft.py"
        if not src.exists():
            self.skipTest("historical source not available in isolated local tests")
        import tempfile
        spec=importlib.util.spec_from_file_location("v01_prepare_sft_test",src)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            inp=Path(td)/"source.jsonl";out=Path(td)/"compiled.jsonl"
            inp.write_bytes(self.source["train"])
            self.assertEqual(module.convert(inp,out),3)
            self.assertEqual(out.read_bytes(),self.compiled["train"])

if __name__=="__main__":unittest.main()

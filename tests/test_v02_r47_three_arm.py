"""CPU-only tests for legacy R47 triple-blind packaging and integrity gates."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from v02_r47_eval_validate import validate_prompts,write_blind

class R47Tests(unittest.TestCase):
    def fixture(self,root):
        rows=[];entries=[]
        for i in range(20):
            m=[{"role":"system","content":f"world {i//10}"},{"role":"user","content":f"input {i}"}]
            h=hashlib.sha256(json.dumps({"messages":m},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            rows.append({"messages":m})
            entries.append({"sample_id":f"eval-{i:03d}-{h[:12]}","prompt_sha256":h,"source_line":i+1})
        prompts=root/"prompts.jsonl";prompts.write_text("".join(json.dumps(x)+"\n" for x in rows))
        manifest=root/"manifest.json";manifest.write_text(json.dumps({"schema":"storyforge-blind-v1","count":20,"samples":entries}))
        results={}
        for arm in ("base","v01","v02"):
            p=root/(arm+".jsonl")
            p.write_text("".join(json.dumps({"messages":row["messages"],"response":f"{arm} response {i}"})+"\n" for i,row in enumerate(rows)))
            results[arm]=p
        return prompts,manifest,results
    def test_pack_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            self.assertEqual(len(validate_prompts(f,m)[0]),20)
            output=p/"output"
            result=write_blind(f,m,r,output)
            self.assertEqual(result["responses"],60)
            self.assertTrue((output/"private/R47_PRIVATE_ANSWER_KEY.json").is_file())
            self.assertEqual(len(list((output/"blind-review").glob("R47_Reviewer_*.csv"))),3)
            with self.assertRaises(FileExistsError):write_blind(f,m,r,output)
    def test_bad_prompt_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            f.write_text(f.read_text().replace("input 0","different input",1))
            with self.assertRaises(ValueError):validate_prompts(f,m)
    def test_result_misalignment_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            rows=r["v02"].read_text().splitlines();rows[0]=rows[1]
            r["v02"].write_text("\n".join(rows)+"\n")
            with self.assertRaises(ValueError):write_blind(f,m,r,p/"output")
    def test_loss_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            rows=[json.loads(s) for s in f.read_text().splitlines()]
            rows[0]["messages"][0]["loss"]=True
            f.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            with self.assertRaises(ValueError):validate_prompts(f,m)
    def test_swift_infer_output_with_null_loss_and_appended_assistant(self):
        # ms-swift may serialize loss:null on input turns and append its
        # assistant output under messages; both representations must agree.
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            import json as _json
            rows=[_json.loads(x) for x in r["base"].read_text().splitlines()]
            for row in rows:
                for message in row["messages"]:
                    message["loss"]=None
                row["messages"].append({"role":"assistant","content":row["response"]})
            r["base"].write_text("\n".join(_json.dumps(x) for x in rows)+"\n")
            from v02_r47_eval_validate import validate_responses
            prompts=[_json.loads(x) for x in f.read_text().splitlines()]
            self.assertEqual(len(validate_responses(r["base"],prompts)),20)
            self.assertEqual(write_blind(f,m,r,p/"output")["responses"],60)

    def test_appended_assistant_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            rows=[json.loads(x) for x in r["base"].read_text().splitlines()]
            rows[0]["messages"].append({"role":"assistant","content":"wrong response"})
            r["base"].write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            from v02_r47_eval_validate import validate_responses
            with self.assertRaises(ValueError):
                validate_responses(r["base"],[json.loads(x) for x in f.read_text().splitlines()])

    def test_swift_prompt_changed_is_not_tolerated(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f,m,r=self.fixture(p)
            rows=[json.loads(x) for x in r["base"].read_text().splitlines()]
            rows[0]["messages"][0]["content"]="different system"
            for row in rows:
                for item in row["messages"]:item["loss"]=None
            r["base"].write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            from v02_r47_eval_validate import validate_responses
            with self.assertRaises(ValueError):
                validate_responses(r["base"],[json.loads(x) for x in f.read_text().splitlines()])
if __name__=="__main__":unittest.main()

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from r58_assistant_first_sft_probe import convert, prepare, canon, SOURCE_SCHEMA
from test_gold195_assistant_first_semantic_pilot import example

class R58AssistantFirstSFTProbeTest(unittest.TestCase):
    def records(self):
        result=[]
        for i in range(132):
            e=example(i)
            result.append({
                "schema":SOURCE_SCHEMA,"review_label":f"full{i+1:03d}",
                "original_history":e["original_history"],
                "original_history_sha256":e["original_history_sha256"],
                "source_target_sha256":e["source_target_sha256"],
                "current_user_text":e["current_user_text"],
                "frozen_target_text":e["frozen_target_text"],
                "source_card_snapshot":e["source_card_snapshot"],
                "training_authorized":False,
            })
        return result

    def test_preserves_leading_assistant_and_final_only_loss(self):
        rows=self.records()
        probes=convert(rows)
        self.assertEqual(len(probes),132)
        for i, p in enumerate(probes):
            messages=p["messages"]
            self.assertEqual(messages[0]["role"],"system")
            self.assertEqual(messages[1]["role"],"assistant")
            self.assertEqual(messages[1]["content"],rows[i]["original_history"][0]["content"])
            self.assertEqual([x["content"] for x in messages[1:-2]],
                             [x["content"] for x in rows[i]["original_history"]])
            self.assertEqual(messages[-2]["role"],"user")
            self.assertEqual(messages[-2]["content"],rows[i]["current_user_text"])
            self.assertEqual(messages[-1]["content"],rows[i]["frozen_target_text"])
            self.assertTrue(messages[-1]["loss"])
            self.assertFalse(any(x["loss"] for x in messages[:-1]))
            self.assertNotIn("PRIVATE_CARD_",json.dumps(messages))

    def test_private_output_and_hash_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            private=base/"private"
            private.mkdir(mode=0o700)
            input_path=private/"source.jsonl"
            input_path.write_bytes(b"".join(canon(x)+b"\n" for x in self.records()))
            input_path.chmod(0o600)
            output=private/"probe.jsonl"
            report=prepare(input_path,output,base/"repo")
            self.assertEqual(report["rows"],132)
            self.assertFalse(report["training_authorized"])
            self.assertEqual(report["quality_v1_admitted"],0)
            self.assertEqual(output.stat().st_mode & 0o777,0o600)
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),report["output_sha256"])
            self.assertEqual(len(output.read_text().splitlines()),132)
            with self.assertRaises(ValueError):
                prepare(input_path,output,base/"repo")

    def test_bad_provenance_or_history_refused(self):
        rows=self.records()
        rows[0]["original_history"][0]["content"]="MUTATED"
        with self.assertRaises(ValueError):
            convert(rows)
        rows=self.records()
        rows[0]["training_authorized"]=True
        with self.assertRaises(ValueError):
            convert(rows)
        rows=self.records()
        rows[0]["original_history"][0]["role"]="user"
        with self.assertRaises(ValueError):
            convert(rows)

if __name__=="__main__":
    unittest.main()

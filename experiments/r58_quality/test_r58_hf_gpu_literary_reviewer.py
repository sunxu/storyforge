import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from r58_hf_gpu_literary_reviewer import (
    PILOT_SCHEMA, MODELS, canon, read_source, prompt_messages,
    response_schema, validate_response, run, save_checkpoint,
    read_checkpoint, checkpoint_path,
)
from r58_gold195_blind_quality_pilot13 import blind_material
from gold195_six_dimension_review_tasks import prepare_row
from test_gold195_six_dimension_review_tasks import example

REV = "a" * 40


def source_rows():
    rows = []
    for i in range(13):
        e = example(i, leading=(i % 2 == 0))
        e["story_uuid"] = f"synthetic-{i}"
        task, reason = prepare_row(e)
        assert reason is None
        rows.append(blind_material(task, f"synthetic-blind-{i}"))
    return rows


def completed_response(row, decision="PASS"):
    return {
        "decision": decision,
        "scores": {
            "chinese_prose": 4, "character_consistency": 4,
            "npc_initiative": 3, "player_agency": 4,
            "rule_fidelity": 4, "narrative_continuity": 4,
        },
        "severe_flags": {
            "serious_player_agency": False, "hard_fact_or_ban": False,
            "safety_exclusion": False,
        },
        "card_snapshot_suitable_for_offline_training": True,
        "card_conflicts_with_visible_history_or_gold": False,
        "specific_source_quotes": [row["messages"][1]["content"]],
        "specific_target_quotes": [row["target_text"]],
        "literary_quality_notes": "独立质量检验的纯合成评分说明，非真实文学结论。",
        "uncertainty": "仍需核对来源设定。" if decision == "HOLD" else "",
    }


class FakeTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "unapproved_card" in messages[1]["content"]
        return {"input_ids": [[11, 13, 17, 19]]}


class HFReviewerSyntheticTests(unittest.TestCase):
    def args(self, input_path, output_dir, slot="A", phase="pilot",
             preflight_only=False):
        return SimpleNamespace(
            slot=slot, model=MODELS[slot], revision=REV,
            input=input_path, output_dir=output_dir, phase=phase,
            preflight_only=preflight_only,
            max_model_len=32768, max_output_tokens=2400)

    def stage(self, root, slot="A"):
        inputdir = root / f"review_{slot}"
        inputdir.mkdir(mode=0o700)
        input_path = inputdir / "review.private.jsonl"
        input_path.write_bytes(b"".join(canon(x) + b"\n" for x in source_rows()))
        input_path.chmod(0o600)
        output_dir = root / f"output_{slot}"
        output_dir.mkdir(mode=0o700)
        return input_path, output_dir

    def test_model_slots_and_schema_are_independent(self):
        self.assertNotEqual(MODELS["A"], MODELS["B"])
        schema = response_schema()
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertEqual(schema["properties"]["scores"]["type"], "object")
        self.assertEqual(schema["properties"]["specific_source_quotes"]["type"], "array")
        self.assertFalse(schema["additionalProperties"])
        row = source_rows()[0]
        messages = prompt_messages(row)
        self.assertEqual(len(messages), 2)
        self.assertNotIn(row["blind_id"], json.dumps(messages, ensure_ascii=False))
        payload = json.loads(messages[1]["content"].split("待审材料如下：\\n", 1)[1])
        self.assertEqual(row["messages"][0]["content"], payload["unapproved_card"])
        self.assertEqual(row["messages"][1:], payload["visible_history"])

    def test_pass_and_holds_with_exact_quote_validation(self):
        row = source_rows()[0]
        answer = completed_response(row)
        self.assertEqual(validate_response(answer, row), "PASS")
        bad = copy.deepcopy(answer)
        bad["specific_source_quotes"] = ["not-source-exact"]
        with self.assertRaises(ValueError):
            validate_response(bad, row)
        bad = copy.deepcopy(answer)
        bad["specific_target_quotes"] = ["not-target-exact"]
        with self.assertRaises(ValueError):
            validate_response(bad, row)
        bad = copy.deepcopy(answer)
        bad["scores"]["chinese_prose"] = 2
        with self.assertRaises(ValueError):
            validate_response(bad, row)
        bad = copy.deepcopy(answer)
        bad["severe_flags"]["hard_fact_or_ban"] = True
        with self.assertRaises(ValueError):
            validate_response(bad, row)
        answer = completed_response(row, "HOLD")
        self.assertEqual(validate_response(answer, row), "HOLD")
        answer["uncertainty"] = ""
        with self.assertRaises(ValueError):
            validate_response(answer, row)

    def test_preflight_without_vllm_or_gpu_then_pilot_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, out = self.stage(root)
            records = read_source(path)
            self.assertEqual(len(records), 13)
            self.assertTrue(all(x["schema"] == PILOT_SCHEMA for x in records))
            factory = lambda *args, **kwargs: FakeTokenizer()
            result = run(self.args(path, out, preflight_only=True),
                         tokenizer_factory=factory)
            self.assertEqual(result["planned"], 2)
            self.assertFalse(list(out.iterdir()))
            save_checkpoint(out, 0, records[0], completed_response(records[0]),
                            "A", MODELS["A"], REV)
            with self.assertRaises(FileExistsError):
                save_checkpoint(out, 0, records[0], completed_response(records[0]),
                                "A", MODELS["A"], REV)
            result = run(self.args(path, out, preflight_only=True),
                         tokenizer_factory=factory)
            self.assertEqual(result["planned"], 1)
            bad_args = self.args(path, out, slot="B", preflight_only=True)
            with self.assertRaises(ValueError):
                run(bad_args, tokenizer_factory=factory)

    def test_remaining_requires_pilot_and_final_matches_original(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, out = self.stage(root)
            records = read_source(path)
            args = self.args(path, out, phase="remaining")
            with self.assertRaises(ValueError):
                run(args, tokenizer_factory=lambda *a, **k: FakeTokenizer())
            for i in range(13):
                save_checkpoint(out, i, records[i],
                                completed_response(records[i], "HOLD" if i == 6 else "PASS"),
                                "A", MODELS["A"], REV)
            result = run(args)
            self.assertEqual(result["count"], 13)
            self.assertEqual(result["decisions"]["PASS"], 12)
            self.assertEqual(result["decisions"]["HOLD"], 1)
            self.assertEqual(result["quality_v1_admitted"], 0)
            self.assertFalse(result["training_authorized"])
            final = out / "reviewer_A.completed.private.jsonl"
            done = [json.loads(x) for x in final.read_text().splitlines()]
            self.assertEqual(len(done), 13)
            for old, new in zip(records, done):
                self.assertEqual({k: v for k, v in new.items() if k != "response"},
                                 {k: v for k, v in old.items() if k != "response"})
            self.assertEqual(final.stat().st_mode & 0o777, 0o600)

    def test_checkpoint_identity_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, out = self.stage(root)
            records = read_source(path)
            save_checkpoint(out, 0, records[0], completed_response(records[0]),
                            "A", MODELS["A"], REV)
            checkpoint = checkpoint_path(out, 0)
            content = json.loads(checkpoint.read_text())
            content["source_sha256"] = "0" * 64
            checkpoint.write_text(json.dumps(content))
            with self.assertRaises(ValueError):
                read_checkpoint(checkpoint, records[0], "A", MODELS["A"], REV, 0)


if __name__ == "__main__":
    unittest.main()

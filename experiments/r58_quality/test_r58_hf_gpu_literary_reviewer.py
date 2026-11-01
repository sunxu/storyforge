import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from r58_hf_gpu_literary_reviewer import (
    PILOT_SCHEMA, MODELS, REVIEW_KEYS, canon, read_source, prompt_messages,
    response_schema, validate_response, run, save_checkpoint,
    read_checkpoint, checkpoint_path, flatten_token_ids,
    QuoteValidationError, QuoteRepairFailure, quote_candidates,
    quote_repair_messages, quote_repair_schema, apply_quote_candidate,
    safe_failure_result,
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
    def __init__(self):
        self.calls = []

    def apply_chat_template(self, messages, **kwargs):
        self.calls.append(copy.deepcopy(messages))
        assert messages[0]["role"] == "system"
        self.assert_payload(messages)
        return {"input_ids": [list(range(64))], "attention_mask": [[1] * 64]}

    @staticmethod
    def assert_payload(messages):
        assert len(messages) >= 2
        assert "unapproved_card" in messages[1]["content"]


class FakeEngine:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, prompts, params, use_tqdm=False):
        self.calls += 1
        if not self.responses:
            raise AssertionError("unexpected generation call")
        text = self.responses.pop(0)
        return [SimpleNamespace(outputs=[
            SimpleNamespace(finish_reason="stop", text=text)])]


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
        payload = json.loads(messages[1]["content"].split("待审材料如下：", 1)[1].strip())
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

    def test_quote_validation_diagnostic_is_safe_and_field_specific(self):
        row = source_rows()[0]
        bad = completed_response(row)
        bad["specific_source_quotes"] = ["not-source-exact"]
        with self.assertRaises(QuoteValidationError) as caught:
            validate_response(bad, row)
        error = caught.exception
        self.assertEqual(error.field, "specific_source_quotes")
        self.assertEqual(error.quote_index, 0)
        self.assertGreater(error.source_candidate_count, 0)
        self.assertNotIn("not-source-exact", str(error))
        self.assertEqual(str(error), "RESPONSE_NONEXACT_QUOTE")

        bad = completed_response(row)
        bad["specific_target_quotes"] = ["not-target-exact"]
        with self.assertRaises(QuoteValidationError) as caught:
            validate_response(bad, row)
        self.assertEqual(caught.exception.field, "specific_target_quotes")
        self.assertEqual(caught.exception.quote_index, 0)
        self.assertEqual(caught.exception.source_candidate_count, 1)

    def test_safe_failure_summary_contains_only_allowlisted_quote_metadata(self):
        error = QuoteValidationError("specific_source_quotes", 2, 7)
        error.case_index = 1
        error.repair_attempted = True
        safe = safe_failure_result(error)
        self.assertEqual(safe["reason_code"], "RESPONSE_NONEXACT_QUOTE")
        self.assertEqual(safe["case_index"], 1)
        self.assertEqual(safe["quote_field"], "specific_source_quotes")
        self.assertEqual(safe["quote_index"], 2)
        self.assertEqual(safe["source_candidate_count"], 7)
        self.assertTrue(safe["quote_repair_attempted"])
        self.assertFalse(safe["quote_repair_succeeded"])
        self.assertFalse(safe["private_text_emitted"])
        self.assertNotIn("quote_text", json.dumps(safe))

        repair_failure = QuoteRepairFailure("QUOTE_REPAIR_RESPONSE_INVALID", error, 1)
        failed = safe_failure_result(repair_failure)
        self.assertEqual(failed["reason_code"], "QUOTE_REPAIR_RESPONSE_INVALID")
        self.assertTrue(failed["quote_repair_attempted"])
        self.assertFalse(failed["quote_repair_succeeded"])
        self.assertNotIn("DO_NOT_LEAK_QUOTE_TEXT", json.dumps(failed))
        self.assertNotIn("quote_text", json.dumps(failed))

    def test_quote_candidates_are_exact_and_exclude_unapproved_card(self):
        row = source_rows()[0]
        target = quote_candidates(row, "specific_target_quotes")
        self.assertTrue(target)
        self.assertTrue(all(q in row["target_text"] for q in target))
        source = quote_candidates(row, "specific_source_quotes")
        visible = [m["content"] for m in row["messages"][1:]
                   if m["role"] in ("user", "assistant")]
        self.assertTrue(source)
        self.assertTrue(all(any(q in body for body in visible) for q in source))
        self.assertLessEqual(len(source), 128)
        self.assertEqual(quote_repair_schema(len(source))["properties"]
                         ["candidate_index"]["maximum"], len(source) - 1)

    def test_quote_candidate_repair_changes_only_failed_quote_field(self):
        row = source_rows()[0]
        original = completed_response(row)
        original["specific_target_quotes"] = ["not-target-exact"]
        error = QuoteValidationError("specific_target_quotes", 0, 1)
        candidate = quote_candidates(row, error.field)[0]
        repaired = apply_quote_candidate(original, row, error, candidate)
        self.assertEqual(repaired["specific_target_quotes"], [candidate])
        self.assertEqual(repaired["specific_source_quotes"],
                         original["specific_source_quotes"])
        for key in REVIEW_KEYS - {"specific_target_quotes"}:
            self.assertEqual(repaired[key], original[key])
        self.assertIn(candidate, row["target_text"])

    def test_one_bounded_quote_repair_saves_only_exact_valid_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, out = self.stage(root)
            rows = read_source(path)
            tokenizer = FakeTokenizer()
            first_bad = completed_response(rows[0])
            first_bad["specific_source_quotes"] = ["not-source-exact"]
            engine = FakeEngine([
                json.dumps(first_bad, ensure_ascii=False),
                json.dumps({"candidate_index": 0}),
                json.dumps(completed_response(rows[1]), ensure_ascii=False),
            ])
            result = run(
                self.args(path, out),
                engine_factory=lambda **kwargs: engine,
                tokenizer_factory=lambda *a, **k: tokenizer,
                sampling_params_factory=lambda **kwargs: kwargs,
                structured_outputs_factory=lambda **kwargs: kwargs,
            )
            self.assertEqual(result["decisions"]["PASS"], 2)
            self.assertEqual(result["quote_repair_attempts"], 1)
            self.assertEqual(result["quote_repair_successes"], 1)
            self.assertEqual(engine.calls, 3)
            self.assertEqual(len(tokenizer.calls), 3)
            repair_messages = tokenizer.calls[2]
            self.assertEqual(repair_messages[-2]["role"], "assistant")
            self.assertEqual(repair_messages[-1]["role"], "user")
            self.assertIn("specific_source_quotes", repair_messages[-1]["content"])
            self.assertIn("candidate_index", repair_messages[-1]["content"])
            self.assertIn("候选清单", repair_messages[-1]["content"])
            self.assertNotIn("只允许修改", repair_messages[-1]["content"])
            saved = read_checkpoint(
                checkpoint_path(out, 0), rows[0], "A", MODELS["A"], REV, 0)
            self.assertIn(saved["specific_source_quotes"][0], rows[0]["messages"][1]["content"])
            self.assertIsNotNone(read_checkpoint(
                checkpoint_path(out, 0), rows[0], "A", MODELS["A"], REV, 0))
            self.assertIsNotNone(read_checkpoint(
                checkpoint_path(out, 1), rows[1], "A", MODELS["A"], REV, 1))

    def test_failed_quote_repair_holds_without_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, out = self.stage(root)
            rows = read_source(path)
            tokenizer = FakeTokenizer()
            first_bad = completed_response(rows[0])
            first_bad["specific_source_quotes"] = ["not-source-exact"]
            engine = FakeEngine([
                json.dumps(first_bad, ensure_ascii=False),
                json.dumps({"candidate_index": 999}),
            ])
            with self.assertRaises(QuoteRepairFailure) as caught:
                run(
                    self.args(path, out),
                    engine_factory=lambda **kwargs: engine,
                    tokenizer_factory=lambda *a, **k: tokenizer,
                    sampling_params_factory=lambda **kwargs: kwargs,
                    structured_outputs_factory=lambda **kwargs: kwargs,
                )
            self.assertEqual(caught.exception.code, "QUOTE_REPAIR_SELECTION_INVALID")
            self.assertEqual(caught.exception.case_index, 0)
            self.assertEqual(caught.exception.quote_error.field, "specific_source_quotes")
            self.assertEqual(caught.exception.quote_error.quote_index, 0)
            self.assertFalse(checkpoint_path(out, 0).exists())
            self.assertFalse(any(out.iterdir()))

    def test_batchencoding_field_count_is_not_token_count(self):
        encoded = {"input_ids": [list(range(64))], "attention_mask": [[1] * 64]}
        self.assertEqual(len(flatten_token_ids(encoded, prompt_chars=1000)), 64)
        for malformed in (
            {"input_ids": [[1, 2]], "attention_mask": [[1, 1]]},
            {"attention_mask": [[1, 1]]},
            {"input_ids": []},
            {"input_ids": [[1, -2] * 20]},
        ):
            with self.assertRaises(ValueError):
                flatten_token_ids(malformed, prompt_chars=1000)

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

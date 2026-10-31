#!/usr/bin/env python3
"""Synthetic-only tests; no HF authentication, HTTP or private files."""
from __future__ import annotations
import json
import types
import unittest
from unittest import mock
from check_hf_training_job_inventory import (KNOWN_SFT_JOBS, Hold, summarize,
                                            stage_only, MAX_JOBS)

class FakeJob:
    def __init__(self, ident, stage="COMPLETED"):
        self.id = ident
        self.status = types.SimpleNamespace(stage=stage)
        self._contents = "never-read"
    @property
    def command(self):
        raise AssertionError("COMMAND_ACCESSED")
    @property
    def environment(self):
        raise AssertionError("ENVIRONMENT_ACCESSED")
    @property
    def secrets(self):
        raise AssertionError("SECRETS_ACCESSED")
    @property
    def arguments(self):
        raise AssertionError("ARGUMENTS_ACCESSED")


def jobs():
    return [FakeJob(ident) for ident in KNOWN_SFT_JOBS.values()]

class HFInventoryTests(unittest.TestCase):
    def test_all_known_jobs_found_still_hold(self):
        result = summarize(jobs(), "adradar")
        self.assertEqual(result["known_sft_or_training_smoke_job_ids_found"], 5)
        self.assertEqual(result["known_sft_or_training_smoke_job_ids_missing"], 0)
        self.assertEqual(result["hf_jobs_returned"], 5)
        self.assertFalse(result["all_actual_sft_runs_and_input_sources_proven_complete"])
        self.assertEqual(result["g1_clearance"], "HOLD")
        self.assertFalse(result["expansion_allowed"])
    def test_missing_job_is_hold(self):
        result = summarize(jobs()[:-1], "adradar")
        self.assertEqual(result["known_sft_or_training_smoke_job_ids_missing"], 1)
        self.assertIn("KNOWN_IDS_MISSING", result["status"])
    def test_unclassified_job_not_a_new_training(self):
        result = summarize(jobs()+[FakeJob("e"*24)], "adradar")
        self.assertEqual(result["other_job_ids_unclassified"], 1)
        self.assertFalse(result["unknown_jobs_proven_non_training"])
    def test_no_job_commands_secrets_or_environment_accessed(self):
        result = summarize(jobs(), "adradar")
        self.assertFalse(result["job_commands_arguments_environment_or_secrets_read_or_exported"])
    def test_output_contains_no_job_id(self):
        result = json.dumps(summarize(jobs()+[FakeJob("e"*24)], "adradar"))
        for ident in (*KNOWN_SFT_JOBS.values(), "e"*24):
            self.assertNotIn(ident, result)
    def test_duplicate_id_fails(self):
        with self.assertRaises(Hold): summarize(jobs()+jobs()[:1], "adradar")
    def test_malformed_id_fails(self):
        with self.assertRaises(Hold): summarize(jobs()+[FakeJob("secret")], "adradar")
    def test_missing_status_fails(self):
        job = FakeJob("f"*24)
        job.status = None
        with self.assertRaises(Hold): summarize(jobs()+[job], "adradar")
    def test_invalid_status_fails(self):
        with self.assertRaises(Hold): summarize(jobs()+[FakeJob("f"*24, "INVALID")], "adradar")
    def test_error_and_canceled_stages_preserved(self):
        test_jobs=jobs()
        test_jobs[0].status.stage="ERROR"
        test_jobs[1].status.stage="CANCELED"
        result=summarize(test_jobs,"adradar")
        self.assertEqual(result["hf_jobs_by_stage"]["ERROR"],1)
        self.assertEqual(result["hf_jobs_by_stage"]["CANCELED"],1)
    def test_no_jobs_is_hold(self):
        result=summarize([],"adradar")
        self.assertEqual(result["known_sft_or_training_smoke_job_ids_missing"],5)
    def test_invalid_namespace_fails(self):
        with self.assertRaises(Hold): summarize(jobs(),"../private")
    def test_job_stage_enum_value_is_accepted(self):
        job=FakeJob("f"*24)
        job.status.stage=types.SimpleNamespace(value="COMPLETED")
        self.assertEqual(stage_only(job),"COMPLETED")
    def test_yielded_partial_then_exception_propagates(self):
        def broken():
            yield jobs()[0]
            raise RuntimeError("pagination failed")
        with self.assertRaises(RuntimeError):summarize(broken(),"adradar")
    def test_100k_limit_guard_fails(self):
        # synthetic generator with identical extra IDs stopped at duplicate first
        with mock.patch("check_hf_training_job_inventory.MAX_JOBS", 2):
            with self.assertRaises(Hold):summarize(jobs(),"adradar")
    def test_no_optional_private_ledger_output_keys(self):
        result=summarize(jobs(),"adradar")
        self.assertNotIn("private_ledger",result)
        self.assertEqual(result["train_admitted"],0)

if __name__=="__main__":unittest.main()

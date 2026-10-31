#!/usr/bin/env python3
"""All-synthetic/no-HF regression tests for HF Job Git-document coverage."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock
from check_hf_training_job_inventory import KNOWN_SFT_JOBS, Hold
from check_hf_job_documentation_coverage import (
    checked_tree_entries, JOB_IN_DOC, classify, frozen_job_mentions, summarize_from_facts
)


def job(i,stage='COMPLETED'):
    class J:
        id=i
        status=types.SimpleNamespace(stage=stage)
        @property
        def command(self): raise AssertionError('command read')
        @property
        def environment(self): raise AssertionError('environment read')
        @property
        def arguments(self): raise AssertionError('arguments read')
        @property
        def secrets(self): raise AssertionError('secrets read')
    return J()


def known():return [job(v) for v in KNOWN_SFT_JOBS.values()]


def tree(p='docs/HF_RUN_REGISTRY.md',sha='a'*40,mode='100644'):
    return f'{mode} blob {sha}\t{p}'.encode()+b'\0'

class Tests(unittest.TestCase):
    def test_01_known_jobs_all_present_no_automatic_clear(self):
        result=classify(known(),set(), 'adradar',5)
        self.assertEqual(result['known_parameter_update_job_ids_found'],5)
        self.assertFalse(result['source_registry_complete'])
        self.assertEqual(result['g1_clearance'],'HOLD')
    def test_02_other_docs_and_unmentioned_split(self):
        result=classify(known()+[job('a'*24),job('b'*24,'ERROR')],{'a'*24},'adradar',3)
        self.assertEqual(result['other_job_ids_mentioned_in_frozen_safe_docs'],1)
        self.assertEqual(result['other_job_ids_not_mentioned_in_frozen_safe_docs'],1)
        self.assertFalse(result['document_mention_proves_non_training'])
    def test_03_no_job_id_in_output(self):
        result=json.dumps(classify(known()+[job('a'*24)],{'a'*24},'adradar',2))
        for i in [*KNOWN_SFT_JOBS.values(),'a'*24]:self.assertNotIn(i,result)
    def test_04_hf_sensitive_fields_not_read(self):
        result=classify(known(),set(),'adradar',3)
        self.assertFalse(result['job_commands_arguments_environment_or_secrets_from_hf_accessed'])
    def test_05_duplicate_job_id_blocked(self):
        with self.assertRaises(Hold):classify(known()+known()[:1],set(),'adradar',1)
    def test_06_unknown_status_blocked(self):
        with self.assertRaises(Hold):classify([job('a'*24,'WHATEVER')],set(),'adradar',1)
    def test_07_doc_id_regex_not_hash_prefix(self):
        blob=(b' x='+b'a'*24+b' y='+b'b'*64+b' z='+b'c'*24+b';')
        self.assertEqual(JOB_IN_DOC.findall(blob),[b'a'*24,b'c'*24])
    def test_08_tree_entry_accepted(self):
        self.assertEqual(checked_tree_entries(tree()), [('docs/HF_RUN_REGISTRY.md','a'*40)])
    def test_09_tree_symlink_blocked(self):
        with self.assertRaises(Hold):checked_tree_entries(tree(mode='120000'))
    def test_10_tree_unexpected_scope_blocked(self):
        with self.assertRaises(Hold):checked_tree_entries(tree(p='private/evidence.md'))
    def test_11_tree_missing_registry_blocked(self):
        with self.assertRaises(Hold):checked_tree_entries(tree(p='docs/evidence/safe.md'))
    def test_12_tree_duplicate_blocked(self):
        with self.assertRaises(Hold):checked_tree_entries(tree()+tree())
    def test_13_tree_no_null_blocked_if_bad(self):
        with self.assertRaises(Hold):checked_tree_entries(b'bad\0')
    def test_14_invalid_namespace_blocked(self):
        with self.assertRaises(Hold):classify(known(),set(),'../org',2)
    def test_15_invalid_document_job_id_blocked(self):
        with self.assertRaises(Hold):classify(known(),{'INVALID'},'adradar',2)
    def test_16_document_coverage_only_not_run_completeness(self):
        result=classify(known(),set(),'adradar',4)
        self.assertFalse(result['all_historical_jobs_including_deleted_other_namespaces_proven_complete'])
        self.assertFalse(result['all_actual_sft_runs_and_input_sources_proven_complete'])
        self.assertFalse(result['remote_trainer_primary_input_bytes_verified'])
    def test_17_partial_enumeration_exception_propagates(self):
        def partial():
            yield known()[0]
            raise RuntimeError('failed page')
        with self.assertRaises(RuntimeError):classify(partial(),set(),'adradar',2)
    def test_18_job_listing_bound(self):
        with mock.patch('check_hf_job_documentation_coverage.MAX_JOBS',2):
            with self.assertRaises(Hold):classify(known(),set(),'adradar',2)
    def test_19_canceled_error_not_assumed_nontraining(self):
        result=classify(known()+[job('a'*24,'CANCELED'),job('b'*24,'ERROR')],set(),'adradar',1)
        self.assertFalse(result['all_job_roles_proven'])
        self.assertEqual(result['other_undocumented_job_status_counts']['ERROR'],1)
        self.assertEqual(result['other_undocumented_job_status_counts']['CANCELED'],1)
    def test_21_safe_sql_queries_skipped_without_failure(self):
        raw=tree()+tree(p='docs/evidence/R58_AUDIT_QUERY_SAFE.sql')
        self.assertEqual(len(checked_tree_entries(raw)),1)

    def test_22_actual_frozen_git_blob_scan_only_tracked_safe_docs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'docs/evidence').mkdir(parents=True)
            (root/'docs/HF_RUN_REGISTRY.md').write_text('known '+next(iter(KNOWN_SFT_JOBS.values())),encoding='utf-8')
            (root/'docs/evidence/other.md').write_text('other '+'a'*24,encoding='utf-8')
            (root/'docs/evidence/skip.sql').write_text('sql '+'b'*24,encoding='utf-8')
            (root/'docs/evidence/local-private.md').write_text('untracked '+'c'*24,encoding='utf-8')
            commands=[['git','init','-q'],['git','add','docs/HF_RUN_REGISTRY.md','docs/evidence/other.md','docs/evidence/skip.sql'],['git','-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','test']]
            for cmd in commands:
                subprocess.run(cmd,cwd=root,check=True,capture_output=True)
            result,n=frozen_job_mentions(root)
            self.assertEqual(n,2)
            self.assertIn('a'*24,result)
            self.assertNotIn('b'*24,result)
            self.assertNotIn('c'*24,result)

    def test_20_no_docs_blocked(self):
        with self.assertRaises(Hold):classify(known(),set(),'adradar',0)

if __name__=='__main__':unittest.main()

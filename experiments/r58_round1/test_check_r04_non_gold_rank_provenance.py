#!/usr/bin/env python3
"""Synthetic-only G1 R04 rank provenance tests. Never read real R50/private case data."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout, redirect_stderr

import check_r04_non_gold_rank_provenance as m
from test_check_r04_non_gold_uuid import uid, snapshots, hashes

RANKS = list(range(6, 16))
MAPPING = {rank:uid(n) for n,rank in enumerate([6,8,9,10,12,13,14,15])}
MAPPING[7]=uid(8)
MAPPING[11]=uid(9)


def synthetic():
    r04,gold=snapshots()
    names=['story_number','story_id','raw_archive_sha256','source_json_equals_jsonl',
           'messages_total','story_created_at']
    buf=io.StringIO(newline='')
    writer=csv.DictWriter(buf,fieldnames=names)
    writer.writeheader()
    archive=[]
    for rank in RANKS:
        digest=hashlib.sha256(f'synthetic-source-{rank}'.encode()).hexdigest()
        writer.writerow({'story_number':rank,'story_id':MAPPING[rank],
                         'raw_archive_sha256':digest,
                         'source_json_equals_jsonl':'True','messages_total':'100',
                         'story_created_at':'synthetic'})
        archive.append({'story_number':rank,'raw_zip_sha256':digest})
    manifest={'schema':'storyforge.v0.2.06-15.github-evidence-index.v1',
              'bundle_sha256':m.EXPECTED_BUNDLE_SHA256,
              'raw_story_zip_count':10,'nested_source_sha256':archive}
    return r04,gold,buf.getvalue().encode(),json.dumps(manifest).encode()


def data_reconcile(args):
    r,g,i,manifest=args
    return m.reconcile(r,g,i,manifest,*hashes(r,g),verify_metadata_git_pins=False)


class ProvenanceTests(unittest.TestCase):
    def test_01_complete_ten_rank_linkage(self):
        result=data_reconcile(synthetic())
        self.assertTrue(result['r04_minus_gold108_is_exactly_ranks_07_and_11'])
        self.assertEqual(result['original_raw_archive_sha256_links_verified'],10)
        self.assertEqual(result['g1_clearance'],'HOLD')
        self.assertEqual(result['train_admitted'],0)
        self.assertFalse(result['private_ledgers_accessed'])
        self.assertFalse(result['r50_protected_content_accessed'])
        self.assertNotIn(uid(8),json.dumps(result))
    def test_02_missing_inventory_rank_holds(self):
        r,g,inv,man=synthetic()
        inv=inv.replace(b'6,',b'17,',1)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_03_wrong_rank_uuid_mapping_holds(self):
        r,g,inv,man=synthetic()
        inv=inv.replace(uid(7).encode(),uid(8).encode(),1)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_04_wrong_archive_zip_digest_holds(self):
        r,g,inv,man=synthetic()
        obj=json.loads(man);obj['nested_source_sha256'][4]['raw_zip_sha256']='a'*64
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,json.dumps(obj).encode()))
    def test_05_missing_archive_rank_holds(self):
        r,g,inv,man=synthetic()
        obj=json.loads(man);obj['nested_source_sha256'][-1]['story_number']=14
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,json.dumps(obj).encode()))
    def test_06_bad_bundle_digest_holds(self):
        r,g,inv,man=synthetic()
        obj=json.loads(man);obj['bundle_sha256']='0'*64
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,json.dumps(obj).encode()))
    def test_07_original_source_not_certified_holds(self):
        r,g,inv,man=synthetic()
        inv=inv.replace(b'True',b'False',1)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_08_duplicate_world_uuid_holds(self):
        r,g,inv,man=synthetic()
        inv=inv.replace(uid(9).encode(),uid(8).encode())
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_09_unknown_inventory_column_schema_holds(self):
        r,g,inv,man=synthetic()
        inv=inv.replace(b'raw_archive_sha256',b'wrong_sha_field',1)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_10_r04_tampered_hash_holds(self):
        r,g,inv,man=synthetic()
        with self.assertRaises(m.Hold):m.reconcile(r,g,inv,man)
    def test_11_gold_not_exact_subset_holds(self):
        r,g,inv,man=synthetic()
        g=g.replace(b'synthetic-only',b'changed!',1)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_12_rearranged_rank_uuid_fails_world_alignment(self):
        r,g,inv,man=synthetic()
        # Swap a Gold world UUID with one non-Gold world UUID in the fixed rank index.
        gold_uid=uid(0).encode();other=uid(8).encode()
        inv=inv.replace(gold_uid,b'placeholder').replace(other,gold_uid).replace(b'placeholder',other)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_13_cli_holds_if_source_unavailable(self):
        err=io.StringIO()
        with (mock.patch.object(m,'frozen_blob',side_effect=m.Hold('private source')),redirect_stderr(err)):
            self.assertEqual(m.main(['--repo-root','/does-not-exist']),42)
        self.assertIn('HOLD',err.getvalue())
        self.assertNotIn('private source',err.getvalue())
    def test_14_cli_no_private_files(self):
        r,g,inv,man=synthetic()
        source_by_pin={m.R04_BLOB:r,m.GOLD108_BLOB:g,m.INVENTORY_BLOB:inv,m.MANIFEST_BLOB:man}
        out=io.StringIO()
        original_reconcile = m.reconcile
        with (mock.patch.object(m,'frozen_blob',side_effect=lambda repo,sha,limit:source_by_pin[sha]),
              mock.patch.object(m,'reconcile',side_effect=lambda *args:original_reconcile(*args,*hashes(r,g),verify_metadata_git_pins=False)),
              redirect_stdout(out)):
            self.assertEqual(m.main(['--repo-root','/synthetic']),0)
        self.assertTrue(json.loads(out.getvalue())['r04_minus_gold108_is_exactly_ranks_07_and_11'])
    def test_15_missing_inventory_row_holds(self):
        r,g,inv,man=synthetic()
        lines=inv.splitlines(keepends=True);inv=b''.join(lines[:-1])
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))
    def test_16_non_uuid_story_id_holds(self):
        r,g,inv,man=synthetic()
        inv=inv.replace(uid(8).encode(),b'not-a-uuid',1)
        with self.assertRaises(m.Hold):data_reconcile((r,g,inv,man))


if __name__=='__main__':
    unittest.main()

"""Synthetic-only tests for source-position to final-release mapping."""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from collections import Counter

import pytest

MODULES = (
    'r60_base336_exploratory_release_verify',
    'r60_base336_exploratory_split',
    'r60_base336_story_json_shape_cpu',
    'r60_base_start_cpu336_template_audit',
    'r60_base336_world_cross_split_private_roster_cpu',
    'r60_real_private_batch',
)


def load(monkeypatch):
    for name in MODULES:
        module = types.ModuleType(name)
        if name == 'r60_base336_exploratory_split':
            module._encode = lambda rows: b''.join((json.dumps(row, sort_keys=True, separators=(',', ':'))+'\n').encode() for row in rows)
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location('actual_release_under_test', Path(__file__).with_name('r60_base336_actual_release_scope_cpu.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(module):
    held = [{'position': n} for n in range(1,337)]
    rows = [{'messages':[{'role':'user','content':f'synthetic-{n}'}]} for n in range(1,337)]
    data = {
        'train':module.split._encode(rows[:293]),
        'validation':module.split._encode(rows[293:]),
    }
    return held,rows,data


def test_maps_final_release_not_preview(monkeypatch):
    m=load(monkeypatch)
    held,rows,data=fixture(m)
    actual=m.classify_positions(held,rows,data)
    assert len(actual)==336
    assert Counter(actual.values())==Counter({'train':293,'validation':43})
    assert actual[293]=='train'
    assert actual[294]=='validation'


def test_rejects_row_tamper(monkeypatch):
    m=load(monkeypatch)
    held,rows,data=fixture(m)
    data['train']=data['train'].replace(b'synthetic-1',b'tampered-1')
    with pytest.raises(m.Hold,match='RELEASE_ROW_MAPPING_HOLD'):
        m.classify_positions(held,rows,data)


def test_rejects_identical_row_in_both_splits(monkeypatch):
    m=load(monkeypatch)
    held,rows,data=fixture(m)
    rows[0]=rows[293].copy()
    data['train']=m.split._encode(rows[:293])
    data['validation']=m.split._encode(rows[293:])
    with pytest.raises(m.Hold,match='CROSS_SPLIT_IDENTICAL_ROW_PROVENANCE_HOLD'):
        m.classify_positions(held,rows,data)


def test_rejects_duplicate_source_position(monkeypatch):
    m=load(monkeypatch)
    held,rows,data=fixture(m)
    held[1]['position']=held[0]['position']
    with pytest.raises(m.Hold,match='DUPLICATE_FROZEN_POSITION_HOLD'):
        m.classify_positions(held,rows,data)


def test_rejects_missing_source_row(monkeypatch):
    m=load(monkeypatch)
    held,rows,data=fixture(m)
    with pytest.raises(m.Hold,match='FROZEN_POSITION_COUNT_HOLD'):
        m.classify_positions(held[:335],rows,data)

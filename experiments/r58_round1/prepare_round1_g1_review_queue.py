#!/usr/bin/env python3
"""R58 Round1: metadata-only private G1 review queue (not a shortlist or admission).

Reads only the Owner's already exported story-level CSV, creates at most five
private review rows with every exclusion gate false, and prints SAFE aggregates.
No protected-set lookups, no text, no training, no automatic expansion.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from pilot_round1_shortlist import CATEGORIES, STORY_FIELDS, Hold, discover, private_csv

REQUIRED_GUARD_FIELDS = [
    'story_id', 'world_component', 'owner_world_graph_reviewed',
    'r50_protected_clear', 'prior_sft_clear', 'r55_r57_dev_clear',
    'other_protected_clear', 'evidence_reference',
]
EXTRA_FIELDS = ['source_type', 'review_state']
OUTPUT_FIELDS = REQUIRED_GUARD_FIELDS + EXTRA_FIELDS
SCHEMA = 'r58_round1_g1_private_review_queue_v1'
QUEUE_STATUS = 'R58_ROUND1_G1_METADATA_REVIEW_QUEUE_CREATED__ALL_GUARDS_HOLD'


def prepare_queue(rows: list[dict]) -> list[dict]:
    eligible=discover(rows)
    queue=[]
    for kind, limit in CATEGORIES.items():
        by_kind=sorted(
            (row for row in eligible if row['source_type']==kind),
            key=lambda row: (
                -row['session_count'],
                -row['assistant_completed'],
                row['story_id'],
            ),
        )
        for candidate in by_kind[:limit]:
            review={
                key: ('false' if key in (
                    'owner_world_graph_reviewed','r50_protected_clear',
                    'prior_sft_clear','r55_r57_dev_clear',
                    'other_protected_clear',
                ) else '')
                for key in REQUIRED_GUARD_FIELDS
            }
            review['story_id']=candidate['story_id']
            review['source_type']=kind
            review['review_state']='G1_HOLD'
            queue.append(review)
    if len(queue)>5 or len({x['story_id'] for x in queue})!=len(queue):
        raise Hold('G1 review queue cap or uniqueness violation')
    return queue


def save_private_csv(path: Path, rows: list[dict]) -> None:
    parent=path.parent
    if (
        path.is_symlink() or path.exists()
        or not parent.is_dir() or parent.is_symlink()
        or (parent.stat().st_mode & 0o077)
    ):
        raise Hold('private output directory or destination invalid')
    fd=os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=OUTPUT_FIELDS,extrasaction='raise')
            writer.writeheader()
            writer.writerows(rows)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(inventory: Path, output: Path) -> dict:
    if inventory.resolve()==output.resolve():
        raise Hold('cannot overwrite inventory')
    rows=private_csv(inventory,STORY_FIELDS)
    queue=prepare_queue(rows)
    if not queue:
        raise Hold('no metadata review queue candidates')
    save_private_csv(output,queue)
    return {
        'schema':SCHEMA,
        'status':QUEUE_STATUS,
        'owner_private_inventory_rows':len(rows),
        'queue_story_records':len(queue),
        'queue_by_source':{
            group:sum(x['source_type']==group for x in queue)
            for group in CATEGORIES
        },
        'actual_world_components_verified':0,
        'protected_worlds_checked':False,
        'existing_training_exposure_checked':False,
        'quality_review_started':False,
        'private_reply_text_read':False,
        'all_guard_flags_default_false':True,
        'pilot_max_worlds':5,
        'pilot_max_reply_targets':20,
        'selection_status':'G1_METADATA_REVIEW_QUEUE_ONLY__NOT_SHORTLISTED',
        'train_admitted':0,
        'validation_admitted':0,
        'teacher_admitted':0,
        'expansion_allowed':False,
        'owner_expansion_approval':'REQUIRED',
    }


def main()->int:
    parser=argparse.ArgumentParser(description='Owner-local R58 G1 metadata review queue')
    parser.add_argument('--inventory',required=True,type=Path)
    parser.add_argument('--private-output',required=True,type=Path)
    args=parser.parse_args()
    try:
        print(json.dumps(run(args.inventory,args.private_output),
                         ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (Hold,OSError,ValueError,TypeError,KeyError):
        print('R58_ROUND1_G1: HOLD (source/output/scope)',file=sys.stderr)
        return 42


if __name__=='__main__':
    raise SystemExit(main())

"""R50 exact source-ID cross-check against historic Gold195 and exposed Test20.

A matching UUID is a blocker. Nonmatching UUIDs do NOT prove semantic isolation.
No inference or training, and no raw narrative text in output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path('evaluations/v0.2/source-archives/16-20')
HISTORIC = (
    ('evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl', 87),
    ('evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl', 108),
    ('evaluations/v0.1/test/prompts.jsonl', 20),
)


def read_jsonl(path: Path):
    with path.open(encoding='utf-8-sig') as stream:
        for idx, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f'blank line in {path.name}: {idx}')
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f'non-object in {path.name}: {idx}')
            yield row


def check(repo: Path) -> dict:
    stories = []
    for directory in sorted((repo / ROOT).iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError('unexpected source entry')
        age = json.loads((directory / 'age-review.json').read_text(encoding='utf-8'))
        runtime = json.loads((directory / 'runtime-context.json').read_text(encoding='utf-8'))
        if age['story_id'] != runtime['story_id'] or age['rank'] != runtime['rank']:
            raise ValueError(f'source metadata mismatch: {directory.name}')
        if not directory.name.startswith(f"{age['rank']}-"):
            raise ValueError(f'source folder rank mismatch: {directory.name}')
        stories.append({'rank': age['rank'], 'story_id': age['story_id'],
                        'session_id': runtime['session_id'],
                        'explicit_under18_in_card': bool(age['has_explicit_under_18']),
                        'sample_level_age_review_required': bool(age['requires_sample_level_review'])})
    if len(stories) != 5 or {r['rank'] for r in stories} != set(range(16, 21)):
        raise ValueError('five source folders required')
    for field in ('story_id', 'session_id'):
        if len({r[field] for r in stories}) != 5:
            raise ValueError(f'duplicate {field} among new worlds')

    counts = {}
    known_ids = {'story_id': set(), 'session_id': set()}
    for rel, expected in HISTORIC:
        rows = 0
        for row in read_jsonl(repo / rel):
            rows += 1
            metadata = row.get('metadata') or {}
            if not isinstance(metadata, dict):
                raise ValueError(f'invalid historical metadata in {rel}')
            for field in known_ids:
                val = metadata.get(field)
                if isinstance(val, str) and val.strip():
                    known_ids[field].add(val)
        if rows != expected:
            raise ValueError(f'historical reference count not {expected}: {rel}: {rows}')
        counts[rel] = rows
    collisions = {
        field: sorted({s[field] for s in stories} & old)
        for field, old in known_ids.items()
    }
    if any(collisions.values()):
        raise ValueError('historic Gold195 exact ID collision; HOLD')
    return {
        'schema': 'storyforge-r50-exact-id-isolation-v1',
        'status': 'EXACT_METADATA_ID_SCREEN_PASS__SEMANTIC_WORLD_ISOLATION_PENDING',
        'world_count': 5, 'new_story_numbers': [s['rank'] for s in stories],
        'history_row_counts': counts,
        'known_historic_story_id_count': len(known_ids['story_id']),
        'known_historic_session_id_count': len(known_ids['session_id']),
        'exact_story_id_conflicts': collisions['story_id'],
        'exact_session_id_conflicts': collisions['session_id'],
        'sample_level_age_checks_still_required': True,
        'old_test_world_metadata_may_be_missing': True,
        'semantic_alias_review': 'PENDING',
        'r45_private_train_val_world_check': 'PENDING',
        'authorship_independence': 'PENDING',
        'heldout_cases_sealed': 0,
        'gpu_executed': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = check(args.repo.resolve())
        content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as f:
                f.write(content)
        else:
            print(content, end='')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'R50_EXACT_ID_ISOLATION_BLOCKED: {exc}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

# StoryForge Gold Quality Pipeline

## Purpose

One private append-only event Manifest for frozen source pins, legacy review evidence, historical exposure, incremental blind reviews, exclusions and adjudication. The CLI is an audit orchestrator, not a reviewer or training-admission shortcut.

Keep exact-target exposure, UUID exposure and semantic world-component isolation separate. Keep Gold87 selection evidence separate from its row metadata; keep Gold108 legacy five-dimension review separate from Quality-v1. Preserve Reviewer A/B disagreement as distinct events.

## Install and commands

```bash
python -m pip install -e .
storyforge-gold-quality inventory
storyforge-gold-quality verify-source --repo-root "$PWD"
```

Supported commands: `inventory`, `verify-source`, `import-history`, `import-exposure`, `append-review`, `append-exclusion`, `validate`, `report-safe`.

The private Manifest must live outside the Git checkout in a directory with mode 0700; the file is created with mode 0600. Writes are append-only and use no-follow file opening. Same-case target hash changes fail closed.

## Import contracts

- Gold87: one batch-level `LEGACY_SELECTION_EVIDENCE` event (87 cases, selection recorded, reviewer independence unproven) plus 87 row-level `SOURCE_METADATA` events (`independent_gold_review=NOT_RUN`, single Curator scores).
- Gold108: first run the existing `gold108_review_binding.py` and require its exact SAFE PASS status. Import 108 row-level `LEGACY_REVIEW` events and one batch-level binding receipt. Keep rubric `FIVE_DIMENSION_LEGACY`; `new_quality_v1=false`.
- Gold195 exposure: safe aggregate imports remain aggregate-only and set case-level exposure to `UNKNOWN_NOT_IMPORTED`. Row-level import requires the original R57 private ledger and the SAFE receipt from the same run proving source byte pins. No aggregate-to-row synthesis.
- Gold192: A/B/AI/adjudication events remain separate. The three unresolved-world exclusions are separate `EXCLUSION` events. Each review row carries six 1–5 scores and a reviewer role.

## Privacy and non-authorization

SAFE output contains counts only; never emit case IDs, story UUIDs, prose, alias maps or row-level target hashes. Quality-v1 admission remains zero; training, GPU and R50 access remain false. Tokenizer preflight continues to reuse only `src/storyforge_dataset/token_preflight.py`.

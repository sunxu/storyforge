# StoryForge v0.2 evidence archive (2026-10-12)

This directory is additive and does **not** alter v0.1 evidence or tag `v0.1-evidence-frozen`.

## Committed

- `gold-quality-87/gold_quality_accepted_87.jsonl`: 87 curator-quality-accepted, A/B double-ACCEPT original-text targets, **not** training-approved.
- `gold-quality-87/gold_87_index.csv`: sources and decisions.
- `gold-quality-87/other_25_closed_without_gold.csv`: 25 other candidates closed without Gold promotion.
- `gold-quality-87/README.md`: admission decision and qualifications.
- `curation/{01-jingquan,02-xianzun,03-snow-reunion,04-virgin-death,05-war-blood}/candidates_r*.jsonl`: latest candidate snapshots (30/27/15/13/27).
- `review/`: A/B aggregation, C integration, Reviewer A quotation corrections and machine-readable overlays.
- `source_manifest.json`: exact source file sizes and SHA256 values, **but not the original raw bytes**.

## Not yet committed

Five **original raw** story exports (112,241,245 bytes total), every intermediate R01–R05 ZIP, the original binary reviewer ZIP uploads, and full reconstruction/helper scripts remain outside this Git archive. Existing files remain available as conversation artifacts, but cannot be considered backed up to Git by this commit. Source hashes in `source_manifest.json` only serve as a verifiable import contract.

To back up raw sources from the user's local checkout, restore the five original JSONL files to `data/raw/v0.2/` locally; verify each exact SHA256 against `source_manifest.json`, and then explicitly choose Git LFS or another content-addressed archive. `data/raw/` is ignored by `.gitignore`, and no Git LFS upload was performed here. Do not bypass ignore rules or commit large raw files without checking GitHub hosting limits first.

## Future work

Additional stories should be ingested into distinct per-story namespaces, with immutable source hashes and separate curator decisions. Extend the candidate corpus only through additive revisions; never rewrite the 87-row accepted snapshot. Quality acceptance is not training approval. Story-card, v0.1 split overlap, pinned Qwen tokenizer and actual last-round mask audits remain pending.

**Status:** `GOLD_QUALITY_ACCEPTED=87`; `OTHER_CANDIDATES_CLOSED=25`; `TRAINING_ADMISSION=PENDING_NOT_APPROVED`; `RAW_SOURCES_BACKUP=PENDING`.

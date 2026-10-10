# StoryForge v0.1 — Validation 1536-token scored evidence

**Status: `VALIDATION_1536_REVIEW_ARCHIVE_PASS / ORIGINAL_INFERENCE_SOURCE_PENDING`.**

This is a **post-freeze addition** to `main`, not a rewrite of `v0.1-evidence-frozen` (`d1186a731a81219f86eb81b89ac1440dd116e9f4`).

## Preserved materials

- `raw/b.csv`, `raw/c.csv`, `raw/g.csv`, `raw/q.csv`: four original scored reviewer CSVs from the 1536-token Validation evaluation, **byte-identical** to the user uploads (Git blobs preserve BOM/newline styles). Each has 15 rows.
- `derived/reconstructed-from-reviewer-sheets.jsonl`: 15 pairs of full A/B responses **reconstructed from the b scorer CSV** and cross-checked against the other three CSVs. **It is NOT the Hugging Face Job's original blind-pairs output.**
- `source_manifest.json`: original SHA256, Git Blob SHA-1, source filenames and limitations.
- `reproduce.py`: CPU-only checksum verification, full context/answer alignment across reviewers, complete 1–5 scores and written reasons, and tally consistency.

### Basic results, still anonymized

| Metric | Value |
|---|---:|
| Submitted reviewer scorecards | 4 |
| Samples per reviewer | 15 |
| Rating rows | 60 |
| A preferences | 29 |
| B preferences | 29 |
| Ties | 2 |

These **A/B totals are not Base/Adapter win totals**. The matching original **1536-token** answer mapping has not yet been independently verified; do not infer the identity of A and B from old 128/512 runs.

### Reproduce without GPU

```bash
python3 evaluations/v0.1/validation-1536/reproduce.py
```

Expected `VALIDATION_1536_REVIEW_ARCHIVE_PASS`. The repository CI includes a test that runs the same script.

## Provenance boundary

HF paired Validation generation Job: `6ac794fae7a0dae8a2788ee6` (historical job reference in `docs/HF_RUN_REGISTRY.md`). This archive **does not** include the independently fetched original 1536-token `blind-pairs.jsonl`, its raw generation metadata, the matching prompts/manifest, or the original 1536 answer key. Full original-job provenance remains **PENDING**.

The historical 128/512-token short-cap inference artifacts were deliberately **excluded**; do not silently substitute those earlier outputs or their A/B order.

The v0.1 acceptance remains `ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED`. The original v0.1 frozen Tag and Gold-heldout supplementary evidence remain untouched.

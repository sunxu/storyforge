# StoryForge v0.1 — Validation 1536-token scored evidence

**Status: `VALIDATION_1536_HF_SOURCE_VERIFIED / MODEL_UNBLIND_PASS / RAW_INFERENCE_REMOTE_ONLY`.**

This is a **post-freeze addition** to `main`, not a rewrite of `v0.1-evidence-frozen` (`d1186a731a81219f86eb81b89ac1440dd116e9f4`).

## Preserved materials

- `raw/b.csv`, `raw/c.csv`, `raw/g.csv`, `raw/q.csv`: four original scored reviewer CSVs from the 1536-token Validation evaluation, **byte-identical** to the user uploads (Git blobs preserve BOM/newline styles). Each has 15 rows.
- `derived/reconstructed-from-reviewer-sheets.jsonl`: 15 pairs of full A/B responses **reconstructed from the b scorer CSV** and cross-checked against the other three CSVs. **It is NOT the Hugging Face Job's original blind-pairs output.**
- `source_manifest.json`: original SHA256, Git Blob SHA-1, source filenames and limitations.
- `reproduce.py`: CPU-only checksum verification, full context/answer alignment across reviewers, complete 1–5 scores and written reasons, and tally consistency.

### Originally recorded anonymous votes (historical)

| Metric | Value |
|---|---:|
| Submitted reviewer scorecards | 4 |
| Samples per reviewer | 15 |
| Rating rows | 60 |
| A preferences | 29 |
| B preferences | 29 |
| Ties | 2 |

These A/B counts remain part of the originally submitted anonymous scorecards. The correct official 1536-token mapping has since been verified, as described below.

### Reproduce without GPU

```bash
python3 evaluations/v0.1/validation-1536/reproduce.py
```

Expected `VALIDATION_1536_REVIEW_ARCHIVE_PASS`. The repository CI includes a test that runs the same script.

## Provenance boundary

HF paired Validation generation Job: `6ac794fae7a0dae8a2788ee6`. On 2026-10-10, the user supplied the authentic HF output ZIP (`StoryForge_Validation_1536_Original.zip`). Its original `SHA256SUMS.txt` validated **7/7 files**; the independently loaded 15 original prompts, 30 Base/Adapter responses, 15 A/B pair records and the matching key aligned perfectly with **all 60 graded rows** in the four previously archived reviewer CSVs.

The **exact original bytes** of the 1536-token `PRIVATE-answer-key.json`, `validation-manifest.json`, `summary.md`, and `SHA256SUMS.txt` are now preserved under [`hf-source/`](hf-source/), with their byte identities checked against the uploaded ZIP by Git Blob SHA-1. [`hf-source/source_verification.json`](hf-source/source_verification.json) preserves the original ZIP SHA256, file-hash provenance and verification counts.

**Important archive scope:** original 1536-token `base-results.jsonl`, `adapter-results.jsonl`, `blind-pairs.jsonl` and `validation-prompts.jsonl` were verified from the user-provided ZIP but their raw bytes are **not stored in this Git commit**. Their canonical sources remain in the HF Bucket at `hf://buckets/adradar/storyforge-training/evaluation-runs/validation/6ac794fae7a0dae8a2788ee6/` and `hf://buckets/adradar/storyforge-training/evaluation/v0.1/`. The full 15 A/B texts already in `derived/` were reconstructed from human scorecards and are not substituted for the original HF JSONLs.

### Official 1536-token model-level Validation unblind

The original key has been authenticated. `unblind.py` combines it with the four original 1536-token scorer CSVs and validates the sample IDs, scores and textual alignment.

| Indicator | Base | v0.1 Adapter |
|---|---:|---:|
| Individual anonymous-reviewer preferences | 28 | **30** |
| Strict sample majorities (at least 3 out of 4 votes) | 5 | 5 |
| Sample plurality (more model votes than opposing model) | 5 | **6** |
| Mean five-dimensional rating (1–5) | 3.7900 | **3.9233** |

There are **two overall TIE votes**. Five source samples have no strict 3/4 majority; four of those are 2:2 and one is Adapter=2/Base=1/TIE=1. The latter is a plurality for Adapter, **not** a strict majority. These are 15 Validation prompts, not 60 independent samples. The adapter's small descriptive lead does not justify production promotion.

To reproduce:

```bash
python3 evaluations/v0.1/validation-1536/reproduce.py
python3 evaluations/v0.1/validation-1536/unblind.py
```

Only the second command uses original Base/Adapter identities. Both use Python's standard library and run in CI.

The historical 128/512-token short-cap inference artifacts were deliberately **excluded**; do not silently substitute those earlier outputs or their A/B order.

The v0.1 acceptance remains `ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED`. The original v0.1 frozen Tag and Gold-heldout supplementary evidence remain untouched.

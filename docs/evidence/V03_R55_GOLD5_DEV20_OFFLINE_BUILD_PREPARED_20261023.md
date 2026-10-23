# StoryForge R55 — Gold + Base/v0.1/v0.2/v0.3-A 20-case DEV-only blind pack builder prepared

**Date:** 2026-10-23 (Asia/Singapore). **Scope:** code and unit tests, NOT real protected R55 response execution.

## Exact prepared deliverable

- Package: `StoryForge_R55_GOLD5_DEV20_NOJOB_20261023.zip`, SHA256 `1906d2f20d67e6753cbce8165681869c2d137d5d9f8375b1de131f023b16e689`; compressed size `10,635` bytes.
- Portable Git patch: `StoryForge_R55_GOLD5_DEV20_NOJOB_20261023.patch`, built from new source/test/README text files and successfully applied in a separate **empty synthetic Git repo**. Exactly **20/20** synthetic standard-library unit tests PASSED both before and after patch application.
- New code (delivered in patch/ZIP, **not yet committed individually to GitHub**):
  - `scripts/v03_r55_gold5_build.py` — exact-source preflight + private reviewer pack construction.
  - `tests/test_v03_r55_gold5_build.py` — 20 synthetic checks.
  - `docs/R55_GOLD5_DEV20_OWNER_RUN_CN.md` — Owner Mac instructions.

## Implementation provenance / mechanical controls

- The historical v0.1 compiled Test is pinned to SHA256 `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`.
- Frozen R47/R48 prompts/manifest are pinned to Git blob SHA1 `ac301a61d4130369a83dc67ac02aa2d8dda9e82b` / `f4e39196c6aa0a87b095d7de5cae4acd8b2fca63`.
- The **existing** audited `scripts/v02_r48_four_arm_build.py` `read_gold()` is imported rather than reimplemented: original Gold reply must match entire original prompt message list exactly. For Base/v0.1/v0.2, `check_r47()` reuses the original R47 source verification; `validate_responses()` additionally validates actual R55 v0.3 reply message roles/content against frozen prompt. Do not relax on schema mismatch.
- Original R55 v0.3-A 20-response SHA256 pinned `80586435b4b8dbe361d2e76d746a1e0e88154d08525d63720562810efa186557`; private R55 run report SHA256 pinned `924404daa12ed5886a879e4445b7995350228f559995f646d480859f76c4fd64`. All real source files must be provided locally by Owner; none was opened or received by this script authoring.
- `preflight`: only checks all 20 exact Gold/model sources and prints status, without creating any reviewer files.
- `build` (only after successful preflight): six PRIVATE CSV sheets (3 reviewers × 2 tasks) — five-way `Gold/Base/v0.1/v0.2/v0.3-A` and **independently randomized** `v0.3-A vs v0.2` direct pairwise. Labels randomized case-by-case; source-to-answer mapping and answer hashes written only into a `0600` coordinator file. All reviewer data stored outside any Git checkout. Only the aggregate hash/response count/verification receipt may be shared in a non-secret discussion.
- Pairwise sheets should be scored **before** the five-way sheets, preventing original Gold from influencing direct pairwise judgments. Gold remains an independently scored historical reference, never a fifth generated model, always subject to the same six-dimension and critical-error review.

## Important limitations

- The real 20-item private R47 and R55 output files have **not been passed through this builder yet**, so **zero real alignment rows are claimed PASS**. The source and output schema may cause the program to HOLD; do not retry GPU/model inference or silently coerce outputs on a mismatch.
- No independent Gold5 reviewer has been assigned or completed a newly blinded score sheet in this task. Earlier R48 and R55 scorecards cannot be pooled as one five-way result.
- This is *only* reused R47/R48/R55 developer set, 20 prompts across 2 already exposed worlds, and does **not** unblock R50, override existing `R55_R54_CHECKPOINT16_NO_GO_FOR_PROTECTED_R50_NOW`, constitute independent quality proof, or authorize R54 promotion.
- No R50 prompts, R50 source maps, original story texts, paired answer keys or private model outputs stored in this Git note. No HF Job, inference, paid CPU/GPU, training or model promotion.

## Owner next action

On the Owner Mac, apply the patch from the provided artifact, run the 20 synthetic tests, find the original private files, run the `--mode preflight` against exact frozen files. If it reports `R55_GOLD5_20_CASE_FIVE_SOURCE_EXACT_ALIGNMENT_PASS__NO_OUTPUT__NO_GPU`, then run `--mode build` once in a new non-Git `0700` directory. Return only `R55_GOLD5_PREP_SAFE_COUNT_ONLY.json`, not the private reviewer sheets or mapping. If the real preflight blocks, report only the HOLD code; diagnose file shape locally without logging private prompt text.

**Gate:** `R55_GOLD5_SYNTHETIC_20_OF_20_PASS__OWNER_REAL_ALIGNMENT_PENDING__DEV_ONLY__NO_NEW_JOB`.

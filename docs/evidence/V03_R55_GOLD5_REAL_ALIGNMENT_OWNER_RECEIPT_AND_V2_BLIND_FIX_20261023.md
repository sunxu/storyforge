# StoryForge R55 — Owner-reported real Gold5 20-case alignment PASS; blind-design correction v2

**Date:** 2026-10-23, Asia/Singapore. Source is the Owner-pasted local stdout and count-only receipt; original private source bytes and reviewer CSVs were **not** received or independently rehashed by this documentation step.

## Owner-local real-input execution reported

- `R55_GOLD5_20_CASE_FIVE_SOURCE_EXACT_ALIGNMENT_PASS__NO_OUTPUT__NO_GPU`
- `R55_GOLD5_FROZEN_PROMPT_AND_GOLD_AND_MODEL_BYTES_MATCHED`
- `R55_GOLD5_20_EXPOSED_CASES_EXACT_SOURCE_ALIGNED__PRIVATE_BLIND_PACK_CREATED__NO_R50`
- 20 reused development questions across 2 historically exposed story worlds. Model answers 80 (Base, v0.1, v0.2, v0.3-A) + source-aligned Original Gold 20 = 100 candidate texts. Three five-way and three pairwise **blank** reviewer CSVs have been created. Review count remains `0`.
- Original compiled Test SHA256 `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`; original prompt SHA256 `2915bb7c4fb601f51253554c11deaefeb8415a5c75fc06bb0b9362c7cb927cc3`.
- Frozen R55 v0.3 response SHA256 `80586435b4b8dbe361d2e76d746a1e0e88154d08525d63720562810efa186557`; original R55 report SHA256 `924404daa12ed5886a859e4445b7995350228f559995f646d480859f76c4fd64`.
- Owner-local **v1** private answer-key SHA256 `5380bf95876818737e4c8466b14ec26360aa64054df9bd20f2fcff4d301e0aa5`.
- The three pristine CSVs for each v1 type share one SHA respectively (expected identical blank templates), not evidence that any independent Reviewer has completed a review.
- No private raw story text, case identifiers, model answers, or mapping is included in this file. No R50 opened, no new model generation, no training, no promotion.

## A pre-distribution blind-design defect was identified

In v1's `R55_GOLD5_FIVE_Reviewer_*_PRIVATE.csv`, the additional field `四模型最佳(请填写对应匿名字母或TIE)` requests the blinded Reviewer to identify and exclude the hidden Original Gold entry. This is logically **impossible without revealing the Gold label** or interpreting identity by inference. The correct way to obtain an independent model-only four-way preference is to create a **separately randomized** four-model task with Gold entirely absent. DO NOT DISTRIBUTE v1 FIVE files for scoring, or silently compute four-model preference from five-way ranking.

## Repair prepared and tested with synthetic files ONLY

Prepared downloadable, non-private-source assets (source not yet committed to the main repository):
- `StoryForge_R55_GOLD5_V2_BLIND_FIX_20261023.patch`, SHA256 `2dc22ae861c8232a9d11d68907156e4919b4fee7f0cf23d0df55aa9aa3930f66`.
- `StoryForge_R55_GOLD5_V2_BLIND_FIX_20261023.zip`, SHA256 `655c36e108c5529a7589a6143bbd4fc7566980799ce018959f4f3a5e373cc69d`.

V2 creates a **new** `owner-pack-v2` directory, leaves v1 intact, and produces exactly **9 distinct reviewer tasks**: 3 independent pairwise v0.3 vs v0.2 blind sheets; 3 model-only Base/v0.1/v0.2/v0.3-A four-way sheets (no Gold); 3 five-way Gold+four-model sheets with Gold label hidden. Each task randomized separately but consistently across three pristine reviewer copies. Coordinator-only mapping saved mode `0600` outside Git; safe receipt has only counts/hashes/booleans.

The v2 source reuses the already authenticated v1 strict Gold, R47, and R55 input-byte validation `load_exact_sources()` verbatim; no private inputs have been run in this assistant environment. V2 tests: **25/25 synthetic stdlib unittests PASS**, Git patch applied successfully to isolated synthetic repository, **25/25 tests again PASS**.

**Next:** The Owner should apply v2 patch, run local 25-test suite, rerun real-source v2 preflight (no new inference), then create v2 package in a NEW directory. Only then send pairwise reviewer sheets, freeze their scored results, send model-only four-way, freeze, and finally send five-way; do not disclose prior ratings or answer keys. Prefer new independent reviewers, because R48/R55 topics are exposed. If using remote reviewers, explicit Owner consent to provide private story content externally is needed.

**Status:** `R55_GOLD5_OWNER_REAL_20_CASE_ALIGNMENT_REPORTED_PASS__V1_REVIEW_NOT_RELEASED__V2_BLIND_FIX_SYNTHETIC_25_PASS__REAL_V2_PENDING__R50_0__R54_NOT_PROMOTED`.

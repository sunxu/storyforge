# StoryForge R55 — R46 vs R54 exposed-20 development unblind

Date: 2026-10-22 (Asia/Singapore).

**Status:** `R55_EXPOSED20_OWNER_UNBLIND_AND_FREEZE_CROSSCHECK_PASS__DEVELOPMENT_ONLY__R54_NOT_PROMOTED__R50_SEALED`.

The Owner uploaded two final JSON artifacts:
- `R55_DEVELOPMENT_UNBLIND_RESULTS_PRIVATE.json`, independently rehashed SHA256 `81e4a7dacf4e6c37333a61c13872dbcbc7bea4f3c4068b9893c3c758748f3e37`.
- `R55_OWNER_ORIGINAL_PRISTINE_FROZEN_SAFE.json`, independently rehashed SHA256 `0684888bc2cbbf86a6b729e551deb3ef10269e7caea3de38b469ff11f79bb95e`.

The final unblind report's `input_sha256.frozen` matches the **actual uploaded original-pristine freeze receipt bytes**, and its `input_sha256.pristine` matches `75ada9c326cac76da927c518689a19a254029dce46193bd922ec4942ff90e703` recorded by that frozen receipt. Its `input_sha256.prep_receipt` and pinned private mapping SHA256 match the earlier actual Owner prep receipt. Three original previously uploaded 20-row anonymous scored Reviewer CSVs independently match the frozen SHA256s. A fresh **29/29 consistency audit passed**, including source hashes, scope, 60 cases/reviewer rows, anonymous summed scores in all six rating dimensions, and both severe-flag total checks. The private answer-mapping bytes were **not** downloaded or independently read in this assistant environment.

## Development regression: 20 reused old questions, 3 Reviewers

| Measure | R46 v0.2 | R54 v0.3 |
|---|---:|---:|
| Per-case Reviewer majority wins | 8 | 12 |
| Reviewer preference votes (not independent cases) | 27 | 33 |
| Six-dimension mean, 1–5 | 3.3972 | 3.2750 |
| Serious player agency Reviewer-case flags | 7 | 9 |
| Explicit banned phrase / world fact Reviewer-case flags | 30 | 29 |

Six scores (R46 → R54): story continuity 3.4333 → 3.4000; character consistency 3.7167 → 3.4833; instruction adherence 2.7333 → 2.6500; literary style 3.6333 → 3.4833; interactive progress 3.5500 → 3.4000; player agency 3.3167 → 3.2333. **All six mean scores favor R46, while 12/20 per-case majority preferences favor R54.** Both are important; do not selectively quote only the headline win count.

Exactly 20 original prompts appeared in **both historical R47 and R48**, in only 2 already-exposed story worlds. Even assuming unrealistic independent fair cases, a 12/20 exact two-sided binomial p is approximately 0.503; this is not convincing evidence of performance generalization. Three votes on the same case are NOT three separate test cases. Serious issue flags are unadjudicated *Reviewer-case markers*, not unique confirmed factual failures.

**Conclusion: R54 must remain NOT PROMOTED.** Do not spend additional GPU compute solely on these metrics. Next, inspect existing frozen development responses for specific instruction/character and player-agency errors, then separately preregister a truly new legally/rights-cleared independent multiworld evaluation without opening the R50 sealed set prematurely. The R46 vs R54 training datasets and optimizer settings differ; these scores cannot isolate a pure dataset effect.

Local detailed aggregate-only acceptance JSON: `R55_UNBLIND_DEVELOPMENT_AUDIT_SAFE_20261022.json`, SHA256 `5f968164beb03ce9cc05f2c636400b5f24fe2684a2b75198558eb86cec8c8470`. Private mapping, story text and per-case scores are not present in this GitHub evidence record.

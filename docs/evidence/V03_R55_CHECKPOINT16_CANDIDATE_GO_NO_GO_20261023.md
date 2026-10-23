# StoryForge R55 — R54 v0.3-A checkpoint-16 candidate GO / NO-GO decision

**Date:** 2026-10-23. **Decision:** `R55_R54_CHECKPOINT16_NO_GO_FOR_PROTECTED_R50_NOW__DEVELOPMENT_CANDIDATE_RETAINED__NO_PROMOTION`.

## Decision scope

This is a conservative decision on whether to **spend the one-time fresh R50 46-case evaluation** on the *present* R54 v0.3-A adapter, **not** proof that R54 is intrinsically worse on unseen worlds, a GPU training failure, or a permanent ban on evaluating that adapter. R50 itself remains PRESEAL and not officially admitted. Its 46 private prompt-only cases were **not** opened for this decision. No new inference, HF Job, training, GPU, or blind review executed.

### Confirmed engineering candidate

- R54 completed one A100-80GB SFT training Job `6ad8e60f5275124786e27d21`, Owner-accepted engineering receipt `R54_V2_OWNER_GPU_ENGINEERING_REPORT_INTAKE_ACCEPTED__NOT_PROMOTED`.
- Frozen base `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`; final checkpoint `output/v0-20261021-162418/checkpoint-16`; Owner cross-checked final `adapter_model.safetensors` SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0`. No independent weight rehash performed by this decision.
- R46 comparator v0.2 adapter SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`.

### R55 frozen three-reviewer development regression

Sources:
- `docs/evidence/V03_R55_R46_R54_DEV20_OWNER_UNBLIND_CROSSCHECK_20261022.md` on main.
- Owner-private `R55_DEVELOPMENT_UNBLIND_RESULTS_PRIVATE.json`, uploaded SHA256 `81e4a7dacf4e6c37333a61c13872dbcbc7bea4f3c4068b9893c3c758748f3e37`.
- Three frozen Reviewer CSVs and unblinding were cryptographically scoped and a prior 29/29 consistency check passed. The private identity mapping was not independently inspected here.

| Measure | R46 v0.2 | R54 v0.3-A | Interpretation |
|---|---:|---:|---|
| Case-majority preference on 20 prompts | 8 | 12 | Favor R54 nominally, small/two-world exposed set |
| 3 reviewers × 20 case votes | 27 | 33 | Dependent judgments, not 60 independent cases |
| Six-axis mean of 1–5 | **3.3972** | 3.2750 | R54 lower by 0.1222 |
| Story continuity | **3.4333** | 3.4000 | R54 lower |
| Character consistency | **3.7167** | 3.4833 | R54 lower by 0.2334 |
| Instruction adherence | **2.7333** | 2.6500 | R54 lower |
| Literary quality | **3.6333** | 3.4833 | R54 lower by 0.1500 |
| Interactive progression | **3.5500** | 3.4000 | R54 lower by 0.1500 |
| Player agency | **3.3167** | 3.2333 | R54 lower |
| Serious agency flags | 7 | 9 | Reviewer-case flags only; not adjudicated unique errors |
| Banned/hard-fact flags | 30 | 29 | Reviewer-case flags only; not adjudicated unique errors |

The 12/20 R54 majority is not compelling multiworld evidence: in an unrealistic i.i.d. fair-case calculation, two-sided exact binomial `p≈0.5034`. Only two already-exposed story worlds were used. R46/R54 differ in data and training settings; not a causal one-factor comparison.

### Original Gold evidence is historical context, NOT an additive R55 verdict

R48 compared the **original Gold response** with Base, v0.1 and v0.2 on the same old 20 prompts: majority 8/7/3/2 (Gold/v0.2/v0.1/Base) and aggregate mean 3.4611/3.3750/2.9111/3.1639, per `docs/evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.md`. Gold was not a model, was not infallible, and its severe agency flags (22/60 Reviewer-case flags) exceeded v0.2 (6/60) *in that older review*. **Do not pool R48 numerical scores or votes with the R55 head-to-head**: different comparison lineup, reviewers/output generation context, and exposure. For a true new R55 five-way comparison, freeze the matching old Gold and each model response by case, then run a fresh independent blinded comparison as **development only**; no R50 prompts involved.

## GO/NO-GO and release conditions

- **NO-GO now** for expenditure of the protected R50 final test on this R54 checkpoint-16 purely on these mixed and deteriorating six-axis R55 results.
- **GO** to retaining, packaging and inspecting R54 checkpoint-16 for developer diagnosis; R46 v0.2 remains the major quality comparator. Do **not** unfreeze weights, automatically retrain, overwrite original R55 scores, or promote R54.
- **GO** to preparing draft four-model + original Gold benchmark design and frozen pre-registration; this does not authorize the R50 seal or paid inference.
- Before revisiting this NO-GO: use existing frozen R55 answers for independent *case-level* adjudication of serious agency/forbidden-line marks and six-axis regression; optionally perform an **honestly labeled new blinded R55 five-way review**, with original Gold aligned to the exact same existing old 20 prompts and distinct Reviewer judgments. The new comparison is still **exposed development regression** and **must not** masquerade as statistically independent promotion validation. Document a reasoned rationale if the Owner decides to authorize scarce R50 use despite mixed development scores.
- R49/R56 evaluation-preregistration, protected source/cutoff provenance, per-arm runtime identity/role parity, and a separate Owner authorization for paid inference remain independent gates. The Owner has attested the stories are independent; record this as author testimony, not automatic technical clearance.

**No protected R50 text, reference keys or original narrative content in this record.**

**Final:** `R55_NO_GO_R50_NOW__R54_ENGINEERING_RETAIN__R46_CONTROL__GOLD_FIVE_WAY_DEV_OPTION__NO_MODEL_PROMOTION`.

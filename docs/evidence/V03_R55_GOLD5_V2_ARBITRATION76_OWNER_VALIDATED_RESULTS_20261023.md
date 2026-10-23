# StoryForge R55 Gold5 v2 — Owner-reported 76-item blinded arbitration results

Date: 2026-10-23 (Asia/Singapore). Source: Owner-pasted local JSON `R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json`, status `R55_GOLD5_ARBITRATION_DECISIONS_SYNTAX_AND_EXACT_QUOTES_VALIDATED__DEV_ONLY__NO_R50`. This record is derived from safe counts only; neither source-private candidate replies, exact quotations nor decision rows were independently examined here.

## Provenance and validation boundary

- 76 flagged candidate-case groups, each independently evaluated in two categories: `agency` (serious player-agency infringement) and `hard_fact_or_ban` (forbidden phrase or hard factual violation). Thus **152 category decisions**, not 152 different underlying events.
- `blind_items_sha256=b97e743ba3901561dc5745f9f50a47e52d1199c7c60f106ad9d011604c741f65`; Owner-reported completed-decision SHA256 `ee573b1d86d5ad2c8e807f69306006addc86d968ad85e1918d524de0d9b7d621`.
- Validator checked decision shape and presence of exact quotes; explicitly `verdict_semantic_correctness_not_automatically_verified=true`, `not_certified_reviewer_independence=true`. A valid exact quote is not independently verified proof of rule violation.
- Scope `flagged` selected by earlier review; cannot treat targeted-confirmation counts as unbiased error frequencies or infer generalization across story worlds.
- `r50_accessed=false`, `gpu_job_started=false`, `training=false`, `model_promoted=false`.

## Results by source and category, as reported by Owner

| Arm | Flagged case+candidate subjects | Agency CONFIRMED | Agency HOLD | Agency REJECTED | Hard/banned CONFIRMED | Hard/banned HOLD | Hard/banned REJECTED | CONFIRMED category decisions sum |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base | 17 | 4 | 3 | 10 | 6 | 1 | 10 | 10 |
| Original Gold (non-model reference) | 13 | 6 | 2 | 5 | 3 | 2 | 8 | 9 |
| v0.1 | 14 | 7 | 4 | 3 | 6 | 1 | 7 | 13 |
| v0.2 R46 | 16 | 3 | 2 | 11 | 9 | 2 | 5 | 12 |
| v0.3-A R54 | 16 | 4 | 3 | 9 | 9 | 2 | 5 | 13 |
| **Total** | **76** | **24** | **14** | **38** | **33** | **8** | **35** | **57** |

Total category verdicts = `CONFIRMED 57`, `HOLD_INSUFFICIENT_EVIDENCE 22`, `REJECTED 73` = **152**. Since both categories may occur on one reply, the sum 57 must NOT be described as 57 unique severe events. Counts also do not distinguish literal banned quote from underlying hard-fact mismatch; avoid claiming nine literal banned phrases for either v0.2 or v0.3.

## Candidate gate unaffected

- In independent direct Pair, case majority v0.2:v0.3-A was 10:10 and six-axis averages were 3.363889 versus 3.216667 (all axes favor v0.2). Separate Four/Five independent blinded reviews also prefer v0.2 among trained arms.
- 76-subject targeted arbitration found v0.2:v0.3-A `agency CONFIRMED` = 3:4 and `hard_fact_or_ban CONFIRMED` = 9:9. These are single-arbitrator category judgments that passed form/quotation validation, **not adjudicated independent event counts nor globally unbiased error rates**.
- Therefore the existing **R54 checkpoint-16 NO-GO for protected R50** and no-promotion decision remain in effect. v0.2 stays quality comparator, not automatically a production release.

## Recommended bounded next phase

1. Freeze and preserve the completed 76-item JSON and SHA; do not alter prior cases, nine reviewer CSVs, candidate model bytes, results or labels.
2. If the decision is to rely on `CONFIRMED` as a hard gate, commission an independent **semantic evidence audit** of all 57 positive category decisions and the 22 HOLD category decisions, plus a prespecified sample of 73 rejected cases for false-negative quality control. Reviewer must assess original visible context and exact candidate quote; no exposure to source model identity, previously unblinded score summary or first arbitrator verdict before their independent verdict.
3. Preserve `HOLD_INSUFFICIENT_EVIDENCE` unless new allowed evidence genuinely resolves it, and resolve disagreements by independent tertiary adjudication. Audit exact banned-phrase versus hard-fact mismatch separately if formal zero-banned-string gates are used.
4. Summarize **per model, per category, unique candidate-case** confirmed/held/rejected counts only after second-pass semantic audit. Keep selected-sample estimates explicitly non-generalizable; consider unflagged controls if claiming any model-wide error rate.
5. R54 regression diagnosis should focus on character consistency, interaction progression and player agency using existing exposed dev examples; do not unlock R50 or launch retraining solely on the basis of this document.

**Status:** `R55_GOLD5_V2_76_ARBITRATION_CATEGORY_FORM_PASS__57_PROVISIONAL_CONFIRMS__22_HOLD__73_REJECTED__R54_NO_GO__NO_R50`.

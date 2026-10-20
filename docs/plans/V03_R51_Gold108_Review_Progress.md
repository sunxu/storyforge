# StoryForge R51 — Gold108 private source-review progress

**Checkpoint:** three 24-case batches independently reviewed by Reviewer A and Reviewer B, reconciled under the strict R51 validator, no Train/Val admission. Public count-only tracking; no private source excerpts, candidate IDs, citations, or rationale.

| Route / status | Batch 01 | Batch 02 | Batch 03 | Total |
|---|---:|---:|---:|---:|
| Agreed context-only possible **HOLD** | 15 | 16 | 14 | 45 |
| Agreed long-range / card needed **HOLD** | 2 | 6 | 5 | 13 |
| Agreed agency / known rule concern **HOLD** | 2 | 1 | 1 | 4 |
| Disagreed **HOLD** | 5 | 1 | 4 | 10 |
| **Reviewed (both A and B)** | **24** | **24** | **24** | **72** |
| Unadmitted Train / Val | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

- A/B same-route: **62/72 (86.11%)**; Cohen's kappa **0.709326**.
- Remaining Gold108: **36** (Batch 04: 24; Batch 05: 12), not yet independently dual-reviewed.
- Third-party Reviewer C: **4/4 Batch 03 disputed cases now have frozen, citation-validated independent-C judgments** (16/16 citations verified, all HOLD); C aligns with A on 1, with B on 2, and differs from both on 1 (**three-way disagreement, source follow-up required**). C blindness is attested in the private submission, not independently provable. The **six Batch 01–02 disputes still await C**, and a final owner source/quality disposition has not been granted.
- Blind adjudication evidence must **not** include A/B routes or rationales. Freeze independent C decisions and validate citations before owner compares against the A/B sidecar. Reviewer A cannot act as independent C.
- All **45** agreed context-only possible cases remain **HOLD** pending broader target quality, original historical story-card/timepoint and usage rights/license gates. A source-window assessment is not training admission.
- Do not alter Gold195 frozen originals, R50 sealed heldout, run HF/GPU training, or promote any model from these review findings alone.
- Keep all complete review files, privately cited evidence, private candidate IDs and C decisions in the owner's mode-0700 directory with mode-0600 files; **never commit them**.

Validation scope: locally reconciled Batch 01–03 files were cross-checked for 72 distinct cases, A original result identity, both reviewer schemas and citations against matching A tasks (same source records). This does **not** repeat the full root archive source replay or independent audit of Reviewer's B original unnormalized Batch 01–02 exports.

Reconciliation file SHA256:
- Batch 01: `762bd5bedaf0d7d8f6f1e336640074af72bb5fe81f4784529f2f9766ce8cbad5`
- Batch 02: `ec5caedc91227b0d67aec5604691e38dd9e7800041358be03335c91ca01fc7ac`
- Batch 03: `adce797466e84c6cd73bc16cab93ea6194ef51b5a279870b9ba30dffd24fb7ed`

## Next executable work

Generate Batch 04 locally using the already-committed `scripts/v03_r51_independent_source_reviews.py --prepare --batch 4`, with the same private 108-case input packet and owner-only output directory. Distribute A and B tasks separately. Keep C blind arbitration for 10 disputes in parallel, and complete Batch 05 after Batch 04.

All statuses remain **PENDING_NOT_APPROVED**. No GPU job authorized.


## R51 Gold108 checkpoint — Batch 04 reconciliation (2026-10-20)

Newly verified private Batch 04 merged output: **24 cases, 21 same-route, 3 disagreements**, all strict `PENDING_NOT_APPROVED`, no Train/Val admission. Source citations were checked against uploaded original A tasks (the matched A/B task candidates), along with 24 unchanged Reviewer A results. The underlying complete original archives and Reviewer B's separate initial export were **not** rechecked here.

| Route / status | Batch 01 | Batch 02 | Batch 03 | Batch 04 | Total |
|---|---:|---:|---:|---:|---:|
| Agreed context-only possible, HOLD | 15 | 16 | 14 | 12 | **57** |
| Agreed long-range/card dependency, HOLD | 2 | 6 | 5 | 8 | **21** |
| Agreed agency/rule concern, HOLD | 2 | 1 | 1 | 1 | **5** |
| A/B disagreement, HOLD | 5 | 1 | 4 | 3 | **13** |
| **A/B reviewed** | **24** | **24** | **24** | **24** | **96** |

- Unique A/B reviewed: **96/108**, **12 remaining** for Batch 05.
- Same-route: **83/96 = 86.4583%**, Cohen's kappa **0.729049**.
- Third-party Reviewer C status: Batch 03 **4/4 C decisions received and evidence-validated** (including one three-way disagreement requiring source follow-up); Batch 01–02 **6** and Batch 04 **3** still require C. Overall **9** C decisions pending. C decisions are not automatic admission.
- Batch 04 reconciliation SHA256: `5eea50eec6ca52a408b392cbbcb5d71f580b917aeea16b8a50ca20c8eafdee40`.
- Separate owner-only blind third-party evidence kit exists for Batch 04's three disputes. **No original dialogues, candidate identities, private reviewer rationale, citations, or comparison sidecars are committed.**
- All samples remain **HOLD**, Train 0 / Validation 0, R50 sealed heldout untouched, no HF/GPU model training or promotion. Historical card timepoints and data rights are not certified.


## R51 Gold108 checkpoint — Batch 05 final dual-review reconciliation (2026-10-20)

**Gold108 two-reviewer scope complete: 108/108 independently reviewed by A and B, 108 distinct candidate records, no training admission.** The five owner-supplied reconciled files were checked against matching A task/result sets for identity, SHA256 of target and visible messages, and all A/B provenance citations; 884 citations were valid. B's original first exports and full raw source archives were not newly re-inspected at this checkpoint.

| Review route/status | Batch 01 | Batch 02 | Batch 03 | Batch 04 | Batch 05 | Total |
|---|---:|---:|---:|---:|---:|---:|
| Agreed context-only possible **HOLD** | 15 | 16 | 14 | 12 | 5 | **62** |
| Agreed long-range/card needed **HOLD** | 2 | 6 | 5 | 8 | 5 | **26** |
| Agreed agency/rule concern **HOLD** | 2 | 1 | 1 | 1 | 1 | **6** |
| Reviewer disagreement **HOLD** | 5 | 1 | 4 | 3 | 1 | **14** |
| Cases | 24 | 24 | 24 | 24 | 12 | **108** |

- Same-route judgments: **94/108 = 87.037%**; Cohen's kappa **0.750947**. Agreement is not admission.
- C adjudication: Batch 03 **4/4** third-party decisions have passed file/citation validation (one three-way split still needs a source/quality decision). **10** original A/B disputes remain to be adjudicated: Batch 01–02 **6**, Batch 04 **3**, Batch 05 **1**. A blind, separate C evidence kit is prepared for Batch 05's one dispute, but no C verdict is claimed for it.
- A/B result citations grounded against matching original A task messages: **884/884**, no duplicates among 108 candidate IDs.
- Strict **Train 0 / Validation 0 / No GPU**, **PENDING_NOT_APPROVED** for all 108 Gold108. No R50 sealed held-out test access or model promotion.
- Previously frozen Gold87 and Gold108 remain immutable; final Gold195 training eligibility requires separate historical card/timepoint proof, rights/license to train, world-level split and quality gate review. The 62 context-only possible cases may proceed to further **eligibility checking only**.
- Raw evidence and all C/A/B comparisons and narrative text remain owner-private, files mode 0600 under owner-private 0700 directory; **do not commit to public Git**.
- Batch 05 reconciled file SHA256: `b9cc7b95816b179f1ea2694fcef2e1632ae038bc49ea9ef67de8405e92ce0be8`.


## R51 Batch 05 Reviewer C blind adjudication (2026-10-20)

- C decision file received from independent reviewer and successfully validated against the original one-case blind evidence: **1/1** complete, **5/5** valid citations, schema and SHA256 pins valid. All states remain `PENDING_NOT_APPROVED`.
- Frozen post-review comparison: C's principal route agrees with **Reviewer B** (long-range/card dependency), not Reviewer A (agency/rule concern). C independently also noted the narrative/agency perspective risk. **Both concerns remain HOLD**; majority alignment must not clear the secondary issue.
- All Gold108 A/B reconciliations are complete **108/108**; A/B original route disagreements **14**. Independently received and evidence-validated C decisions total **5/14** (Batch 03: 4; Batch 05: 1). Still pending C: **9** (Batch 01–02: 6, Batch 04: 3).
- Reviewer C submitted `reviewer_a_b_analyses_seen=false` as an independence attestation, but the evidence validator cannot independently verify actual blinding.
- No rights/card-version certification or final admission from C; Train **0**, Validation **0**, and **no GPU job**. Private C decision, receipt, and post-freeze A/B/C comparison stay outside the public repository.

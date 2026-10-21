# StoryForge v0.3 / R53 — frozen-source replay and release precheck (2026-10-21)

Status: `R53_SOURCE_AND_PRE_GPU_LOCAL_GATES_REPLAYED__NO_ADMISSION__NO_GPU`.

This document is count-only; no private stories, candidate identifiers, raw training examples, owner crosswalk, or sealed R50 content are committed.

## Actual offline source verification

- Verified original R45 frozen **49 Train + 15 Validation** exact source bytes, and original R52 46 targets and frozen histories against hashes.
- Verified that R46's **provided** completed-job report uses these exact R45 source split SHA256 identities and reports compiled-input SHA256 for both splits. This is reported engineering lineage; the remote job's full logs and per-optimizer-step sampling were **not** independently inspected.
- R52 original target intersection with those frozen R45 splits: **15 exact Train target repeats**, **9 exact Validation target repeats**, **22 neither**. Within the latter 22, **20** remain contextual-quality-possible HOLD and **2** have substantive defect HOLD. Exact target non-overlap is NOT world/model independence.
- Seven current source story UUID groups: only **one group of 10 candidates** has no observed exact R45 story UUID overlap (9 quality-possible HOLD). All other groups share a source UUID with R45 Train or Validation. Semantic link/alias components remain unsigned.

## R53 source-pinned release precheck

Ran against the *real original pending* 46-case owner ledger (not a synthetic approved ledger). Confirmed 46 frozen identities, 3 defect-route originals held, and 0 selected Train / 0 selected Validation. Correct result: `R53_BLOCKED__NO_ADMISSION__NO_GPU`, exit code 2.

A new offline, standard-library-only source-bound integrity guard was tested with **10 synthetic-only cases** covering changed hashes, defect admission, reopened R50, spurious GPU flag, train/validation component leakage, missing rights or actual-collator claims, absent splits, inconsistent components, and no-card-design approval scope. All passed. Structural checks cannot authenticate human signoffs, rights, safety, true model exposure, or runtime tokenizer labels.

Safe offline artifacts are stored in the conversation attachment named `R53_R52_PRE_GPU_SOURCE_AND_RELEASE_GUARD_SAFE_20261021.zip` (not in this repository; ZIP SHA256 `4ecdf396dfd7568c673b1580aa8607957681c27474c22334a31817de4baad05f`). No private source archive is included. Local script SHA256: `edcb3af6e7fdab6d71c95b78ff57956cae7328bf19f0ef783899d6bed8b04703`.

## Still blocked

1. Owner's per-case final content, consent/adulthood, player-agency, provenance/rights and quality evidence; 43 quality-possible cases still `PENDING_NOT_APPROVED`. Three defect originals remain excluded.
2. Complete source-grounded world/alias component signoff and historic R45/R46 exposure reconciliation; no Train/Val split certified.
3. Exact approved-data bytes, R53 pinned Qwen/ms-swift real tokenizer, collator and last-round label-mask verification. No paid CPU job was launched.
4. A separate explicit paid GPU authorization. R27 input design approval is **not** training-data or GPU permission.

At this checkpoint: Owner final signoffs 0/46, world component signoffs 0/7, new Train 0, new Validation 0, R50 sealed, new GPU none.

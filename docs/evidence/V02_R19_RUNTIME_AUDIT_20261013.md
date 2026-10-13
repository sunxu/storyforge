# StoryForge v0.2 — R19 remote runtime evidence audit (2026-10-13)

**Disposition: `PENDING_NOT_APPROVED`**. This is a no-training engineering validation record; it is not authorization for a fine-tuning job, dataset mutation, or train/validation/test split.

## Real-world evidence chain

- HF Job: `6acdeae181fefd5110e1963c` (reported complete by the owner).
- HF private report: `hf://buckets/adradar/storyforge-training/preflight/v02-r18/results/r18-20261013T082505Z-11237/r18_actual_no_train_report.json`.
- Owner-uploaded report SHA256: `2b8bc8e5988a60d842e6e2c0c3f60e4e677fc9e77813a0f3e71da12ea803d44f`.
- R17 source ZIP SHA256: `ba42ad7568ce0ca3ab8b3d218397006b430affc9f1b2f74b7ea4392e5103eab3`.
- Base snapshot: `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Runtime: `ms-swift==4.5.3`, `transformers==5.16.1`, `tokenizers==0.23.3`, `torch==2.6.0+cu124`, `huggingface-hub==1.33.0`.

## Exact submitted report metrics

- 40 distinct first-lane diagnostic sample IDs aligned with the immutable R15 queue and R17 fingerprint manifest; 10 distinct story IDs.
- The remote job reports 40/40 `ACTUAL_COLLATOR_LABELS_CONSISTENT`, `status=COLLATOR_INTERNAL_CONSISTENCY_ONLY`, `training_performed=false`.
- Transformers token lengths: min **526**, max **3,292**, sum **46,401**, mean **1,160.025**.
- Actual ms-swift template token lengths: min **480**, max **3,230**, sum **44,389**, mean **1,109.725**.
- Both views are below 16,384 for all 40 samples.
- **Cross-renderer mismatch: 40/40** `transformers_ms_swift_input_same=false`. Length deltas 46 (11), 50 (20), 54 (6), 58 (1), 62 (2). The reason for these differences was **not proven**; do not claim the templates are token equivalent.
- Exactly **25 of the 40** R15 records have missing original `split_group`. None has an approved Train/Validation/Test assignment.

## Evidence qualifications

The JSON contains recorded per-item `labels_sha256`, not raw token/label arrays. The read-only R19 verifier confirms report byte identity, frozen ID/story mapping, numerical consistency, digest shape, actual runtime-version metadata and the recorded results. **It does not independently rerun the HF model or recalculate labels from raw arrays.** “40/40” here is the reported successful remote diagnostic, not a second independently reproduced collator audit.

The 38 prior HOLD, 99 opening-truncated-only and 18 `War & Blood` age/content-scope records remain isolated; their underlying Gold text has not been edited. The 40 candidates remain *diagnostic only*, pending global content/age signoff, complete v0.1 and linked-world split-graph collision checks, a genuine fresh held-out set and human approval.

## Training gate

| Gate | Result |
|---|---|
| R18 private report integrity and source ID alignment | PASS (read-only) |
| Actual HF tokenizer budget, 40 diagnostic candidates | REMOTE REPORTED PASS |
| Actual ms-swift `last_round` collator internal checks, 40 | REMOTE REPORTED PASS |
| Cross-implementation token identity | **NOT ESTABLISHED** (40 mismatches) |
| Per-token independent recomputation | **NOT PERFORMED** |
| Story UUID and linked-world isolation | BLOCKED |
| Safety/age global approval | BLOCKED |
| Approved train/validation/test split | BLOCKED |
| Formal training admission | **PENDING_NOT_APPROVED** |

This file contains no story dialogue, source export, credentials, or model weights. The private HF artifact and R19 ZIP are the detailed evidence stores.

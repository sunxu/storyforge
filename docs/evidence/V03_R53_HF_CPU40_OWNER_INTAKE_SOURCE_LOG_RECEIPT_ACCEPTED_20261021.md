# StoryForge R53 — HF CPU40 owner-machine source/log intake receipt accepted

Date: 2026-10-21 (Asia/Singapore).

**Current status:** `R53_HF_CPU40_OWNER_MACHINE_INTAKE_PASS__31_TRAIN_9_VALIDATION__FORMAL_ADMISSION_0_0__NO_GPU`.

## Context and evidence custody

The owner reported an HF CPU-only no-training Job `6ad8a7af0a35baab53a1ced2` completed with terminal `R53_HF_CPU40_WORKER_EXECUTED_NO_TRAIN` and actual CPU report PASS for run key `r53-cpu40-20261021T113539Z-523139`.

The owner then ran the **original strict local intake verifier**, `scripts/v03_r53_hf_cpu40_verify.py`, with the downloaded actual runtime log and returned the exact marker:

`R53_CPU40_RECEIPT_SOURCE_LOG_CROSSCHECK_PASS__NOT_DATA_RELEASE`

The uploaded generated JSON `R53_CPU40_OWNER_INTAKE_VERIFIED.json` SHA256 `b3bff2625c360aad10d985b42884263a26a72e85e7d1ddc7d0df916b6598381e` contains schema `storyforge-r53-hf-cpu40-owner-intake-v1`, source-frozen check `true`, 31 Train / 9 Validation, 40 unique case attestations, no formal training admission, no GPU authorization and R50 unopened.

The uploaded audit report's SHA256 `8624c21b6d9fff5e74006bca000c69f0d39870f1fb030c2ff4fb96cc523f1f45` was **independently recomputed from the report bytes present here**, and matches the owner-machine verifier receipt.

The owner-machine runtime-log hash recorded in the receipt is `7ebe369f83b168d2c3f0830c91cd77370154638d74482fe57cdc93e55d8ca39f`. **The log file itself was NOT uploaded to this conversation and its bytes were NOT independently rehashed in the present environment.** This is acceptance of the original owner-machine verifier receipt, **not** an assertion of a second independent HF provider attestation.

## Local checks performed in this intake

- Frozen Stage `preflight` independently re-executed and passed **31/9**, with exact message-only source SHA `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7` Train and `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d` Validation.
- Receipt, report and original freeze all agree on model `Qwen/Qwen3.8-27B`, exact revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, `ms-swift=4.5.3`, `transformers=5.16.1`, Stage manifest SHA256 `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261`.
- Report includes exactly **40 distinct source IDs**, **31 Train and 9 Validation** and **40** `REAL_LAST_ASSISTANT_AND_COLLATOR_PASS` statuses, each source-pinned target checked in preceding standalone report review; **11,230 supervised tokens**, maximum native input **3,668**.
- Native ms-swift singleton collator supervision PASS is accepted on the returned real runtime report; `transformers_vs_swift_input_identical=false` for **all 40**, so rendering parity must not be claimed.
- All 40 remote Collator checks had **zero padding**, meaning that **multi-example batch padding was not exercised remotely**. Existing offline multi-example padding tests remain separate, not a remote parity claim.
- The current acceptance receipt `R53_CPU40_OWNER_RECEIPT_ACCEPTANCE_SAFE_20261021.json`, SHA256 `aa277825fad90a96a40b5c9d436ef3d2fcd1d83a32a21cc72b528a4a49e0c0c4`, stores only safe aggregates and expected limitations, no story text or candidate IDs.

## Decision and remaining blocks

The scoped **R53 CPU 40 real tokenizer/ms-swift last-round label and singleton collator evidence gate is now ACCEPTED at the owner-machine original-verifier receipt level**. No new HF Job or paid GPU has been launched in response to this receipt.

The following remain **separate release gates**: 7-story rights/provenance according to the adopted release policy, and a new **explicit owner authorization for exact frozen 31/9 dataset release**; formal Trainer `train.jsonl` and `validation.jsonl` are **not released**, and formal admitted Train **0**, Validation **0**. All original six HOLD cases remain excluded. R50 remains sealed, paid GPU not authorized. The earlier accepted Reviewer E seven-world source-bounded policy and R46 user-machine primary evidence receipt remain unchanged.

This document records an owner-machine receipt verification, not a cryptographic institutional signature or fully independently repeated source-log audit.

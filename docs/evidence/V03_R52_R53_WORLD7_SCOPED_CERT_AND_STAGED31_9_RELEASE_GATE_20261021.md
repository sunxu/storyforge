# StoryForge R52 → R53: owner-scoped seven-world certificate and staged 31/9 release gate

**Date:** 2026-10-21  
**Status:** `OWNER_WORLD7_SOURCE_UUID_SPLIT_PASS__STAGED31_9_BYTES_READY__FORMAL_DATA_RELEASE_BLOCKED__NO_GPU`

## Scope of the world certificate

The story creator/owner explicitly attested all seven stories are original, their characters are adults, training use is authorized, and **the seven stories are mutually independent without shared characters, worlds or continuous plots**. Seven corresponding source story UUIDs were checked against **40 owner-delegated, content-accepted R52 cases**. The prior 21 bounded world-pair review tasks and decisions were source-pin replayed (**21/21 pairs, 126/126 source witnesses**), with zero proven common-world edges. Existing historical full-original 21-pair reviews reporting 87 full-source citations were documented earlier but **their original full 18-case payloads were not available for direct replay in this pass**.

The verified **scope-limited certificate** proves that all seven owner-attested story components have unique source UUIDs and **none of the five Train story UUIDs is among the two Validation story UUIDs**. This **does not** certify independent full semantic/alias-world audit or complete R45/R46 model exposure. Those formal gates remain separately BLOCKED; no false third-party signature has been supplied.

## Actual staged R53 data bytes, source-pinned but NOT admitted

Compiled directly from frozen original R52 visible histories, unchanged original target replies, and precisely SHA-pinned R27 no-character-card System prompt; only final Assistant has `loss=true`.

| Private stage payload | Rows | Byte length | SHA256 |
|---|---:|---:|---|
| Staged source-inclusive Train | 31 | 357331 | `f17fc33f566b5a1ddd424de2d26a032a812453255c76e0f5fa321fb0f3a9ecf9` |
| Staged source-inclusive Validation | 9 | 83543 | `83e3d1ab4cc955c4b5bba2afc63f355a227934a89203bcc058cfb922a093b01d` |
| Staged message-only Train (R46 `prepare_sft.py`-compatible) | 31 | 308291 | `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7` |
| Staged message-only Validation | 9 | 69938 | `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d` |

The names deliberately include `STAGED` and `NOT_ADMITTED`. **No official train.jsonl or validation.jsonl was released.** The earlier five excluded HOLD and the one additional targeted consent HOLD remain excluded. R50 stays sealed. All 31 staged Train contain **14 exact R45 Train targets and 9 exact R45 Validation targets**. Validation has **0 exact R45 target repeats**, but one Validation story UUID was in R45 Train, so it is not a genuinely unseen-world evaluation.

## Executable release gate

A source-bound release checker verified the real staged payload and returned **exit 2 / BLOCKED** in the actual current evidence state. **10/10 fail-closed negative tests passed** (tampered source/target SHA, candidate duplicates, world crossing, changed labels, forged admission, missing independent world cert and runtime logs).

The gate will only issue the formal Trainer `train.jsonl` and `validation.jsonl` when all of these exist and are checked together:

1. **Separate independently signed source-world/alias certificate**, not merely the owner's authorship declaration.
2. **Seven-story training rights/provenance evidence** that is not just relabeling the owner's statement.
3. **R45/R46 actual runtime input/exposure reconciliation** from original training artifacts and logs.
4. **Real exact Qwen3.8-27B revision tokenizer/ms-swift 4.5.3 full 31+9 collator and last-round label-mask audit**, with compiled input SHA and unaltered audit logs.
5. **Separately recorded explicit dataset-release approval** bound to the frozen staged data SHA. GPU authorization remains a separate future action.

No such runtime audit was run here; required `swift`/`transformers` runtime was not present, and no CPU cloud or paid GPU job was launched.

## Private package and reproducibility

Conversation-only `StoryForge_R52_R53_WORLD7_STAGED31_9_RELEASE_GATE_PRIVATE_20261021.zip`:

- SHA256: `9b669ac7110649bfe1e21ddd8285b0f50b1a216d67cc098fef39dc739b33dd83`
- 19 validated ZIP members: the *actual private staged* 31/9 source and message-only inputs, owner-scoped world certificate, parent source hashes, safety receipts, standard-library code to rebuild/verify, 10 negative tests and optional CPU-only local preflight instructions.
- Source and compiled stage files contain confidential narrative text and candidate identities, are **not** to be uploaded to ordinary Git. This Git report is aggregate/hash-only.

**Bottom line:** source-pinned owner-world structure and all 40 model-input byte strings are ready; independent semantic certification, source rights verification, historic input reconciliation, **actual** Qwen/ms-swift masking and explicit dataset release are **not done**. Formal Train/Val admission remains **0/0**, R50 unopened, and new GPU **not authorized**.

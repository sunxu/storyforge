# StoryForge R52 → R53 — 40-case conditional source/split lock (2026-10-21)

**State:** `R53_40_SOURCE_AND_SHAPE_REPLAY_PASS__DATA_ADMISSION_BLOCKED__NO_GPU`.

The project owner selected all 41 case candidates for final review, then explicitly delegated individual content review to the assistant. Source-pinned review decisions were **40 content-scope PASS, 1 consent-boundary HOLD**. The preceding five excluded cases remain held. These are delegated content judgments, **not owner handwritten signatures or released SFT rows**.

## Newly replayed original evidence

- Replayed all 41 original targets and 427 frozen model-visible history messages against SHA256 and Owner's delegated source-index citations (82/82).
- The **40** content-passed cases contain **415** frozen-visible history messages; the targeted HOLD stays excluded.
- Replayed seven Owner independence/adulthood/training-use declarations. Confirmed seven distinct story UUIDs.
- Crosschecked all **21** original bounded world-pair decision records and their task witnesses, including **126/126** bound source-message citations. Original review routes: 18 no link observed within bounded evidence, 3 insufficient evidence; no positive link. These older decisions remain historically unchanged. Owner attests seven worlds independent; there is **no independent final world-certificate signature**, so a semantic independence PASS is not asserted.
- Independently compared all 40 target hashes with original R45 frozen 49 Train / 15 Validation, not solely with an older risk queue.
- Verified the exact R27 449-byte synthetic no-card System Prompt SHA256 `5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83` against its original 117 rows. In-memory R53 shape check used precisely that System + frozen history with `loss=false` and the original final Assistant reply with `loss=true`, but this is **not** the actual Qwen/ms-swift tokenizer/collator check.
- The source-bound offline guard passed 12 deliberate in-memory tampering tests; it **creates no train.jsonl/validation.jsonl**.

## Frozen identity proposal only, **not** approved split

| Proposed partition | Cases | Story ranks | Exact R45 Train targets | Exact R45 Val targets |
| --- | ---: | --- | ---: | ---: |
| Train | **31** | 09, 10, 12, 14, 15 | **14** | **9** |
| Validation | **9** | 06, 13 | **0** | **0** |

Train and Validation are disjoint by current Owner-attested story UUID/component mapping. Proposed Validation has **one story UUID (rank 06) that occurred in historical R45 Train**; do not describe this validation as an untouched-world generalization test. R50 sealed heldout was not accessed.

Private manifest identity/member-pair SHA256, sorted by private candidate ID:
- Conditional Train member identity/target SHA: `42f3606ce11e8c4870b309b1cf21f856c47dfeb6808289e33e691be241a52a2a`
- Conditional Validation member identity/target SHA: `9ccce18b39eda985d763fdf5f1106ce2a047a6ccd35f05e862a4a505e6c8a920`
- All-40 deterministic private manifest SHA256: `cdf46f7ac988bd5f8bf519497fbe058a997e1440346d6d44e29b052d541812ac`.

## Private custody

Conversation-private artifact `R52_R53_40_CONDITIONAL_31_9_SOURCE_LOCK_PRIVATE_20261021.zip`, SHA256:
`afc8ec961a221c079901d9cf6929b16c86913babb16fd7c7fb4d801308a5a684`.

It contains a 40-row private ID/hash **proposal**, per-partition integrity report, safe receipt, offline source replay program and 12 mutation tests. No story narratives, actual compiled SFT JSONL, private candidate IDs or model inputs are checked into ordinary Git.

## Remaining real gates

1. Formal approval/certification of world components and publication of the Train/Val split at the required level of source assurance; Owner seven-story independence testimony already exists and must not be repeatedly solicited.
2. Admission decision for exactly those 40, accounting for source rights Owner attestation and targeted consent HOLD; avoid automatically converting older frozen `PENDING_NOT_APPROVED` source records.
3. Actual pinned Qwen/chat template + ms-swift collator/last-round-label-mask verification on final exact bytes. Current runtime has no `transformers` or `swift` installed; no paid CPU job was executed.
4. Explicit **separate** owner authorization for new paid GPU SFT (and budget/time limit). This step has not been requested or granted.

**Training admission Train=0, Val=0; model quality not promoted; R50 sealed.**
